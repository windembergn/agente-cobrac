#!/usr/bin/env python3
"""Traduz o aviso de troca de modelo do Hermes, e tira o jargao dele.

O Hermes ja faz o certo: quando o modelo principal cai no meio de uma resposta
(cota do plano estourada, provedor sobrecarregado, 500), ele desce para o
proximo da cadeia NA HORA e emite UM aviso dizendo o que trocou e por que
(agent/chat_completion_helpers.py -> _pending_fallback_notice).

O problema e' o texto:

    "⚠️ Model fallback: X via anthropic unavailable (rate limit); using Y via anthropic."

Ingles e nome de provedor — as duas coisas que a persona do Copiloto proibe no
grupo do cirurgiao. Este patch troca a montagem desse texto por uma versao em
PT-BR/ES que diz a mesma coisa em portugues de gente, e mantem os nomes dos
MODELOS de proposito: e' a informacao que faz o dono da instalacao entender que
precisa por credito, e nao "o sistema piorou sozinho".

Roda no BUILD (Dockerfile), como o patch-bridge.py: /opt/hermes vem da imagem.
Falha com codigo != 0 se o alvo nao existir mais — melhor descobrir no build,
quando a imagem nova do Hermes mudar o trecho, do que em producao.
"""
import io
import sys

ALVO = sys.argv[1] if len(sys.argv) > 1 else "/opt/hermes/agent/chat_completion_helpers.py"

TRECHO_ANTIGO = '''        notice = (
            f"⚠️ Model fallback: {old_model} via {old_provider} unavailable "
            f"({_fallback_reason_text(reason)}); using {fb_model} via {fb_provider}."
        )'''

TRECHO_NOVO = '''        notice = _copiloto_aviso_fallback(old_model, fb_model, reason)'''

FUNCAO = '''

# ===================== COPILOTO (patch da imagem) =====================
# O aviso de troca de modelo, em PT-BR/ES e sem jargao. Ver
# /opt/copiloto/patch-aviso-fallback.py para o porque.
_COPILOTO_MOTIVOS = {
    "pt": {
        "billing": "créditos ou cota esgotados",
        "rate_limit": "limite de uso atingido",
        "upstream_rate_limit": "limite de uso do modelo",
        "auth": "credencial recusada",
        "auth_permanent": "credencial recusada",
        "overloaded": "provedor sobrecarregado",
        "server_error": "erro no provedor",
        "timeout": "tempo de resposta esgotado",
        "context_overflow": "conversa longa demais para esse modelo",
        "model_not_found": "modelo indisponível nesta conta",
    },
    "es": {
        "billing": "créditos o cuota agotados",
        "rate_limit": "límite de uso alcanzado",
        "upstream_rate_limit": "límite de uso del modelo",
        "auth": "credencial rechazada",
        "auth_permanent": "credencial rechazada",
        "overloaded": "proveedor sobrecargado",
        "server_error": "error del proveedor",
        "timeout": "tiempo de respuesta agotado",
        "context_overflow": "conversación demasiado larga para ese modelo",
        "model_not_found": "modelo no disponible en esta cuenta",
    },
}
_COPILOTO_MOTIVO_PADRAO = {"pt": "falha no provedor", "es": "fallo del proveedor"}
_COPILOTO_AVISO = {
    "pt": ("⚠️ Troquei de modelo: {antigo} está indisponível agora ({motivo}). "
           "Segui com {novo} para não te deixar esperando."),
    "es": ("⚠️ He cambiado de modelo: {antigo} no está disponible ahora ({motivo}). "
           "Sigo con {novo} para no dejarte esperando."),
}


def _copiloto_idioma():
    import os
    v = (os.environ.get("COPILOTO_IDIOMA") or "pt").strip().lower()[:2]
    return "es" if v == "es" else "pt"


def _copiloto_aviso_fallback(old_model, fb_model, reason):
    """Uma linha, no idioma da instalacao, dizendo o que trocou e por que."""
    idi = _copiloto_idioma()
    chave = getattr(reason, "value", None) or str(reason or "")
    motivo = _COPILOTO_MOTIVOS[idi].get(chave) or _COPILOTO_MOTIVO_PADRAO[idi]
    return _COPILOTO_AVISO[idi].format(
        antigo=old_model, novo=fb_model, motivo=motivo,
    )
# =================== fim do patch do Copiloto ===================
'''

ANCORA = 'def _fallback_reason_text('


def main():
    NL = chr(10)
    try:
        s = io.open(ALVO, encoding="utf-8").read()
    except OSError as e:
        print("[patch-aviso] nao consegui abrir %s: %s" % (ALVO, e))
        return 1

    if "_copiloto_aviso_fallback" in s:
        print("[patch-aviso] ja aplicado")
        return 0

    if s.count(TRECHO_ANTIGO) != 1:
        print("[patch-aviso] ERRO: o texto do aviso mudou nesta versao do Hermes "
              "(achei %d ocorrencias do trecho esperado)." % s.count(TRECHO_ANTIGO))
        print("[patch-aviso] Conferir agent/chat_completion_helpers.py e atualizar o patch.")
        return 1
    if s.count(ANCORA) != 1:
        print("[patch-aviso] ERRO: nao achei onde inserir a funcao (%r)." % ANCORA)
        return 1

    s = s.replace(TRECHO_ANTIGO, TRECHO_NOVO)
    # A funcao entra ANTES de _fallback_reason_text, para ficar junto do assunto.
    pos = s.index(ANCORA)
    inicio = s.rfind(NL, 0, pos) + 1
    s = s[:inicio] + FUNCAO.lstrip(NL) + NL + s[inicio:]

    io.open(ALVO, "w", encoding="utf-8", newline=NL).write(s)
    print("[patch-aviso] aviso de troca de modelo agora sai em PT-BR/ES")
    return 0


if __name__ == "__main__":
    sys.exit(main())
