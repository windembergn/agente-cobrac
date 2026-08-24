#!/usr/bin/env python3
"""Copiloto — mini-CRM (funil comercial ate cirurgia).

Kanban simples: Novo Lead -> Atendimento -> Agendou -> Compareceu -> Exames ->
Cirurgia -> Finalizado. Arrastar um card pra um status dispara (se a mensagem
daquele status estiver ligada) um WhatsApp automatico pro paciente, via
POST http://127.0.0.1:3000/send do bridge do proprio Hermes.

  GET    /crm                          pagina (basic auth = senha do painel)
  GET    /crm/api/cards                lista todos os cards
  POST   /crm/api/cards                cria um card {name, phone, status?}
  PATCH  /crm/api/cards/<id>           atualiza {name?, phone?, status?, notes?}
  DELETE /crm/api/cards/<id>           remove um card
  GET    /crm/api/templates            lista as mensagens por status
  PUT    /crm/api/templates/<status>   atualiza {message?, enabled?}

Lead automatico: uma thread le $DATA/crm/inbound_pings/*.json (escritos pelo
bridge do WhatsApp — patch "Copiloto CRM lead ping" em patch-bridge.py — para
TODO contato direto que manda mensagem, mesmo quando o dm_policy do agente
bloqueia a resposta). Se o telefone ainda nao tem card, cria um em "Novo Lead".

Sem dependencia externa: so biblioteca padrao do Python (como o qr_server.py).
"""
import base64
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import yaml

PORT = int(os.environ.get("COPILOTO_CRM_PORT", "8101"))
DASH_USER = os.environ.get("DASH_USER", "admin")
DASH_PASS = os.environ.get("DASH_PASS", "TroqueASenha2026")
DATA_DIR = os.environ.get("COPILOTO_DATA_DIR", "/opt/data")
CRM_DIR = os.path.join(DATA_DIR, "crm")
DB_PATH = os.path.join(CRM_DIR, "crm.db")
PINGS_DIR = os.path.join(CRM_DIR, "inbound_pings")
BRIDGE_SEND_URL = os.environ.get("COPILOTO_BRIDGE_SEND_URL", "http://127.0.0.1:3000/send")
BRIDGE_SEND_MEDIA_URL = os.environ.get("COPILOTO_BRIDGE_SEND_MEDIA_URL", "http://127.0.0.1:3000/send-media")
SITES_DIR = os.path.join(DATA_DIR, "sites")
BACKUPS_DIR = os.path.join(DATA_DIR, "copiloto-backups")
CONFIG_PATH = os.path.join(DATA_DIR, "config.yaml")
COPILOTO_DOMINIO = os.environ.get("COPILOTO_DOMINIO", "")
CHROMIUM_PATH = os.environ.get("AGENT_BROWSER_EXECUTABLE_PATH", "/usr/bin/chromium")

os.makedirs(CRM_DIR, exist_ok=True)
os.makedirs(PINGS_DIR, exist_ok=True)

_auth_header = "Basic " + base64.b64encode(f"{DASH_USER}:{DASH_PASS}".encode()).decode()

STATUSES = [
    ("novo_lead", "Novo Lead"),
    ("atendimento", "Atendimento"),
    ("agendou", "Agendou"),
    ("compareceu", "Compareceu"),
    ("exames", "Exames"),
    ("cirurgia", "Cirurgia"),
    ("finalizado", "Finalizado"),
]
STATUS_KEYS = [s[0] for s in STATUSES]

DEFAULT_TEMPLATES = {
    "novo_lead": ("", 0),
    "atendimento": (
        "Oi {{nome}}! Recebemos seu contato e já estamos com você. Qualquer dúvida, é só chamar por aqui.",
        1,
    ),
    "agendou": (
        "Prontinho, {{nome}}! Sua consulta está agendada. Qualquer imprevisto, nos avise por aqui.",
        1,
    ),
    "compareceu": (
        "Foi um prazer te atender hoje, {{nome}}! Qualquer dúvida depois da consulta, é só chamar.",
        1,
    ),
    "exames": (
        "Oi {{nome}}, estamos com seus exames em andamento. Assim que sair o resultado, te avisamos por aqui.",
        1,
    ),
    "cirurgia": (
        "Sua cirurgia está agendada, {{nome}}. Em breve enviamos as orientações de preparo.",
        1,
    ),
    "finalizado": (
        "{{nome}}, seu tratamento com a gente foi concluído! Se precisar de algo, estamos por aqui. 🙏",
        1,
    ),
}

_lock = threading.Lock()


def _db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init_db():
    with _lock, _db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'novo_lead',
                notes TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS templates (
                status TEXT PRIMARY KEY,
                message TEXT NOT NULL DEFAULT '',
                enabled INTEGER NOT NULL DEFAULT 1
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS message_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                sent_at INTEGER NOT NULL,
                success INTEGER NOT NULL,
                error TEXT
            )"""
        )
        for status, (message, enabled) in DEFAULT_TEMPLATES.items():
            conn.execute(
                "INSERT OR IGNORE INTO templates (status, message, enabled) VALUES (?, ?, ?)",
                (status, message, enabled),
            )
        conn.commit()


def _row_to_card(r):
    return {
        "id": r["id"],
        "name": r["name"],
        "phone": r["phone"],
        "status": r["status"],
        "notes": r["notes"],
        "created_at": r["created_at"],
        "updated_at": r["updated_at"],
    }


def _norm_phone(p):
    return re.sub(r"\D", "", p or "")


def _send_whatsapp(phone, text):
    """Chama o /send do bridge do proprio Hermes (so localhost, mesmo container)."""
    chat_id = f"{_norm_phone(phone)}@s.whatsapp.net"
    body = json.dumps({"chatId": chat_id, "message": text}).encode()
    req = urllib.request.Request(
        BRIDGE_SEND_URL, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read() or b"{}")
            return bool(data.get("success")), None
    except Exception as e:
        return False, str(e)


def _fire_status_message(card_id, name, phone, status):
    with _lock, _db() as conn:
        row = conn.execute("SELECT message, enabled FROM templates WHERE status=?", (status,)).fetchone()
    if not row or not row["enabled"] or not (row["message"] or "").strip():
        return
    text = row["message"].replace("{{nome}}", name or "").replace("{nome}", name or "")
    ok, err = _send_whatsapp(phone, text)
    with _lock, _db() as conn:
        conn.execute(
            "INSERT INTO message_log (card_id, status, sent_at, success, error) VALUES (?, ?, ?, ?, ?)",
            (card_id, status, int(time.time()), 1 if ok else 0, err),
        )
        conn.commit()


def _intake_loop():
    """Thread de fundo: le os pings de lead que o bridge do WhatsApp escreve
    para TODO contato direto que manda mensagem (mesmo sem o agente responder),
    e cria um card em Novo Lead se o telefone ainda nao existe no CRM."""
    while True:
        try:
            for fname in sorted(os.listdir(PINGS_DIR)):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(PINGS_DIR, fname)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        ping = json.load(f)
                except Exception:
                    os.unlink(fpath)
                    continue
                phone = _norm_phone(ping.get("phone", ""))
                name = (ping.get("push_name") or "").strip() or phone or "Lead sem nome"
                if phone:
                    with _lock, _db() as conn:
                        existing = conn.execute(
                            "SELECT id FROM cards WHERE phone=?", (phone,)
                        ).fetchone()
                        if not existing:
                            now = int(time.time())
                            conn.execute(
                                "INSERT INTO cards (name, phone, status, notes, created_at, updated_at) "
                                "VALUES (?, ?, 'novo_lead', '', ?, ?)",
                                (name, phone, now, now),
                            )
                            conn.commit()
                os.unlink(fpath)
        except Exception:
            pass
        time.sleep(3)


# ============================================================ DOCUMENTOS


def _safe_site_name(nome):
    """So letras/numeros/hifen — mesmo padrao de nome que a habilidade publicar-site usa."""
    if not nome or not re.match(r"^[a-z0-9-]+$", nome):
        return None
    pasta = os.path.join(SITES_DIR, nome)
    # Nunca deixa escapar de $DATA/sites nem mexer no _kit (e' do sistema, nao e' documento).
    if nome == "_kit" or not os.path.abspath(pasta).startswith(os.path.abspath(SITES_DIR) + os.sep):
        return None
    return pasta


def _list_sites():
    out = []
    if not os.path.isdir(SITES_DIR):
        return out
    for nome in sorted(os.listdir(SITES_DIR)):
        if nome == "_kit" or nome.startswith("_"):
            continue
        pasta = os.path.join(SITES_DIR, nome)
        idx = os.path.join(pasta, "index.html")
        if not os.path.isfile(idx):
            continue
        try:
            st = os.stat(idx)
            with open(idx, encoding="utf-8", errors="ignore") as f:
                head = f.read(4000)
            is_doc = 'class="documento"' in head or "class='documento'" in head
            title_m = re.search(r"<title>(.*?)</title>", head, re.S)
            title = (title_m.group(1).strip() if title_m else nome)[:120]
            out.append(
                {
                    "nome": nome,
                    "titulo": title,
                    "url": f"/s/{nome}",
                    "tipo": "documento" if is_doc else "pagina",
                    "modificado_em": int(st.st_mtime),
                    "tamanho": st.st_size,
                }
            )
        except OSError:
            continue
    out.sort(key=lambda x: x["modificado_em"], reverse=True)
    return out


def _soft_delete_site(nome):
    """Mesma logica do 'copiloto site remover': guarda copia em copiloto-backups/
    antes de tirar do ar — so que sem exigir grupo principal (esta e' uma
    ferramenta autenticada por senha, nao um comando que chega por chat)."""
    pasta = _safe_site_name(nome)
    if not pasta or not os.path.isdir(pasta):
        return False, "não encontrado"
    destino = os.path.join(BACKUPS_DIR, time.strftime("%Y%m%d-%H%M%S") + "-site-" + nome)
    os.makedirs(destino, exist_ok=True)
    shutil.copytree(pasta, os.path.join(destino, nome), dirs_exist_ok=True)
    with open(os.path.join(destino, "motivo.txt"), "w", encoding="utf-8") as f:
        f.write("site removido do ar (via /documentos)\n")
    shutil.rmtree(pasta, ignore_errors=True)
    return True, None


def _home_channel_chat_id():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return (
            cfg.get("platforms", {})
            .get("whatsapp", {})
            .get("home_channel", {})
            .get("chat_id")
        )
    except Exception:
        return None


def _generate_pdf(nome):
    """Renderiza a pagina publicada (a URL publica de verdade, com o kit de CSS
    carregado) num PDF via Chromium headless. Devolve o caminho do PDF
    temporario (chamador precisa apagar) ou (None, erro)."""
    if not COPILOTO_DOMINIO:
        return None, "COPILOTO_DOMINIO não configurado nesta instalação."
    url = f"https://{COPILOTO_DOMINIO}/s/{nome}"
    out_path = os.path.join(tempfile.gettempdir(), f"doc-{nome}-{int(time.time())}.pdf")
    try:
        subprocess.run(
            [
                CHROMIUM_PATH,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--print-to-pdf-no-header",
                f"--print-to-pdf={out_path}",
                url,
            ],
            timeout=30,
            capture_output=True,
        )
    except Exception as e:
        return None, str(e)
    if not os.path.isfile(out_path) or os.path.getsize(out_path) == 0:
        return None, "Chromium não gerou o PDF."
    return out_path, None


def _send_pdf_to_group(nome, titulo):
    chat_id = _home_channel_chat_id()
    if not chat_id:
        return False, "grupo principal não configurado (home_channel)."
    pdf_path, err = _generate_pdf(nome)
    if err:
        return False, err
    try:
        body = json.dumps(
            {
                "chatId": chat_id,
                "filePath": pdf_path,
                "mediaType": "document",
                "fileName": f"{nome}.pdf",
                "caption": titulo or nome,
            }
        ).encode()
        req = urllib.request.Request(
            BRIDGE_SEND_MEDIA_URL, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read() or b"{}")
            ok = bool(data.get("success"))
            return ok, None if ok else data.get("error", "falha desconhecida")
    except Exception as e:
        return False, str(e)
    finally:
        try:
            os.unlink(pdf_path)
        except OSError:
            pass


# ============================================================ FRONTEND (HTML)
PAGE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CRM — Copiloto</title>
<style>
:root{--bg:#0e131a;--panel:#151c26;--panel-2:#1c2531;--line:#293445;--ink:#e7ecf3;--ink-soft:#98a7b8;--brand:#0e5aa7;--ok:#1e8e5a;--warn:#b8862a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif;-webkit-font-smoothing:antialiased}
header{position:sticky;top:0;z-index:20;background:rgba(14,19,26,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:12px 16px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
header h1{font-size:16px;margin:0;font-weight:650}
header .sub{font-size:12px;color:var(--ink-soft)}
.btn{background:var(--brand);color:#fff;border:none;border-radius:8px;padding:9px 14px;font-size:13px;font-weight:600;cursor:pointer}
.btn:hover{filter:brightness(1.1)}
.btn-ghost{background:transparent;border:1px solid var(--line);color:var(--ink)}
.board{display:flex;gap:10px;padding:12px;overflow-x:auto;min-height:calc(100vh - 60px)}
.col{background:var(--panel);border:1px solid var(--line);border-radius:12px;min-width:250px;max-width:270px;flex:0 0 auto;display:flex;flex-direction:column;max-height:calc(100vh - 84px)}
.col-head{padding:10px 12px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;gap:6px}
.col-head b{font-size:13px}
.col-head .count{font-size:11px;color:var(--ink-soft);background:var(--panel-2);border-radius:20px;padding:1px 8px}
.col-msg-btn{background:none;border:none;color:var(--ink-soft);cursor:pointer;font-size:14px;padding:2px 4px}
.col-msg-btn.off{opacity:.35}
.col-body{padding:8px;overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:8px}
.card{background:var(--panel-2);border:1px solid var(--line);border-radius:9px;padding:9px 10px;cursor:grab;font-size:13px}
.card.dragging{opacity:.4}
.card b{display:block;font-size:13px;margin-bottom:2px}
.card .phone{font-size:11px;color:var(--ink-soft)}
.col-body.dragover{outline:2px dashed var(--brand);outline-offset:-4px;border-radius:9px}
.fab{position:fixed;bottom:20px;right:20px;z-index:30}
.fab .btn{border-radius:24px;padding:12px 18px;box-shadow:0 6px 18px rgba(0,0,0,.4)}
dialog{background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:12px;padding:0;width:min(420px,92vw)}
dialog::backdrop{background:rgba(0,0,0,.55)}
.dlg-body{padding:16px}
.dlg-body h2{font-size:15px;margin:0 0 12px}
.field{margin-bottom:10px}
.field label{display:block;font-size:12px;color:var(--ink-soft);margin-bottom:4px}
.field input,.field textarea{width:100%;background:var(--bg);border:1px solid var(--line);color:var(--ink);border-radius:8px;padding:8px 10px;font-size:13px;font-family:inherit}
.field textarea{min-height:90px;resize:vertical}
.field.toggle{display:flex;align-items:center;gap:8px}
.dlg-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:14px}
.btn-danger{background:#7a2231}
@media (max-width:640px){.col{min-width:82vw;max-height:none}.board{scroll-snap-type:x mandatory}.col{scroll-snap-align:start}}
</style>
</head>
<body>
<header>
  <div>
    <h1>CRM — funil do consultório</h1>
    <div class="sub">arraste o card entre as colunas · toque no ✉️ pra editar a mensagem de cada etapa</div>
  </div>
  <div style="display:flex;gap:8px">
    <a class="btn btn-ghost" href="/documentos" style="text-decoration:none;display:inline-flex;align-items:center">📄 Documentos</a>
    <button class="btn" id="btnNovo">+ Novo Lead</button>
  </div>
</header>
<div class="board" id="board"></div>

<dialog id="dlgCard">
  <div class="dlg-body">
    <h2 id="dlgCardTitle">Novo Lead</h2>
    <div class="field"><label>Nome</label><input id="fName"></div>
    <div class="field"><label>Telefone (com DDI, só números)</label><input id="fPhone" placeholder="5511999999999"></div>
    <div class="field"><label>Observações</label><textarea id="fNotes"></textarea></div>
    <div class="dlg-actions">
      <button class="btn btn-danger" id="btnDelete" style="display:none;margin-right:auto">Excluir</button>
      <button class="btn btn-ghost" id="btnCancelCard">Cancelar</button>
      <button class="btn" id="btnSaveCard">Salvar</button>
    </div>
  </div>
</dialog>

<dialog id="dlgMsg">
  <div class="dlg-body">
    <h2 id="dlgMsgTitle">Mensagem da etapa</h2>
    <div class="field toggle">
      <input type="checkbox" id="fEnabled" style="width:auto">
      <label style="margin:0" for="fEnabled">Disparar automaticamente ao entrar nesta etapa</label>
    </div>
    <div class="field">
      <label>Texto (use {{nome}} para o nome do paciente)</label>
      <textarea id="fMessage"></textarea>
    </div>
    <div class="dlg-actions">
      <button class="btn btn-ghost" id="btnCancelMsg">Cancelar</button>
      <button class="btn" id="btnSaveMsg">Salvar</button>
    </div>
  </div>
</dialog>

<script>
const STATUSES = __STATUSES_JSON__;
let cards = [];
let templates = {};
let editingCardId = null;
let editingStatus = null;

async function api(path, opts) {
  const r = await fetch(path, Object.assign({headers: {'Content-Type': 'application/json'}}, opts || {}));
  if (!r.ok) throw new Error('erro ' + r.status);
  return r.status === 204 ? null : r.json();
}

async function load() {
  const [c, t] = await Promise.all([api('/crm/api/cards'), api('/crm/api/templates')]);
  cards = c; templates = {}; t.forEach(x => templates[x.status] = x);
  render();
}

function render() {
  const board = document.getElementById('board');
  board.innerHTML = '';
  STATUSES.forEach(([key, label]) => {
    const col = document.createElement('div');
    col.className = 'col';
    const tpl = templates[key] || {enabled: false, message: ''};
    col.innerHTML = `
      <div class="col-head">
        <b>${label}</b>
        <div style="display:flex;align-items:center;gap:6px">
          <span class="count">${cards.filter(c => c.status === key).length}</span>
          <button class="col-msg-btn ${tpl.enabled ? '' : 'off'}" data-status="${key}" title="Mensagem automática desta etapa">✉️</button>
        </div>
      </div>
      <div class="col-body" data-status="${key}"></div>
    `;
    board.appendChild(col);
    const body = col.querySelector('.col-body');
    cards.filter(c => c.status === key).forEach(c => {
      const el = document.createElement('div');
      el.className = 'card';
      el.draggable = true;
      el.dataset.id = c.id;
      el.innerHTML = `<b>${escapeHtml(c.name)}</b><span class="phone">${escapeHtml(c.phone)}</span>`;
      el.addEventListener('dragstart', e => { el.classList.add('dragging'); e.dataTransfer.setData('text/plain', c.id); });
      el.addEventListener('dragend', () => el.classList.remove('dragging'));
      el.addEventListener('click', () => openCardDialog(c));
      body.appendChild(el);
    });
    body.addEventListener('dragover', e => { e.preventDefault(); body.classList.add('dragover'); });
    body.addEventListener('dragleave', () => body.classList.remove('dragover'));
    body.addEventListener('drop', async e => {
      e.preventDefault(); body.classList.remove('dragover');
      const id = e.dataTransfer.getData('text/plain');
      const card = cards.find(c => String(c.id) === String(id));
      if (!card || card.status === key) return;
      card.status = key; render();
      await api('/crm/api/cards/' + id, {method: 'PATCH', body: JSON.stringify({status: key})});
      load();
    });
  });
  board.querySelectorAll('.col-msg-btn').forEach(b => b.addEventListener('click', () => openMsgDialog(b.dataset.status)));
}

function escapeHtml(s) { return String(s || '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }

function openCardDialog(card) {
  editingCardId = card ? card.id : null;
  document.getElementById('dlgCardTitle').textContent = card ? 'Editar lead' : 'Novo lead';
  document.getElementById('fName').value = card ? card.name : '';
  document.getElementById('fPhone').value = card ? card.phone : '';
  document.getElementById('fNotes').value = card ? card.notes : '';
  document.getElementById('btnDelete').style.display = card ? '' : 'none';
  document.getElementById('dlgCard').showModal();
}

document.getElementById('btnNovo').addEventListener('click', () => openCardDialog(null));
document.getElementById('btnCancelCard').addEventListener('click', () => document.getElementById('dlgCard').close());
document.getElementById('btnSaveCard').addEventListener('click', async () => {
  const body = {
    name: document.getElementById('fName').value.trim(),
    phone: document.getElementById('fPhone').value.trim(),
    notes: document.getElementById('fNotes').value.trim(),
  };
  if (!body.name || !body.phone) return alert('Preencha nome e telefone.');
  if (editingCardId) await api('/crm/api/cards/' + editingCardId, {method: 'PATCH', body: JSON.stringify(body)});
  else await api('/crm/api/cards', {method: 'POST', body: JSON.stringify(body)});
  document.getElementById('dlgCard').close();
  load();
});
document.getElementById('btnDelete').addEventListener('click', async () => {
  if (!editingCardId || !confirm('Excluir este lead?')) return;
  await api('/crm/api/cards/' + editingCardId, {method: 'DELETE'});
  document.getElementById('dlgCard').close();
  load();
});

function openMsgDialog(status) {
  editingStatus = status;
  const tpl = templates[status] || {enabled: false, message: ''};
  const label = STATUSES.find(s => s[0] === status)[1];
  document.getElementById('dlgMsgTitle').textContent = 'Mensagem — ' + label;
  document.getElementById('fEnabled').checked = !!tpl.enabled;
  document.getElementById('fMessage').value = tpl.message || '';
  document.getElementById('dlgMsg').showModal();
}
document.getElementById('btnCancelMsg').addEventListener('click', () => document.getElementById('dlgMsg').close());
document.getElementById('btnSaveMsg').addEventListener('click', async () => {
  await api('/crm/api/templates/' + editingStatus, {method: 'PUT', body: JSON.stringify({
    message: document.getElementById('fMessage').value,
    enabled: document.getElementById('fEnabled').checked,
  })});
  document.getElementById('dlgMsg').close();
  load();
});

load();
setInterval(load, 15000);
</script>
</body>
</html>
"""
PAGE = PAGE.replace("__STATUSES_JSON__", json.dumps(STATUSES, ensure_ascii=False))


DOCS_PAGE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Documentos — Copiloto</title>
<style>
:root{--bg:#0e131a;--panel:#151c26;--panel-2:#1c2531;--line:#293445;--ink:#e7ecf3;--ink-soft:#98a7b8;--brand:#0e5aa7}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif;-webkit-font-smoothing:antialiased}
header{position:sticky;top:0;z-index:20;background:rgba(14,19,26,.92);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:12px 16px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
header h1{font-size:16px;margin:0;font-weight:650}
header .sub{font-size:12px;color:var(--ink-soft)}
.btn{background:var(--brand);color:#fff;border:none;border-radius:8px;padding:9px 14px;font-size:13px;font-weight:600;cursor:pointer}
.btn:hover{filter:brightness(1.1)}
.btn-ghost{background:transparent;border:1px solid var(--line);color:var(--ink)}
.btn-danger{background:#7a2231}
.wrap{max-width:900px;margin:0 auto;padding:16px}
.item{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-bottom:10px;display:flex;align-items:center;gap:12px}
.item .info{flex:1;min-width:0}
.item b{display:block;font-size:14px;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.item .meta{font-size:11px;color:var(--ink-soft)}
.tag{font-size:10px;background:var(--panel-2);border:1px solid var(--line);border-radius:20px;padding:1px 8px;color:var(--ink-soft)}
.item a.open{color:var(--brand);text-decoration:none;font-size:12px}
.empty{color:var(--ink-soft);font-size:13px;padding:30px 0;text-align:center}
dialog{background:var(--panel);color:var(--ink);border:1px solid var(--line);border-radius:12px;padding:0;width:min(720px,94vw)}
dialog::backdrop{background:rgba(0,0,0,.55)}
.dlg-body{padding:16px}
.dlg-body h2{font-size:15px;margin:0 0 12px}
textarea#fContent{width:100%;min-height:50vh;background:var(--bg);border:1px solid var(--line);color:var(--ink);border-radius:8px;padding:10px;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px}
.dlg-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:14px;flex-wrap:wrap}
.status{font-size:12px;color:var(--ink-soft);margin-top:8px}
@media (max-width:640px){.item{flex-wrap:wrap}.item .info{width:100%}}
</style>
</head>
<body>
<header>
  <div>
    <h1>Documentos e páginas publicadas</h1>
    <div class="sub">tudo que o Copiloto publicou em /s — edite, baixe ou mande no grupo</div>
  </div>
  <a class="btn btn-ghost" href="/crm" style="text-decoration:none;display:inline-flex;align-items:center">← CRM</a>
</header>
<div class="wrap" id="list"></div>

<dialog id="dlgEdit">
  <div class="dlg-body">
    <h2 id="dlgTitle">Editar</h2>
    <textarea id="fContent" spellcheck="false"></textarea>
    <div class="status" id="dlgStatus"></div>
    <div class="dlg-actions">
      <button class="btn btn-danger" id="btnDelete" style="margin-right:auto">Excluir</button>
      <button class="btn btn-ghost" id="btnOpen">Abrir página</button>
      <button class="btn btn-ghost" id="btnSendGroup">📲 Enviar PDF no grupo</button>
      <button class="btn btn-ghost" id="btnCancel">Fechar</button>
      <button class="btn" id="btnSave">Salvar</button>
    </div>
  </div>
</dialog>

<script>
let editingNome = null;

async function api(path, opts) {
  const r = await fetch(path, Object.assign({headers: {'Content-Type': 'application/json'}}, opts || {}));
  if (!r.ok) throw new Error('erro ' + r.status);
  return r.status === 204 ? null : r.json();
}

function fmtBytes(n) { return n < 1024*1024 ? Math.round(n/1024)+' KB' : (n/1024/1024).toFixed(1)+' MB'; }
function fmtDate(ts) { return new Date(ts*1000).toLocaleString('pt-BR'); }
function escapeHtml(s) { return String(s || '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }

async function load() {
  const items = await api('/documentos/api/list');
  const el = document.getElementById('list');
  if (!items.length) { el.innerHTML = '<div class="empty">Nenhum documento publicado ainda.</div>'; return; }
  el.innerHTML = items.map(it => `
    <div class="item">
      <div class="info">
        <b>${escapeHtml(it.titulo)}</b>
        <div class="meta">
          <span class="tag">${it.tipo === 'documento' ? 'documento' : 'página'}</span>
          ${fmtDate(it.modificado_em)} · ${fmtBytes(it.tamanho)}
        </div>
      </div>
      <a class="open" href="${it.url}" target="_blank" rel="noopener">abrir ↗</a>
      <button class="btn btn-ghost" data-nome="${it.nome}" data-titulo="${escapeHtml(it.titulo)}">Editar</button>
    </div>
  `).join('');
  el.querySelectorAll('button[data-nome]').forEach(b => b.addEventListener('click', () => openEdit(b.dataset.nome, b.dataset.titulo)));
}

async function openEdit(nome, titulo) {
  editingNome = nome;
  document.getElementById('dlgTitle').textContent = titulo || nome;
  document.getElementById('dlgStatus').textContent = 'Carregando...';
  document.getElementById('dlgEdit').showModal();
  const data = await api('/documentos/api/' + nome + '/content');
  document.getElementById('fContent').value = data.content;
  document.getElementById('dlgStatus').textContent = '';
}

document.getElementById('btnCancel').addEventListener('click', () => document.getElementById('dlgEdit').close());
document.getElementById('btnOpen').addEventListener('click', () => window.open('/s/' + editingNome, '_blank'));
document.getElementById('btnSave').addEventListener('click', async () => {
  const st = document.getElementById('dlgStatus');
  st.textContent = 'Salvando...';
  try {
    await api('/documentos/api/' + editingNome + '/content', {method: 'PUT', body: JSON.stringify({content: document.getElementById('fContent').value})});
    st.textContent = '✅ Salvo.';
  } catch (e) { st.textContent = '❌ Falha ao salvar.'; }
});
document.getElementById('btnDelete').addEventListener('click', async () => {
  if (!confirm('Excluir "' + editingNome + '"? (fica guardado como cópia de segurança)')) return;
  await api('/documentos/api/' + editingNome, {method: 'DELETE'});
  document.getElementById('dlgEdit').close();
  load();
});
document.getElementById('btnSendGroup').addEventListener('click', async () => {
  const st = document.getElementById('dlgStatus');
  st.textContent = 'Gerando PDF e enviando no grupo...';
  try {
    await api('/documentos/api/' + editingNome + '/send-group', {method: 'POST'});
    st.textContent = '✅ Enviado no grupo.';
  } catch (e) { st.textContent = '❌ Falha ao enviar — confira se o WhatsApp está conectado.'; }
});

load();
</script>
</body>
</html>
"""


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
        if not (self.path.startswith("/crm") or self.path.startswith("/documentos")):
            self.send_response(404)
            self.end_headers()
            return False
        if not self._auth_ok():
            self._deny()
            return False
        return True

    def do_GET(self):
        if not self._guard():
            return
        path = urlparse(self.path).path

        if path in ("/crm", "/crm/"):
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/crm/api/cards":
            with _lock, _db() as conn:
                rows = conn.execute("SELECT * FROM cards ORDER BY updated_at DESC").fetchall()
            return self._json([_row_to_card(r) for r in rows])

        if path == "/crm/api/templates":
            with _lock, _db() as conn:
                rows = conn.execute("SELECT * FROM templates").fetchall()
            return self._json(
                [{"status": r["status"], "message": r["message"], "enabled": bool(r["enabled"])} for r in rows]
            )

        if path in ("/documentos", "/documentos/"):
            body = DOCS_PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if path == "/documentos/api/list":
            return self._json(_list_sites())

        m = re.match(r"^/documentos/api/([a-z0-9-]+)/content$", path)
        if m:
            pasta = _safe_site_name(m.group(1))
            if not pasta or not os.path.isdir(pasta):
                return self._json({"error": "não encontrado"}, 404)
            try:
                with open(os.path.join(pasta, "index.html"), encoding="utf-8") as f:
                    return self._json({"content": f.read()})
            except OSError as e:
                return self._json({"error": str(e)}, 500)

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if not self._guard():
            return
        path = urlparse(self.path).path
        if path == "/crm/api/cards":
            b = self._body()
            name = (b.get("name") or "").strip()
            phone = _norm_phone(b.get("phone") or "")
            status = b.get("status") if b.get("status") in STATUS_KEYS else "novo_lead"
            if not name or not phone:
                return self._json({"error": "name e phone são obrigatórios"}, 400)
            now = int(time.time())
            with _lock, _db() as conn:
                cur = conn.execute(
                    "INSERT INTO cards (name, phone, status, notes, created_at, updated_at) "
                    "VALUES (?, ?, ?, '', ?, ?)",
                    (name, phone, status, now, now),
                )
                conn.commit()
                card_id = cur.lastrowid
            return self._json({"id": card_id}, 201)

        m = re.match(r"^/documentos/api/([a-z0-9-]+)/send-group$", path)
        if m:
            nome = m.group(1)
            pasta = _safe_site_name(nome)
            if not pasta or not os.path.isdir(pasta):
                return self._json({"error": "não encontrado"}, 404)
            titulo = next((s["titulo"] for s in _list_sites() if s["nome"] == nome), nome)
            ok, err = _send_pdf_to_group(nome, titulo)
            if not ok:
                return self._json({"error": err}, 502)
            return self._json({"ok": True})

        self.send_response(404)
        self.end_headers()

    def do_PATCH(self):
        if not self._guard():
            return
        path = urlparse(self.path).path
        m = re.match(r"^/crm/api/cards/(\d+)$", path)
        if m:
            card_id = int(m.group(1))
            b = self._body()
            with _lock, _db() as conn:
                row = conn.execute("SELECT * FROM cards WHERE id=?", (card_id,)).fetchone()
                if not row:
                    return self._json({"error": "não encontrado"}, 404)
                name = b.get("name", row["name"])
                phone = _norm_phone(b.get("phone")) if "phone" in b else row["phone"]
                notes = b.get("notes", row["notes"])
                new_status = b.get("status", row["status"])
                if new_status not in STATUS_KEYS:
                    new_status = row["status"]
                old_status = row["status"]
                conn.execute(
                    "UPDATE cards SET name=?, phone=?, notes=?, status=?, updated_at=? WHERE id=?",
                    (name, phone, notes, new_status, int(time.time()), card_id),
                )
                conn.commit()
            if new_status != old_status:
                threading.Thread(
                    target=_fire_status_message, args=(card_id, name, phone, new_status), daemon=True
                ).start()
            return self._json({"ok": True})
        self.send_response(404)
        self.end_headers()

    def do_PUT(self):
        if not self._guard():
            return
        path = urlparse(self.path).path
        m = re.match(r"^/crm/api/templates/([a-z_]+)$", path)
        if m:
            status = m.group(1)
            if status not in STATUS_KEYS:
                return self._json({"error": "status inválido"}, 400)
            b = self._body()
            with _lock, _db() as conn:
                row = conn.execute("SELECT * FROM templates WHERE status=?", (status,)).fetchone()
                message = b.get("message", row["message"] if row else "")
                enabled = 1 if b.get("enabled", bool(row["enabled"]) if row else True) else 0
                conn.execute(
                    "INSERT INTO templates (status, message, enabled) VALUES (?, ?, ?) "
                    "ON CONFLICT(status) DO UPDATE SET message=excluded.message, enabled=excluded.enabled",
                    (status, message, enabled),
                )
                conn.commit()
            return self._json({"ok": True})

        m = re.match(r"^/documentos/api/([a-z0-9-]+)/content$", path)
        if m:
            pasta = _safe_site_name(m.group(1))
            if not pasta or not os.path.isdir(pasta):
                return self._json({"error": "não encontrado"}, 404)
            b = self._body()
            content = b.get("content")
            if content is None:
                return self._json({"error": "content é obrigatório"}, 400)
            idx = os.path.join(pasta, "index.html")
            # Guarda uma copia antes de sobrescrever — mesmo espirito do
            # "copiloto ajuste" antes de qualquer mudanca.
            backup_dir = os.path.join(BACKUPS_DIR, time.strftime("%Y%m%d-%H%M%S") + "-edicao-" + m.group(1))
            os.makedirs(backup_dir, exist_ok=True)
            try:
                shutil.copy2(idx, os.path.join(backup_dir, "index.html"))
            except OSError:
                pass
            with open(idx, "w", encoding="utf-8") as f:
                f.write(content)
            return self._json({"ok": True})

        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        if not self._guard():
            return
        path = urlparse(self.path).path
        m = re.match(r"^/crm/api/cards/(\d+)$", path)
        if m:
            card_id = int(m.group(1))
            with _lock, _db() as conn:
                conn.execute("DELETE FROM cards WHERE id=?", (card_id,))
                conn.execute("DELETE FROM message_log WHERE card_id=?", (card_id,))
                conn.commit()
            self.send_response(204)
            self.end_headers()
            return

        m = re.match(r"^/documentos/api/([a-z0-9-]+)$", path)
        if m:
            ok, err = _soft_delete_site(m.group(1))
            if not ok:
                return self._json({"error": err}, 404)
            self.send_response(204)
            self.end_headers()
            return

        self.send_response(404)
        self.end_headers()


if __name__ == "__main__":
    _init_db()
    threading.Thread(target=_intake_loop, daemon=True).start()
    print(f"[crm] listening on 127.0.0.1:{PORT}", file=sys.stderr)
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
