#!/usr/bin/env python3
"""Copiloto — servidor de QR do WhatsApp + vigia do comando /main.

Usa o onboarding do Hermes IN-PROCESS (mesma abordagem do get_wa_qr.py),
sem depender de cookie/HTTP auth do painel.

- GET /whatsapp        -> pagina (basic auth = senha do painel) com o QR
- GET /whatsapp/qr.png -> PNG do QR atual
- GET /whatsapp/state  -> JSON { connected, status }
- thread: quando o bridge grava /opt/data/whatsapp/main_group.request,
  grava o JID em group_allow_from do config.yaml e reinicia o gateway.
"""
import asyncio
import base64
import io
import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("COPILOTO_QR_PORT", "8099"))
DASH_USER = os.environ.get("DASH_USER", "admin")
DASH_PASS = os.environ.get("DASH_PASS", "TroqueASenha2026")
CFG = "/opt/data/config.yaml"
REQ = "/opt/data/whatsapp/main_group.request"

_auth_header = "Basic " + base64.b64encode(f"{DASH_USER}:{DASH_PASS}".encode()).decode()
_state = {"qr": None, "status": "starting", "connected": False}
_lock = threading.Lock()


# ---------------- onboarding in-process (async) ----------------
def _onboarding_loop():
    try:
        from hermes_cli import web_server as ws
    except Exception as e:
        with _lock:
            _state["status"] = "erro_import"
        return

    async def manager():
        pid = None
        while True:
            try:
                with _lock:
                    if _state["connected"]:
                        await asyncio.sleep(5)
                        continue
                if pid is None:
                    res = await ws.start_whatsapp_onboarding(
                        ws.WhatsAppOnboardingStart(mode="bot", allowed_users="", profile=None))
                    pid = res.get("pairing_id")
                    with _lock:
                        _state["qr"] = res.get("qr_payload")
                        _state["status"] = res.get("status") or "waiting"
                else:
                    cur = await ws.get_whatsapp_onboarding_status(pid)
                    st = str(cur.get("status") or "")
                    with _lock:
                        if cur.get("qr_payload"):
                            _state["qr"] = cur.get("qr_payload")
                        _state["status"] = st or _state["status"]
                    if st == "connected":
                        try:
                            await ws.apply_whatsapp_onboarding(
                                pid, ws.WhatsAppOnboardingApply(mode="bot", allowed_users=None, profile=None))
                        except Exception:
                            pass
                        _enable_whatsapp()
                        _restart_gateway()
                        with _lock:
                            _state["connected"] = True
                            _state["status"] = "connected"
                            _state["qr"] = None
                    elif st in ("expired", "error", "failed", "timeout") or cur.get("error"):
                        pid = None
            except Exception:
                pid = None
            await asyncio.sleep(2)

    try:
        asyncio.run(manager())
    except Exception:
        pass


def _restart_gateway():
    for cmd in ("/command/s6-svc -r /run/service/gateway-default",
                "s6-svc -r /run/service/gateway-default"):
        try:
            if subprocess.call(cmd.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0:
                return
        except Exception:
            continue


def _enable_whatsapp():
    try:
        with open("/run/s6/container_environment/WHATSAPP_ENABLED", "w") as f:
            f.write("true")
    except Exception:
        pass


def _qr_png(payload):
    import qrcode
    img = qrcode.make(payload, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------- /main watcher ----------------
def _set_main_group(jid):
    jid = jid.strip()
    if not jid:
        return
    try:
        import yaml
        with open(CFG) as f:
            cfg = yaml.safe_load(f) or {}
        cfg.setdefault("platforms", {}).setdefault("whatsapp", {})
        cfg["platforms"]["whatsapp"]["group_policy"] = "allowlist"
        cfg["platforms"]["whatsapp"]["dm_policy"] = "disabled"
        cfg["platforms"]["whatsapp"]["group_allow_from"] = [jid]
        with open(CFG, "w") as f:
            yaml.safe_dump(cfg, f, allow_unicode=True, sort_keys=False)
    except Exception:
        try:
            import re
            txt = open(CFG).read()
            new = f'group_allow_from: ["{jid}"]'
            if re.search(r"group_allow_from:\s*\[.*?\]", txt):
                txt = re.sub(r"group_allow_from:\s*\[.*?\]", new, txt, count=1)
            else:
                txt += f"\n{new}\n"
            open(CFG, "w").write(txt)
        except Exception:
            return
    try:
        os.system("chown 1000:1000 " + CFG + " 2>/dev/null")
    except Exception:
        pass
    _restart_gateway()


def _watch_main():
    while True:
        try:
            if os.path.exists(REQ):
                jid = open(REQ).read().strip()
                try:
                    os.remove(REQ)
                except Exception:
                    pass
                if jid:
                    _set_main_group(jid)
        except Exception:
            pass
        time.sleep(3)


PAGE = """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Conectar WhatsApp — Copiloto</title>
<style>
body{margin:0;background:#0A1322;color:#EAF1F8;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
display:flex;min-height:100vh;align-items:center;justify-content:center;text-align:center}
.card{background:#13243A;border:1px solid #23374F;border-radius:20px;padding:34px 28px;max-width:380px;width:90%}
h1{font-size:22px;margin:0 0 6px}p{color:#94A8BE;font-size:15px;margin:6px 0 18px}
.qrbox{background:#fff;border-radius:14px;padding:14px;display:inline-block;min-height:230px;min-width:230px}
img{width:230px;height:230px;display:block}
.ok{font-size:52px;margin:10px 0}.okmsg{color:#4FE0CB;font-weight:600;font-size:20px}
.small{color:#62768D;font-size:12px;margin-top:14px}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#E9B872;margin-right:6px;animation:p 1.2s infinite}
@keyframes p{50%{opacity:.3}}
</style></head><body>
<div class="card" id="card">
  <h1>Conectar o WhatsApp</h1>
  <p><span class="dot"></span>No WhatsApp do número do copiloto → <b>Aparelhos conectados</b> → <b>Conectar um aparelho</b> e aponte para o código.</p>
  <div class="qrbox"><img id="qr" src="/whatsapp/qr.png" alt="Gerando código…" onerror="this.alt='Gerando código… aguarde'"></div>
  <div class="small" id="st">Gerando código…</div>
</div>
<script>
function refreshImg(){document.getElementById('qr').src='/whatsapp/qr.png?t='+Date.now();}
async function tick(){
  try{
    const r=await fetch('/whatsapp/state',{cache:'no-store'});const s=await r.json();
    if(s.connected){
      document.getElementById('card').innerHTML='<div class="ok">✅</div><div class="okmsg">Conectado com sucesso!</div><p>Pode fechar esta página. Agora envie <b>/main</b> no grupo onde o copiloto deve responder.</p>';
      return;
    }
    document.getElementById('st').textContent = s.status==='waiting' ? 'Aguardando leitura do código…' : 'Gerando código…';
    if(s.status==='waiting') refreshImg();
  }catch(e){}
  setTimeout(tick,3000);
}
setInterval(refreshImg,18000);
setTimeout(refreshImg,2500);
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

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if not path.startswith("/whatsapp"):
            self.send_response(404); self.end_headers(); return
        if not self._auth_ok():
            return self._deny()
        if path in ("/whatsapp", "/whatsapp/"):
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers(); self.wfile.write(body); return
        if path == "/whatsapp/state":
            with _lock:
                out = {"connected": _state["connected"], "status": _state["status"]}
            body = json.dumps(out).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if path == "/whatsapp/qr.png":
            with _lock:
                qr = None if _state["connected"] else _state["qr"]
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


if __name__ == "__main__":
    threading.Thread(target=_watch_main, daemon=True).start()
    threading.Thread(target=_onboarding_loop, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
