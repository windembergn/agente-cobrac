#!/usr/bin/env python3
"""Copiloto — atualizacao automatica.

Confere de tempos em tempos se saiu versao nova da imagem e, quando sair, se
atualiza sozinho. Assim o cirurgiao recebe correcao sem precisar abrir o
Portainer nem saber que existe um `/update`.

Tres decisoes que explicam o desenho:

1. **Mora DENTRO da imagem.** Nao e' um servico novo na stack — se fosse, todo
   mundo que ja instalou precisaria editar a stack para receber, que e'
   exatamente o trabalho que isto existe para evitar. Quem ja instalou pega o
   auto-update UMA vez (pelo /update ou pelo painel) e dali em diante e' sozinho.

2. **Confere sem baixar nada.** Pergunta o digest ao registro (uma requisicao
   de ~1 KB, anonima, porque a imagem e' publica) e compara com o que esta
   rodando. So baixa a imagem quando realmente mudou.

3. **So atualiza com o copiloto OCIOSO.** A troca derruba o container por cerca
   de um minuto. Fazer isso no meio de um pedido — um audio sendo transcrito,
   uma pagina sendo escrita — perderia o trabalho do cirurgiao. Se estiver
   ocupado, espera a proxima rodada.

Desliga com COPILOTO_AUTO_UPDATE=off na stack.
"""
import json
import os
import random
import sqlite3
import sys
import time
import urllib.request

sys.path.insert(0, "/opt/copiloto")

DATA = os.environ.get("COPILOTO_DATA", "/opt/data")
IMAGEM = os.environ.get("COPILOTO_IMAGEM", "ghcr.io/windembergn/copiloto-cirurgiao")
# O canal que as instalacoes seguem. `latest` e' a versao JA VALIDADA — o que
# ainda nao foi testado sobe em outra tag (homolog) e nao chega a ninguem.
CANAL = os.environ.get("COPILOTO_CANAL", "latest")
LIGADO = os.environ.get("COPILOTO_AUTO_UPDATE", "on").strip().lower() not in (
    "off", "0", "false", "nao", "não"
)
INTERVALO_S = int(os.environ.get("COPILOTO_UPDATE_CHECK_S", "120"))
# Quanto tempo sem mensagem nova para considerar que ninguem esta usando.
OCIOSO_S = int(os.environ.get("COPILOTO_UPDATE_OCIOSO_S", "180"))

TURNO = os.path.join(DATA, "whatsapp", "turno_atual.json")
STATE_DB = os.path.join(DATA, "state.db")
AVISO = os.path.join(DATA, ".copiloto_avisar_update")
BRIDGE_SEND = os.environ.get("COPILOTO_BRIDGE_SEND_URL", "http://127.0.0.1:3000/send")
CONFIG = os.path.join(DATA, "config.yaml")


def _log(msg):
    print("[auto-update] %s" % msg, flush=True)


# ------------------------------------------------------------------ registro
def digest_publicado(tag):
    """Digest da tag no GHCR, sem baixar a imagem. None se nao der pra saber."""
    repo = IMAGEM.split("/", 1)[1] if "/" in IMAGEM else IMAGEM
    try:
        url = "https://ghcr.io/token?scope=repository:%s:pull&service=ghcr.io" % repo
        with urllib.request.urlopen(url, timeout=20) as r:
            token = json.loads(r.read())["token"]
        req = urllib.request.Request(
            "https://ghcr.io/v2/%s/manifests/%s" % (repo, tag), method="HEAD"
        )
        req.add_header("Authorization", "Bearer " + token)
        req.add_header(
            "Accept",
            "application/vnd.oci.image.index.v1+json, "
            "application/vnd.docker.distribution.manifest.list.v2+json",
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.headers.get("Docker-Content-Digest")
    except Exception as e:
        _log("nao consegui consultar o registro (%s)" % e)
        return None


VERSAO = os.path.join(DATA, ".copiloto_versao")


def versao_instalada():
    """Digest que esta instalado aqui, segundo o nosso proprio registro.

    NAO se pergunta ao Docker qual imagem esta rodando, e isso e' deliberado:
      - `docker image inspect <tag>` responde o que a TAG aponta no disco, que
        pode ja ser a versao nova (por exemplo, num host que tambem builda) —
        e ai o copiloto se acharia atualizado sem estar;
      - o `.Image` do container as vezes e' o digest do manifesto e as vezes o
        digest da config, dependendo da versao do Docker e do armazenamento.
        No segundo caso ele NUNCA seria igual ao digest do registro, e o
        copiloto se atualizaria a cada rodada — um loop de reinicio na cara do
        cirurgiao.

    Entao guardamos nos, num arquivo do volume: e' deterministico e nao tem como
    entrar em loop. Na primeira execucao adotamos o que esta publicado como
    linha de base (a instalacao acabou de receber esta imagem, entao esta em dia).
    """
    try:
        with open(VERSAO, encoding="utf-8") as f:
            return (f.read() or "").strip() or None
    except OSError:
        return None


def anotar_versao(digest):
    try:
        with open(VERSAO, "w", encoding="utf-8") as f:
            f.write(digest)
    except OSError as e:
        _log("nao consegui anotar a versao (%s)" % e)


# -------------------------------------------------------------------- ocioso
def _ts_segundos(valor):
    """O bridge grava Date.now() (MILISSEGUNDOS); outros pontos gravam segundos."""
    try:
        v = float(valor or 0)
    except (TypeError, ValueError):
        return 0.0
    return v / 1000.0 if v > 1e11 else v


def esta_ocioso():
    """True quando nao ha turno em andamento nem conversa recente.

    Fail-closed: se nao der para ter certeza, responde False (nao atualiza).
    Adiar uma atualizacao custa alguns minutos; interromper o cirurgiao no meio
    de um pedido custa o trabalho dele.
    """
    try:
        conn = sqlite3.connect("file:%s?mode=ro" % STATE_DB, uri=True, timeout=5)
        try:
            for (entrada,) in conn.execute("SELECT entry_json FROM gateway_routing"):
                try:
                    e = json.loads(entrada)
                except ValueError:
                    continue
                if e.get("active_turn_token") or e.get("active_turn_started_at"):
                    return False
        finally:
            conn.close()
    except sqlite3.Error as e:
        _log("nao consegui ler o estado das sessoes (%s) — adiando" % e)
        return False

    try:
        with open(TURNO, encoding="utf-8") as f:
            t = json.load(f)
        if time.time() - _ts_segundos(t.get("ts")) < OCIOSO_S:
            return False
    except (OSError, ValueError):
        # Sem marcador (ninguem falou com ele desde o boot) — pode atualizar.
        pass
    return True


# --------------------------------------------------------------------- aviso
def avisar(chat_id, texto):
    if not chat_id:
        return
    try:
        corpo = json.dumps({"chatId": chat_id, "message": texto}).encode()
        req = urllib.request.Request(
            BRIDGE_SEND, data=corpo,
            headers={"Content-Type": "application/json"}, method="POST",
        )
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:
        _log("nao consegui avisar no grupo (%s)" % e)


def grupo_principal():
    try:
        import copiloto_self
        return copiloto_self.grupo_principal()
    except Exception:
        return ""


# ---------------------------------------------------------------------- loop
def main():
    if not LIGADO:
        _log("desligado nesta instalacao (COPILOTO_AUTO_UPDATE=off)")
        return 0

    import copiloto_self as cs

    if not cs.SSH_KEY.exists():
        _log("sem acesso ao servidor — atualizacao automatica indisponivel aqui")
        return 0

    # Cada instalacao comeca num minuto diferente: sem isto, todas consultariam
    # o registro no mesmo instante depois de um deploy nosso.
    time.sleep(random.uniform(10, 90))
    _log("ligado — canal '%s', conferindo a cada %ds" % (CANAL, INTERVALO_S))

    ultimo_avisado = None
    while True:
        try:
            publicado = digest_publicado(CANAL)
            if publicado:
                atual = versao_instalada()
                if atual is None:
                    anotar_versao(publicado)
                    _log("linha de base: %s" % publicado[:19])
                elif publicado != atual:
                    if esta_ocioso():
                        servico, motivo = cs._servico_do_copiloto()
                        if not servico:
                            _log("nao achei meu servico (%s)" % motivo)
                        else:
                            chat = grupo_principal()
                            try:
                                with open(AVISO, "w", encoding="utf-8") as f:
                                    json.dump({"chat_id": chat, "ts": time.time()}, f)
                            except OSError:
                                pass
                            avisar(chat, "🔄 Saiu uma versão nova minha — vou me "
                                          "atualizar agora. Volto em cerca de um minuto.")
                            ok, saida = cs.disparar_update(servico, CANAL)
                            if ok:
                                # Anota ANTES de morrer: se ficasse para depois,
                                # o container novo nao saberia que ja aplicou e
                                # tentaria de novo, e de novo.
                                anotar_versao(publicado)
                                _log("atualizando para %s" % publicado[:19])
                                # O container morre em seguida; nao ha o que fazer aqui.
                                time.sleep(300)
                            else:
                                try:
                                    os.unlink(AVISO)
                                except OSError:
                                    pass
                                _log("falhei ao disparar (%s)" % saida[:160])
                    elif publicado != ultimo_avisado:
                        ultimo_avisado = publicado
                        _log("versao nova disponivel, mas ele esta ocupado — espero")
        except Exception as e:  # nunca deixa o servico morrer por um erro de rede
            _log("erro na rodada (%s)" % e)
        time.sleep(INTERVALO_S)


if __name__ == "__main__":
    sys.exit(main())
