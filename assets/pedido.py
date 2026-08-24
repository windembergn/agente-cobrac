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


def catalogo():
    """O que a tela precisa para montar os cliques."""
    return {
        "cirurgias": CIRURGIAS,
        "maloclusoes": MALOCLUSOES,
        "associados": ASSOCIADOS,
        "exames": EXAMES,
        "convenios": CONVENIOS,
        "fornecedores": FORNECEDORES_PADRAO,
        "carater": CARATER,
        "tipo_internacao": TIPO_INTERNACAO,
        "regime": REGIME,
    }


def _cirurgia(key):
    for c in CIRURGIAS:
        if c["key"] == key:
            return c
    return CIRURGIAS[-1]


# ============================================================== TEXTO CLINICO
def _lista_por_extenso(itens):
    itens = [i for i in itens if i]
    if not itens:
        return ""
    if len(itens) == 1:
        return itens[0]
    return ", ".join(itens[:-1]) + " e " + itens[-1]


def _frase_associados(associados):
    txt = _lista_por_extenso(associados)
    return f", com quadro associado de {txt}" if txt else ""


def _frase_maloclusao(maloclusao, cirurgia):
    if maloclusao:
        return maloclusao + ","
    return "alteração esquelética," if cirurgia.get("pede_maloclusao") else ""


def montar_textos(p):
    """Monta indicacao clinica, justificativa e conduta a partir dos cliques.

    Se o pedido vier com texto proprio (o agente escreveu no WhatsApp, ou o
    cirurgiao editou na tela), o texto proprio ganha — nunca sobrescrevemos."""
    c = _cirurgia(p.get("tipo", ""))
    ctx = {
        "maloclusao": _frase_maloclusao(p.get("maloclusao", ""), c),
        "associados_frase": _frase_associados(p.get("associados", [])),
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
    nome = re.sub(r"[^a-z0-9]+", "-", nome).strip("-")
    partes = [x for x in nome.split("-") if x][:3]
    base = "pedido-" + ("-".join(partes) or "paciente")
    return base[:60]


# ============================================================== RENDER (HTML)
def _e(s):
    return html.escape(str(s or "").strip(), quote=False)


def _campo(num, rotulo, valor="", classe=""):
    v = _e(valor) or '<span class="linha-vazia"></span>'
    return (
        f'<td class="{classe}"><span class="campo-num">{_e(num)} — {_e(rotulo)}</span>'
        f'<span class="campo-valor">{v}</span></td>'
    )


def _data_extenso(ts=None):
    t = time.localtime(ts or time.time())
    return f"{t.tm_mday} de {MESES[t.tm_mon - 1]} de {t.tm_year}"


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


def _pendencias(p):
    faltando = []
    if not (p.get("carteirinha") or "").strip():
        faltando.append("número da carteirinha")
    if not (p.get("cro") or "").strip():
        faltando.append("CRO do solicitante")
    if not (p.get("cid") or "").strip():
        faltando.append("CID-10")
    if not (p.get("hospital") or "").strip():
        faltando.append("hospital")
    if not (p.get("data_procedimento") or "").strip():
        faltando.append("data do procedimento")
    sem_codigo = [
        pr.get("desc")
        for pr in p.get("procedimentos", [])
        if pr.get("desc") and not (pr.get("codigo") or "").strip()
    ]
    if sem_codigo:
        faltando.append("código do procedimento na tabela da operadora (" + ", ".join(sem_codigo[:3]) + ")")
    return "; ".join(faltando) if faltando else "nenhuma"


PARTES = ("completo", "guia", "relatorio")

_TITULO_PARTE = {
    "completo": "Solicitação de cirurgia",
    "guia": "Guia de solicitação de internação",
    "relatorio": "Relatório médico para solicitação",
}


def render_pagina(p, parte="completo"):
    """Devolve o HTML da pagina do pedido.

    Sao DUAS pecas com destinos diferentes: a guia e' o formulario DA OPERADORA
    (tem campo que so ela preenche e tres assinaturas) e o relatorio e' o anexo
    que justifica, assinado so pelo cirurgiao. No balcao vao grampeadas; no
    portal da operadora sobe um arquivo para cada. Por isso a mesma ficha gera
    tres saidas: `completo`, `guia` e `relatorio`."""
    if parte not in PARTES:
        parte = "completo"
    c = _cirurgia(p.get("tipo", ""))
    indicacao, justificativa, conduta = montar_textos(p)
    titulo_cirurgia = (p.get("tipo_livre") or "").strip() or c["nome"]

    paciente = p.get("paciente") or "(paciente a confirmar)"
    idade = (p.get("idade") or "").strip()
    paciente_linha = f"{paciente}, {idade} anos" if idade else paciente
    convenio = (p.get("convenio") or "").strip()
    carteirinha = (p.get("carteirinha") or "").strip()
    convenio_linha = " — carteirinha ".join([x for x in [convenio, carteirinha] if x]) or "(a confirmar)"
    cid = (p.get("cid") or "").strip()
    cid_desc = (p.get("cid_desc") or c.get("cid_desc") or "").strip()
    cid_linha = " — ".join([x for x in [cid, cid_desc] if x]) or "(a confirmar pelo cirurgião)"
    cid2 = (p.get("cid2") or "").strip()

    procs_txt = "; ".join(
        [
            " ".join([x for x in [pr.get("desc", "").strip(), f"({pr.get('codigo')})" if pr.get("codigo") else ""] if x])
            for pr in p.get("procedimentos", [])
            if pr.get("desc")
        ]
    ) or "(a confirmar)"

    exames = p.get("exames", [])
    associados = p.get("associados", [])
    materiais_li = "\n      ".join(
        f"<li>{_e(m.get('desc'))} — {_e(m.get('qtd'))}</li>"
        for m in p.get("materiais", [])
        if m.get("desc")
    ) or "<li>(nenhum material especificado)</li>"
    exames_li = "\n      ".join(f"<li>{_e(x)}</li>" for x in exames) or "<li>(nenhum exame anexado)</li>"

    fornecedores = [f for f in p.get("fornecedores", []) if f]
    forn_txt = _lista_por_extenso(fornecedores)
    data_proc = _data_br(p.get("data_procedimento", ""))
    cirurgiao = (p.get("cirurgiao") or "Dr(a). [nome do cirurgião]").strip()
    cro = (p.get("cro") or "(a confirmar)").strip()
    uf = (p.get("uf") or "").strip()
    hospital = (p.get("hospital") or "").strip()
    obs = (p.get("observacao") or "Não necessariamente será utilizado todo OPME solicitado").strip()

    secao_associados = ""
    if associados:
        secao_associados = (
            "<h2>Quadro associado</h2>\n    <ul>\n      "
            + "\n      ".join(f"<li>{_e(a)}</li>" for a in associados)
            + "\n    </ul>"
        )

    carater_lbl = dict(CARATER).get(p.get("carater", "E"), "Eletiva")
    tipo_int_lbl = dict(TIPO_INTERNACAO).get(p.get("tipo_internacao", c["tipo_internacao"]), "Cirúrgica")
    regime_lbl = dict(REGIME).get(p.get("regime", c["regime"]), "Hospitalar")

    cabeca = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_TITULO_PARTE[parte]} — {_e(paciente)}</title>
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
        "completo": '<a class="btn btn-vazado" href="guia.html">Só a guia</a>\n  <a class="btn btn-vazado" href="relatorio.html">Só o relatório</a>',
        "guia": '<a class="btn btn-vazado" href="relatorio.html">Ver o relatório</a>\n  <a class="btn btn-vazado" href="./">Ver os dois</a>',
        "relatorio": '<a class="btn btn-vazado" href="guia.html">Ver a guia</a>\n  <a class="btn btn-vazado" href="./">Ver os dois</a>',
    }[parte]

    acoes = f"""
<div class="acoes-doc" style="margin-top:var(--sp-5)">
  <button class="btn" onclick="window.print()">🖨️ Imprimir / salvar em PDF</button>
  {outras}
</div>
"""

    relatorio = f"""
<article class="documento">

  <header>
    <p class="rotulo">Solicitação de liberação de cirurgia</p>
    <h1>{_e(titulo_cirurgia)}</h1>
    <p class="small muted">Emitido em {_data_extenso()}</p>
  </header>

  <dl class="dados">
    <div><dt>Paciente</dt><dd>{_e(paciente_linha)}</dd></div>
    <div><dt>Convênio</dt><dd>{_e(convenio_linha)}</dd></div>
    <div><dt>Hipótese diagnóstica</dt><dd>{_e(cid_linha)}</dd></div>
    <div><dt>Procedimento</dt><dd>{_e(procs_txt)}</dd></div>
    <div><dt>Hospital</dt><dd>{_e(hospital) or "(a confirmar)"}</dd></div>
    <div><dt>Data prevista</dt><dd>{_e(data_proc) or "(a confirmar)"}</dd></div>
  </dl>

  <section class="prosa" style="padding-block:var(--sp-5)">
    <h2>Justificativa clínica</h2>
    <p>{_e(justificativa)}</p>

    <h2>Conduta proposta</h2>
    <p>{_e(conduta)}</p>

    {secao_associados}

    <h2>Materiais solicitados (OPME)</h2>
    <ul>
      {materiais_li}
    </ul>

    <h2>Exames anexados</h2>
    <ul>
      {exames_li}
    </ul>
  </section>

  <div class="aviso">
    <p><strong>Pendências para o cirurgião confirmar:</strong> {_e(_pendencias(p))}.</p>
  </div>

  <div class="assinatura">
    {_e(cirurgiao)}<br>
    <span class="muted">CRO {_e(cro)}{(" / " + _e(uf)) if uf else ""}</span>
  </div>

  <p class="small muted" style="margin-top:var(--sp-6)">Minuta gerada para revisão e assinatura do cirurgião responsável.</p>

</article>
"""

    guia = f"""
<article class="documento guia">

  <table class="guia-topo">
    <tr>
      <td class="operadora">{_e(convenio) or "OPERADORA"}</td>
      <td class="titulo-guia">GUIA DE SOLICITAÇÃO DE INTERNAÇÃO</td>
      {_campo("2", "Nº da guia")}
    </tr>
  </table>

  <table>
    <tr>
      {_campo("1", "Registro ANS")}
      {_campo("3", "Data da autorização")}
      {_campo("4", "Senha")}
      {_campo("5", "Validade da senha")}
      {_campo("6", "Data de emissão", _data_br(time.strftime("%Y-%m-%d")))}
    </tr>
  </table>

  <p class="titulo-bloco">Dados do beneficiário</p>
  <table>
    <tr>
      {_campo("7", "Número da carteira", carteirinha)}
      {_campo("8", "Plano", p.get("plano", ""))}
      {_campo("9", "Validade da carteira", _data_br(p.get("validade_carteira", "")))}
    </tr>
    <tr>
      {_campo("10", "Nome", paciente)}
      {_campo("11", "Cartão Nacional de Saúde", p.get("cns", ""), "col2")}
    </tr>
  </table>

  <p class="titulo-bloco">Dados do contratado solicitante</p>
  <table>
    <tr>
      {_campo("12", "Código na operadora / CNPJ / CPF", p.get("codigo_operadora", ""))}
      {_campo("13", "Nome do contratado", p.get("contratado", ""))}
      {_campo("14", "Código CNES", p.get("cnes", ""))}
    </tr>
    <tr>
      {_campo("15", "Nome do profissional solicitante", cirurgiao)}
      {_campo("16", "Conselho", "CRO")}
      {_campo("17", "Número no conselho", cro)}
      {_campo("18", "UF", uf)}
    </tr>
  </table>

  <p class="titulo-bloco">Dados do contratado solicitado / dados da internação</p>
  <table>
    <tr>
      {_campo("20", "Código na operadora / CNPJ", p.get("codigo_hospital", ""))}
      {_campo("21", "Nome do prestador", hospital)}
    </tr>
    <tr>
      {_campo("22", "Caráter da internação", carater_lbl)}
      {_campo("23", "Tipo de internação", tipo_int_lbl)}
      {_campo("24", "Regime de internação", regime_lbl)}
      {_campo("25", "Qtde. diárias solicitadas", p.get("diarias", c["diarias"]))}
    </tr>
  </table>

  <table>
    <tr>{_campo("26", "Indicação clínica", indicacao, "col4")}</tr>
  </table>

  <p class="titulo-bloco">Hipóteses diagnósticas</p>
  <table>
    <tr>
      {_campo("27", "Tipo de doença", p.get("tipo_doenca", ""))}
      {_campo("28", "Tempo de doença referido", p.get("tempo_doenca", ""))}
      {_campo("30", "CID-10 principal", cid)}
      {_campo("31", "CID-10 (2)", cid2)}
    </tr>
  </table>

  <p class="titulo-bloco">Procedimentos solicitados</p>
  <table class="itens">
    <thead>
      <tr><th class="num">#</th><th class="cod">35 — Código</th><th>36 — Descrição</th><th class="qtd">37 — Qtde. sol.</th><th class="qtd">38 — Qtde. aut.</th></tr>
    </thead>
    <tbody>
      {_bloco_procedimentos(p)}
    </tbody>
  </table>

  <p class="titulo-bloco">OPM solicitados</p>
  <table class="itens">
    <thead>
      <tr><th class="num">#</th><th class="cod">40 — Código</th><th>41 — Descrição</th><th class="qtd">42 — Qtde.</th><th class="forn">43 — Fabricante</th><th class="qtd">44 — Valor</th></tr>
    </thead>
    <tbody>
      {_bloco_opme(p)}
    </tbody>
  </table>

  <table>
    <tr>
      {_campo("45", "Data provável da admissão hospitalar", data_proc)}
      {_campo("46", "Qtde. diárias autorizadas")}
      {_campo("47", "Tipo de acomodação autorizada")}
    </tr>
  </table>

  <table>
    <tr>{_campo("51", "Observação", obs, "col3")}</tr>
  </table>

  <table class="assinaturas">
    <tr>
      <td><span class="campo-num">52 — Data e assinatura do médico solicitante</span>
        <span class="assina">{_e(cirurgiao)}<br><span class="muted small">CRO {_e(cro)}{(" / " + _e(uf)) if uf else ""}</span></span></td>
      <td><span class="campo-num">53 — Data e assinatura do beneficiário</span><span class="assina">&nbsp;</span></td>
      <td><span class="campo-num">54 — Data e assinatura do responsável pela autorização</span><span class="assina">&nbsp;</span></td>
    </tr>
  </table>

  <p class="small muted" style="margin-top:var(--sp-5)">Guia preenchida pelo Copiloto a partir dos dados informados pelo cirurgião. Confira os códigos na tabela da operadora antes de protocolar.{(" Fornecedores indicados: " + _e(forn_txt) + ".") if forn_txt else ""}</p>

</article>
"""

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


def normalizar(b):
    """Aceita tanto o JSON da tela quanto o que a habilidade monta no WhatsApp,
    e devolve o pedido com os defaults do tipo de cirurgia preenchidos."""
    c = _cirurgia(b.get("tipo", ""))
    p = {
        "tipo": c["key"],
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
        "fornecedores": [f for f in (b.get("fornecedores") or FORNECEDORES_PADRAO) if f][:3],
        "procedimentos": [
            {
                "codigo": (pr.get("codigo") or "").strip(),
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
FORM_PAGE = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pedido de cirurgia — Copiloto</title>
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
    <h1>Pedido de cirurgia</h1>
    <div class="sub">clique no que se aplica — o resto vem preenchido e você só confere</div>
  </div>
  <div style="display:flex;gap:8px">
    <a class="btn btn-ghost" href="/documentos" style="text-decoration:none;display:inline-flex;align-items:center">📄 Documentos</a>
    <a class="btn btn-ghost" href="/crm" style="text-decoration:none;display:inline-flex;align-items:center">← CRM</a>
  </div>
</header>

<div class="wrap">

  <div class="resultado sumiu" id="resultado"></div>

  <div class="bloco">
    <h2>1 · Tipo de cirurgia</h2>
    <div class="chips" id="chipsTipo"></div>
    <div class="campo sumiu" id="campoTipoLivre" style="margin-top:10px">
      <label>Descreva a cirurgia</label><input id="fTipoLivre" placeholder="ex.: frenectomia lingual sob anestesia geral">
    </div>
  </div>

  <div class="bloco sumiu" id="blocoMaloclusao">
    <h2>2 · Tipo de má oclusão</h2>
    <div class="chips" id="chipsMaloclusao"></div>
  </div>

  <div class="bloco">
    <h2>3 · Problemas associados</h2>
    <p class="dica">entram na justificativa clínica do relatório</p>
    <div class="chips" id="chipsAssociados"></div>
  </div>

  <div class="bloco">
    <h2>4 · Paciente e convênio</h2>
    <div class="linha">
      <div class="campo" style="flex:2"><label>Nome do paciente</label><input id="fPaciente"></div>
      <div class="campo"><label>Idade</label><input id="fIdade" inputmode="numeric"></div>
    </div>
    <div class="campo"><label>Convênio</label><div class="chips" id="chipsConvenio"></div></div>
    <div class="linha">
      <div class="campo"><label>Convênio (outro / conferir)</label><input id="fConvenio"></div>
      <div class="campo"><label>Carteirinha</label><input id="fCarteirinha"></div>
      <div class="campo"><label>Plano</label><input id="fPlano"></div>
    </div>
  </div>

  <div class="bloco">
    <h2>5 · Diagnóstico</h2>
    <div class="linha">
      <div class="campo"><label>CID-10 principal</label><input id="fCid"></div>
      <div class="campo" style="flex:2"><label>Descrição do CID</label><input id="fCidDesc"></div>
      <div class="campo"><label>CID-10 (2)</label><input id="fCid2"></div>
    </div>
  </div>

  <div class="bloco">
    <h2>6 · Procedimentos solicitados</h2>
    <p class="dica">código da tabela da operadora — confira antes de protocolar; em branco significa "preencher na guia"</p>
    <div id="listaProcs"></div>
    <button class="mini" id="btnAddProc">+ procedimento</button>
  </div>

  <div class="bloco">
    <h2>7 · Hospital e internação</h2>
    <div class="linha">
      <div class="campo" style="flex:2"><label>Hospital</label><input id="fHospital"></div>
      <div class="campo"><label>Data do procedimento</label><input id="fData" type="date"></div>
    </div>
    <div class="linha">
      <div class="campo"><label>Caráter</label><select id="fCarater"></select></div>
      <div class="campo"><label>Tipo de internação</label><select id="fTipoInternacao"></select></div>
      <div class="campo"><label>Regime</label><select id="fRegime"></select></div>
      <div class="campo"><label>Diárias</label><input id="fDiarias" style="max-width:90px"></div>
    </div>
  </div>

  <div class="bloco">
    <h2>8 · Exames anexados</h2>
    <div class="chips" id="chipsExames"></div>
  </div>

  <div class="bloco">
    <h2>9 · Material (OPME) e fornecedores</h2>
    <div id="listaMats"></div>
    <button class="mini" id="btnAddMat">+ material</button>
    <div class="linha" style="margin-top:12px">
      <div class="campo"><label>Fornecedor 1</label><input id="fForn1"></div>
      <div class="campo"><label>Fornecedor 2</label><input id="fForn2"></div>
      <div class="campo"><label>Fornecedor 3</label><input id="fForn3"></div>
    </div>
  </div>

  <div class="bloco">
    <h2>10 · Solicitante</h2>
    <p class="dica">fica guardado neste navegador e já vem preenchido no próximo pedido</p>
    <div class="linha">
      <div class="campo" style="flex:2"><label>Cirurgião</label><input id="fCirurgiao" placeholder="Dr(a). ..."></div>
      <div class="campo"><label>CRO</label><input id="fCro"></div>
      <div class="campo"><label>UF</label><input id="fUf" style="max-width:80px" maxlength="2"></div>
    </div>
    <div class="campo"><label>Observação (campo 51 da guia)</label><input id="fObs"></div>
  </div>

  <details class="bloco">
    <summary style="cursor:pointer;font-size:12px;color:#98a7b8;text-transform:uppercase;letter-spacing:.05em;font-weight:650">11 · Textos do relatório (opcional — o Copiloto já escreve)</summary>
    <div style="margin-top:12px">
      <div class="campo"><label>Indicação clínica (campo 26 da guia)</label><textarea id="fIndicacao" placeholder="deixe vazio para o Copiloto escrever"></textarea></div>
      <div class="campo"><label>Justificativa clínica</label><textarea id="fJustificativa" placeholder="deixe vazio para o Copiloto escrever"></textarea></div>
      <div class="campo"><label>Conduta proposta</label><textarea id="fConduta" placeholder="deixe vazio para o Copiloto escrever"></textarea></div>
    </div>
  </details>

  <div class="status" id="status"></div>
</div>

<div class="barra">
  <button class="btn btn-ghost" id="btnLimpar">Limpar</button>
  <button class="btn" id="btnGerar">Gerar pedido</button>
</div>

<script>
let CAT = null;
let editando = null;           // nome do site quando veio de ?editar=
const sel = {tipo: "ortognatica", maloclusao: "", associados: new Set(), exames: new Set()};
const $ = (id) => document.getElementById(id);

function chip(texto, ativo, onclick){
  const b = document.createElement("button");
  b.className = "chip" + (ativo ? " on" : "");
  b.type = "button";
  b.textContent = texto;
  b.onclick = () => onclick(b);
  return b;
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
}

function linhaProc(pr){
  const d = document.createElement("div");
  d.className = "item-lista";
  d.innerHTML = '<input class="cod" placeholder="código"><input class="desc" placeholder="procedimento"><input class="qtd" placeholder="qtd">';
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
  d.innerHTML = '<input class="desc" placeholder="material"><input class="qtd" placeholder="qtd">';
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
    tipo: sel.tipo,
    tipo_livre: $("fTipoLivre").value,
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
  aplicaTipo(p.tipo || "ortognatica", false);
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
  CAT.convenios.forEach(c => cc.appendChild(chip(c, $("fConvenio").value === c, (b) => {
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
  if (!p.paciente.trim()) { $("status").textContent = "Falta o nome do paciente."; $("fPaciente").focus(); return; }
  $("btnGerar").disabled = true;
  $("status").textContent = "Gerando...";
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
    box.innerHTML = '<h2>✅ Pedido gerado</h2>' +
      '<p style="font-size:13px;margin:.2em 0">Abrir: ' +
      '<a href="' + destino + '/guia.html" target="_blank">só a guia</a> · ' +
      '<a href="' + destino + '/relatorio.html" target="_blank">só o relatório</a> · ' +
      '<a href="' + destino + '" target="_blank">os dois</a></p>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">' +
      '<button class="btn btn-ghost" data-parte="guia">📲 Mandar a guia</button>' +
      '<button class="btn btn-ghost" data-parte="relatorio">📲 Mandar o relatório</button>' +
      '<button class="btn btn-ghost" data-parte="">📲 Mandar os dois</button>' +
      '<a class="btn btn-ghost" href="/crm/pedido" style="text-decoration:none">+ Novo pedido</a></div>' +
      '<div class="status" id="statusZap" style="text-align:left"></div>';
    box.querySelectorAll("button[data-parte]").forEach(b => {
      b.onclick = () => mandarZap(b.dataset.parte);
    });
    $("status").textContent = "";
    window.scrollTo({top: 0, behavior: "smooth"});
  } catch (e) {
    $("status").textContent = "Não deu pra gerar: " + e.message;
  }
  $("btnGerar").disabled = false;
}

async function mandarZap(parte){
  const s = $("statusZap");
  const nome = parte === "guia" ? "a guia" : (parte === "relatorio" ? "o relatório" : "o pedido completo");
  s.textContent = "Gerando o PDF e mandando " + nome + "...";
  try {
    const url = "/documentos/api/" + editando + "/send-group" + (parte ? ("?parte=" + parte) : "");
    const r = await fetch(url, {method: "POST"});
    const j = await r.json();
    s.textContent = r.ok ? ("✅ Mandei " + nome + " no grupo principal.") : ("Não deu: " + (j.error || ""));
  } catch (e) {
    s.textContent = "Não deu: " + e.message;
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
      $("status").textContent = "Editando um pedido já gerado — gerar de novo substitui a página dele.";
      aplicaLembrado();
      return;
    }
  }
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
