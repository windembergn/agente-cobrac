#!/usr/bin/env python3
"""Copiloto — liga o MCP do Composio a partir de COMPOSIO_API_KEY.

Roda no boot (cont-init 03-copiloto). O cirurgiao so cola a chave do Composio
na stack; o resto e' feito aqui.

Por que NAO da pra pedir isso ao agente por prompt (o que o tutorial fazia):
o agente nao escreve no config.yaml do host nem reinicia o gateway — ele
responde pedindo pra "acionar a equipe tecnica". Config de MCP e' semeada por
fora, como todo o resto da imagem.

Autenticacao (testado ao vivo em 27/07/2026): o Tool Router
https://connect.composio.dev/mcp aceita a consumer key (ck_...) tanto em
`Authorization: Bearer` quanto em `x-consumer-api-key`. NAO aceita ela como
`x-api-key` (isso e' da API REST v3, que rejeita a ck_ com 401
"Invalid API key"). Usamos Bearer, que e' o esquema anunciado pelo proprio
www-authenticate do endpoint.

O router expoe 7 meta-ferramentas (COMPOSIO_SEARCH_TOOLS,
COMPOSIO_MANAGE_CONNECTIONS, COMPOSIO_MULTI_EXECUTE_TOOL, ...) que dao acesso
a 500+ apps sob demanda — inclusive o link de autorizacao do Google, que o
agente manda no proprio WhatsApp. Por isso nao precisamos criar MCP server
via REST nem fixar uma lista de toolkits.

Idempotente e nunca derruba o boot: qualquer falha e' logada e o script sai 0.
"""

import json
import os
import sys
import urllib.error
import urllib.request

import yaml

DATA = os.environ.get("COPILOTO_DATA") or "/opt/data"
CFG = os.path.join(DATA, "config.yaml")
LOG = os.path.join(DATA, "composio-setup.log")

URL = (os.environ.get("COMPOSIO_MCP_URL") or "https://connect.composio.dev/mcp").strip()

_RAW_KEY = (os.environ.get("COMPOSIO_API_KEY") or "").strip().strip('"').strip("'")
# O campo do tutorial vem preenchido com placeholder e stack sem a var manda
# string vazia — nos dois casos o Composio fica desligado.
_PLACEHOLDERS = {"", "none", "null", "placeholder", "comp_cole-sua-chave-aqui", "ck_cole-sua-chave-aqui", "cole-sua-chave-aqui", "sua-chave-aqui"}
KEY = "" if _RAW_KEY.lower() in _PLACEHOLDERS else _RAW_KEY

ENTRY = {
    "url": URL,
    # A chave NAO fica em texto no config: o Hermes interpola ${VAR} nos
    # headers (tools/mcp_tool.py:_interpolate_env_vars) usando o ambiente do
    # gateway, e a env ja vem da stack.
    "headers": {"Authorization": "Bearer ${COMPOSIO_API_KEY}"},
    "timeout": 180,
    "connect_timeout": 60,
}


def log(msg):
    line = f"[composio-setup] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def load_cfg():
    try:
        with open(CFG) as fh:
            return yaml.safe_load(fh) or {}
    except (FileNotFoundError, yaml.YAMLError):
        return {}


def save_cfg(cfg):
    tmp = CFG + ".tmp"
    with open(tmp, "w") as fh:
        yaml.safe_dump(cfg, fh, sort_keys=False, allow_unicode=True)
    os.replace(tmp, CFG)


def check_key():
    """Handshake MCP real, so pra logar um diagnostico claro no boot.

    Nao bloqueia a escrita da config: se a rede estiver fora no boot, o
    gateway ainda tenta conectar depois (o cliente MCP do Hermes reconecta
    com backoff).
    """
    body = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                   "clientInfo": {"name": "copiloto-setup", "version": "1.0"}},
    }).encode()
    req = urllib.request.Request(URL, method="POST", data=body, headers={
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "Authorization": f"Bearer {KEY}",
    })
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            return resp.status == 200, f"HTTP {resp.status}"
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:200]
        return False, f"HTTP {exc.code}: {detail}"
    except Exception as exc:
        return False, f"rede indisponivel: {exc}"


def main():
    cfg = load_cfg()
    current = (cfg.get("mcp_servers") or {}).get("composio")

    if not KEY:
        if current is None:
            return
        del cfg["mcp_servers"]["composio"]
        if not cfg["mcp_servers"]:
            cfg.pop("mcp_servers", None)
        save_cfg(cfg)
        log("COMPOSIO_API_KEY ausente — Composio desligado (entrada removida do config.yaml)")
        return

    ok, detail = check_key()
    if ok:
        log("chave do Composio validada (handshake MCP OK)")
    else:
        # Config escrita mesmo assim: chave boa + rede instavel no boot e' o
        # caso mais provavel, e o cliente do Hermes reconecta sozinho.
        log(f"AVISO: nao consegui validar a chave agora ({detail})")
        log("a config sera escrita mesmo assim; se a chave estiver errada, as ferramentas nao aparecem")

    if current == ENTRY:
        return
    cfg.setdefault("mcp_servers", {})["composio"] = ENTRY
    save_cfg(cfg)
    log(f"Composio ligado em {URL} — o agente ganha COMPOSIO_SEARCH_TOOLS, MANAGE_CONNECTIONS e afins")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # nunca derrubar o boot por causa disso
        log(f"ERRO inesperado: {exc}")
    sys.exit(0)
