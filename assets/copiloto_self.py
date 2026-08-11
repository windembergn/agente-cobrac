#!/usr/bin/env python3
"""Copiloto — auto-ajuste seguro (usado pelo AGENTE, nao pelo cirurgiao).

Verbos:
  ajuste "<motivo>"  tira copia de seguranca do estado atual (SEMPRE antes de mudar)
  desfazer           volta ao estado da ultima copia
  historico          lista as copias, da mais nova pra mais velha
  reiniciar          reinicia o gateway para aplicar mudanca de config
  status             o que ja foi alterado em relacao ao original
  fabrica            ultimo recurso: descarta TODOS os ajustes (nao desconecta o WhatsApp)

Trava de grupo: os verbos que MUDAM alguma coisa so rodam se a mensagem que esta
sendo atendida veio do grupo principal (o primeiro ativado, campo "home" do slot 1).
O bridge grava a origem do turno em whatsapp/turno_atual.json; sem marcador fresco
o script RECUSA (fail-closed) — e melhor bloquear um ajuste legitimo do que aceitar
um pedido vindo de um grupo secundario.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

DATA = Path(os.environ.get("COPILOTO_DATA", "/opt/data"))
BACKUPS = DATA / "copiloto-backups"
FABRICA = DATA / ".fabrica"
SLOTS = DATA / "whatsapp" / "slots.json"
TURNO = DATA / "whatsapp" / "turno_atual.json"
SKILLS = DATA / "skills"

# Arquivos versionados a cada "ajuste". Caminhos relativos a DATA.
ITENS = ["config.yaml", "SOUL.md", "CLAUDE.md"]

# As skills sao tratadas a parte: /opt/data/skills tem ~8,5 MB de skills nativas
# que vem prontas no sistema. Copiar tudo a cada ajuste encheria o disco por nada,
# entao versionamos SO as pastas que o agente criou — as nativas ficam onde estao.
# A lista das nativas e' gravada no primeiro boot em .fabrica/skills_originais.txt.
SKILLS_ORIG = FABRICA / "skills_originais.txt"

# Janela em que o marcador de turno ainda vale. Um turno longo (audio grande,
# documento pesado) leva minutos; acima disso o marcador e' velho demais pra
# provar de onde veio o pedido.
TURNO_VALIDO_S = 900
MAX_BACKUPS = 30


def _erro(msg, dica=""):
    print("ERRO: " + msg)
    if dica:
        print(dica)
    sys.exit(1)


def _ok(msg):
    print(msg)
    sys.exit(0)


def grupo_principal():
    """chat_id do grupo principal = 'home' do slot 1 (o primeiro ativado)."""
    try:
        d = json.loads(SLOTS.read_text(encoding="utf-8"))
        for s in d.get("slots", []):
            if s.get("id") == "wa1":
                return (s.get("home") or "").strip()
        slots = d.get("slots") or []
        return (slots[0].get("home") or "").strip() if slots else ""
    except Exception:
        return ""


def exige_grupo_principal(verbo):
    """Fail-closed: so segue se o turno atual veio do grupo principal."""
    home = grupo_principal()
    if not home:
        # Nenhum grupo ativado ainda: nao ha grupo secundario de onde um pedido
        # pudesse vir, entao nao ha o que proteger.
        return
    try:
        t = json.loads(TURNO.read_text(encoding="utf-8"))
        origem = (t.get("chat_id") or "").strip()
        quando = float(t.get("ts") or 0)
    except Exception:
        _erro(
            "nao consegui confirmar de qual grupo veio este pedido, entao nao vou "
            "mexer em nada (verbo: %s)." % verbo,
            "Peca ao cirurgiao para repetir o pedido no grupo principal.",
        )
    idade = time.time() - (quando / 1000.0 if quando > 1e11 else quando)
    if idade > TURNO_VALIDO_S:
        _erro(
            "o pedido e' antigo demais para eu confirmar a origem (%d min)." % (idade // 60),
            "Peca ao cirurgiao para repetir o pedido agora, no grupo principal.",
        )
    if origem != home:
        _erro(
            "este pedido nao veio do grupo principal — ajuste so no grupo principal.",
            "Responda ao pedinte que mudancas no seu funcionamento so sao aceitas "
            "no grupo principal do cirurgiao.",
        )


def _copiar(origem: Path, destino: Path):
    if not origem.exists():
        return False
    destino.parent.mkdir(parents=True, exist_ok=True)
    if origem.is_dir():
        if destino.exists():
            shutil.rmtree(destino, ignore_errors=True)
        shutil.copytree(origem, destino, dirs_exist_ok=True)
    else:
        shutil.copy2(origem, destino)
    return True


def skills_nativas():
    """Nomes das skills que ja vinham no sistema (nao sao do agente)."""
    try:
        return {
            l.strip()
            for l in SKILLS_ORIG.read_text(encoding="utf-8").splitlines()
            if l.strip()
        }
    except Exception:
        return set()


def skills_do_agente():
    """Pastas em /opt/data/skills que o agente criou."""
    if not SKILLS.is_dir():
        return []
    nativas = skills_nativas()
    return [p for p in sorted(SKILLS.iterdir()) if p.is_dir() and p.name not in nativas]


def _snapshot(motivo, prefixo="ajuste"):
    ts = time.strftime("%Y%m%d-%H%M%S")
    dest = BACKUPS / ("%s-%s" % (ts, prefixo))
    dest.mkdir(parents=True, exist_ok=True)
    salvos = [i for i in ITENS if _copiar(DATA / i, dest / i)]
    proprias = skills_do_agente()
    for p in proprias:
        _copiar(p, dest / "skills" / p.name)
    if proprias:
        salvos.append("skills (%d sua(s))" % len(proprias))
    (dest / "motivo.txt").write_text(
        (motivo or "(sem motivo)") + "\n", encoding="utf-8"
    )
    _podar()
    return dest, salvos


def _restaurar_skills(origem: Path):
    """Deixa /opt/data/skills exatamente com as nativas + as da copia."""
    for p in skills_do_agente():
        shutil.rmtree(p, ignore_errors=True)
    guardadas = origem / "skills"
    if guardadas.is_dir():
        for p in guardadas.iterdir():
            if p.is_dir():
                _copiar(p, SKILLS / p.name)


def _podar():
    try:
        todas = sorted([p for p in BACKUPS.iterdir() if p.is_dir()])
        for velha in todas[:-MAX_BACKUPS]:
            shutil.rmtree(velha, ignore_errors=True)
    except Exception:
        pass


def _lista_backups():
    if not BACKUPS.exists():
        return []
    return sorted([p for p in BACKUPS.iterdir() if p.is_dir()], reverse=True)


def cmd_ajuste(motivo):
    dest, salvos = _snapshot(motivo)
    _ok(
        "copia de seguranca guardada (%s). Itens: %s.\nPode fazer a mudanca. "
        "Se der errado: /opt/data/copiloto desfazer"
        % (dest.name, ", ".join(salvos) or "nenhum")
    )


def cmd_desfazer():
    exige_grupo_principal("desfazer")
    todas = _lista_backups()
    if not todas:
        _erro(
            "nao existe nenhuma copia de seguranca para voltar.",
            "Da proxima vez rode 'ajuste \"<motivo>\"' ANTES de mudar qualquer coisa.",
        )
    ultima = todas[0]
    # Guarda o estado atual antes de sobrescrever: desfazer tambem tem que ter volta.
    _snapshot("antes de desfazer para " + ultima.name, prefixo="predesfazer")
    voltou = []
    for i in ITENS:
        if (ultima / i).exists():
            _copiar(ultima / i, DATA / i)
            voltou.append(i)
    _restaurar_skills(ultima)
    voltou.append("skills")
    motivo = ""
    try:
        motivo = (ultima / "motivo.txt").read_text(encoding="utf-8").strip()
    except Exception:
        pass
    print("voltei ao estado de %s (%s). Itens: %s." % (ultima.name, motivo, ", ".join(voltou)))
    print("Se a mudanca era de config.yaml, rode agora: /opt/data/copiloto reiniciar")
    sys.exit(0)


def cmd_historico():
    todas = _lista_backups()
    if not todas:
        _ok("nenhuma copia de seguranca ainda.")
    print("copias (da mais nova pra mais velha):")
    for p in todas[:15]:
        try:
            motivo = (p / "motivo.txt").read_text(encoding="utf-8").strip()
        except Exception:
            motivo = "(sem motivo)"
        print("  %s — %s" % (p.name, motivo))
    sys.exit(0)


def cmd_reiniciar():
    exige_grupo_principal("reiniciar")
    r = subprocess.run(
        ["/command/s6-svc", "-r", "/run/service/gateway-default"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        _erro(
            "nao consegui reiniciar (%s)." % (r.stderr or r.stdout or "sem detalhe").strip(),
            "Avise que o ajuste vai valer sozinho na proxima atualizacao do sistema.",
        )
    _ok(
        "reiniciando — volto em alguns segundos e o WhatsApp reconecta sozinho.\n"
        "Avise o cirurgiao em uma linha ('um instante, aplicando o ajuste')."
    )


def cmd_status():
    if not FABRICA.exists():
        _ok("nao encontrei o estado original para comparar.")
    mudou, iguais = [], []
    for i in ITENS:
        orig, atual = FABRICA / i, DATA / i
        # O config.yaml e' reescrito pelo proprio sistema em todo boot (Composio,
        # slots, normalizacao do Hermes). Comparar contra o de fabrica acusaria
        # essa reescrita como "mudanca sua"; o que interessa e' o que mudou
        # DEPOIS que o sistema assentou.
        if i == "config.yaml" and (FABRICA / "config_aplicado.yaml").exists():
            orig = FABRICA / "config_aplicado.yaml"
        if not orig.exists():
            if atual.exists():
                mudou.append(i + " (criado por voce)")
            continue
        if not atual.exists():
            mudou.append(i + " (apagado)")
        else:
            (mudou if orig.read_bytes() != atual.read_bytes() else iguais).append(i)
    proprias = skills_do_agente()
    if proprias:
        mudou.append("skills que voce criou: " + ", ".join(p.name for p in proprias))
    print("alterado por voce: " + (", ".join(mudou) if mudou else "nada"))
    print("igual ao original: " + (", ".join(iguais) if iguais else "nada"))
    print("copias de seguranca: %d" % len(_lista_backups()))
    sys.exit(0)


def cmd_fabrica(forcado=False):
    # --forcado: chamado pelo cont-init quando o cirurgiao aperta "Restaurar
    # original" no painel. Nesse caso nao ha turno de WhatsApp para conferir —
    # quem pediu foi o dono do painel, autenticado por senha.
    if not forcado:
        exige_grupo_principal("fabrica")
    if not FABRICA.exists():
        _erro("nao encontrei o estado original guardado; nao vou apagar nada.")
    _snapshot("antes do restaurar original", prefixo="prefabrica")
    for i in ITENS:
        if (FABRICA / i).exists():
            _copiar(FABRICA / i, DATA / i)
    # Skills: apaga so as que o agente criou; as nativas ficam intactas.
    apagadas = [p.name for p in skills_do_agente()]
    for p in skills_do_agente():
        shutil.rmtree(p, ignore_errors=True)
    if apagadas:
        print("removi as skills que voce tinha criado: " + ", ".join(apagadas))
    print("restaurei o estado original. O WhatsApp segue conectado e os grupos, ativos.")
    print("Agora rode: /opt/data/copiloto reiniciar")
    sys.exit(0)


USO = __doc__


def main():
    if len(sys.argv) < 2:
        print(USO)
        sys.exit(2)
    v = sys.argv[1].strip().lower()
    flags = [a for a in sys.argv[2:] if a.startswith("--")]
    positivos = [a for a in sys.argv[2:] if not a.startswith("--")]
    arg = positivos[0] if positivos else ""
    forcado = "--forcado" in flags
    BACKUPS.mkdir(parents=True, exist_ok=True)
    if v in ("ajuste", "backup", "copia"):
        cmd_ajuste(arg)
    elif v in ("desfazer", "undo", "voltar"):
        cmd_desfazer()
    elif v in ("historico", "historico", "copias"):
        cmd_historico()
    elif v in ("reiniciar", "restart"):
        cmd_reiniciar()
    elif v == "status":
        cmd_status()
    elif v in ("fabrica", "original", "reset"):
        cmd_fabrica(forcado)
    else:
        print(USO)
        sys.exit(2)


if __name__ == "__main__":
    main()
