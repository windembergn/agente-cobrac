#!/usr/bin/env python3
"""Copiloto — painel de numeros de WhatsApp (multi-slot) + vigia dos comandos.

Cada "slot" e' um numero. O painel deixa conectar quantos numeros quiser no
mesmo container, cada um com sua sessao, seu bridge e seus grupos.

  GET    /whatsapp                       pagina (basic auth = senha do painel)
  GET    /whatsapp/api/state             JSON com todos os slots
  POST   /whatsapp/api/slots             cria um slot   {label, mode}
  POST   /whatsapp/api/slots/<id>/pair   (re)inicia o pareamento
  DELETE /whatsapp/api/slots/<id>        remove o slot (desconecta o numero)
  DELETE /whatsapp/api/slots/<id>/groups/<jid>   tira o copiloto de um grupo
  GET    /whatsapp/qr.png?slot=<id>      PNG do QR daquele slot

  thread: le $DATA/whatsapp/requests/*.json, escritos pelo bridge quando
  alguem manda /main ou /sair num grupo, e reconcilia a configuracao.

Compat: /whatsapp/state e /whatsapp/qr.png sem parametro respondem pelo
slot 1, que e' como as versoes anteriores do tutorial funcionavam.
"""
import base64
import io
import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

sys.path.insert(0, "/opt/hermes")
sys.path.insert(0, "/opt/copiloto")

import copiloto_slots as S  # noqa: E402

PORT = int(os.environ.get("COPILOTO_QR_PORT", "8099"))
DASH_USER = os.environ.get("DASH_USER", "admin")
DASH_PASS = os.environ.get("DASH_PASS", "TroqueASenha2026")
MAX_SLOTS = int(os.environ.get("COPILOTO_MAX_SLOTS", "8"))

_auth_header = "Basic " + base64.b64encode(f"{DASH_USER}:{DASH_PASS}".encode()).decode()
_lock = threading.Lock()
_pairers = {}   # slot_id -> Pairer


def _log(msg):
    print("[qr] %s" % msg, flush=True)


# ------------------------------------------------------------- pareamento
def _bridge_dir():
    """Pasta do bridge a usar no pareamento.

    O volume ganha preferencia: e' la que o Hermes instala as dependencias
    e e' o bridge que o gateway roda de verdade (ja patchado pelo
    cont-init). A copia da imagem so entra em cena numa instalacao nova,
    antes de o volume ter sido populado.
    """
    vol = os.path.join(S.DATA, "scripts", "whatsapp-bridge")
    if os.path.exists(os.path.join(vol, "bridge.js")) and \
            os.path.isdir(os.path.join(vol, "node_modules")):
        return vol
    try:
        from gateway.platforms.whatsapp_common import resolve_whatsapp_bridge_dir
        img = str(resolve_whatsapp_bridge_dir())
        if os.path.exists(os.path.join(img, "bridge.js")):
            return img
    except Exception:
        pass
    return vol


def _ensure_deps(bridge_dir):
    """npm install quando faltam as dependencias do bridge.

    Instalacao nova: no primeiro boot o WhatsApp fica desligado (sem sessao
    nao ha o que conectar), entao o adapter nunca rodou e ninguem instalou
    o node_modules ainda. Sem isto o QR simplesmente nunca aparece.
    """
    if os.path.isdir(os.path.join(bridge_dir, "node_modules")):
        return
    from hermes_constants import find_node_executable, with_hermes_node_path
    npm = find_node_executable("npm")
    if not npm:
        raise RuntimeError("npm nao encontrado")
    _log("instalando dependencias do bridge em %s (primeira vez, pode demorar)" % bridge_dir)
    subprocess.run([npm, "install", "--silent"], cwd=bridge_dir,
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", timeout=int(os.environ.get(
                       "WHATSAPP_NPM_INSTALL_TIMEOUT", "300")),
                   env=with_hermes_node_path())
    if bridge_dir.startswith(S.DATA):
        S.fix_perms()
    _log("dependencias do bridge prontas")


class Pairer:
    """Pareia UM numero rodando o bridge em modo --pair-only.

    O bridge emite eventos JSON por linha (started / qr / connected / error),
    que e' exatamente o mesmo mecanismo que o painel nativo do Hermes usa —
    a diferenca e' que aqui o caminho da sessao e' escolhido por slot, e nao
    derivado do HERMES_HOME, que so serviria a um numero.
    """

    def __init__(self, slot):
        self.slot_id = slot["id"]
        self.session = S.session_path(slot)
        self.qr = None
        self.status = "starting"
        self.phone = None
        self.error = None
        self.proc = None
        self.started_at = 0.0
        self._stop = False

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self._stop = True
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
        except Exception:
            pass

    def _spawn(self):
        from hermes_constants import find_node_executable, with_hermes_node_path

        bridge_dir = _bridge_dir()
        script = os.path.join(bridge_dir, "bridge.js")
        node = find_node_executable("node")
        if not node or not os.path.exists(script):
            raise RuntimeError("bridge/node nao encontrados")
        _ensure_deps(bridge_dir)

        os.makedirs(self.session, exist_ok=True)
        # O painel roda como root. Se o node rodasse como root tambem, a
        # sessao inteira nasceria root: e o gateway (uid 1000) nao
        # conseguiria abrir — era o bug que derrubava o gateway apos o
        # primeiro pareamento. Criamos a pasta ja com o dono certo e
        # largamos privilegio no filho.
        try:
            os.chown(self.session, S.HERMES_UID, S.HERMES_GID)
            os.chown(os.path.dirname(self.session), S.HERMES_UID, S.HERMES_GID)
        except Exception:
            pass

        env = with_hermes_node_path()
        env["WHATSAPP_MODE"] = os.environ.get("WHATSAPP_MODE", "bot")
        env["WHATSAPP_DM_POLICY"] = "pairing"
        env["HOME"] = S.DATA

        def _drop():
            try:
                os.setgid(S.HERMES_GID)
                os.setuid(S.HERMES_UID)
            except Exception:
                pass

        return subprocess.Popen(
            [node, script, "--pair-only", "--pair-json", "--session", self.session],
            cwd=str(bridge_dir), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
            start_new_session=True, env=env, preexec_fn=_drop,
        )

    def _run(self):
        try:
            self.proc = self._spawn()
        except Exception as e:
            with _lock:
                self.status, self.error = "error", str(e)
            _log("slot %s: falha ao iniciar pareamento: %s" % (self.slot_id, e))
            return

        for line in self.proc.stdout:
            if self._stop:
                break
            line = (line or "").strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            kind = ev.get("event")
            if kind == "qr":
                with _lock:
                    self.qr, self.status = ev.get("qr"), "waiting"
            elif kind == "connected":
                user = ev.get("user") or {}
                with _lock:
                    self.status, self.qr = "connected", None
                    self.phone = str(user.get("id") or "").split("@")[0].split(":")[0]
                self._on_connected()
                break
            elif kind == "error":
                with _lock:
                    self.status, self.error = "error", str(ev.get("error") or "erro")
                break

        self.stop()

    def _on_connected(self):
        """Sessao gravada: liga o slot e recarrega o gateway certo."""
        _log("slot %s pareado (%s)" % (self.slot_id, self.phone))
        try:
            cfg = S.load_or_migrate()
            slot = S.find_slot(cfg, self.slot_id)
            if slot and S.slot_num(slot) == 1 and slot.get("mode") != "isolated":
                # O plugin oficial do WhatsApp so sobe com esta env; os
                # slots extras sao ligados pelo config.yaml.
                _enable_whatsapp_env()
            S.reconcile(cfg)
            S.fix_perms()
            if slot and slot.get("mode") == "isolated":
                S.restart_gateway(profile=slot["id"])
            else:
                S.restart_gateway()
        except Exception as e:
            _log("pos-pareamento do slot %s falhou: %s" % (self.slot_id, e))


def _enable_whatsapp_env():
    try:
        with open("/run/s6/container_environment/WHATSAPP_ENABLED", "w") as f:
            f.write("true")
    except Exception:
        pass
    try:
        from hermes_cli.gateway import save_env_value
        save_env_value("WHATSAPP_ENABLED", "true")
        save_env_value("WHATSAPP_MODE", os.environ.get("WHATSAPP_MODE", "bot"))
    except Exception:
        pass


PAIR_RETRY_SECONDS = 20


def _pairer_for(slot, restart=False):
    """Devolve o pareador do slot, criando/reiniciando quando faz sentido.

    O painel consulta o estado de poucos em poucos segundos e um pareamento
    que falha volta como 'error'. Sem o intervalo minimo abaixo, cada
    consulta abriria um processo node novo — dezenas deles em um minuto.
    """
    now = time.monotonic()
    with _lock:
        p = _pairers.get(slot["id"])
    if p and not restart:
        if p.status in ("connected", "error") and not S.is_paired(slot):
            if now - getattr(p, "started_at", 0) < PAIR_RETRY_SECONDS:
                return p
            restart = True
        else:
            return p
    if p:
        p.stop()
    p = Pairer(slot)
    p.started_at = now
    with _lock:
        _pairers[slot["id"]] = p
    p.start()
    return p


def _qr_png(payload):
    import qrcode
    img = qrcode.make(payload, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------- watcher
def _handle_request(path):
    """Um pedido /main ou /sair vindo de algum bridge."""
    try:
        with open(path, encoding="utf-8") as f:
            req = json.load(f)
    except Exception:
        return
    finally:
        try:
            os.remove(path)
        except Exception:
            pass

    action = req.get("action") or "add"
    chat_id = str(req.get("chat_id") or "").strip()
    if not chat_id:
        return

    cfg = S.load_or_migrate()
    slot = S.slot_by_session(cfg, req.get("session"))
    if not slot:
        # Bridge de um slot que ja nao existe, ou pedido de uma versao
        # antiga do bridge (sem o campo session): cai no slot 1.
        slot = cfg["slots"][0] if cfg["slots"] else None
    if not slot:
        return

    if action == "remove":
        ok, _ = S.remove_group(cfg, slot["id"], chat_id)
    else:
        ok, _ = S.add_group(cfg, slot["id"], chat_id, req.get("name") or "")
    if not ok:
        return
    S.save(cfg)
    S.reconcile(cfg)
    S.fix_perms()
    _log("slot %s: grupo %s -> %s" % (slot["id"], action, chat_id))
    if slot.get("mode") == "isolated":
        S.restart_gateway(profile=slot["id"])
    else:
        S.restart_gateway()


def _watch_requests():
    legacy = os.path.join(S.WA_DIR, "main_group.request")
    while True:
        try:
            os.makedirs(S.REQ_DIR, exist_ok=True)
            for name in sorted(os.listdir(S.REQ_DIR)):
                if name.endswith(".json"):
                    _handle_request(os.path.join(S.REQ_DIR, name))
            # Bridge da versao anterior (durante um update, antes do
            # sincronismo do cont-init) ainda escreve no caminho antigo.
            if os.path.exists(legacy):
                raw = open(legacy, encoding="utf-8").read().strip()
                os.remove(legacy)
                data = json.loads(raw) if raw.startswith("{") else {"chat_id": raw}
                cfg = S.load_or_migrate()
                if cfg["slots"]:
                    S.add_group(cfg, cfg["slots"][0]["id"],
                                str(data.get("chat_id") or ""), data.get("name") or "")
                    S.save(cfg)
                    S.reconcile(cfg)
                    S.fix_perms()
                    S.restart_gateway()
        except Exception:
            pass
        time.sleep(2)


# --------------------------------------------------------------- estado
def _state():
    cfg = S.load_or_migrate()
    out = []
    for slot in cfg["slots"]:
        paired = S.is_paired(slot)
        with _lock:
            p = _pairers.get(slot["id"])
        status = "connected" if paired else (p.status if p else "idle")
        out.append({
            "id": slot["id"],
            "label": slot.get("label") or slot["id"],
            "mode": slot.get("mode") or "shared",
            "port": S.bridge_port(slot),
            "paired": paired,
            "phone": S.phone_of(slot) or (p.phone if p else None),
            "status": status,
            "error": (p.error if p else None),
            "groups": slot.get("groups") or [],
            "home": slot.get("home"),
        })
    return {"slots": out, "max": MAX_SLOTS}


def _create_slot(body):
    cfg = S.load_or_migrate()
    if len(cfg["slots"]) >= MAX_SLOTS:
        return None, "limite de %d números atingido" % MAX_SLOTS
    mode = "isolated" if str(body.get("mode")) == "isolated" else "shared"
    sid = S.next_id(cfg)
    label = (body.get("label") or "").strip() or ("Zap %s" % S.slot_num({"id": sid}))
    slot = {"id": sid, "label": label, "mode": mode,
            "port": S.BASE_PORT + S.slot_num({"id": sid}) - 1,
            "groups": [], "home": None}
    cfg["slots"].append(slot)
    S.save(cfg)
    S.reconcile(cfg)
    S.fix_perms()
    _log("slot %s criado (%s, %s)" % (sid, label, mode))
    return slot, None


def _delete_slot(slot_id):
    cfg = S.load_or_migrate()
    slot = S.find_slot(cfg, slot_id)
    if not slot:
        return "número não encontrado"
    if S.slot_num(slot) == 1:
        return "o número principal não pode ser removido"
    with _lock:
        p = _pairers.pop(slot_id, None)
    if p:
        p.stop()
    import shutil
    shutil.rmtree(S.session_path(slot), ignore_errors=True)
    cfg["slots"] = [s for s in cfg["slots"] if s["id"] != slot_id]
    S.save(cfg)
    S.reconcile(cfg)
    S.fix_perms()
    S.restart_gateway()
    _log("slot %s removido" % slot_id)
    return None


def _delete_group(slot_id, jid):
    cfg = S.load_or_migrate()
    ok, msg = S.remove_group(cfg, slot_id, jid)
    if not ok:
        return msg
    S.save(cfg)
    S.reconcile(cfg)
    S.fix_perms()
    slot = S.find_slot(cfg, slot_id)
    S.restart_gateway(profile=slot["id"] if slot and slot.get("mode") == "isolated" else None)
    return None


PAGE = r"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WhatsApp — Copiloto</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#0A1322;color:#EAF1F8;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;padding:26px 14px 60px}
.wrap{max-width:720px;margin:0 auto}
h1{font-size:23px;margin:0 0 4px}
.sub{color:#94A8BE;font-size:14px;margin:0 0 22px}
.card{background:#13243A;border:1px solid #23374F;border-radius:18px;padding:20px;margin-bottom:16px}
.head{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.name{font-weight:600;font-size:17px}
.tag{font-size:11px;padding:3px 9px;border-radius:999px;border:1px solid #2E4560;color:#94A8BE}
.tag.on{background:#0E3A32;border-color:#1C6B5B;color:#4FE0CB}
.tag.off{background:#3A2A16;border-color:#7A5A24;color:#E9B872}
.phone{color:#94A8BE;font-size:13px;margin-top:3px}
.qrbox{background:#fff;border-radius:14px;padding:12px;display:inline-block;margin-top:14px}
.qrbox img{width:210px;height:210px;display:block}
.hint{color:#94A8BE;font-size:13px;margin-top:10px;line-height:1.5}
.groups{margin-top:14px;border-top:1px solid #23374F;padding-top:12px}
.glabel{font-size:12px;color:#62768D;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
.g{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:7px 0;font-size:14px;border-bottom:1px solid #1B2C43}
.g:last-child{border-bottom:0}
.g .gn{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.g .home{font-size:10px;color:#4FE0CB;border:1px solid #1C6B5B;border-radius:999px;padding:2px 7px;margin-left:6px}
.empty{color:#62768D;font-size:13px;font-style:italic}
button{font:inherit;cursor:pointer;border-radius:10px;border:1px solid #2E4560;background:#1B2C43;color:#EAF1F8;padding:8px 14px}
button:hover{border-color:#3E5A7C}
button.x{padding:4px 9px;font-size:12px;color:#94A8BE;background:transparent;border-color:#2E4560}
button.x:hover{color:#FF8A8A;border-color:#6B2C2C}
button.primary{background:#1C6B5B;border-color:#1C6B5B;color:#fff;font-weight:600}
button.primary:hover{background:#22806D}
.add{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:6px}
input,select{font:inherit;background:#0E1B2D;color:#EAF1F8;border:1px solid #2E4560;border-radius:10px;padding:9px 11px}
input{flex:1;min-width:170px}
.foot{color:#62768D;font-size:12px;margin-top:18px;line-height:1.6}
code{background:#0E1B2D;border:1px solid #23374F;border-radius:6px;padding:1px 6px;font-size:13px}
.spin{display:inline-block;width:8px;height:8px;border-radius:50%;background:#E9B872;margin-right:6px;animation:p 1.2s infinite}
@keyframes p{50%{opacity:.3}}
</style></head><body><div class="wrap">
<h1>Números do WhatsApp</h1>
<p class="sub">Conecte um ou mais números. Cada número atende os grupos que você ativar nele.</p>
<div id="slots"></div>
<div class="card">
  <div class="glabel">Adicionar número</div>
  <div class="add">
    <input id="lbl" placeholder="Nome (ex: Zap da clínica)" maxlength="40">
    <select id="mode">
      <option value="shared">Mesmo copiloto (memória compartilhada)</option>
      <option value="isolated">Copiloto separado (memória própria)</option>
    </select>
    <button class="primary" onclick="addSlot()">Adicionar</button>
  </div>
  <div class="hint"><b>Mesmo copiloto:</b> o número é mais uma entrada do seu copiloto — ele lembra de tudo junto.<br>
  <b>Copiloto separado:</b> um assistente independente, com memória e histórico próprios.</div>
</div>
<div class="foot">
No grupo do WhatsApp: <code>/main</code> ativa o copiloto ali · <code>/sair</code> desativa · <code>/grupos</code> lista os grupos daquele número.
</div>
</div>
<script>
let busy=false;
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function slotCard(s){
  const on=s.paired;
  const tag=on?'<span class="tag on">conectado</span>':'<span class="tag off">aguardando</span>';
  const mode='<span class="tag">'+(s.mode==='isolated'?'copiloto separado':'mesmo copiloto')+'</span>';
  let qr='';
  if(!on){
    qr='<div class="qrbox"><img src="/whatsapp/qr.png?slot='+s.id+'&t='+Date.now()+'" alt="gerando..."></div>'
      +'<div class="hint"><span class="spin"></span>No WhatsApp deste número: <b>Aparelhos conectados</b> → <b>Conectar um aparelho</b> e aponte para o código.</div>';
  }
  let gs='<div class="empty">Nenhum grupo ainda. Mande <b>/main</b> no grupo onde ele deve responder.</div>';
  if(s.groups.length){
    gs=s.groups.map(g=>'<div class="g"><span class="gn">'+esc(g.name||g.id)
      +(g.id===s.home?'<span class="home">principal</span>':'')+'</span>'
      +'<button class="x" onclick="delGroup(\''+s.id+'\',\''+encodeURIComponent(g.id)+'\')">remover</button></div>').join('');
  }
  const del=s.id==='wa1'?'':'<button class="x" onclick="delSlot(\''+s.id+'\',\''+esc(s.label)+'\')">remover número</button>';
  return '<div class="card"><div class="head"><span class="name">'+esc(s.label)+'</span>'+tag+mode
    +'<span style="flex:1"></span>'+del+'</div>'
    +(s.phone?'<div class="phone">+'+esc(s.phone)+'</div>':'')
    +qr
    +'<div class="groups"><div class="glabel">Grupos ativos ('+s.groups.length+')</div>'+gs+'</div></div>';
}
async function tick(){
  if(!busy){
    try{
      const r=await fetch('/whatsapp/api/state',{cache:'no-store'});
      const st=await r.json();
      document.getElementById('slots').innerHTML=st.slots.map(slotCard).join('');
    }catch(e){}
  }
  setTimeout(tick,4000);
}
async function addSlot(){
  busy=true;
  const label=document.getElementById('lbl').value;
  const mode=document.getElementById('mode').value;
  try{
    const r=await fetch('/whatsapp/api/slots',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({label,mode})});
    const j=await r.json();
    if(j.error) alert(j.error); else document.getElementById('lbl').value='';
  }catch(e){alert('falhou');}
  busy=false;
}
async function delSlot(id,label){
  if(!confirm('Remover "'+label+'"?\n\nO número será desconectado do copiloto.')) return;
  busy=true;
  try{const r=await fetch('/whatsapp/api/slots/'+id,{method:'DELETE'});const j=await r.json();if(j.error)alert(j.error);}catch(e){}
  busy=false;
}
async function delGroup(id,jid){
  busy=true;
  try{const r=await fetch('/whatsapp/api/slots/'+id+'/groups/'+jid,{method:'DELETE'});const j=await r.json();if(j.error)alert(j.error);}catch(e){}
  busy=false;
}
tick();
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _auth_ok(self):
        return self.headers.get("Authorization", "") == _auth_header

    def _deny(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="Copiloto"')
        self.end_headers()

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return {}

    def _guard(self):
        if not self.path.startswith("/whatsapp"):
            self.send_response(404); self.end_headers(); return False
        if not self._auth_ok():
            self._deny(); return False
        return True

    # ------------------------------------------------------------- GET
    def do_GET(self):
        if not self._guard():
            return
        u = urlparse(self.path)
        path, q = u.path, parse_qs(u.query)

        if path in ("/whatsapp", "/whatsapp/"):
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body); return

        if path == "/whatsapp/api/state":
            st = _state()
            # Abrir o painel ja comeca o pareamento de quem falta — e' o que
            # torna o primeiro acesso "abriu e leu o QR", sem clique extra.
            cfg = S.load_or_migrate()
            for slot in cfg["slots"]:
                if not S.is_paired(slot):
                    _pairer_for(slot)
            return self._json(st)

        if path == "/whatsapp/state":  # compat com o tutorial antigo
            st = _state()["slots"]
            s0 = st[0] if st else {}
            return self._json({"connected": bool(s0.get("paired")),
                               "status": s0.get("status") or "starting"})

        if path == "/whatsapp/qr.png":
            cfg = S.load_or_migrate()
            sid = (q.get("slot") or [None])[0]
            slot = S.find_slot(cfg, sid) if sid else (cfg["slots"][0] if cfg["slots"] else None)
            if not slot or S.is_paired(slot):
                self.send_response(204); self.end_headers(); return
            p = _pairer_for(slot)
            with _lock:
                qr = p.qr
            if not qr:
                self.send_response(204); self.end_headers(); return
            try:
                png = _qr_png(qr)
            except Exception:
                self.send_response(204); self.end_headers(); return
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(png)))
            self.end_headers(); self.wfile.write(png); return

        self.send_response(404); self.end_headers()

    # ------------------------------------------------------------ POST
    def do_POST(self):
        if not self._guard():
            return
        path = urlparse(self.path).path
        if path == "/whatsapp/api/slots":
            slot, err = _create_slot(self._body())
            return self._json({"error": err} if err else {"ok": True, "slot": slot["id"]})
        parts = path.strip("/").split("/")
        if len(parts) == 5 and parts[:3] == ["whatsapp", "api", "slots"] and parts[4] == "pair":
            cfg = S.load_or_migrate()
            slot = S.find_slot(cfg, parts[3])
            if not slot:
                return self._json({"error": "número não encontrado"}, 404)
            _pairer_for(slot, restart=True)
            return self._json({"ok": True})
        self.send_response(404); self.end_headers()

    # ---------------------------------------------------------- DELETE
    def do_DELETE(self):
        if not self._guard():
            return
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) == 4 and parts[:3] == ["whatsapp", "api", "slots"]:
            err = _delete_slot(parts[3])
            return self._json({"error": err} if err else {"ok": True})
        if len(parts) == 6 and parts[:3] == ["whatsapp", "api", "slots"] and parts[4] == "groups":
            err = _delete_group(parts[3], unquote(parts[5]))
            return self._json({"error": err} if err else {"ok": True})
        self.send_response(404); self.end_headers()


if __name__ == "__main__":
    try:
        S.reconcile()
    except Exception as e:
        _log("reconcile inicial falhou: %s" % e)
    threading.Thread(target=_watch_requests, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
