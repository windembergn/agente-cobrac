#!/usr/bin/env python3
"""Copiloto — multiplos numeros de WhatsApp (slots) no mesmo container.

Um "slot" e' um numero de WhatsApp. Cada slot tem sessao propria, bridge
proprio (porta propria) e sua propria lista de grupos. Dois modos:

  shared   — o numero e' mais uma "boca" do copiloto principal: mesma
             memoria, mesmos arquivos, mesmo Composio. Implementado como
             uma PLATAFORMA extra (whatsapp2, whatsapp3, ...) no mesmo
             gateway. O plugin de cada plataforma e' gerado aqui.
  isolated — o numero e' um copiloto independente: memoria, persona e
             historico proprios. Implementado como um PERFIL do Hermes,
             com gateway proprio.

A fonte da verdade e' $DATA/whatsapp/slots.json. Este modulo reconcilia o
config.yaml (e os perfis) a partir dele, a cada boot e a cada alteracao
feita pelo painel ou pelos comandos do grupo.

Uso:  copiloto_slots.py reconcile | list
"""
import json
import os
import re
import shutil
import subprocess
import sys

DATA = os.environ.get("COPILOTO_DATA", "/opt/data")
CFG = os.path.join(DATA, "config.yaml")
WA_DIR = os.path.join(DATA, "whatsapp")
SLOTS_FILE = os.path.join(WA_DIR, "slots.json")
REQ_DIR = os.path.join(WA_DIR, "requests")
PLUGINS_DIR = "/opt/hermes/plugins/platforms"
BASE_PORT = int(os.environ.get("COPILOTO_BASE_PORT", "3000"))
HERMES_UID = int(os.environ.get("HERMES_UID", "1000"))
HERMES_GID = int(os.environ.get("HERMES_GID", "1000"))

# Silencio no WhatsApp: sem "pensamento", sem transcricao, sem aviso de
# sistema. Replicado para CADA plataforma de slot — sem isso o segundo
# numero voltaria a despejar no grupo tudo que o primeiro ja nao mostra.
DISPLAY_QUIET = {
    "tool_progress": "off",
    "show_reasoning": False,
    "interim_assistant_messages": False,
    "long_running_notifications": False,
    "busy_steer_ack_enabled": False,
    "busy_ack_detail": False,
    "memory_notifications": "off",
}


def _log(msg):
    print("[slots] %s" % msg, flush=True)


# ---------------------------------------------------------------- storage
def _default_slots():
    return {"version": 1, "slots": []}


def load():
    try:
        with open(SLOTS_FILE, encoding="utf-8") as f:
            cfg = json.load(f)
        if not isinstance(cfg, dict) or not isinstance(cfg.get("slots"), list):
            raise ValueError("shape")
        return cfg
    except Exception:
        return None


def save(cfg):
    os.makedirs(WA_DIR, exist_ok=True)
    tmp = SLOTS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SLOTS_FILE)
    _chown(SLOTS_FILE)


def _chown(path):
    try:
        os.chown(path, HERMES_UID, HERMES_GID)
    except Exception:
        pass


# ---------------------------------------------------------------- helpers
def slot_num(slot):
    """wa1 -> 1. O numero decide plataforma, porta e pasta da sessao."""
    m = re.search(r"(\d+)$", str(slot.get("id") or ""))
    return int(m.group(1)) if m else 1


def platform_name(slot):
    """Plataforma do gateway que serve este slot.

    Slots isolados rodam num gateway proprio (o do perfil), entao la dentro
    eles sao a plataforma 'whatsapp' normal.
    """
    if slot.get("mode") == "isolated":
        return "whatsapp"
    n = slot_num(slot)
    return "whatsapp" if n == 1 else "whatsapp%d" % n


def profile_name(slot):
    return slot["id"] if slot.get("mode") == "isolated" else None


def profile_dir(slot):
    return os.path.join(DATA, "profiles", slot["id"])


def session_path(slot):
    if slot.get("mode") == "isolated":
        return os.path.join(profile_dir(slot), "platforms", "whatsapp", "session")
    n = slot_num(slot)
    name = "whatsapp" if n == 1 else "whatsapp%d" % n
    return os.path.join(DATA, "platforms", name, "session")


def bridge_port(slot):
    return int(slot.get("port") or (BASE_PORT + slot_num(slot) - 1))


def is_paired(slot):
    return os.path.exists(os.path.join(session_path(slot), "creds.json"))


def phone_of(slot):
    """Numero conectado, lido da sessao (so para exibir no painel)."""
    try:
        with open(os.path.join(session_path(slot), "creds.json"), encoding="utf-8") as f:
            creds = json.load(f)
        me = (creds.get("me") or {}).get("id") or ""
        digits = re.sub(r"\D+", "", str(me).split("@")[0].split(":")[0])
        return digits or None
    except Exception:
        return None


def find_slot(cfg, slot_id):
    for s in cfg["slots"]:
        if s.get("id") == slot_id:
            return s
    return None


def slot_by_session(cfg, sess):
    """Usado pelo watcher: o bridge se identifica pelo --session."""
    sess = os.path.normpath(str(sess or "")).rstrip("/")
    for s in cfg["slots"]:
        if os.path.normpath(session_path(s)).rstrip("/") == sess:
            return s
    return None


def next_id(cfg):
    used = {slot_num(s) for s in cfg["slots"]}
    n = 1
    while n in used:
        n += 1
    return "wa%d" % n


# ---------------------------------------------------------------- migracao
def migrate():
    """Primeira execucao: monta o slots.json a partir do que ja existe.

    A instalacao viva ja tem um numero pareado e um grupo ativo em
    platforms.whatsapp — ela precisa continuar funcionando exatamente igual
    depois do update, sem reparear e sem refazer /main.
    """
    cfg = _default_slots()
    groups, home = [], None
    try:
        import yaml
        with open(CFG, encoding="utf-8") as f:
            y = yaml.safe_load(f) or {}
        wa = ((y.get("platforms") or {}).get("whatsapp") or {})
        hc = wa.get("home_channel") or {}
        home = hc.get("chat_id")
        names = {home: hc.get("name")} if home else {}
        for jid in (wa.get("group_allow_from") or []):
            groups.append({"id": str(jid), "name": names.get(str(jid)) or ""})
    except Exception:
        pass

    cfg["slots"].append({
        "id": "wa1",
        "label": "Zap principal",
        "mode": "shared",
        "port": BASE_PORT,
        "groups": groups,
        "home": home,
    })
    _log("slots.json criado a partir do config.yaml (%d grupo(s) no wa1)" % len(groups))
    return cfg


def load_or_migrate():
    cfg = load()
    if cfg is None:
        cfg = migrate()
        save(cfg)
    return cfg


# ---------------------------------------------------------------- plugins
_PLUGIN_ADAPTER = '''"""Plataforma WhatsApp extra (slot {n}) — gerada pelo Copiloto.

O adapter oficial do Hermes serve UM numero: ele fixa Platform.WHATSAPP no
__init__. Esta subclasse fina troca so a identidade da plataforma, para que
o mesmo gateway possa manter varias sessoes de WhatsApp ao mesmo tempo —
cada uma com sua porta de bridge, sua pasta de sessao e seus grupos.
"""
import importlib

from gateway.config import Platform

_wa = importlib.import_module("plugins.platforms.whatsapp.adapter")

PLATFORM = "whatsapp{n}"


class WhatsAppSlotAdapter(_wa.WhatsAppAdapter):
    def __init__(self, config):
        super().__init__(config)
        # Trocar depois do super() e' seguro: a base so guarda o valor
        # (self.platform = platform), nao deriva nada dele no __init__.
        self.platform = Platform(PLATFORM)


def _build(config):
    return WhatsAppSlotAdapter(config)


def _check():
    # Cada slot e' ligado individualmente pelo config.yaml (enabled), que o
    # reconciliador so marca true quando o numero ja esta pareado. Amarrar
    # isso a WHATSAPP_ENABLED faria o slot seguir o estado do numero 1.
    return True


def register(ctx):
    ctx.register_platform(
        name=PLATFORM,
        label="WhatsApp ({n})",
        adapter_factory=_build,
        check_fn=_check,
        max_message_length=4096,
        emoji="\\N{{SPEECH BALLOON}}",
        allow_update_command=True,
    )
'''


def ensure_plugin(n):
    """Gera plugins/platforms/whatsapp<n>/ dentro da arvore do Hermes.

    Fica na arvore da imagem (nao no volume) de proposito: o enum Platform
    aceita nomes novos via scan de plugins/platforms SEM depender de o
    discovery ja ter rodado, o que torna o carregamento deterministico.
    Como /opt/hermes e' efemero (some ao recriar o container), o cont-init
    regenera isto a cada boot.
    """
    d = os.path.join(PLUGINS_DIR, "whatsapp%d" % n)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "plugin.yaml"), "w", encoding="utf-8") as f:
        f.write(
            "name: whatsapp%d-platform\n"
            "label: WhatsApp (%d)\n"
            "kind: platform\n"
            "version: 1.0.0\n"
            "description: Numero de WhatsApp adicional do Copiloto (slot %d).\n" % (n, n, n)
        )
    with open(os.path.join(d, "__init__.py"), "w", encoding="utf-8") as f:
        f.write("from .adapter import register\n\n__all__ = [\"register\"]\n")
    with open(os.path.join(d, "adapter.py"), "w", encoding="utf-8") as f:
        f.write(_PLUGIN_ADAPTER.format(n=n))
    return d


def prune_plugins(keep):
    """Remove plugins de slots que nao existem mais."""
    try:
        for name in os.listdir(PLUGINS_DIR):
            m = re.fullmatch(r"whatsapp(\d+)", name)
            if m and int(m.group(1)) not in keep:
                shutil.rmtree(os.path.join(PLUGINS_DIR, name), ignore_errors=True)
                _log("plugin %s removido (slot nao existe mais)" % name)
    except Exception:
        pass


# ---------------------------------------------------------------- config
def _platform_block(slot, native=False):
    """Bloco platforms.<x> do config.yaml para um slot.

    native=True quando a plataforma e' a "whatsapp" oficial — o slot 1, e
    tambem o WhatsApp dentro do perfil de um slot isolado. Nesse caso as
    chaves ficam no NIVEL DO BLOCO, que e' o caminho que o loader legado do
    Hermes ja traduz (e o formato validado em producao hoje).

    Para as plataformas extras (whatsapp2, whatsapp3...) esse tratamento
    legado nao existe, entao tudo precisa ir em `extra`, que o
    PlatformConfig.from_dict le diretamente.
    """
    groups = [g["id"] for g in slot.get("groups") or []]
    policies = {
        "dm_policy": "disabled",
        "group_policy": "allowlist",
        "group_allow_from": groups,
    }
    # Um slot so entra no ar depois de pareado: habilitar sem sessao faz o
    # adapter marcar erro fatal "enabled but not paired".
    block = {"enabled": bool(is_paired(slot))}

    if native:
        block.update(policies)
        # A porta so precisa ser dita quando NAO e' o slot 1 — um slot
        # isolado roda no gateway do proprio perfil, mas divide a maquina
        # com os outros bridges, entao nao pode ficar na 3000 padrao.
        if bridge_port(slot) != BASE_PORT:
            block["extra"] = {"bridge_port": bridge_port(slot)}
        # session_path fica de fora de proposito: o default do Hermes ja
        # resolve para dentro do HERMES_HOME certo (o do perfil, no caso
        # isolado), e fixar o caminho aqui so criaria uma segunda verdade.
    else:
        block["extra"] = dict(policies, bridge_port=bridge_port(slot),
                              session_path=session_path(slot))

    home = slot.get("home") or (groups[0] if groups else None)
    if home:
        name = ""
        for g in slot.get("groups") or []:
            if g["id"] == home:
                name = g.get("name") or ""
        block["home_channel"] = {
            "platform": platform_name(slot),
            "chat_id": home,
            "name": name or "Grupo do Copiloto",
        }
    return block


def _write_yaml(path, y):
    import yaml
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(y, f, allow_unicode=True, sort_keys=False)
    os.replace(tmp, path)
    _chown(path)


def _reconcile_main_config(cfg):
    """Escreve os slots compartilhados no config.yaml principal."""
    import yaml
    try:
        with open(CFG, encoding="utf-8") as f:
            y = yaml.safe_load(f) or {}
    except Exception as e:
        _log("config.yaml ilegivel (%s) — nada a fazer" % e)
        return

    platforms = y.setdefault("platforms", {})
    display = y.setdefault("display", {}).setdefault("platforms", {})

    shared = [s for s in cfg["slots"] if s.get("mode") != "isolated"]
    wanted = set()
    for slot in shared:
        p = platform_name(slot)
        wanted.add(p)
        block = _platform_block(slot, native=(p == "whatsapp"))
        # Preserva chaves que o usuario/painel tenham posto no bloco.
        cur = platforms.get(p) if isinstance(platforms.get(p), dict) else {}
        cur.update(block)
        platforms[p] = cur
        display[p] = dict(DISPLAY_QUIET)

    # Remove plataformas de slots apagados (so as nossas, whatsapp<N>).
    for key in list(platforms.keys()):
        if re.fullmatch(r"whatsapp\d+", str(key)) and key not in wanted:
            platforms.pop(key, None)
            display.pop(key, None)

    _write_yaml(CFG, y)
    _log("config.yaml reconciliado: %s" % ", ".join(sorted(wanted)) or "(vazio)")


# ---------------------------------------------------------------- perfis
def _reconcile_profile(slot):
    """Cria/atualiza o perfil de um slot isolado (copiloto independente)."""
    import yaml
    name = slot["id"]
    pdir = profile_dir(slot)
    created = not os.path.isdir(pdir)
    if created:
        try:
            sys.path.insert(0, "/opt/hermes")
            from hermes_cli.profiles import create_profile
            create_profile(name, no_alias=True)
            _log("perfil %s criado" % name)
        except Exception as e:
            _log("falha ao criar perfil %s: %s" % (name, e))
            os.makedirs(pdir, exist_ok=True)

    pcfg = os.path.join(pdir, "config.yaml")
    y = {}
    try:
        with open(pcfg, encoding="utf-8") as f:
            y = yaml.safe_load(f) or {}
    except Exception:
        y = {}

    # Herda do principal o que faz o copiloto ser o copiloto (modelo, voz,
    # silencio, Composio), mas com memoria e historico proprios.
    try:
        with open(CFG, encoding="utf-8") as f:
            main = yaml.safe_load(f) or {}
        for key in ("model", "stt", "approvals", "compression", "cron",
                    "onboarding", "mcp_servers"):
            if key in main and key not in y:
                y[key] = main[key]
        if "display" in main and "display" not in y:
            y["display"] = main["display"]
    except Exception:
        pass

    y.setdefault("platforms", {})["whatsapp"] = _platform_block(slot, native=True)
    y.setdefault("display", {}).setdefault("platforms", {})["whatsapp"] = dict(DISPLAY_QUIET)
    _write_yaml(pcfg, y)

    soul = os.path.join(pdir, "SOUL.md")
    if not os.path.exists(soul):
        for src in (os.path.join(DATA, "SOUL.md"), "/opt/copiloto/SOUL.md"):
            if os.path.exists(src):
                shutil.copy(src, soul)
                _chown(soul)
                break

    # Marca a intencao de rodar; o container_boot recria o servico s6 no
    # proximo boot e o service_manager registra agora, se puder.
    state = os.path.join(pdir, "gateway_state.json")
    try:
        cur = {}
        if os.path.exists(state):
            with open(state, encoding="utf-8") as f:
                cur = json.load(f) or {}
        cur["desired_state"] = "running" if is_paired(slot) else "stopped"
        with open(state, "w", encoding="utf-8") as f:
            json.dump(cur, f)
        _chown(state)
    except Exception:
        pass

    for root, dirs, files in os.walk(pdir):
        for p in dirs + files:
            _chown(os.path.join(root, p))
    _chown(pdir)

    if is_paired(slot):
        _register_profile_service(name)


def _register_profile_service(name):
    try:
        sys.path.insert(0, "/opt/hermes")
        from hermes_cli.service_manager import detect_service_manager
        sm = detect_service_manager()
        if getattr(sm, "supports_runtime_registration", lambda: False)():
            sm.register_profile_gateway(name, start=True)
            _log("gateway do perfil %s registrado" % name)
            return
    except Exception as e:
        _log("registro runtime do perfil %s falhou (%s) — sobe no proximo boot" % (name, e))


def _prune_profiles(cfg):
    """Perfis de slots apagados param de subir (os dados ficam)."""
    keep = {s["id"] for s in cfg["slots"] if s.get("mode") == "isolated"}
    base = os.path.join(DATA, "profiles")
    if not os.path.isdir(base):
        return
    for name in os.listdir(base):
        if not re.fullmatch(r"wa\d+", name) or name in keep:
            continue
        state = os.path.join(base, name, "gateway_state.json")
        try:
            cur = {}
            if os.path.exists(state):
                with open(state, encoding="utf-8") as f:
                    cur = json.load(f) or {}
            cur["desired_state"] = "stopped"
            with open(state, "w", encoding="utf-8") as f:
                json.dump(cur, f)
        except Exception:
            pass
        try:
            sys.path.insert(0, "/opt/hermes")
            from hermes_cli.service_manager import detect_service_manager
            sm = detect_service_manager()
            if getattr(sm, "supports_runtime_registration", lambda: False)():
                sm.unregister_profile_gateway(name)
        except Exception:
            pass


# ---------------------------------------------------------------- grupos
def add_group(cfg, slot_id, chat_id, name=""):
    slot = find_slot(cfg, slot_id)
    if not slot:
        return False, "slot nao encontrado"
    groups = slot.setdefault("groups", [])
    for g in groups:
        if g["id"] == chat_id:
            if name and not g.get("name"):
                g["name"] = name
            return True, "ja estava ativo"
    groups.append({"id": chat_id, "name": name or ""})
    if not slot.get("home"):
        slot["home"] = chat_id
    return True, "adicionado"


def remove_group(cfg, slot_id, chat_id):
    slot = find_slot(cfg, slot_id)
    if not slot:
        return False, "slot nao encontrado"
    before = len(slot.get("groups") or [])
    slot["groups"] = [g for g in (slot.get("groups") or []) if g["id"] != chat_id]
    if slot.get("home") == chat_id:
        slot["home"] = slot["groups"][0]["id"] if slot["groups"] else None
    return len(slot["groups"]) < before, "removido"


# ---------------------------------------------------------------- publico
def reconcile(cfg=None):
    cfg = cfg or load_or_migrate()
    os.makedirs(REQ_DIR, exist_ok=True)
    _chown(WA_DIR)
    _chown(REQ_DIR)

    nums = set()
    for slot in cfg["slots"]:
        if slot.get("mode") == "isolated":
            continue
        n = slot_num(slot)
        if n > 1:
            ensure_plugin(n)
            nums.add(n)
    prune_plugins(nums)

    _reconcile_main_config(cfg)

    for slot in cfg["slots"]:
        if slot.get("mode") == "isolated":
            _reconcile_profile(slot)
    _prune_profiles(cfg)
    return cfg


def restart_gateway(profile=None):
    svc = "gateway-%s" % (profile or "default")
    for cmd in ("/command/s6-svc -r /run/service/%s" % svc,
                "s6-svc -r /run/service/%s" % svc):
        try:
            if subprocess.call(cmd.split(), stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL) == 0:
                return True
        except Exception:
            continue
    return False


def fix_perms():
    try:
        subprocess.call(["chown", "-R", "%d:%d" % (HERMES_UID, HERMES_GID), DATA],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "reconcile"
    cfg = load_or_migrate()
    if cmd == "list":
        for s in cfg["slots"]:
            print("%-5s %-18s %-9s porta=%-5d pareado=%-5s grupos=%d" % (
                s["id"], s.get("label") or "", s.get("mode"), bridge_port(s),
                is_paired(s), len(s.get("groups") or [])))
        return 0
    reconcile(cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
