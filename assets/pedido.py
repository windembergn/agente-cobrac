#!/usr/bin/env python3
"""Copiloto — pedido de cirurgia (guia de solicitacao + relatorio).

"O cirurgiao vai clicando: tipo de cirurgia, ma oclusao, problemas associados,
convenio, hospital, exames anexados, fornecedor de material, qual material,
quantidade, data — e sai o pedido."  (pedido do Dr. no grupo do COBRAC)

Este modulo e' o MOTOR, usado por dois caminhos:

  1. a pagina /crm/pedido (formulario clicavel, servido pelo crm_server);
  2. a habilidade `pedido-cirurgia`, quando o cirurgiao pede pelo WhatsApp —
     ela monta o mesmo JSON e chama POST /crm/api/pedido.

A saida e' UMA pagina publicada em /opt/data/sites/<nome>/index.html (logo,
no ar em https://<dominio>/s/<nome>), com duas partes:

  * o RELATORIO MEDICO de justificativa (esqueleto do modelo documento.html,
    entao continua editavel pelo editor visual de /documentos);
  * a GUIA DE SOLICITACAO DE INTERNACAO no padrao TISS, com os campos
    numerados — a mesma que a operadora espera receber.

O JSON que gerou a pagina fica ao lado, em pedido.json, para reabrir o
formulario ja preenchido e so trocar o que mudou.

Nada aqui decide conduta: o catalogo abaixo e' um PONTO DE PARTIDA que o
cirurgiao confere e edita na tela. Codigo de procedimento que nao veio de
documento real fica em branco de proposito — inventar codigo TUSS e' pior do
que deixar o campo para o cirurgiao preencher.
"""
import html
import json
import os
import re
import time

import pedido_es

# ============================================================== IDIOMA / PAIS
# Sao duas coisas diferentes e nao devem ser amarradas:
#
#   IDIOMA  — a lingua da tela e dos documentos. Vale para a instalacao
#             inteira (COPILOTO_IDIOMA=es na stack), porque quem opera o
#             sistema e' sempre a mesma pessoa.
#   PAIS    — qual formulario a operadora espera. Escolhido em CADA pedido,
#             porque a mesma cirurgia pode ir para um convenio brasileiro
#             hoje e para uma aseguradora hispano-americana amanha.
#
# Sao tres paises hoje: `br` sai na guia TISS/ANS; `ve` e `es` saem na mesma
# Solicitud de Autorizacion (o impresso e' o mesmo, mudam as seguradoras e
# tres rotulos). Pais novo entra em pedido_es.ASEGURADORAS_POR_PAIS.
#
# O default dos dois e' o Brasil/PT-BR: uma instalacao que ja existe nao muda
# de comportamento ao atualizar a imagem.
PAISES = ("br", "ve", "es")


def idioma():
    v = (os.environ.get("COPILOTO_IDIOMA") or "pt").strip().lower()[:2]
    return "es" if v == "es" else "pt"


def T(idi=None):
    """Os rotulos do idioma em vigor (o PT-BR cobre o que faltar em ES)."""
    return pedido_es.textos(idi or idioma())


def pais_padrao():
    """O pais que a tela ja vem marcando.

    COPILOTO_PAIS na stack manda. Sem ele, o idioma decide — mas so' entre
    Brasil e Espanha, porque nao da' para adivinhar QUAL pais hispano: uma
    cirurgia venezuelana e uma espanhola falam a mesma lingua e usam
    seguradoras completamente diferentes. Quem instala para a Venezuela poe
    COPILOTO_PAIS=ve e para de pensar nisso."""
    v = (os.environ.get("COPILOTO_PAIS") or "").strip().lower()
    if v in PAISES:
        return v
    return "es" if idioma() == "es" else "br"


def pais_do(p):
    v = (p.get("pais") or pais_padrao()).strip().lower()
    return v if v in PAISES else "br"

# ============================================================== CATALOGO
# Cada tipo de cirurgia traz o que muda no pedido: CID sugerido, procedimentos,
# materiais tipicos e o texto-base da justificativa. Tudo editavel na tela.

FORNECEDORES_PADRAO = ["ORTHOFACE (OSTEOMED)", "STRYKER (CMO)", "MEDCOSTA (KLS)"]

CIRURGIAS = [
    {
        "key": "ortognatica",
        "nome": "Cirurgia ortognática",
        "pede_maloclusao": True,
        "cid": "K07.2",
        "cid_desc": "Anomalias da relação entre as arcadas dentárias",
        "diarias": "02",
        "tipo_internacao": "2",
        "regime": "1",
        "procedimentos": [
            {"codigo": "30208050", "desc": "OSTEOTOMIA LE FORT", "qtd": "01"},
            {"codigo": "30208025", "desc": "OSTEOPLASTIA PARA MICROGNATISMO", "qtd": "01"},
            {"codigo": "30209021", "desc": "OSTEOPLASTIA DE MANDÍBULA", "qtd": "01"},
        ],
        "materiais": [
            {"desc": "Miniplacas pré-bent / maxilar", "qtd": "02"},
            {"desc": "Parafusos 1.5 / 2.0", "qtd": "44"},
            {"desc": "Placa reta 2.0", "qtd": "04"},
            {"desc": "Ponta ultrassônica Piezo", "qtd": "01"},
            {"desc": "Serra reciprocante", "qtd": "01"},
        ],
        "indicacao": (
            "Paciente diagnosticado com deformidade dentofacial, {maloclusao} com indicação de "
            "procedimento cirúrgico sob anestesia geral"
        ),
        "justificativa": (
            "Paciente portador de deformidade dentofacial, com {maloclusao} que não é passível de "
            "correção apenas por tratamento ortodôntico compensatório, uma vez que a alteração é de "
            "base esquelética. O quadro compromete a função mastigatória, a estabilidade oclusal e a "
            "harmonia facial{associados_frase}. A correção cirúrgica das bases ósseas, associada ao "
            "preparo ortodôntico já em curso, é o tratamento indicado para restabelecer a relação "
            "maxilomandibular adequada, a função e a estabilidade a longo prazo."
        ),
        "conduta": (
            "Osteotomia maxilar tipo Le Fort I e osteotomia sagital bilateral de mandíbula, com "
            "fixação interna rígida, sob anestesia geral, em ambiente hospitalar, com previsão de "
            "internação conforme a guia anexa."
        ),
    },
    {
        "key": "saos",
        "nome": "Avanço maxilomandibular (apneia do sono)",
        "pede_maloclusao": True,
        "cid": "G47.3",
        "cid_desc": "Apneia do sono",
        "cid_extra": "K07.2",
        "diarias": "02",
        "tipo_internacao": "2",
        "regime": "1",
        "procedimentos": [
            {"codigo": "30208050", "desc": "OSTEOTOMIA LE FORT", "qtd": "01"},
            {"codigo": "30208025", "desc": "OSTEOPLASTIA PARA MICROGNATISMO", "qtd": "01"},
        ],
        "materiais": [
            {"desc": "Miniplacas pré-bent / maxilar", "qtd": "02"},
            {"desc": "Parafusos 1.5 / 2.0", "qtd": "44"},
            {"desc": "Placa reta 2.0", "qtd": "04"},
            {"desc": "Ponta ultrassônica Piezo", "qtd": "01"},
            {"desc": "Serra reciprocante", "qtd": "01"},
        ],
        "indicacao": (
            "Paciente com síndrome da apneia obstrutiva do sono e deficiência esquelética "
            "maxilomandibular, {maloclusao} com indicação de avanço maxilomandibular sob anestesia geral"
        ),
        "justificativa": (
            "Paciente com diagnóstico de síndrome da apneia obstrutiva do sono confirmado em "
            "polissonografia, associado a deficiência esquelética maxilomandibular e {maloclusao}. O "
            "quadro reduz o espaço aéreo posterior e mantém o paciente sintomático{associados_frase}. "
            "O avanço maxilomandibular é o procedimento com maior taxa de resolução do colapso da via "
            "aérea nesse perfil de paciente, atuando na causa esquelética do estreitamento, e está "
            "indicado após avaliação multiprofissional."
        ),
        "conduta": (
            "Avanço maxilomandibular por osteotomia Le Fort I e osteotomia sagital bilateral de "
            "mandíbula, com fixação interna rígida, sob anestesia geral."
        ),
    },
    {
        "key": "terceiros-molares",
        "nome": "Terceiros molares inclusos",
        "pede_maloclusao": False,
        "cid": "K01.1",
        "cid_desc": "Dente incluso",
        "diarias": "01",
        "tipo_internacao": "2",
        "regime": "2",
        "procedimentos": [
            {"codigo": "", "desc": "EXODONTIA DE DENTE INCLUSO / IMPACTADO", "qtd": "04"},
        ],
        "materiais": [
            {"desc": "Kit cirúrgico para exodontia de incluso", "qtd": "01"},
            {"desc": "Sutura reabsorvível", "qtd": "02"},
            {"desc": "Broca cirúrgica descartável", "qtd": "02"},
        ],
        "indicacao": (
            "Paciente com terceiros molares inclusos sintomáticos, com indicação de exodontia sob "
            "anestesia geral"
        ),
        "justificativa": (
            "Paciente apresenta terceiros molares inclusos, em posição desfavorável, com episódios "
            "recorrentes de pericoronarite, dor e dificuldade de higienização local{associados_frase}. "
            "Há risco de reagudização infecciosa, de reabsorção radicular dos segundos molares e de "
            "formação de lesão cística associada ao folículo pericoronário. A remoção cirúrgica é "
            "indicada em caráter preventivo e terapêutico; o ambiente hospitalar se justifica pela "
            "quantidade de elementos, pela proximidade com estruturas nobres e pela necessidade de "
            "anestesia geral."
        ),
        "conduta": (
            "Exodontia dos terceiros molares inclusos com osteotomia e odontossecção quando "
            "necessário, sob anestesia geral, em regime de hospital-dia."
        ),
    },
    {
        "key": "enxerto-osseo",
        "nome": "Enxerto ósseo / reconstrução alveolar",
        "pede_maloclusao": False,
        "cid": "K08.2",
        "cid_desc": "Atrofia do rebordo alveolar desdentado",
        "diarias": "01",
        "tipo_internacao": "2",
        "regime": "2",
        "procedimentos": [
            {"codigo": "", "desc": "ENXERTO ÓSSEO ALVEOLAR / RECONSTRUÇÃO DE REBORDO", "qtd": "01"},
        ],
        "materiais": [
            {"desc": "Bio-Oss Collagen", "qtd": "04"},
            {"desc": "Membrana de colágeno", "qtd": "02"},
            {"desc": "Parafusos de fixação 1.5", "qtd": "06"},
            {"desc": "Broca trefina / kit de coleta óssea", "qtd": "01"},
        ],
        "indicacao": (
            "Paciente com atrofia óssea de rebordo alveolar com indicação de enxerto ósseo prévio à "
            "reabilitação"
        ),
        "justificativa": (
            "Paciente apresenta rebordo alveolar atrófico, com volume ósseo insuficiente para a "
            "reabilitação funcional planejada{associados_frase}. A reconstrução do leito ósseo é etapa "
            "necessária e prévia à instalação dos implantes: sem ela, não há estabilidade primária nem "
            "previsibilidade de longo prazo. O procedimento está indicado conforme o planejamento "
            "tomográfico anexado."
        ),
        "conduta": (
            "Enxertia óssea do rebordo alveolar com biomaterial e/ou osso autógeno, fixação quando "
            "indicada e recobrimento com membrana, sob anestesia geral."
        ),
    },
    {
        "key": "implantes",
        "nome": "Implantes osseointegrados",
        "pede_maloclusao": False,
        "cid": "K08.1",
        "cid_desc": "Perda de dentes devida a acidente, extração ou doença periodontal local",
        "diarias": "01",
        "tipo_internacao": "2",
        "regime": "2",
        "procedimentos": [
            {"codigo": "", "desc": "INSTALAÇÃO DE IMPLANTE OSSEOINTEGRADO", "qtd": "02"},
        ],
        "materiais": [
            {"desc": "Implante osseointegrado", "qtd": "02"},
            {"desc": "Cicatrizador / parafuso de cobertura", "qtd": "02"},
            {"desc": "Kit de fresas do sistema", "qtd": "01"},
        ],
        "indicacao": "Paciente com edentulismo e indicação de reabilitação com implantes osseointegrados",
        "justificativa": (
            "Paciente apresenta perda dentária com prejuízo funcional da mastigação e da fonação"
            "{associados_frase}. A reabilitação com implantes osseointegrados é a conduta indicada para "
            "restabelecer a função, preservar o osso remanescente e evitar a sobrecarga dos dentes "
            "vizinhos, conforme planejamento tomográfico anexado."
        ),
        "conduta": "Instalação de implantes osseointegrados conforme planejamento, com guia cirúrgica.",
    },
    {
        "key": "seio-maxilar",
        "nome": "Levantamento de seio maxilar",
        "pede_maloclusao": False,
        "cid": "K08.2",
        "cid_desc": "Atrofia do rebordo alveolar desdentado",
        "diarias": "01",
        "tipo_internacao": "2",
        "regime": "2",
        "procedimentos": [
            {"codigo": "", "desc": "LEVANTAMENTO DE SEIO MAXILAR COM ENXERTO", "qtd": "01"},
        ],
        "materiais": [
            {"desc": "Bio-Oss / biomaterial de enxerto", "qtd": "02"},
            {"desc": "Membrana de colágeno", "qtd": "02"},
            {"desc": "Ponta ultrassônica Piezo", "qtd": "01"},
        ],
        "indicacao": "Pneumatização de seio maxilar com altura óssea insuficiente para reabilitação",
        "justificativa": (
            "Paciente apresenta pneumatização do seio maxilar com altura óssea residual insuficiente "
            "para a instalação de implantes na região posterior de maxila{associados_frase}. O "
            "levantamento da membrana sinusal com enxertia é o procedimento indicado para recuperar "
            "altura óssea e viabilizar a reabilitação."
        ),
        "conduta": "Levantamento de seio maxilar por acesso lateral, com enxertia e recobrimento com membrana.",
    },
    {
        "key": "atm",
        "nome": "Cirurgia de ATM",
        "pede_maloclusao": False,
        "cid": "K07.6",
        "cid_desc": "Transtornos da articulação temporomandibular",
        "diarias": "01",
        "tipo_internacao": "2",
        "regime": "1",
        "procedimentos": [
            {"codigo": "", "desc": "ARTROCENTESE / ARTROSCOPIA DE ATM", "qtd": "01"},
        ],
        "materiais": [
            {"desc": "Kit de artrocentese", "qtd": "01"},
            {"desc": "Solução de lavagem articular", "qtd": "02"},
        ],
        "indicacao": "Transtorno interno da articulação temporomandibular refratário ao tratamento conservador",
        "justificativa": (
            "Paciente apresenta transtorno interno da articulação temporomandibular, com dor "
            "persistente e limitação de abertura bucal, refratário ao tratamento conservador "
            "instituído{associados_frase}. Está indicada a abordagem cirúrgica articular para alívio "
            "da dor e recuperação funcional, conforme exames de imagem anexados."
        ),
        "conduta": "Abordagem articular conforme achado intraoperatório, sob anestesia geral.",
    },
    {
        "key": "trauma",
        "nome": "Trauma facial (fratura)",
        "pede_maloclusao": False,
        "cid": "S02.6",
        "cid_desc": "Fratura de mandíbula",
        "diarias": "02",
        "tipo_internacao": "2",
        "regime": "1",
        "procedimentos": [
            {"codigo": "", "desc": "REDUÇÃO CRUENTA DE FRATURA COM FIXAÇÃO INTERNA RÍGIDA", "qtd": "01"},
        ],
        "materiais": [
            {"desc": "Miniplacas do sistema 2.0", "qtd": "04"},
            {"desc": "Parafusos 1.5 / 2.0", "qtd": "24"},
            {"desc": "Barra de Erich / bloqueio maxilomandibular", "qtd": "01"},
        ],
        "indicacao": "Fratura de face com desalinhamento oclusal, com indicação de redução e fixação",
        "justificativa": (
            "Paciente vítima de trauma facial, apresentando fratura com desvio e alteração da oclusão"
            "{associados_frase}. Está indicada a redução cirúrgica com fixação interna rígida para "
            "restabelecer a oclusão, a função mastigatória e o contorno facial, evitando consolidação "
            "viciosa. O caráter do atendimento é definido pelo tempo de trauma, conforme a guia."
        ),
        "conduta": "Redução cruenta da fratura com fixação interna rígida, sob anestesia geral.",
    },
    {
        "key": "patologia",
        "nome": "Patologia / biópsia / exérese de lesão",
        "pede_maloclusao": False,
        "cid": "K09.0",
        "cid_desc": "Cistos odontogênicos de desenvolvimento",
        "diarias": "01",
        "tipo_internacao": "2",
        "regime": "2",
        "procedimentos": [
            {"codigo": "", "desc": "EXÉRESE DE LESÃO / BIÓPSIA EM CAVIDADE ORAL", "qtd": "01"},
        ],
        "materiais": [
            {"desc": "Kit cirúrgico para exérese de lesão", "qtd": "01"},
            {"desc": "Frasco para exame anatomopatológico", "qtd": "01"},
        ],
        "indicacao": "Lesão em região maxilofacial com indicação de exérese e exame anatomopatológico",
        "justificativa": (
            "Paciente apresenta lesão em região maxilofacial identificada em exame clínico e de "
            "imagem{associados_frase}. Está indicada a remoção cirúrgica com envio da peça para exame "
            "anatomopatológico, tanto para tratamento quanto para definição diagnóstica, evitando "
            "progressão da lesão e comprometimento de estruturas vizinhas."
        ),
        "conduta": "Exérese da lesão com margem adequada e envio para exame anatomopatológico.",
    },
    {
        "key": "outra",
        "nome": "Outra (descrever)",
        "pede_maloclusao": False,
        "cid": "",
        "cid_desc": "",
        "diarias": "01",
        "tipo_internacao": "2",
        "regime": "1",
        "procedimentos": [{"codigo": "", "desc": "", "qtd": "01"}],
        "materiais": [{"desc": "", "qtd": "01"}],
        "indicacao": "",
        "justificativa": (
            "Paciente com indicação de procedimento cirúrgico bucomaxilofacial conforme quadro "
            "clínico descrito{associados_frase}."
        ),
        "conduta": "",
    },
]

MALOCLUSOES = [
    "má-oclusão classe II",
    "má-oclusão classe III",
    "má-oclusão classe I com discrepância vertical",
    "mordida aberta anterior",
    "mordida cruzada posterior",
    "deficiência transversa de maxila",
    "assimetria facial",
    "excesso vertical de maxila",
]

ASSOCIADOS = [
    "síndrome da apneia obstrutiva do sono",
    "disfunção temporomandibular (DTM)",
    "dor orofacial crônica",
    "respiração predominantemente bucal",
    "dificuldade mastigatória",
    "alteração fonética",
    "bruxismo",
    "apinhamento dentário severo",
    "recessão gengival por trauma oclusal",
    "doença periodontal",
    "impacto estético e psicossocial",
]

EXAMES = [
    "Tomografia computadorizada de feixe cônico",
    "Telerradiografia lateral com traçado cefalométrico",
    "Radiografia panorâmica",
    "Documentação ortodôntica completa",
    "Polissonografia",
    "Fotografias clínicas",
    "Modelos de estudo / escaneamento digital",
    "Laudo do ortodontista",
    "Exames laboratoriais pré-operatórios",
    "Risco cirúrgico / avaliação cardiológica",
]

CONVENIOS = [
    "CASSI",
    "Unimed",
    "Bradesco Saúde",
    "SulAmérica",
    "Amil",
    "Golden Cross",
    "Hapvida / NotreDame",
    "GEAP",
    "Postal Saúde",
    "Petrobras / AMS",
    "Assefaz",
    "Particular",
]

CARATER = [("E", "Eletiva"), ("U", "Urgência / Emergência")]
TIPO_INTERNACAO = [("1", "Clínica"), ("2", "Cirúrgica"), ("3", "Obstétrica"), ("4", "Pediátrica"), ("5", "Psiquiátrica")]
REGIME = [("1", "Hospitalar"), ("2", "Hospital-dia"), ("3", "Domiciliar")]

MESES = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]


def _traduz_cirurgia(c, idi):
    """A mesma cirurgia com os textos na lingua pedida.

    Codigo TUSS, CID, diarias, regime e quantidades NAO sao traduzidos — sao os
    mesmos numeros nos dois paises. Por isso o catalogo espanhol guarda so' as
    strings, e uma cirurgia nova continua entrando em um lugar so'."""
    if idi != "es":
        return c
    es = pedido_es.CIRURGIAS_ES.get(c["key"])
    if not es:
        return c
    d = dict(c)
    d["nome"] = es["nome"]
    d["cid_desc"] = es.get("cid_desc", c.get("cid_desc", ""))
    d["indicacao"] = es.get("indicacao", "")
    d["justificativa"] = es.get("justificativa", "")
    d["conduta"] = es.get("conduta", "")
    # As listas andam em paralelo com as do PT-BR: mesma ordem, mesmo tamanho.
    # Se um dia sairem de sincronia, o zip corta no menor e o que sobra fica no
    # original — nunca troca a descricao de um procedimento pela de outro.
    d["procedimentos"] = [
        {**pr, "desc": desc}
        for pr, desc in zip(c["procedimentos"], es.get("procedimentos", []))
    ] or c["procedimentos"]
    d["materiais"] = [
        {**m, "desc": desc}
        for m, desc in zip(c["materiais"], es.get("materiais", []))
    ] or c["materiais"]
    return d


def catalogo(idi=None):
    """O que a tela precisa para montar os cliques, na lingua em vigor.

    `convenios` vem separado por pais: a tela troca a lista inteira quando o
    cirurgiao muda o pais do tramite, sem ir ao servidor de novo."""
    idi = idi or idioma()
    es = idi == "es"
    return {
        "idioma": idi,
        # Os chips do bloco 0. Rotulo ja traduzido: a tela nao decide nome de pais.
        "paises": [(k, T(idi)["pais_" + k]) for k in PAISES],
        "cirurgias": [_traduz_cirurgia(c, idi) for c in CIRURGIAS],
        "maloclusoes": pedido_es.MALOCLUSOES_ES if es else MALOCLUSOES,
        "associados": pedido_es.ASSOCIADOS_ES if es else ASSOCIADOS,
        "exames": pedido_es.EXAMES_ES if es else EXAMES,
        "convenios": CONVENIOS,
        "convenios_por_pais": dict({"br": CONVENIOS}, **pedido_es.ASEGURADORAS_POR_PAIS),
        "fornecedores": FORNECEDORES_PADRAO,
        "fornecedores_por_pais": {
            "br": FORNECEDORES_PADRAO,
            "ve": pedido_es.FABRICANTES_ES,
            "es": pedido_es.FABRICANTES_ES,
        },
        "carater": pedido_es.CARATER_ES if es else CARATER,
        "tipo_internacao": pedido_es.TIPO_INTERNACAO_ES if es else TIPO_INTERNACAO,
        "regime": pedido_es.REGIME_ES if es else REGIME,
    }


def _cirurgia(key, idi=None):
    for c in CIRURGIAS:
        if c["key"] == key:
            return _traduz_cirurgia(c, idi or idioma())
    return _traduz_cirurgia(CIRURGIAS[-1], idi or idioma())


# ============================================================== TEXTO CLINICO
def _lista_por_extenso(itens, idi=None):
    itens = [i for i in itens if i]
    if not itens:
        return ""
    if len(itens) == 1:
        return itens[0]
    # "y" vira "e" antes de som de i- ("e implantes"), regra do espanhol.
    if (idi or idioma()) == "es":
        ultimo = itens[-1]
        conj = " e " if re.match(r"^[iíhI]", ultimo.strip()) else " y "
    else:
        conj = " e "
    return ", ".join(itens[:-1]) + conj + itens[-1]


def _frase_associados(associados, idi=None):
    idi = idi or idioma()
    txt = _lista_por_extenso(associados, idi)
    if not txt:
        return ""
    rotulo = ", con cuadro asociado de " if idi == "es" else ", com quadro associado de "
    return rotulo + txt


def _frase_maloclusao(maloclusao, cirurgia, idi=None):
    if maloclusao:
        return maloclusao + ","
    if not cirurgia.get("pede_maloclusao"):
        return ""
    return "alteración esquelética," if (idi or idioma()) == "es" else "alteração esquelética,"


def montar_textos(p):
    """Monta indicacao clinica, justificativa e conduta a partir dos cliques.

    Se o pedido vier com texto proprio (o agente escreveu no WhatsApp, ou o
    cirurgiao editou na tela), o texto proprio ganha — nunca sobrescrevemos."""
    idi = idioma()
    c = _cirurgia(p.get("tipo", ""), idi)
    ctx = {
        "maloclusao": _frase_maloclusao(p.get("maloclusao", ""), c, idi),
        "associados_frase": _frase_associados(p.get("associados", []), idi),
    }

    def fmt(tpl):
        try:
            return re.sub(r"\s+", " ", tpl.format(**ctx)).replace(" ,", ",").strip()
        except (KeyError, IndexError):
            return tpl

    indicacao = (p.get("indicacao") or "").strip() or fmt(c.get("indicacao", ""))
    justificativa = (p.get("justificativa") or "").strip() or fmt(c.get("justificativa", ""))
    conduta = (p.get("conduta") or "").strip() or fmt(c.get("conduta", ""))
    return indicacao, justificativa, conduta


def slug_do_pedido(p):
    nome = (p.get("paciente") or "paciente").lower()
    nome = nome.replace("ã", "a").replace("á", "a").replace("â", "a").replace("à", "a")
    nome = nome.replace("é", "e").replace("ê", "e").replace("í", "i").replace("ó", "o")
    nome = nome.replace("ô", "o").replace("õ", "o").replace("ú", "u").replace("ç", "c")
    nome = nome.replace("ñ", "n").replace("ü", "u")
    nome = re.sub(r"[^a-z0-9]+", "-", nome).strip("-")
    partes = [x for x in nome.split("-") if x][:3]
    base = "pedido-" + ("-".join(partes) or "paciente")
    return base[:60]


# ============================================================== RENDER (HTML)
def _e(s):
    return html.escape(str(s or "").strip(), quote=False)


def _campo(num, rotulo, valor="", classe=""):
    """Uma celula do formulario. `num` vazio = sem numeracao de campo.

    A guia brasileira numera os campos porque a ANS numera; a solicitud hispana
    nao numera nada, e um travessao solto na frente do rotulo denunciaria o
    molde emprestado."""
    v = _e(valor) or '<span class="linha-vazia"></span>'
    titulo = f"{_e(num)} — {_e(rotulo)}" if str(num).strip() else _e(rotulo)
    return (
        f'<td class="{classe}"><span class="campo-num">{titulo}</span>'
        f'<span class="campo-valor">{v}</span></td>'
    )


def _data_extenso(ts=None, idi=None):
    t = time.localtime(ts or time.time())
    meses = pedido_es.MESES_ES if (idi or idioma()) == "es" else MESES
    return f"{t.tm_mday} de {meses[t.tm_mon - 1]} de {t.tm_year}"


def _data_br(iso):
    """'2026-09-15' -> '15/09/2026'. Devolve o que veio se nao for ISO."""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", (iso or "").strip())
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else (iso or "").strip()


def _bloco_procedimentos(p):
    linhas = []
    for i, pr in enumerate(p.get("procedimentos", []), 1):
        if not (pr.get("desc") or pr.get("codigo")):
            continue
        linhas.append(
            f"<tr><td class='num'>{i}</td><td class='cod'>{_e(pr.get('codigo')) or '&nbsp;'}</td>"
            f"<td>{_e(pr.get('desc'))}</td><td class='qtd'>{_e(pr.get('qtd'))}</td>"
            f"<td class='qtd'>&nbsp;</td></tr>"
        )
    return "\n".join(linhas) or "<tr><td colspan='5'>&nbsp;</td></tr>"


def _bloco_opme(p):
    forn = " / ".join([f for f in p.get("fornecedores", []) if f])
    linhas = []
    for i, m in enumerate(p.get("materiais", []), 1):
        if not m.get("desc"):
            continue
        linhas.append(
            f"<tr><td class='num'>{i}</td><td class='cod'>&nbsp;</td><td>{_e(m.get('desc'))}</td>"
            f"<td class='qtd'>{_e(m.get('qtd'))}</td><td class='forn'>{_e(forn)}</td>"
            f"<td class='qtd'>&nbsp;</td></tr>"
        )
    return "\n".join(linhas) or "<tr><td colspan='6'>&nbsp;</td></tr>"


def _pendencias(p, t=None):
    t = t or T()
    faltando = []
    if not (p.get("carteirinha") or "").strip():
        faltando.append(t["p_carteirinha"])
    if not (p.get("cro") or "").strip():
        faltando.append(t["p_conselho"])
    if not (p.get("cid") or "").strip():
        faltando.append(t["p_cid"])
    if not (p.get("hospital") or "").strip():
        faltando.append(t["p_hospital"])
    if not (p.get("data_procedimento") or "").strip():
        faltando.append(t["p_data"])
    sem_codigo = [
        pr.get("desc")
        for pr in p.get("procedimentos", [])
        if pr.get("desc") and not (pr.get("codigo") or "").strip()
    ]
    if sem_codigo:
        faltando.append(t["p_codigo"] + " (" + ", ".join(sem_codigo[:3]) + ")")
    return "; ".join(faltando) if faltando else t["p_nenhuma"]


PARTES = ("completo", "guia", "relatorio")


def _titulo_parte(parte, t):
    return {"completo": t["doc_completo"], "guia": t["doc_guia"], "relatorio": t["doc_relatorio"]}[parte]


def _valores(p, idi):
    """Tudo que os dois formularios (BR e ES) leem, ja limpo e formatado.

    Existe para que a guia brasileira e a solicitud espanhola nunca divirjam no
    conteudo: as duas se abastecem daqui, e o que muda entre elas e' so' o
    papel — quais campos aparecem, com que rotulo e em que ordem."""
    t = T(idi)
    c = _cirurgia(p.get("tipo", ""), idi)
    indicacao, justificativa, conduta = montar_textos(p)

    paciente = p.get("paciente") or t["paciente_confirmar"]
    idade = (p.get("idade") or "").strip()
    convenio = (p.get("convenio") or "").strip()
    carteirinha = (p.get("carteirinha") or "").strip()
    cid = (p.get("cid") or "").strip()
    cid_desc = (p.get("cid_desc") or c.get("cid_desc") or "").strip()
    cro = (p.get("cro") or t["a_confirmar"]).strip()

    return {
        "t": t,
        "c": c,
        "titulo_cirurgia": (p.get("tipo_livre") or "").strip() or c["nome"],
        "paciente": paciente,
        "paciente_linha": f"{paciente}, {idade}{t['anos']}" if idade else paciente,
        "idade": idade,
        "convenio": convenio,
        "carteirinha": carteirinha,
        "convenio_linha": t["carteirinha_sep"].join([x for x in [convenio, carteirinha] if x]) or t["a_confirmar"],
        "cid": cid,
        "cid_desc": cid_desc,
        "cid_linha": " — ".join([x for x in [cid, cid_desc] if x]) or t["cid_confirmar"],
        "cid2": (p.get("cid2") or "").strip(),
        "indicacao": indicacao,
        "justificativa": justificativa,
        "conduta": conduta,
        "procs_txt": "; ".join(
            [
                " ".join([x for x in [pr.get("desc", "").strip(),
                                      f"({pr.get('codigo')})" if pr.get("codigo") else ""] if x])
                for pr in p.get("procedimentos", []) if pr.get("desc")
            ]
        ) or t["a_confirmar"],
        "materiais_li": "\n      ".join(
            f"<li>{_e(m.get('desc'))} — {_e(m.get('qtd'))}</li>"
            for m in p.get("materiais", []) if m.get("desc")
        ) or f"<li>{t['sem_material']}</li>",
        "exames_li": "\n      ".join(f"<li>{_e(x)}</li>" for x in p.get("exames", []))
                     or f"<li>{t['sem_exame']}</li>",
        "forn_txt": _lista_por_extenso([f for f in p.get("fornecedores", []) if f], idi),
        "data_proc": _data_br(p.get("data_procedimento", "")),
        "cirurgiao": (p.get("cirurgiao") or t["nome_cirurgiao"]).strip(),
        "cro": cro,
        "uf": (p.get("uf") or "").strip(),
        "hospital": (p.get("hospital") or "").strip(),
        "obs": (p.get("observacao") or t["obs_padrao"]).strip(),
        "carater_lbl": dict(pedido_es.CARATER_ES if idi == "es" else CARATER).get(p.get("carater", "E"), ""),
        "tipo_int_lbl": dict(pedido_es.TIPO_INTERNACAO_ES if idi == "es" else TIPO_INTERNACAO).get(
            p.get("tipo_internacao", c["tipo_internacao"]), ""),
        "regime_lbl": dict(pedido_es.REGIME_ES if idi == "es" else REGIME).get(
            p.get("regime", c["regime"]), ""),
        "diarias": p.get("diarias", c["diarias"]),
    }


def _guia_br(p, v):
    """A guia de solicitacao de internacao no padrao TISS/ANS (Brasil).

    Numeracao dos campos preservada: e' por ela que o atendente da operadora se
    guia no balcao, entao ela nao muda nem quando a tela esta em espanhol."""
    t = v["t"]
    return f"""
<article class="documento guia">

  <table class="guia-topo">
    <tr>
      <td class="operadora">{_e(v["convenio"]) or t["g_operadora"]}</td>
      <td class="titulo-guia">{t["g_titulo"]}</td>
      {_campo("2", t["g_num_guia"])}
    </tr>
  </table>

  <table>
    <tr>
      {_campo("1", t["g_ans"])}
      {_campo("3", t["g_data_aut"])}
      {_campo("4", t["g_senha"])}
      {_campo("5", t["g_validade_senha"])}
      {_campo("6", t["g_emissao"], _data_br(time.strftime("%Y-%m-%d")))}
    </tr>
  </table>

  <p class="titulo-bloco">{t["g_bloco_benef"]}</p>
  <table>
    <tr>
      {_campo("7", t["g_carteira"], v["carteirinha"])}
      {_campo("8", t["g_plano"], p.get("plano", ""))}
      {_campo("9", t["g_validade_carteira"], _data_br(p.get("validade_carteira", "")))}
    </tr>
    <tr>
      {_campo("10", t["g_nome"], v["paciente"])}
      {_campo("11", t["g_cns"], p.get("cns", ""), "col2")}
    </tr>
  </table>

  <p class="titulo-bloco">{t["g_bloco_solic"]}</p>
  <table>
    <tr>
      {_campo("12", t["g_cod_operadora"], p.get("codigo_operadora", ""))}
      {_campo("13", t["g_contratado"], p.get("contratado", ""))}
      {_campo("14", t["g_cnes"], p.get("cnes", ""))}
    </tr>
    <tr>
      {_campo("15", t["g_profissional"], v["cirurgiao"])}
      {_campo("16", t["g_conselho"], "CRO")}
      {_campo("17", t["g_num_conselho"], v["cro"])}
      {_campo("18", t["g_uf"], v["uf"])}
    </tr>
  </table>

  <p class="titulo-bloco">{t["g_bloco_intern"]}</p>
  <table>
    <tr>
      {_campo("20", t["g_cod_hospital"], p.get("codigo_hospital", ""))}
      {_campo("21", t["g_prestador"], v["hospital"])}
    </tr>
    <tr>
      {_campo("22", t["g_carater"], v["carater_lbl"])}
      {_campo("23", t["g_tipo_intern"], v["tipo_int_lbl"])}
      {_campo("24", t["g_regime"], v["regime_lbl"])}
      {_campo("25", t["g_diarias"], v["diarias"])}
    </tr>
  </table>

  <table>
    <tr>{_campo("26", t["g_indicacao"], v["indicacao"], "col4")}</tr>
  </table>

  <p class="titulo-bloco">{t["g_bloco_hipoteses"]}</p>
  <table>
    <tr>
      {_campo("27", t["g_tipo_doenca"], p.get("tipo_doenca", ""))}
      {_campo("28", t["g_tempo_doenca"], p.get("tempo_doenca", ""))}
      {_campo("30", t["g_cid"], v["cid"])}
      {_campo("31", t["g_cid2"], v["cid2"])}
    </tr>
  </table>

  <p class="titulo-bloco">{t["g_bloco_procs"]}</p>
  <table class="itens">
    <thead>
      <tr><th class="num">#</th><th class="cod">35 — {t["g_th_cod"]}</th><th>36 — {t["g_th_desc"]}</th><th class="qtd">37 — {t["g_th_qtd_sol"]}</th><th class="qtd">38 — {t["g_th_qtd_aut"]}</th></tr>
    </thead>
    <tbody>
      {_bloco_procedimentos(p)}
    </tbody>
  </table>

  <p class="titulo-bloco">{t["g_bloco_opme"]}</p>
  <table class="itens">
    <thead>
      <tr><th class="num">#</th><th class="cod">40 — {t["g_th_cod"]}</th><th>41 — {t["g_th_desc"]}</th><th class="qtd">42 — {t["g_th_qtd"]}</th><th class="forn">43 — {t["g_th_fab"]}</th><th class="qtd">44 — {t["g_th_valor"]}</th></tr>
    </thead>
    <tbody>
      {_bloco_opme(p)}
    </tbody>
  </table>

  <table>
    <tr>
      {_campo("45", t["g_admissao"], v["data_proc"])}
      {_campo("46", t["g_diarias_aut"])}
      {_campo("47", t["g_acomodacao"])}
    </tr>
  </table>

  <table>
    <tr>{_campo("51", t["g_obs"], v["obs"], "col3")}</tr>
  </table>

  <table class="assinaturas">
    <tr>
      <td><span class="campo-num">52 — {t["g_ass_medico"]}</span>
        <span class="assina">{_e(v["cirurgiao"])}<br><span class="muted small">CRO {_e(v["cro"])}{(" / " + _e(v["uf"])) if v["uf"] else ""}</span></span></td>
      <td><span class="campo-num">53 — {t["g_ass_benef"]}</span><span class="assina">&nbsp;</span></td>
      <td><span class="campo-num">54 — {t["g_ass_aut"]}</span><span class="assina">&nbsp;</span></td>
    </tr>
  </table>

  <p class="small muted" style="margin-top:var(--sp-5)">{t["g_rodape"]}{(t["g_rodape_forn"] + _e(v["forn_txt"]) + ".") if v["forn_txt"] else ""}</p>

</article>
"""


def _solicitud_es(p, v):
    """A solicitud de autorizacao da aseguradora (Espanha).

    Nao existe na Espanha um impresso nacional unico como o TISS: cada
    aseguradora tem o seu, e todos pedem o mesmo conjunto — asegurado, poliza,
    CIE-10, procedimento, centro concertado, material implantavel e a firma do
    facultativo. E' esse denominador comum que sai aqui, sem numeracao de campo
    (a numeracao da guia brasileira vem da ANS e nao significaria nada aqui)."""
    t = v["t"]
    S = pedido_es.solicitud(pais_do(p))
    return f"""
<article class="documento guia">

  <table class="guia-topo">
    <tr>
      <td class="operadora">{_e(v["convenio"]) or S["aseguradora"]}</td>
      <td class="titulo-guia">{S["titulo"]}</td>
      {_campo("", S["ref"])}
    </tr>
  </table>

  <table>
    <tr>
      {_campo("", S["emision"], _data_br(time.strftime("%Y-%m-%d")))}
      {_campo("", S["fecha_prev"], v["data_proc"])}
    </tr>
  </table>

  <p class="titulo-bloco">{S["b_asegurado"]}</p>
  <table>
    <tr>
      {_campo("", S["nombre"], v["paciente"], "col2")}
      {_campo("", S["dni"], p.get("dni", ""))}
      {_campo("", S["edad"], v["idade"])}
    </tr>
    <tr>
      {_campo("", S["poliza"], v["carteirinha"])}
      {_campo("", S["modalidad"], p.get("plano", ""))}
      {_campo("", S["validez"], _data_br(p.get("validade_carteira", "")))}
    </tr>
  </table>

  <p class="titulo-bloco">{S["b_solicitante"]}</p>
  <table>
    <tr>
      {_campo("", S["facultativo"], v["cirurgiao"], "col2")}
      {_campo("", S["colegiado"], v["cro"])}
      {_campo("", S["colegio"], v["uf"])}
    </tr>
    <tr>
      {_campo("", S["especialidad"], S["esp_valor"], "col4")}
    </tr>
  </table>

  <p class="titulo-bloco">{S["b_centro"]}</p>
  <table>
    <tr>
      {_campo("", S["centro"], v["hospital"], "col2")}
      {_campo("", S["cod_centro"], p.get("codigo_hospital", ""))}
    </tr>
    <tr>
      {_campo("", S["caracter"], v["carater_lbl"])}
      {_campo("", S["tipo"], v["tipo_int_lbl"])}
      {_campo("", S["regimen"], v["regime_lbl"])}
      {_campo("", S["estancias"], v["diarias"])}
    </tr>
  </table>

  <p class="titulo-bloco">{S["b_diag"]}</p>
  <table>
    <tr>
      {_campo("", S["cie"], v["cid"])}
      {_campo("", S["cie2"], v["cid2"])}
      {_campo("", S["evolucion"], p.get("tempo_doenca", ""))}
    </tr>
    <tr>{_campo("", S["indicacion"], v["indicacao"], "col4")}</tr>
  </table>

  <p class="titulo-bloco">{S["b_procs"]}</p>
  <table class="itens">
    <thead>
      <tr><th class="num">#</th><th class="cod">{S["th_cod"]}</th><th>{S["th_desc"]}</th><th class="qtd">{S["th_cant"]}</th><th class="qtd">{S["th_aut"]}</th></tr>
    </thead>
    <tbody>
      {_bloco_procedimentos(p)}
    </tbody>
  </table>

  <p class="titulo-bloco">{S["b_material"]}</p>
  <table class="itens">
    <thead>
      <tr><th class="num">#</th><th class="cod">{S["th_cod"]}</th><th>{S["th_desc"]}</th><th class="qtd">{S["th_cant"]}</th><th class="forn">{S["th_fab"]}</th><th class="qtd">{S["th_importe"]}</th></tr>
    </thead>
    <tbody>
      {_bloco_opme(p)}
    </tbody>
  </table>

  <table>
    <tr>{_campo("", S["obs"], v["obs"], "col3")}</tr>
  </table>

  <table class="assinaturas">
    <tr>
      <td><span class="campo-num">{S["firma_medico"]}</span>
        <span class="assina">{_e(v["cirurgiao"])}<br><span class="muted small">Nº col. {_e(v["cro"])}{(" / " + _e(v["uf"])) if v["uf"] else ""}</span></span></td>
      <td><span class="campo-num">{S["firma_asegurado"]}</span><span class="assina">&nbsp;</span></td>
      <td><span class="campo-num">{S["firma_aut"]}</span><span class="assina">&nbsp;</span></td>
    </tr>
  </table>

  <p class="small muted" style="margin-top:var(--sp-5)">{S["anexo"]} {S["rodape"]}{(S["rodape_fab"] + _e(v["forn_txt"]) + ".") if v["forn_txt"] else ""}</p>

</article>
"""


def render_pagina(p, parte="completo"):
    """Devolve o HTML da pagina do pedido.

    Sao DUAS pecas com destinos diferentes: o formulario e' o impresso DA
    OPERADORA (tem campo que so ela preenche e tres assinaturas) e o relatorio
    e' o anexo que justifica, assinado so pelo cirurgiao. No balcao vao
    grampeados; no portal sobe um arquivo para cada. Por isso a mesma ficha
    gera tres saidas: `completo`, `guia` e `relatorio`.

    O IDIOMA vem da instalacao (COPILOTO_IDIOMA) e o PAIS vem do pedido: uma
    tela em espanhol pode perfeitamente emitir a guia TISS brasileira."""
    if parte not in PARTES:
        parte = "completo"
    idi = idioma()
    pais = pais_do(p)
    v = _valores(p, idi)
    t = v["t"]

    secao_associados = ""
    if p.get("associados"):
        secao_associados = (
            f"<h2>{t['rel_associado']}</h2>\n    <ul>\n      "
            + "\n      ".join(f"<li>{_e(a)}</li>" for a in p["associados"])
            + "\n    </ul>"
        )

    cabeca = f"""<!doctype html>
<html lang="{"es" if idi == "es" else "pt-BR"}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_titulo_parte(parte, t)} — {_e(v["paciente"])}</title>
<meta name="robots" content="noindex, nofollow">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🦷</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600;650&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/s/_kit/base.css">
<script src="/s/_kit/kit.js" defer></script>
<style>:root {{ --brand: #0e5aa7; }}</style>
</head>
<body>
"""

    # Barra de acoes: nao sai no papel (@media print esconde .acoes-doc), entao
    # o atalho entre as pecas fica aqui e nao suja o documento impresso.
    outras = {
        "completo": f'<a class="btn btn-vazado" href="guia.html">{t["btn_so_guia"]}</a>\n  <a class="btn btn-vazado" href="relatorio.html">{t["btn_so_rel"]}</a>',
        "guia": f'<a class="btn btn-vazado" href="relatorio.html">{t["btn_ver_rel"]}</a>\n  <a class="btn btn-vazado" href="./">{t["btn_ver_dois"]}</a>',
        "relatorio": f'<a class="btn btn-vazado" href="guia.html">{t["btn_ver_guia"]}</a>\n  <a class="btn btn-vazado" href="./">{t["btn_ver_dois"]}</a>',
    }[parte]

    acoes = f"""
<div class="acoes-doc" style="margin-top:var(--sp-5)">
  <button class="btn" onclick="window.print()">{t["btn_imprimir"]}</button>
  {outras}
</div>
"""

    relatorio = f"""
<article class="documento">

  <header>
    <p class="rotulo">{t["rel_rotulo"]}</p>
    <h1>{_e(v["titulo_cirurgia"])}</h1>
    <p class="small muted">{t["rel_emitido"]}{_data_extenso(idi=idi)}</p>
  </header>

  <dl class="dados">
    <div><dt>{t["rel_paciente"]}</dt><dd>{_e(v["paciente_linha"])}</dd></div>
    <div><dt>{t["rel_convenio"]}</dt><dd>{_e(v["convenio_linha"])}</dd></div>
    <div><dt>{t["rel_hipotese"]}</dt><dd>{_e(v["cid_linha"])}</dd></div>
    <div><dt>{t["rel_procedimento"]}</dt><dd>{_e(v["procs_txt"])}</dd></div>
    <div><dt>{t["rel_hospital"]}</dt><dd>{_e(v["hospital"]) or t["a_confirmar"]}</dd></div>
    <div><dt>{t["rel_data"]}</dt><dd>{_e(v["data_proc"]) or t["a_confirmar"]}</dd></div>
  </dl>

  <section class="prosa" style="padding-block:var(--sp-5)">
    <h2>{t["rel_justificativa"]}</h2>
    <p>{_e(v["justificativa"])}</p>

    <h2>{t["rel_conduta"]}</h2>
    <p>{_e(v["conduta"])}</p>

    {secao_associados}

    <h2>{t["rel_materiais"]}</h2>
    <ul>
      {v["materiais_li"]}
    </ul>

    <h2>{t["rel_exames"]}</h2>
    <ul>
      {v["exames_li"]}
    </ul>
  </section>

  <div class="aviso">
    <p><strong>{t["rel_pendencias"]}</strong> {_e(_pendencias(p, t))}.</p>
  </div>

  <div class="assinatura">
    {_e(v["cirurgiao"])}<br>
    <span class="muted">{"Nº col." if idi == "es" else "CRO"} {_e(v["cro"])}{(" / " + _e(v["uf"])) if v["uf"] else ""}</span>
  </div>

  <p class="small muted" style="margin-top:var(--sp-6)">{t["rel_minuta"]}</p>

</article>
"""

    # Brasil e' o unico com formulario proprio (a guia TISS/ANS). Todo o resto
    # sai na Solicitud de Autorizacion — por isso a comparacao e' contra "br" e
    # nao contra a lista de paises hispanos: pais novo entra sem tocar aqui.
    guia = _guia_br(p, v) if pais == "br" else _solicitud_es(p, v)
    corpo = {"completo": relatorio + guia, "guia": guia, "relatorio": relatorio}[parte]
    return cabeca + acoes + corpo + "\n</body>\n</html>\n"


# ============================================================== PERSISTENCIA
def salvar_pedido(sites_dir, p, nome=None):
    """Escreve a pagina (index.html) e o pedido.json ao lado. Devolve o nome."""
    nome = nome or slug_do_pedido(p)
    if not re.match(r"^[a-z0-9-]+$", nome):
        nome = "pedido-paciente"
    pasta = os.path.join(sites_dir, nome)
    # Nome ja usado por OUTRO pedido/pagina: acrescenta sufixo em vez de
    # sobrescrever o documento de outro paciente.
    if os.path.isdir(pasta) and not os.path.isfile(os.path.join(pasta, "pedido.json")):
        i = 2
        while os.path.isdir(os.path.join(sites_dir, f"{nome}-{i}")):
            i += 1
        nome = f"{nome}-{i}"
        pasta = os.path.join(sites_dir, nome)
    os.makedirs(pasta, exist_ok=True)
    # Tres arquivos do MESMO preenchimento: o combinado (index), a guia sozinha
    # e o relatorio sozinho — porque no portal da operadora sobe um arquivo para
    # cada peca, e no balcao vao grampeados.
    for arquivo, parte in (("index.html", "completo"), ("guia.html", "guia"), ("relatorio.html", "relatorio")):
        with open(os.path.join(pasta, arquivo), "w", encoding="utf-8") as f:
            f.write(render_pagina(p, parte))
    p = dict(p)
    p["_atualizado_em"] = int(time.time())
    with open(os.path.join(pasta, "pedido.json"), "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=1)
    return nome


def ler_pedido(sites_dir, nome):
    caminho = os.path.join(sites_dir, nome, "pedido.json")
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _fornecedores_de(pais):
    return FORNECEDORES_PADRAO if pais == "br" else pedido_es.FABRICANTES_ES


def normalizar(b):
    """Aceita tanto o JSON da tela quanto o que a habilidade monta no WhatsApp,
    e devolve o pedido com os defaults do tipo de cirurgia preenchidos."""
    idi = idioma()
    c = _cirurgia(b.get("tipo", ""), idi)
    pais = (b.get("pais") or pais_padrao()).strip().lower()
    pais = pais if pais in PAISES else "br"
    _do_catalogo = not b.get("procedimentos")
    p = {
        "tipo": c["key"],
        # O pais e' do PEDIDO, nao da instalacao: a mesma cirurgia pode ir para
        # um convenio brasileiro hoje e para uma aseguradora hispana amanha.
        "pais": pais,
        "dni": (b.get("dni") or "").strip(),
        "tipo_livre": (b.get("tipo_livre") or "").strip(),
        "paciente": (b.get("paciente") or "").strip(),
        "idade": (b.get("idade") or "").strip(),
        "convenio": (b.get("convenio") or "").strip(),
        "carteirinha": (b.get("carteirinha") or "").strip(),
        "plano": (b.get("plano") or "").strip(),
        "validade_carteira": (b.get("validade_carteira") or "").strip(),
        "cns": (b.get("cns") or "").strip(),
        "maloclusao": (b.get("maloclusao") or "").strip(),
        "associados": [a for a in (b.get("associados") or []) if a],
        "exames": [x for x in (b.get("exames") or []) if x],
        "hospital": (b.get("hospital") or "").strip(),
        "codigo_hospital": (b.get("codigo_hospital") or "").strip(),
        "codigo_operadora": (b.get("codigo_operadora") or "").strip(),
        "contratado": (b.get("contratado") or "").strip(),
        "cnes": (b.get("cnes") or "").strip(),
        "cid": (b.get("cid") or c.get("cid") or "").strip(),
        "cid_desc": (b.get("cid_desc") or c.get("cid_desc") or "").strip(),
        "cid2": (b.get("cid2") or c.get("cid_extra") or "").strip(),
        "tipo_doenca": (b.get("tipo_doenca") or "").strip(),
        "tempo_doenca": (b.get("tempo_doenca") or "").strip(),
        "carater": b.get("carater") if b.get("carater") in dict(CARATER) else "E",
        "tipo_internacao": b.get("tipo_internacao") or c["tipo_internacao"],
        "regime": b.get("regime") or c["regime"],
        "diarias": (b.get("diarias") or c["diarias"]).strip(),
        "data_procedimento": (b.get("data_procedimento") or "").strip(),
        "cirurgiao": (b.get("cirurgiao") or "").strip(),
        "cro": (b.get("cro") or "").strip(),
        "uf": (b.get("uf") or "").strip(),
        "observacao": (b.get("observacao") or "").strip(),
        "indicacao": (b.get("indicacao") or "").strip(),
        "justificativa": (b.get("justificativa") or "").strip(),
        "conduta": (b.get("conduta") or "").strip(),
        "fornecedores": [f for f in (b.get("fornecedores") or _fornecedores_de(pais)) if f][:3],
        "procedimentos": [
            {
                # O codigo do catalogo e' TUSS, que so' existe no Brasil. Fora
                # dele o nomenclator e' outro (cada aseguradora tem o seu),
                # entao o campo vai VAZIO e entra nas pendencias — pela mesma
                # razao de sempre: codigo inventado e' pior que campo em
                # branco. Codigo que o proprio cirurgiao mandou e' respeitado.
                "codigo": "" if (_do_catalogo and pais != "br") else (pr.get("codigo") or "").strip(),
                "desc": (pr.get("desc") or "").strip(),
                "qtd": (pr.get("qtd") or "01").strip(),
            }
            for pr in (b.get("procedimentos") or c["procedimentos"])
        ],
        "materiais": [
            {"desc": (m.get("desc") or "").strip(), "qtd": (m.get("qtd") or "01").strip()}
            for m in (b.get("materiais") or c["materiais"])
        ],
    }
    return p


# ============================================================== TELA (/crm/pedido)
# Formulario clicavel. O cirurgiao escolhe o tipo de cirurgia e o resto ja vem
# preenchido do catalogo — ele confere, ajusta e gera. Nada de digitar do zero.
def form_page(idi=None):
    """A tela, com os rotulos do idioma em vigor.

    Os textos vivem no dicionario (pedido_es.TEXTOS) e entram aqui por @@chave@@
    — nao ha uma segunda copia do HTML em espanhol para sair de sincronia. Uma
    chave que nao existir fica visivel na tela de proposito: erro de traducao
    tem que aparecer para quem esta testando, nao virar espaco em branco."""
    idi = idi or idioma()
    t = dict(T(idi))
    t["_lang"] = "es" if idi == "es" else "pt-BR"
    t["_pais_padrao"] = pais_padrao()
    return re.sub(r"@@([a-z_][a-z0-9_]*)@@", lambda m: str(t.get(m.group(1), m.group(0))), FORM_PAGE)


FORM_PAGE = """<!doctype html>
<html lang="@@_lang@@">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@tela_titulo@@ — Copiloto</title>
<style>
:root{--bg:#0e131a;--panel:#151c26;--panel-2:#1c2531;--line:#293445;--ink:#e7ecf3;--ink-soft:#98a7b8;--brand:#0e5aa7;--ok:#1e8e5a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif;-webkit-font-smoothing:antialiased}
header{position:sticky;top:0;z-index:20;background:rgba(14,19,26,.94);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);padding:12px 16px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
header h1{font-size:16px;margin:0;font-weight:650}
header .sub{font-size:12px;color:var(--ink-soft)}
.btn{background:var(--brand);color:#fff;border:none;border-radius:8px;padding:9px 14px;font-size:13px;font-weight:600;cursor:pointer}
.btn:hover{filter:brightness(1.1)}
.btn:disabled{opacity:.5;cursor:default}
.btn-ghost{background:transparent;border:1px solid var(--line);color:var(--ink)}
.wrap{max-width:860px;margin:0 auto;padding:16px 16px 120px}
.bloco{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:12px}
.bloco > h2{font-size:12px;margin:0 0 10px;color:var(--ink-soft);text-transform:uppercase;letter-spacing:.05em;font-weight:650}
.campo{margin-bottom:10px}
.campo label{display:block;font-size:11px;color:var(--ink-soft);margin-bottom:4px}
.campo input,.campo select,.campo textarea{width:100%;background:var(--bg);border:1px solid var(--line);color:var(--ink);border-radius:8px;padding:9px 10px;font-size:13px;font-family:inherit}
.campo textarea{min-height:80px;resize:vertical}
.linha{display:flex;gap:8px;flex-wrap:wrap}
.linha .campo{flex:1;min-width:130px}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{background:var(--panel-2);border:1px solid var(--line);color:var(--ink-soft);border-radius:20px;padding:7px 13px;font-size:12.5px;cursor:pointer;font-family:inherit}
.chip:hover{border-color:var(--brand);color:var(--ink)}
.chip.on{background:var(--brand);border-color:var(--brand);color:#fff;font-weight:600}
.item-lista{display:flex;gap:6px;margin-bottom:6px;align-items:center}
/* Sem isto o input da lista nasce branco (so .campo input era estilizado) e a
   linha de procedimento/material destoa do resto da tela. */
.item-lista input{background:var(--bg);border:1px solid var(--line);color:var(--ink);border-radius:8px;padding:9px 10px;font-size:13px;font-family:inherit}
.item-lista input.cod{width:96px;flex:none}
.item-lista input.qtd{width:62px;flex:none;text-align:center}
.item-lista input.desc{flex:1;min-width:0}
.mini{background:transparent;border:1px solid var(--line);color:var(--ink-soft);border-radius:6px;padding:7px 9px;font-size:11px;cursor:pointer;white-space:nowrap;font-family:inherit}
.mini:hover{color:var(--ink);border-color:var(--brand)}
.barra{position:fixed;left:0;right:0;bottom:0;background:rgba(14,19,26,.96);backdrop-filter:blur(8px);border-top:1px solid var(--line);padding:12px 16px;display:flex;gap:8px;justify-content:center;flex-wrap:wrap;z-index:30}
.barra .btn{padding:12px 22px;font-size:14px}
.status{font-size:12.5px;color:var(--ink-soft);text-align:center;margin-top:8px}
.dica{font-size:11.5px;color:var(--ink-soft);margin:-4px 0 10px}
.sumiu{display:none}
.resultado{background:var(--panel);border:1px solid var(--ok);border-radius:12px;padding:16px;margin-bottom:12px}
.resultado h2{font-size:14px;margin:0 0 8px;color:var(--ok)}
.resultado a{color:#7fd3ff;word-break:break-all}
@media (max-width:640px){.linha .campo{min-width:100%}.item-lista{flex-wrap:wrap}.item-lista input.desc{width:100%;flex:1 1 100%}}
</style>
</head>
<body>
<header>
  <div>
    <h1>@@tela_titulo@@</h1>
    <div class="sub">@@tela_sub@@</div>
  </div>
  <div style="display:flex;gap:8px">
    <a class="btn btn-ghost" href="/documentos" style="text-decoration:none;display:inline-flex;align-items:center">@@nav_docs@@</a>
    <a class="btn btn-ghost" href="/crm" style="text-decoration:none;display:inline-flex;align-items:center">@@nav_crm@@</a>
  </div>
</header>

<div class="wrap">

  <div class="resultado sumiu" id="resultado"></div>

  <div class="bloco">
    <h2>@@b_pais@@</h2>
    <p class="dica">@@b_pais_dica@@</p>
    <div class="chips" id="chipsPais"></div>
  </div>

  <div class="bloco">
    <h2>@@b_tipo@@</h2>
    <div class="chips" id="chipsTipo"></div>
    <div class="campo sumiu" id="campoTipoLivre" style="margin-top:10px">
      <label>@@l_tipo_livre@@</label><input id="fTipoLivre" placeholder="@@ph_tipo_livre@@">
    </div>
  </div>

  <div class="bloco sumiu" id="blocoMaloclusao">
    <h2>@@b_maloclusao@@</h2>
    <div class="chips" id="chipsMaloclusao"></div>
  </div>

  <div class="bloco">
    <h2>@@b_associados@@</h2>
    <p class="dica">@@d_associados@@</p>
    <div class="chips" id="chipsAssociados"></div>
  </div>

  <div class="bloco">
    <h2>@@b_paciente@@</h2>
    <div class="linha">
      <div class="campo" style="flex:2"><label>@@l_paciente@@</label><input id="fPaciente"></div>
      <div class="campo"><label>@@l_idade@@</label><input id="fIdade" inputmode="numeric"></div>
    </div>
    <div class="campo"><label>@@l_convenio@@</label><div class="chips" id="chipsConvenio"></div></div>
    <div class="linha">
      <div class="campo"><label>@@l_convenio_outro@@</label><input id="fConvenio"></div>
      <div class="campo"><label>@@l_carteirinha@@</label><input id="fCarteirinha"></div>
      <div class="campo"><label>@@l_plano@@</label><input id="fPlano"></div>
      <div class="campo sumiu" id="campoDni"><label>@@l_dni@@</label><input id="fDni"></div>
    </div>
  </div>

  <div class="bloco">
    <h2>@@b_diagnostico@@</h2>
    <div class="linha">
      <div class="campo"><label>@@l_cid@@</label><input id="fCid"></div>
      <div class="campo" style="flex:2"><label>@@l_cid_desc@@</label><input id="fCidDesc"></div>
      <div class="campo"><label>@@l_cid2@@</label><input id="fCid2"></div>
    </div>
  </div>

  <div class="bloco">
    <h2>@@b_procs@@</h2>
    <p class="dica">@@d_procs@@</p>
    <div id="listaProcs"></div>
    <button class="mini" id="btnAddProc">@@add_proc@@</button>
  </div>

  <div class="bloco">
    <h2>@@b_hospital@@</h2>
    <div class="linha">
      <div class="campo" style="flex:2"><label>@@l_hospital@@</label><input id="fHospital"></div>
      <div class="campo"><label>@@l_data@@</label><input id="fData" type="date"></div>
    </div>
    <div class="linha">
      <div class="campo"><label>@@l_carater@@</label><select id="fCarater"></select></div>
      <div class="campo"><label>@@l_tipo_internacao@@</label><select id="fTipoInternacao"></select></div>
      <div class="campo"><label>@@l_regime@@</label><select id="fRegime"></select></div>
      <div class="campo"><label>@@l_diarias@@</label><input id="fDiarias" style="max-width:90px"></div>
    </div>
  </div>

  <div class="bloco">
    <h2>@@b_exames@@</h2>
    <div class="chips" id="chipsExames"></div>
  </div>

  <div class="bloco">
    <h2>@@b_material@@</h2>
    <div id="listaMats"></div>
    <button class="mini" id="btnAddMat">@@add_mat@@</button>
    <div class="linha" style="margin-top:12px">
      <div class="campo"><label>@@l_forn@@ 1</label><input id="fForn1"></div>
      <div class="campo"><label>@@l_forn@@ 2</label><input id="fForn2"></div>
      <div class="campo"><label>@@l_forn@@ 3</label><input id="fForn3"></div>
    </div>
  </div>

  <div class="bloco">
    <h2>@@b_solicitante@@</h2>
    <p class="dica">@@d_solicitante@@</p>
    <div class="linha">
      <div class="campo" style="flex:2"><label>@@l_cirurgiao@@</label><input id="fCirurgiao" placeholder="@@ph_cirurgiao@@"></div>
      <div class="campo"><label>@@l_conselho@@</label><input id="fCro"></div>
      <div class="campo"><label>@@l_uf@@</label><input id="fUf" style="max-width:80px" maxlength="2"></div>
    </div>
    <div class="campo"><label>@@l_obs@@</label><input id="fObs"></div>
  </div>

  <details class="bloco">
    <summary style="cursor:pointer;font-size:12px;color:#98a7b8;text-transform:uppercase;letter-spacing:.05em;font-weight:650">@@b_textos@@</summary>
    <div style="margin-top:12px">
      <div class="campo"><label>@@l_indicacao@@</label><textarea id="fIndicacao" placeholder="@@ph_vazio@@"></textarea></div>
      <div class="campo"><label>@@l_justificativa@@</label><textarea id="fJustificativa" placeholder="@@ph_vazio@@"></textarea></div>
      <div class="campo"><label>@@l_conduta@@</label><textarea id="fConduta" placeholder="@@ph_vazio@@"></textarea></div>
    </div>
  </details>

  <div class="status" id="status"></div>
</div>

<div class="barra">
  <button class="btn btn-ghost" id="btnLimpar">@@btn_limpar@@</button>
  <button class="btn" id="btnGerar">@@btn_gerar@@</button>
</div>

<script>
let CAT = null;
let editando = null;           // nome do site quando veio de ?editar=
const sel = {pais: "@@_pais_padrao@@", tipo: "ortognatica", maloclusao: "", associados: new Set(), exames: new Set()};
const $ = (id) => document.getElementById(id);

function chip(texto, ativo, onclick){
  const b = document.createElement("button");
  b.className = "chip" + (ativo ? " on" : "");
  b.type = "button";
  b.textContent = texto;
  b.onclick = () => onclick(b);
  return b;
}

// Trocar o pais troca o FORMULARIO que sai no fim: guia TISS no Brasil,
// solicitud de autorizacion nos paises hispanos. Na tela muda so' a lista de
// seguradoras, a de fabricantes e o campo de documento — os dados clinicos
// sao os mesmos, e por isso nao se perde nada ao trocar no meio.
function aplicaPais(pais, trocarListas){
  sel.pais = pais;
  [...$("chipsPais").children].forEach(b => b.classList.toggle("on", b.dataset.pais === pais));
  $("campoDni").classList.toggle("sumiu", pais === "br");
  if (trocarListas) {
    const forn = (CAT.fornecedores_por_pais || {})[pais] || CAT.fornecedores || [];
    $("fForn1").value = forn[0] || "";
    $("fForn2").value = forn[1] || "";
    $("fForn3").value = forn[2] || "";
    // A seguradora escolhida so' e' apagada se nao existir no pais novo — quem
    // digitou "Particular" ou um nome proprio nao perde o que escreveu.
    const lista = (CAT.convenios_por_pais || {})[pais] || [];
    const atual = $("fConvenio").value;
    if (atual && (CAT.convenios_por_pais || {}).br && Object.values(CAT.convenios_por_pais)
        .some(l => l.includes(atual)) && !lista.includes(atual)) {
      $("fConvenio").value = "";
    }
    ajustaCodigosPorPais();
  }
  montaChips();
}

// Codigo TUSS so' existe no Brasil. Ao sair do Brasil os codigos que vieram do
// catalogo somem da tela (o nomenclator de la' e' outro, e codigo inventado e'
// pior que campo em branco); ao voltar, reaparecem. O que o cirurgiao digitou a
// mao nunca e' apagado nem sobrescrito.
function ajustaCodigosPorPais(){
  const c = CAT.cirurgias.find(x => x.key === sel.tipo) || {};
  const doCatalogo = (c.procedimentos || []).map(pr => pr.codigo || "").filter(Boolean);
  [...$("listaProcs").children].forEach((d, i) => {
    const inp = d.querySelector(".cod");
    if (sel.pais !== "br") {
      if (doCatalogo.includes(inp.value)) inp.value = "";
    } else if (!inp.value) {
      const pr = (c.procedimentos || [])[i];
      if (pr && pr.codigo) inp.value = pr.codigo;
    }
  });
}

function pintaTipo(key){
  [...$("chipsTipo").children].forEach(b => b.classList.toggle("on", b.dataset.key === key));
  const c = CAT.cirurgias.find(x => x.key === key) || {};
  $("blocoMaloclusao").classList.toggle("sumiu", !c.pede_maloclusao);
  $("campoTipoLivre").classList.toggle("sumiu", key !== "outra");
}

function aplicaTipo(key, repovoar){
  const c = CAT.cirurgias.find(x => x.key === key);
  if (!c) return;
  sel.tipo = key;
  pintaTipo(key);
  // Trocar de tipo repovoa procedimento/material/CID: e' o ponto todo do
  // catalogo. So nao mexe quando estamos carregando um pedido ja salvo.
  if (!repovoar) return;
  $("fCid").value = c.cid || "";
  $("fCidDesc").value = c.cid_desc || "";
  $("fCid2").value = c.cid_extra || "";
  $("fDiarias").value = c.diarias || "01";
  $("fTipoInternacao").value = c.tipo_internacao || "2";
  $("fRegime").value = c.regime || "1";
  desenhaProcs(c.procedimentos);
  desenhaMats(c.materiais);
  ajustaCodigosPorPais();
}

function linhaProc(pr){
  const d = document.createElement("div");
  d.className = "item-lista";
  d.innerHTML = '<input class="cod" placeholder="@@ph_codigo@@"><input class="desc" placeholder="@@ph_proc@@"><input class="qtd" placeholder="@@ph_qtd@@">';
  const rm = document.createElement("button");
  rm.className = "mini"; rm.type = "button"; rm.textContent = "✕";
  rm.onclick = () => d.remove();
  d.appendChild(rm);
  d.querySelector(".cod").value = pr.codigo || "";
  d.querySelector(".desc").value = pr.desc || "";
  d.querySelector(".qtd").value = pr.qtd || "01";
  return d;
}

function linhaMat(m){
  const d = document.createElement("div");
  d.className = "item-lista";
  d.innerHTML = '<input class="desc" placeholder="@@ph_material@@"><input class="qtd" placeholder="@@ph_qtd@@">';
  const rm = document.createElement("button");
  rm.className = "mini"; rm.type = "button"; rm.textContent = "✕";
  rm.onclick = () => d.remove();
  d.appendChild(rm);
  d.querySelector(".desc").value = m.desc || "";
  d.querySelector(".qtd").value = m.qtd || "01";
  return d;
}

function desenhaProcs(lista){
  $("listaProcs").innerHTML = "";
  (lista || []).forEach(pr => $("listaProcs").appendChild(linhaProc(pr)));
}
function desenhaMats(lista){
  $("listaMats").innerHTML = "";
  (lista || []).forEach(m => $("listaMats").appendChild(linhaMat(m)));
}

function opcoes(selectEl, pares){
  selectEl.innerHTML = "";
  pares.forEach(([v, t]) => {
    const o = document.createElement("option");
    o.value = v; o.textContent = t;
    selectEl.appendChild(o);
  });
}

function coleta(){
  const procs = [...$("listaProcs").children].map(d => ({
    codigo: d.querySelector(".cod").value,
    desc: d.querySelector(".desc").value,
    qtd: d.querySelector(".qtd").value,
  })).filter(x => x.desc || x.codigo);
  const mats = [...$("listaMats").children].map(d => ({
    desc: d.querySelector(".desc").value,
    qtd: d.querySelector(".qtd").value,
  })).filter(x => x.desc);
  return {
    pais: sel.pais,
    tipo: sel.tipo,
    tipo_livre: $("fTipoLivre").value,
    dni: $("fDni").value,
    paciente: $("fPaciente").value,
    idade: $("fIdade").value,
    convenio: $("fConvenio").value,
    carteirinha: $("fCarteirinha").value,
    plano: $("fPlano").value,
    cid: $("fCid").value,
    cid_desc: $("fCidDesc").value,
    cid2: $("fCid2").value,
    maloclusao: sel.maloclusao,
    associados: [...sel.associados],
    exames: [...sel.exames],
    hospital: $("fHospital").value,
    data_procedimento: $("fData").value,
    carater: $("fCarater").value,
    tipo_internacao: $("fTipoInternacao").value,
    regime: $("fRegime").value,
    diarias: $("fDiarias").value,
    fornecedores: [$("fForn1").value, $("fForn2").value, $("fForn3").value],
    cirurgiao: $("fCirurgiao").value,
    cro: $("fCro").value,
    uf: $("fUf").value,
    observacao: $("fObs").value,
    indicacao: $("fIndicacao").value,
    justificativa: $("fJustificativa").value,
    conduta: $("fConduta").value,
    procedimentos: procs,
    materiais: mats,
  };
}

function preenche(p){
  aplicaPais(p.pais || "br", false);
  aplicaTipo(p.tipo || "ortognatica", false);
  $("fDni").value = p.dni || "";
  $("fTipoLivre").value = p.tipo_livre || "";
  $("fPaciente").value = p.paciente || "";
  $("fIdade").value = p.idade || "";
  $("fConvenio").value = p.convenio || "";
  $("fCarteirinha").value = p.carteirinha || "";
  $("fPlano").value = p.plano || "";
  $("fCid").value = p.cid || "";
  $("fCidDesc").value = p.cid_desc || "";
  $("fCid2").value = p.cid2 || "";
  $("fHospital").value = p.hospital || "";
  $("fData").value = p.data_procedimento || "";
  $("fCarater").value = p.carater || "E";
  $("fTipoInternacao").value = p.tipo_internacao || "2";
  $("fRegime").value = p.regime || "1";
  $("fDiarias").value = p.diarias || "01";
  const f = p.fornecedores || [];
  $("fForn1").value = f[0] || ""; $("fForn2").value = f[1] || ""; $("fForn3").value = f[2] || "";
  $("fCirurgiao").value = p.cirurgiao || "";
  $("fCro").value = p.cro || "";
  $("fUf").value = p.uf || "";
  $("fObs").value = p.observacao || "";
  $("fIndicacao").value = p.indicacao || "";
  $("fJustificativa").value = p.justificativa || "";
  $("fConduta").value = p.conduta || "";
  sel.maloclusao = p.maloclusao || "";
  sel.associados = new Set(p.associados || []);
  sel.exames = new Set(p.exames || []);
  desenhaProcs(p.procedimentos);
  desenhaMats(p.materiais);
  montaChips();
}

function montaChips(){
  const cm = $("chipsMaloclusao"); cm.innerHTML = "";
  CAT.maloclusoes.forEach(m => cm.appendChild(chip(m, sel.maloclusao === m, () => {
    sel.maloclusao = (sel.maloclusao === m) ? "" : m;
    montaChips();
  })));
  const ca = $("chipsAssociados"); ca.innerHTML = "";
  CAT.associados.forEach(a => ca.appendChild(chip(a, sel.associados.has(a), (b) => {
    if (sel.associados.has(a)) { sel.associados.delete(a); } else { sel.associados.add(a); }
    b.classList.toggle("on");
  })));
  const ce = $("chipsExames"); ce.innerHTML = "";
  CAT.exames.forEach(x => ce.appendChild(chip(x, sel.exames.has(x), (b) => {
    if (sel.exames.has(x)) { sel.exames.delete(x); } else { sel.exames.add(x); }
    b.classList.toggle("on");
  })));
  const cc = $("chipsConvenio"); cc.innerHTML = "";
  const listaConv = (CAT.convenios_por_pais || {})[sel.pais] || CAT.convenios;
  listaConv.forEach(c => cc.appendChild(chip(c, $("fConvenio").value === c, (b) => {
    $("fConvenio").value = c;
    [...cc.children].forEach(x => x.classList.remove("on"));
    b.classList.add("on");
  })));
}

function lembraSolicitante(){
  try {
    localStorage.setItem("copiloto_solicitante", JSON.stringify({
      cirurgiao: $("fCirurgiao").value, cro: $("fCro").value,
      uf: $("fUf").value, hospital: $("fHospital").value,
      fornecedores: [$("fForn1").value, $("fForn2").value, $("fForn3").value],
    }));
  } catch (e) {}
}

function aplicaLembrado(){
  try {
    const s = JSON.parse(localStorage.getItem("copiloto_solicitante") || "{}");
    if (s.cirurgiao && !$("fCirurgiao").value) $("fCirurgiao").value = s.cirurgiao;
    if (s.cro && !$("fCro").value) $("fCro").value = s.cro;
    if (s.uf && !$("fUf").value) $("fUf").value = s.uf;
    if (s.hospital && !$("fHospital").value) $("fHospital").value = s.hospital;
    const f = s.fornecedores || [];
    if (f[0] && !$("fForn1").value) { $("fForn1").value = f[0]; $("fForn2").value = f[1] || ""; $("fForn3").value = f[2] || ""; }
  } catch (e) {}
}

async function gerar(){
  const p = coleta();
  if (!p.paciente.trim()) { $("status").textContent = "@@s_falta_paciente@@"; $("fPaciente").focus(); return; }
  $("btnGerar").disabled = true;
  $("status").textContent = "@@s_gerando@@";
  lembraSolicitante();
  try {
    const url = editando ? ("/crm/api/pedido/" + editando) : "/crm/api/pedido";
    const r = await fetch(url, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(p)});
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || "falhou");
    editando = j.nome;
    history.replaceState(null, "", "/crm/pedido?editar=" + j.nome);
    const destino = j.url || ("/s/" + j.nome);
    const box = $("resultado");
    box.classList.remove("sumiu");
    // Duas peças, destinos diferentes: a guia é o formulário da operadora e o
    // relatório é o anexo que justifica. O portal costuma pedir um arquivo para
    // cada; no balcão vão grampeados — por isso as três saídas.
    box.innerHTML = '<h2>@@r_gerado@@</h2>' +
      '<p style="font-size:13px;margin:.2em 0">@@r_abrir@@' +
      '<a href="' + destino + '/guia.html" target="_blank">@@r_so_guia@@</a> · ' +
      '<a href="' + destino + '/relatorio.html" target="_blank">@@r_so_rel@@</a> · ' +
      '<a href="' + destino + '" target="_blank">@@r_os_dois@@</a></p>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">' +
      '<button class="btn btn-ghost" data-parte="guia">@@r_mandar_guia@@</button>' +
      '<button class="btn btn-ghost" data-parte="relatorio">@@r_mandar_rel@@</button>' +
      '<button class="btn btn-ghost" data-parte="">@@r_mandar_dois@@</button>' +
      '<a class="btn btn-ghost" href="/crm/pedido" style="text-decoration:none">@@r_novo@@</a></div>' +
      '<div class="status" id="statusZap" style="text-align:left"></div>';
    box.querySelectorAll("button[data-parte]").forEach(b => {
      b.onclick = () => mandarZap(b.dataset.parte);
    });
    $("status").textContent = "";
    window.scrollTo({top: 0, behavior: "smooth"});
  } catch (e) {
    $("status").textContent = "@@s_erro@@" + e.message;
  }
  $("btnGerar").disabled = false;
}

async function mandarZap(parte){
  const s = $("statusZap");
  const nome = parte === "guia" ? "@@z_a_guia@@" : (parte === "relatorio" ? "@@z_o_rel@@" : "@@z_completo@@");
  s.textContent = "@@z_gerando@@" + nome + "...";
  try {
    const url = "/documentos/api/" + editando + "/send-group" + (parte ? ("?parte=" + parte) : "");
    const r = await fetch(url, {method: "POST"});
    const j = await r.json();
    s.textContent = r.ok ? ("@@z_ok@@" + nome + "@@z_ok_fim@@") : ("@@z_nao@@" + (j.error || ""));
  } catch (e) {
    s.textContent = "@@z_nao@@" + e.message;
  }
}

async function iniciar(){
  CAT = await (await fetch("/crm/api/pedido/catalogo")).json();
  const ct = $("chipsTipo");
  CAT.cirurgias.forEach(c => {
    const b = chip(c.nome, false, () => aplicaTipo(c.key, true));
    b.dataset.key = c.key;
    ct.appendChild(b);
  });
  const cp = $("chipsPais");
  CAT.paises.forEach(([codigo, rotulo]) => {
    const b = chip(rotulo, false, () => aplicaPais(codigo, true));
    b.dataset.pais = codigo;
    cp.appendChild(b);
  });

  opcoes($("fCarater"), CAT.carater);
  opcoes($("fTipoInternacao"), CAT.tipo_internacao);
  opcoes($("fRegime"), CAT.regime);
  $("fForn1").value = CAT.fornecedores[0] || "";
  $("fForn2").value = CAT.fornecedores[1] || "";
  $("fForn3").value = CAT.fornecedores[2] || "";

  const q = new URLSearchParams(location.search).get("editar");
  if (q) {
    const r = await fetch("/crm/api/pedido/" + q);
    if (r.ok) {
      editando = q;
      preenche(await r.json());
      $("status").textContent = "@@s_editando@@";
      aplicaLembrado();
      return;
    }
  }
  aplicaPais(sel.pais, true);
  aplicaTipo("ortognatica", true);
  montaChips();
  aplicaLembrado();
}

$("btnAddProc").onclick = () => $("listaProcs").appendChild(linhaProc({}));
$("btnAddMat").onclick = () => $("listaMats").appendChild(linhaMat({}));
$("btnGerar").onclick = gerar;
$("btnLimpar").onclick = () => { location.href = "/crm/pedido"; };
$("fConvenio").addEventListener("input", () => {
  [...$("chipsConvenio").children].forEach(b => b.classList.toggle("on", b.textContent === $("fConvenio").value));
});
iniciar();
</script>
</body>
</html>
"""
