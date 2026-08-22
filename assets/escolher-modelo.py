#!/usr/bin/env python3
"""Escolhe o cerebro do Copiloto e imprime duas linhas para o cont-init:

    provider=<id>
    default=<modelo>

Regra: se a stack trouxer ANTHROPIC_API_KEY valida, o cerebro vira Claude
(melhor em redacao longa e MUITO melhor em HTML/CSS — que e' o que faz a
pagina publicada sair bonita). Sem a chave, segue no gpt-5 de sempre.

O modelo NAO e' fixo no codigo: perguntamos ao proprio /v1/models qual existe
hoje e escolhemos o melhor da familia pedida. Uma imagem construida hoje
continua acertando o modelo daqui a seis meses, sem rebuild.

COPILOTO_MODELO=<id> manda em tudo (ex: trocar Sonnet por Opus).
Sai 0 sempre; qualquer falha cai no padrao e o boot segue.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

TIMEOUT = 12
PLACEHOLDERS = ("cole", "sua-chave", "sk-cole", "xxx", "troque", "placeholder")

# Familia preferida: SONNET, sempre, e de proposito.
#
# Opus e' melhor por resposta, mas o Copiloto fica ligado o dia inteiro
# processando audio, imagem e documento — no token do plano ele torraria a cota
# de Opus em poucas horas e o cirurgiao ficaria sem copiloto no meio do dia; na
# chave avulsa, a conta sobe na mesma proporcao. Com o kit de design fazendo o
# acabamento das paginas, a diferenca pratica e' pequena.
# Quem quiser o topo: COPILOTO_FAMILIA=opus na stack.
FALLBACK_ANTHROPIC = "claude-sonnet-4-5-20250929"
FALLBACK_OPENAI = "gpt-5"


def limpa(v):
    v = (v or "").strip().strip('"').strip("'")
    if not v or len(v) < 12:
        return ""
    if any(p in v.lower() for p in PLACEHOLDERS):
        return ""
    return v


def limpa_texto(v):
    """Como limpa(), mas sem exigir tamanho de chave (serve para nome de modelo)."""
    v = (v or "").strip().strip('"').strip("'")
    if not v or any(p in v.lower() for p in PLACEHOLDERS):
        return ""
    return v


def peso(modelo_id):
    """Ordena ids tipo claude-opus-4-6 / claude-sonnet-5 / claude-opus-4-5-20251101."""
    numeros = [int(n) for n in re.findall(r"\d+", modelo_id)]
    # a data no fim (8 digitos) nao e' versao — vira desempate, nao peso maior
    versao = [n for n in numeros if n < 1000][:3]
    data = [n for n in numeros if n >= 1000][:1]
    while len(versao) < 3:
        versao.append(0)
    return tuple(versao) + tuple(data or [0])


def eh_token_do_plano(chave):
    """sk-ant-oat* = setup-token do Claude Code (assinatura), nao chave de API."""
    return chave.startswith("sk-ant-oat") or chave.startswith("cc-")


def familia_preferida(chave):
    escolhida = limpa_texto(os.environ.get("COPILOTO_FAMILIA"))
    return escolhida.lower() if escolhida else "sonnet"


def lista_modelos(chave):
    # Token do plano nao passa em x-api-key: a API so o aceita como Bearer, e
    # so com o beta de oauth ligado. E' a mesma distincao que o Hermes faz em
    # agent/anthropic_adapter.py — se mudar aqui, conferir la tambem.
    if eh_token_do_plano(chave):
        cabecalhos = {
            "Authorization": "Bearer " + chave,
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "oauth-2025-04-20",
        }
    else:
        cabecalhos = {"x-api-key": chave, "anthropic-version": "2023-06-01"}
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/models?limit=100", headers=cabecalhos,
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        corpo = json.loads(r.read().decode("utf-8"))
    return [m.get("id", "") for m in corpo.get("data", []) if m.get("id")]


def escolhe_claude(chave):
    """(modelo, motivo). Nunca levanta excecao."""
    forcado = limpa_texto(os.environ.get("COPILOTO_MODELO"))
    try:
        ids = lista_modelos(chave)
    except urllib.error.HTTPError as e:
        return ("", "a chave da Anthropic foi recusada (HTTP %s)" % e.code)
    except Exception as e:
        # Rede fora no boot nao pode custar o cerebro bom: seguimos com o
        # fallback, que so erra se a Anthropic aposentar o modelo.
        if forcado:
            return (forcado, "sem resposta da API (%s); usando o modelo pedido na stack" % e)
        return (FALLBACK_ANTHROPIC, "sem resposta da API (%s); usando o padrao embutido" % e)

    if forcado:
        if forcado in ids:
            return (forcado, "modelo pedido na stack")
        parciais = sorted([i for i in ids if forcado in i], key=peso, reverse=True)
        if parciais:
            return (parciais[0], "modelo pedido na stack (resolvido para o mais novo)")
        return (FALLBACK_ANTHROPIC,
                "COPILOTO_MODELO='%s' nao existe nesta conta; usando o padrao" % forcado)

    for familia in (familia_preferida(chave), "sonnet", "opus"):
        candidatos = [i for i in ids if ("claude-%s" % familia) in i]
        if candidatos:
            melhor = sorted(candidatos, key=peso, reverse=True)[0]
            return (melhor, "melhor %s disponivel na conta" % familia)
    if ids:
        return (sorted(ids, key=peso, reverse=True)[0], "unico disponivel na conta")
    return ("", "a conta nao listou nenhum modelo")


def aplicar(provider, modelo):
    """Grava o cerebro escolhido no config.yaml VIVO.

    O config.yaml so nasce no primeiro boot, entao sem isto uma instalacao que
    ja existia continuaria no gpt-5 depois de colar a chave da Anthropic na
    stack — exatamente o erro que o Composio ja nos custou uma vez.
    """
    import yaml
    caminho = os.path.join(os.environ.get("COPILOTO_DATA", "/opt/data"), "config.yaml")
    try:
        with open(caminho) as fh:
            cfg = yaml.safe_load(fh) or {}
    except Exception:
        return
    atual = cfg.get("model") or {}
    if atual.get("provider") == provider and atual.get("default") == modelo:
        print("modelo=inalterado", file=sys.stderr)
        return
    atual["provider"] = provider
    atual["default"] = modelo
    cfg["model"] = atual
    tmp = caminho + ".tmp"
    with open(tmp, "w") as fh:
        yaml.safe_dump(cfg, fh, sort_keys=False, allow_unicode=True)
    os.replace(tmp, caminho)
    print("modelo=atualizado para %s/%s" % (provider, modelo), file=sys.stderr)


def preferencia():
    """Escolha manual do cirurgiao, feita por `copiloto cerebro <...>`.

    Vive em $DATA/cerebro.json e ganha da deteccao automatica — senao a proxima
    atualizacao da stack desfaria a troca que ele pediu no grupo. "auto" (ou
    arquivo ausente) devolve a decisao para a deteccao.
    """
    caminho = os.path.join(os.environ.get("COPILOTO_DATA", "/opt/data"), "cerebro.json")
    try:
        with open(caminho) as fh:
            d = json.load(fh) or {}
    except Exception:
        return {}
    if (d.get("provider") or "auto") == "auto":
        return {}
    return d


def main():
    if len(sys.argv) > 3 and sys.argv[1] == "--aplicar":
        aplicar(sys.argv[2], sys.argv[3])
        return

    pref = preferencia()
    if pref.get("familia"):
        os.environ["COPILOTO_FAMILIA"] = pref["familia"]
    if pref.get("modelo"):
        os.environ["COPILOTO_MODELO"] = pref["modelo"]

    chave = (limpa(os.environ.get("ANTHROPIC_API_KEY"))
             or limpa(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"))
             or limpa(os.environ.get("ANTHROPIC_TOKEN")))

    if pref.get("provider") == "openai-api":
        modelo = limpa_texto(pref.get("modelo")) or FALLBACK_OPENAI
        print("provider=openai-api")
        print("default=%s" % modelo)
        print("motivo=OpenAI escolhido no grupo (cerebro.json)", file=sys.stderr)
        return

    if not chave:
        modelo = limpa_texto(os.environ.get("COPILOTO_MODELO")) or FALLBACK_OPENAI
        print("provider=openai-api")
        print("default=%s" % modelo)
        print("motivo=sem chave da Anthropic — seguindo no OpenAI", file=sys.stderr)
        return

    modelo, motivo = escolhe_claude(chave)
    if not modelo:
        print("provider=openai-api")
        print("default=%s" % FALLBACK_OPENAI)
        print("motivo=%s — voltando para o OpenAI" % motivo, file=sys.stderr)
        return
    print("provider=anthropic")
    print("default=%s" % modelo)
    print("motivo=Claude ligado (%s): %s" % (modelo, motivo), file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # nunca derruba o boot
        print("provider=openai-api")
        print("default=%s" % FALLBACK_OPENAI)
        print("motivo=erro inesperado (%s)" % e, file=sys.stderr)
