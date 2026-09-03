#!/usr/bin/env python3
"""Copiloto em ESPANHOL: os textos, e o tramite fora do Brasil.

Este modulo e' so' DADO — catalogo clinico traduzido, aseguradoras, e os
rotulos de TODAS as telas (pedido de cirurgia, CRM, documentos). Quem monta
pagina e' o `pedido.py` e o `crm_server.py`; aqui nao ha logica de render.

Uma fonte so' de traducao de proposito: telas em espanhol espalhadas em copias
do HTML sairiam de sincronia no primeiro conserto feito com pressa.

Duas coisas independentes, e e' de proposito que sejam:

  * IDIOMA (`COPILOTO_IDIOMA=es`) — em que lingua a tela e os documentos saem.
    Vale para a instalacao inteira.
  * PAIS DO TRAMITE (escolhido em CADA pedido) — qual formulario sai no fim:
    `br` = a guia TISS/ANS; `es` = a Solicitud de Autorizacion da aseguradora.

Uma cirurgia bucomaxilofacial e' a mesma nos dois lados do Atlantico; o que
muda e' o papel que a operadora exige. Por isso a cirurgia de uma paciente
espanhola operando no Brasil continua saindo na guia TISS, e vice-versa.

O CID-10 e o CIE-10 sao a MESMA classificacao da OMS (so muda o nome): os
codigos do catalogo servem nos dois paises, so as descricoes sao traduzidas.

Codigo de procedimento: no Brasil e' a tabela TUSS; na Espanha cada aseguradora
usa o seu nomenclator. Como no PT-BR, codigo que nao veio de documento real
fica em BRANCO — inventar codigo e' pior do que deixar o campo para a cirurgia.
"""

# ============================================================ ASEGURADORAS
# Venezuela: as companhias de HCM (Hospitalizacion, Cirugia y Maternidad), que
# e' a apolice sob a qual uma cirurgia bucomaxilofacial e' autorizada, mais o
# publico (IVSS) e o particular.
ASEGURADORAS_VE = [
    "Seguros Caracas",
    "Mercantil Seguros",
    "Seguros La Previsora",
    "Banesco Seguros",
    "Seguros Universitas",
    "Seguros Constitución",
    "Seguros Pirámide",
    "Multinacional de Seguros",
    "Seguros Horizonte",
    "IVSS",
    "Particular",
]

# Espanha: as grandes do seguro privado, as tres mutualidades de funcionarios
# (que operam por concierto), o publico e o particular.
ASEGURADORAS_ES = [
    "Sanitas",
    "SegurCaixa Adeslas",
    "DKV Seguros",
    "Asisa",
    "Mapfre Salud",
    "Caser Salud",
    "AXA Salud",
    "Cigna",
    "Generali Seguros",
    "Nueva Mutua Sanitaria",
    "MUFACE",
    "ISFAS",
    "MUGEJU",
    "Seguridad Social (SNS)",
    "Particular",
]

ASEGURADORAS_POR_PAIS = {"ve": ASEGURADORAS_VE, "es": ASEGURADORAS_ES}

# Fabricantes de material. Os mesmos nos dois paises: o formulario pede o
# FABRICANTE (que e' global), nao o distribuidor local. Ponto de partida
# editavel, como os brasileiros.
FABRICANTES_ES = ["KLS MARTIN", "STRYKER CMF", "MEDARTIS"]

MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

MALOCLUSOES_ES = [
    "maloclusión clase II",
    "maloclusión clase III",
    "maloclusión clase I con discrepancia vertical",
    "mordida abierta anterior",
    "mordida cruzada posterior",
    "deficiencia transversal del maxilar",
    "asimetría facial",
    "exceso vertical del maxilar",
]

ASSOCIADOS_ES = [
    "síndrome de apnea obstructiva del sueño",
    "trastorno temporomandibular (TTM)",
    "dolor orofacial crónico",
    "respiración predominantemente bucal",
    "dificultad masticatoria",
    "alteración fonética",
    "bruxismo",
    "apiñamiento dentario severo",
    "recesión gingival por trauma oclusal",
    "enfermedad periodontal",
    "impacto estético y psicosocial",
]

EXAMES_ES = [
    "Tomografía computarizada de haz cónico (CBCT)",
    "Telerradiografía lateral con trazado cefalométrico",
    "Ortopantomografía",
    "Documentación ortodóncica completa",
    "Polisomnografía",
    "Fotografías clínicas",
    "Modelos de estudio / escaneado digital",
    "Informe del ortodoncista",
    "Analítica preoperatoria",
    "Riesgo quirúrgico / valoración preanestésica",
]

CARATER_ES = [("E", "Programada"), ("U", "Urgente / Emergencia")]
TIPO_INTERNACAO_ES = [
    ("1", "Médica"), ("2", "Quirúrgica"), ("3", "Obstétrica"),
    ("4", "Pediátrica"), ("5", "Psiquiátrica"),
]
REGIME_ES = [("1", "Hospitalización"), ("2", "Hospital de día / CMA"), ("3", "Domiciliaria")]

# ============================================================ CATALOGO CLINICO
# So' o que MUDA de lingua. Codigos (TUSS, CID/CIE), quantidades, diarias,
# regime e tipo de internacao continuam vindo do catalogo PT-BR — sao os mesmos
# numeros. Assim uma cirurgia nova entra em um lugar so'.
CIRURGIAS_ES = {
    "ortognatica": {
        "nome": "Cirugía ortognática",
        "cid_desc": "Anomalías de la relación entre los arcos dentarios",
        "procedimentos": [
            "OSTEOTOMÍA LE FORT I",
            "OSTEOTOMÍA SAGITAL DE RAMA MANDIBULAR",
            "OSTEOPLASTIA DE MANDÍBULA",
        ],
        "materiais": [
            "Miniplacas premoldeadas / maxilar",
            "Tornillos 1.5 / 2.0",
            "Placa recta 2.0",
            "Punta ultrasónica piezoeléctrica",
            "Sierra reciprocante",
        ],
        "indicacao": (
            "Paciente diagnosticado de deformidad dentofacial, {maloclusao} con indicación de "
            "intervención quirúrgica bajo anestesia general"
        ),
        "justificativa": (
            "El paciente presenta una deformidad dentofacial, con {maloclusao} que no es "
            "susceptible de corrección únicamente mediante tratamiento ortodóncico compensatorio, "
            "dado que la alteración es de base esquelética. El cuadro compromete la función "
            "masticatoria, la estabilidad oclusal y la armonía facial{associados_frase}. La "
            "corrección quirúrgica de las bases óseas, junto con la preparación ortodóncica ya en "
            "curso, es el tratamiento indicado para restablecer la relación maxilomandibular "
            "adecuada, la función y la estabilidad a largo plazo."
        ),
        "conduta": (
            "Osteotomía maxilar tipo Le Fort I y osteotomía sagital bilateral de mandíbula, con "
            "fijación interna rígida, bajo anestesia general, en régimen hospitalario, con "
            "previsión de ingreso según la solicitud adjunta."
        ),
    },
    "saos": {
        "nome": "Avance maxilomandibular (apnea del sueño)",
        "cid_desc": "Apnea del sueño",
        "procedimentos": [
            "OSTEOTOMÍA LE FORT I",
            "OSTEOTOMÍA SAGITAL DE RAMA MANDIBULAR",
        ],
        "materiais": [
            "Miniplacas premoldeadas / maxilar",
            "Tornillos 1.5 / 2.0",
            "Placa recta 2.0",
            "Punta ultrasónica piezoeléctrica",
            "Sierra reciprocante",
        ],
        "indicacao": (
            "Paciente con síndrome de apnea obstructiva del sueño y deficiencia esquelética "
            "maxilomandibular, {maloclusao} con indicación de avance maxilomandibular bajo "
            "anestesia general"
        ),
        "justificativa": (
            "Paciente con diagnóstico de síndrome de apnea obstructiva del sueño confirmado "
            "mediante polisomnografía, asociado a deficiencia esquelética maxilomandibular y "
            "{maloclusao}. El cuadro reduce el espacio aéreo posterior y mantiene al paciente "
            "sintomático{associados_frase}. El avance maxilomandibular es el procedimiento con "
            "mayor tasa de resolución del colapso de la vía aérea en este perfil de paciente, ya "
            "que actúa sobre la causa esquelética del estrechamiento, y está indicado tras "
            "valoración multidisciplinar."
        ),
        "conduta": (
            "Avance maxilomandibular mediante osteotomía Le Fort I y osteotomía sagital bilateral "
            "de mandíbula, con fijación interna rígida, bajo anestesia general."
        ),
    },
    "terceiros-molares": {
        "nome": "Terceros molares incluidos",
        "cid_desc": "Diente incluido",
        "procedimentos": ["EXODONCIA DE DIENTE INCLUIDO / RETENIDO"],
        "materiais": [
            "Kit quirúrgico para exodoncia de incluido",
            "Sutura reabsorbible",
            "Fresa quirúrgica desechable",
        ],
        "indicacao": (
            "Paciente con terceros molares incluidos sintomáticos, con indicación de exodoncia "
            "bajo anestesia general"
        ),
        "justificativa": (
            "El paciente presenta terceros molares incluidos, en posición desfavorable, con "
            "episodios recurrentes de pericoronaritis, dolor y dificultad de higiene "
            "local{associados_frase}. Existe riesgo de reagudización infecciosa, de reabsorción "
            "radicular de los segundos molares y de formación de lesión quística asociada al "
            "folículo pericoronario. La extracción quirúrgica está indicada con carácter "
            "preventivo y terapéutico; el ámbito hospitalario se justifica por el número de "
            "piezas, por la proximidad a estructuras nobles y por la necesidad de anestesia "
            "general."
        ),
        "conduta": (
            "Exodoncia de los terceros molares incluidos con osteotomía y odontosección cuando "
            "sea necesario, bajo anestesia general, en régimen de cirugía mayor ambulatoria."
        ),
    },
    "enxerto-osseo": {
        "nome": "Injerto óseo / reconstrucción alveolar",
        "cid_desc": "Atrofia del reborde alveolar desdentado",
        "procedimentos": ["INJERTO ÓSEO ALVEOLAR / RECONSTRUCCIÓN DE REBORDE"],
        "materiais": [
            "Bio-Oss Collagen",
            "Membrana de colágeno",
            "Tornillos de fijación 1.5",
            "Fresa trefina / kit de recogida ósea",
        ],
        "indicacao": (
            "Paciente con atrofia ósea del reborde alveolar con indicación de injerto óseo previo "
            "a la rehabilitación"
        ),
        "justificativa": (
            "El paciente presenta un reborde alveolar atrófico, con volumen óseo insuficiente "
            "para la rehabilitación funcional planificada{associados_frase}. La reconstrucción "
            "del lecho óseo es una etapa necesaria y previa a la colocación de los implantes: sin "
            "ella no hay estabilidad primaria ni previsibilidad a largo plazo. El procedimiento "
            "está indicado según la planificación tomográfica adjunta."
        ),
        "conduta": (
            "Injerto óseo del reborde alveolar con biomaterial y/o hueso autógeno, fijación "
            "cuando esté indicada y recubrimiento con membrana, bajo anestesia general."
        ),
    },
    "implantes": {
        "nome": "Implantes oseointegrados",
        "cid_desc": "Pérdida de dientes por accidente, extracción o enfermedad periodontal local",
        "procedimentos": ["COLOCACIÓN DE IMPLANTE OSEOINTEGRADO"],
        "materiais": [
            "Implante oseointegrado",
            "Tornillo de cicatrización / de cobertura",
            "Kit de fresas del sistema",
        ],
        "indicacao": (
            "Paciente con edentulismo e indicación de rehabilitación con implantes oseointegrados"
        ),
        "justificativa": (
            "El paciente presenta pérdida dentaria con perjuicio funcional de la masticación y de "
            "la fonación{associados_frase}. La rehabilitación con implantes oseointegrados es la "
            "conducta indicada para restablecer la función, preservar el hueso remanente y evitar "
            "la sobrecarga de los dientes vecinos, según la planificación tomográfica adjunta."
        ),
        "conduta": (
            "Colocación de implantes oseointegrados según planificación, con férula quirúrgica."
        ),
    },
    "seio-maxilar": {
        "nome": "Elevación de seno maxilar",
        "cid_desc": "Atrofia del reborde alveolar desdentado",
        "procedimentos": ["ELEVACIÓN DE SENO MAXILAR CON INJERTO"],
        "materiais": [
            "Bio-Oss / biomaterial de injerto",
            "Membrana de colágeno",
            "Punta ultrasónica piezoeléctrica",
        ],
        "indicacao": (
            "Neumatización del seno maxilar con altura ósea insuficiente para la rehabilitación"
        ),
        "justificativa": (
            "El paciente presenta neumatización del seno maxilar con altura ósea residual "
            "insuficiente para la colocación de implantes en la región posterior del "
            "maxilar{associados_frase}. La elevación de la membrana sinusal con injerto es el "
            "procedimiento indicado para recuperar altura ósea y hacer viable la rehabilitación."
        ),
        "conduta": (
            "Elevación de seno maxilar por abordaje lateral, con injerto y recubrimiento con "
            "membrana."
        ),
    },
    "atm": {
        "nome": "Cirugía de ATM",
        "cid_desc": "Trastornos de la articulación temporomandibular",
        "procedimentos": ["ARTROCENTESIS / ARTROSCOPIA DE ATM"],
        "materiais": ["Kit de artrocentesis", "Solución de lavado articular"],
        "indicacao": (
            "Trastorno interno de la articulación temporomandibular refractario al tratamiento "
            "conservador"
        ),
        "justificativa": (
            "El paciente presenta un trastorno interno de la articulación temporomandibular, con "
            "dolor persistente y limitación de la apertura bucal, refractario al tratamiento "
            "conservador instaurado{associados_frase}. Está indicado el abordaje quirúrgico "
            "articular para el alivio del dolor y la recuperación funcional, según las pruebas de "
            "imagen adjuntas."
        ),
        "conduta": "Abordaje articular según hallazgo intraoperatorio, bajo anestesia general.",
    },
    "trauma": {
        "nome": "Traumatismo facial (fractura)",
        "cid_desc": "Fractura del maxilar inferior",
        "procedimentos": ["REDUCCIÓN ABIERTA DE FRACTURA CON FIJACIÓN INTERNA RÍGIDA"],
        "materiais": [
            "Miniplacas del sistema 2.0",
            "Tornillos 1.5 / 2.0",
            "Arcos de Erich / bloqueo intermaxilar",
        ],
        "indicacao": (
            "Fractura facial con alteración oclusal, con indicación de reducción y fijación"
        ),
        "justificativa": (
            "Paciente víctima de traumatismo facial, que presenta fractura con desplazamiento y "
            "alteración de la oclusión{associados_frase}. Está indicada la reducción quirúrgica "
            "con fijación interna rígida para restablecer la oclusión, la función masticatoria y "
            "el contorno facial, evitando una consolidación viciosa. El carácter de la atención "
            "viene definido por el tiempo transcurrido desde el traumatismo, según la solicitud."
        ),
        "conduta": (
            "Reducción abierta de la fractura con fijación interna rígida, bajo anestesia general."
        ),
    },
    "patologia": {
        "nome": "Patología / biopsia / exéresis de lesión",
        "cid_desc": "Quistes odontogénicos del desarrollo",
        "procedimentos": ["EXÉRESIS DE LESIÓN / BIOPSIA EN CAVIDAD ORAL"],
        "materiais": [
            "Kit quirúrgico para exéresis de lesión",
            "Frasco para estudio anatomopatológico",
        ],
        "indicacao": (
            "Lesión en región maxilofacial con indicación de exéresis y estudio anatomopatológico"
        ),
        "justificativa": (
            "El paciente presenta una lesión en la región maxilofacial identificada en la "
            "exploración clínica y en las pruebas de imagen{associados_frase}. Está indicada la "
            "extirpación quirúrgica con envío de la pieza para estudio anatomopatológico, tanto "
            "para el tratamiento como para la definición diagnóstica, evitando la progresión de "
            "la lesión y el compromiso de estructuras vecinas."
        ),
        "conduta": (
            "Exéresis de la lesión con margen adecuado y envío para estudio anatomopatológico."
        ),
    },
    "outra": {
        "nome": "Otra (describir)",
        "cid_desc": "",
        "procedimentos": [""],
        "materiais": [""],
        "indicacao": "",
        "justificativa": (
            "Paciente con indicación de intervención quirúrgica bucomaxilofacial según el cuadro "
            "clínico descrito{associados_frase}."
        ),
        "conduta": "",
    },
}

# ============================================================ ROTULOS
# Tudo que aparece escrito, nas duas linguas. Chave curta de proposito: e' o
# mesmo dicionario que serve a tela (@@chave no FORM_PAGE) e os documentos.
#
# Quando falta uma chave em "es", o pedido.py cai no "pt" — assim uma string
# nova nao quebra a instalacao espanhola enquanto a traducao nao chega.
TEXTOS = {
    "pt": {
        # --- tela
        "tela_titulo": "Pedido de cirurgia",
        "tela_sub": "clique no que se aplica — o resto vem preenchido e você só confere",
        "nav_docs": "📄 Documentos",
        "nav_crm": "← CRM",
        "b_pais": "0 · País do trâmite",
        "b_pais_dica": "define qual formulário sai no fim — o preenchimento é o mesmo",
        "pais_br": "🇧🇷 Brasil — guia TISS",
        "pais_ve": "🇻🇪 Venezuela — solicitud",
        "pais_es": "🇪🇸 Espanha — solicitud",
        "b_tipo": "1 · Tipo de cirurgia",
        "l_tipo_livre": "Descreva a cirurgia",
        "ph_tipo_livre": "ex.: frenectomia lingual sob anestesia geral",
        "b_maloclusao": "2 · Tipo de má oclusão",
        "b_associados": "3 · Problemas associados",
        "d_associados": "entram na justificativa clínica do relatório",
        "b_paciente": "4 · Paciente e convênio",
        "l_paciente": "Nome do paciente",
        "l_idade": "Idade",
        "l_convenio": "Convênio",
        "l_convenio_outro": "Convênio (outro / conferir)",
        "l_carteirinha": "Carteirinha",
        "l_dni": "Documento (DNI / cédula)",
        "l_plano": "Plano",
        "b_diagnostico": "5 · Diagnóstico",
        "l_cid": "CID-10 principal",
        "l_cid_desc": "Descrição do CID",
        "l_cid2": "CID-10 (2)",
        "b_procs": "6 · Procedimentos solicitados",
        "d_procs": "código da tabela da operadora — confira antes de protocolar; em branco significa \"preencher na guia\"",
        "add_proc": "+ procedimento",
        "b_hospital": "7 · Hospital e internação",
        "l_hospital": "Hospital",
        "l_data": "Data do procedimento",
        "l_carater": "Caráter",
        "l_tipo_internacao": "Tipo de internação",
        "l_regime": "Regime",
        "l_diarias": "Diárias",
        "b_exames": "8 · Exames anexados",
        "b_material": "9 · Material (OPME) e fornecedores",
        "add_mat": "+ material",
        "l_forn": "Fornecedor",
        "b_solicitante": "10 · Solicitante",
        "d_solicitante": "fica guardado neste navegador e já vem preenchido no próximo pedido",
        "l_cirurgiao": "Cirurgião",
        "ph_cirurgiao": "Dr(a). ...",
        "l_conselho": "CRO",
        "l_uf": "UF",
        "l_obs": "Observação",
        "b_textos": "11 · Textos do relatório (opcional — o Copiloto já escreve)",
        "l_indicacao": "Indicação clínica",
        "l_justificativa": "Justificativa clínica",
        "l_conduta": "Conduta proposta",
        "ph_vazio": "deixe vazio para o Copiloto escrever",
        "btn_limpar": "Limpar",
        "btn_gerar": "Gerar pedido",
        "ph_codigo": "código",
        "ph_proc": "procedimento",
        "ph_qtd": "qtd",
        "ph_material": "material",
        "s_falta_paciente": "Falta o nome do paciente.",
        "s_gerando": "Gerando...",
        "s_erro": "Não deu pra gerar: ",
        "s_editando": "Editando um pedido já gerado — gerar de novo substitui a página dele.",
        "r_gerado": "✅ Pedido gerado",
        "r_abrir": "Abrir: ",
        "r_so_guia": "só a guia",
        "r_so_rel": "só o relatório",
        "r_os_dois": "os dois",
        "r_mandar_guia": "📲 Mandar a guia",
        "r_mandar_rel": "📲 Mandar o relatório",
        "r_mandar_dois": "📲 Mandar os dois",
        "r_novo": "+ Novo pedido",
        "z_gerando": "Gerando o PDF e mandando ",
        "z_ok": "✅ Mandei ",
        "z_ok_fim": " no grupo principal.",
        "z_nao": "Não deu: ",
        "z_a_guia": "a guia",
        "z_o_rel": "o relatório",
        "z_completo": "o pedido completo",
        # --- documentos (comuns)
        "doc_completo": "Solicitação de cirurgia",
        "doc_guia": "Guia de solicitação de internação",
        "doc_relatorio": "Relatório médico para solicitação",
        "btn_imprimir": "🖨️ Imprimir / salvar em PDF",
        "btn_so_guia": "Só a guia",
        "btn_so_rel": "Só o relatório",
        "btn_ver_guia": "Ver a guia",
        "btn_ver_rel": "Ver o relatório",
        "btn_ver_dois": "Ver os dois",
        "rel_rotulo": "Solicitação de liberação de cirurgia",
        "rel_emitido": "Emitido em ",
        "rel_paciente": "Paciente",
        "rel_convenio": "Convênio",
        "rel_hipotese": "Hipótese diagnóstica",
        "rel_procedimento": "Procedimento",
        "rel_hospital": "Hospital",
        "rel_data": "Data prevista",
        "rel_justificativa": "Justificativa clínica",
        "rel_conduta": "Conduta proposta",
        "rel_associado": "Quadro associado",
        "rel_materiais": "Materiais solicitados (OPME)",
        "rel_exames": "Exames anexados",
        "rel_pendencias": "Pendências para o cirurgião confirmar:",
        "rel_minuta": "Minuta gerada para revisão e assinatura do cirurgião responsável.",
        "anos": " anos",
        "carteirinha_sep": " — carteirinha ",
        "a_confirmar": "(a confirmar)",
        "paciente_confirmar": "(paciente a confirmar)",
        "cid_confirmar": "(a confirmar pelo cirurgião)",
        "sem_material": "(nenhum material especificado)",
        "sem_exame": "(nenhum exame anexado)",
        "obs_padrao": "Não necessariamente será utilizado todo OPME solicitado",
        "nome_cirurgiao": "Dr(a). [nome do cirurgião]",
        "p_carteirinha": "número da carteirinha",
        "p_conselho": "CRO do solicitante",
        "p_cid": "CID-10",
        "p_hospital": "hospital",
        "p_data": "data do procedimento",
        "p_codigo": "código do procedimento na tabela da operadora",
        "p_nenhuma": "nenhuma",
        # --- guia TISS
        "g_operadora": "OPERADORA",
        "g_titulo": "GUIA DE SOLICITAÇÃO DE INTERNAÇÃO",
        "g_num_guia": "Nº da guia",
        "g_ans": "Registro ANS",
        "g_data_aut": "Data da autorização",
        "g_senha": "Senha",
        "g_validade_senha": "Validade da senha",
        "g_emissao": "Data de emissão",
        "g_bloco_benef": "Dados do beneficiário",
        "g_carteira": "Número da carteira",
        "g_plano": "Plano",
        "g_validade_carteira": "Validade da carteira",
        "g_nome": "Nome",
        "g_cns": "Cartão Nacional de Saúde",
        "g_bloco_solic": "Dados do contratado solicitante",
        "g_cod_operadora": "Código na operadora / CNPJ / CPF",
        "g_contratado": "Nome do contratado",
        "g_cnes": "Código CNES",
        "g_profissional": "Nome do profissional solicitante",
        "g_conselho": "Conselho",
        "g_num_conselho": "Número no conselho",
        "g_uf": "UF",
        "g_bloco_intern": "Dados do contratado solicitado / dados da internação",
        "g_cod_hospital": "Código na operadora / CNPJ",
        "g_prestador": "Nome do prestador",
        "g_carater": "Caráter da internação",
        "g_tipo_intern": "Tipo de internação",
        "g_regime": "Regime de internação",
        "g_diarias": "Qtde. diárias solicitadas",
        "g_indicacao": "Indicação clínica",
        "g_bloco_hipoteses": "Hipóteses diagnósticas",
        "g_tipo_doenca": "Tipo de doença",
        "g_tempo_doenca": "Tempo de doença referido",
        "g_cid": "CID-10 principal",
        "g_cid2": "CID-10 (2)",
        "g_bloco_procs": "Procedimentos solicitados",
        "g_th_cod": "Código",
        "g_th_desc": "Descrição",
        "g_th_qtd_sol": "Qtde. sol.",
        # campo 42 da guia ANS e' so' "Qtde." — nao repetir o rotulo do 37
        "g_th_qtd": "Qtde.",
        "g_th_qtd_aut": "Qtde. aut.",
        "g_bloco_opme": "OPM solicitados",
        "g_th_fab": "Fabricante",
        "g_th_valor": "Valor",
        "g_admissao": "Data provável da admissão hospitalar",
        "g_diarias_aut": "Qtde. diárias autorizadas",
        "g_acomodacao": "Tipo de acomodação autorizada",
        "g_obs": "Observação",
        "g_ass_medico": "Data e assinatura do médico solicitante",
        "g_ass_benef": "Data e assinatura do beneficiário",
        "g_ass_aut": "Data e assinatura do responsável pela autorização",
        "g_rodape": "Guia preenchida pelo Copiloto a partir dos dados informados pelo cirurgião. Confira os códigos na tabela da operadora antes de protocolar.",
        "g_rodape_forn": " Fornecedores indicados: ",
    },
    "es": {
        # --- tela
        "tela_titulo": "Solicitud de cirugía",
        "tela_sub": "haz clic en lo que aplique — el resto viene relleno y solo lo revisas",
        "nav_docs": "📄 Documentos",
        "nav_crm": "← CRM",
        "b_pais": "0 · País del trámite",
        "b_pais_dica": "define qué formulario sale al final — el resto se rellena igual",
        "pais_br": "🇧🇷 Brasil — guía TISS",
        "pais_ve": "🇻🇪 Venezuela — solicitud",
        "pais_es": "🇪🇸 España — solicitud",
        "b_tipo": "1 · Tipo de cirugía",
        "l_tipo_livre": "Describe la cirugía",
        "ph_tipo_livre": "p. ej.: frenectomía lingual bajo anestesia general",
        "b_maloclusao": "2 · Tipo de maloclusión",
        "b_associados": "3 · Problemas asociados",
        "d_associados": "entran en la justificación clínica del informe",
        "b_paciente": "4 · Paciente y aseguradora",
        "l_paciente": "Nombre del paciente",
        "l_idade": "Edad",
        "l_convenio": "Aseguradora",
        "l_convenio_outro": "Aseguradora (otra / revisar)",
        "l_carteirinha": "Nº de póliza",
        "l_dni": "Documento de identidad (DNI / cédula)",
        "l_plano": "Modalidad / póliza",
        "b_diagnostico": "5 · Diagnóstico",
        "l_cid": "CIE-10 principal",
        "l_cid_desc": "Descripción del CIE",
        "l_cid2": "CIE-10 (2)",
        "b_procs": "6 · Procedimientos solicitados",
        "d_procs": "código del nomenclátor de la aseguradora — revísalo antes de presentar; en blanco significa \"rellenar en la solicitud\"",
        "add_proc": "+ procedimiento",
        "b_hospital": "7 · Centro e ingreso",
        "l_hospital": "Centro / hospital",
        "l_data": "Fecha de la intervención",
        "l_carater": "Carácter",
        "l_tipo_internacao": "Tipo de ingreso",
        "l_regime": "Régimen",
        "l_diarias": "Estancias",
        "b_exames": "8 · Pruebas adjuntas",
        "b_material": "9 · Material implantable y fabricantes",
        "add_mat": "+ material",
        "l_forn": "Fabricante",
        "b_solicitante": "10 · Solicitante",
        "d_solicitante": "se guarda en este navegador y ya viene relleno en la próxima solicitud",
        "l_cirurgiao": "Cirujano/a",
        "ph_cirurgiao": "Dr./Dra. ...",
        "l_conselho": "Nº de colegiado",
        "l_uf": "Colegio",
        "l_obs": "Observaciones",
        "b_textos": "11 · Textos del informe (opcional — el Copiloto ya los escribe)",
        "l_indicacao": "Indicación clínica",
        "l_justificativa": "Justificación clínica",
        "l_conduta": "Conducta propuesta",
        "ph_vazio": "déjalo vacío para que lo escriba el Copiloto",
        "btn_limpar": "Limpiar",
        "btn_gerar": "Generar solicitud",
        "ph_codigo": "código",
        "ph_proc": "procedimiento",
        "ph_qtd": "cant.",
        "ph_material": "material",
        "s_falta_paciente": "Falta el nombre del paciente.",
        "s_gerando": "Generando...",
        "s_erro": "No se pudo generar: ",
        "s_editando": "Estás editando una solicitud ya generada — al generar de nuevo se sustituye su página.",
        "r_gerado": "✅ Solicitud generada",
        "r_abrir": "Abrir: ",
        "r_so_guia": "solo la solicitud",
        "r_so_rel": "solo el informe",
        "r_os_dois": "las dos",
        "r_mandar_guia": "📲 Enviar la solicitud",
        "r_mandar_rel": "📲 Enviar el informe",
        "r_mandar_dois": "📲 Enviar las dos",
        "r_novo": "+ Nueva solicitud",
        "z_gerando": "Generando el PDF y enviando ",
        "z_ok": "✅ He enviado ",
        "z_ok_fim": " al grupo principal.",
        "z_nao": "No se pudo: ",
        "z_a_guia": "la solicitud",
        "z_o_rel": "el informe",
        "z_completo": "la solicitud completa",
        # --- documentos (comuns)
        "doc_completo": "Solicitud de cirugía",
        "doc_guia": "Solicitud de autorización",
        "doc_relatorio": "Informe médico justificativo",
        "btn_imprimir": "🖨️ Imprimir / guardar en PDF",
        "btn_so_guia": "Solo la solicitud",
        "btn_so_rel": "Solo el informe",
        "btn_ver_guia": "Ver la solicitud",
        "btn_ver_rel": "Ver el informe",
        "btn_ver_dois": "Ver las dos",
        "rel_rotulo": "Solicitud de autorización de intervención quirúrgica",
        "rel_emitido": "Emitido el ",
        "rel_paciente": "Paciente",
        "rel_convenio": "Aseguradora",
        "rel_hipotese": "Juicio diagnóstico",
        "rel_procedimento": "Procedimiento",
        "rel_hospital": "Centro",
        "rel_data": "Fecha prevista",
        "rel_justificativa": "Justificación clínica",
        "rel_conduta": "Conducta propuesta",
        "rel_associado": "Cuadro asociado",
        "rel_materiais": "Material implantable solicitado",
        "rel_exames": "Pruebas adjuntas",
        "rel_pendencias": "Pendiente de confirmar por el cirujano:",
        "rel_minuta": "Borrador generado para revisión y firma del cirujano responsable.",
        "anos": " años",
        "carteirinha_sep": " — póliza ",
        "a_confirmar": "(por confirmar)",
        "paciente_confirmar": "(paciente por confirmar)",
        "cid_confirmar": "(a confirmar por el cirujano)",
        "sem_material": "(ningún material especificado)",
        "sem_exame": "(ninguna prueba adjunta)",
        "obs_padrao": "No necesariamente se utilizará todo el material solicitado",
        "nome_cirurgiao": "Dr./Dra. [nombre del cirujano]",
        "p_carteirinha": "número de póliza",
        "p_conselho": "número de colegiado del solicitante",
        "p_cid": "CIE-10",
        "p_hospital": "centro",
        "p_data": "fecha de la intervención",
        "p_codigo": "código del procedimiento en el nomenclátor de la aseguradora",
        "p_nenhuma": "ninguna",
        # --- guia TISS, quando o tramite e' Brasil mas a tela esta em espanhol
        "g_operadora": "ASEGURADORA",
        "g_titulo": "GUÍA DE SOLICITUD DE INGRESO (TISS — Brasil)",
        "g_num_guia": "Nº de guía",
        "g_ans": "Registro ANS",
        "g_data_aut": "Fecha de la autorización",
        "g_senha": "Clave",
        "g_validade_senha": "Validez de la clave",
        "g_emissao": "Fecha de emisión",
        "g_bloco_benef": "Datos del asegurado",
        "g_carteira": "Número de tarjeta",
        "g_plano": "Modalidad",
        "g_validade_carteira": "Validez de la tarjeta",
        "g_nome": "Nombre",
        "g_cns": "Tarjeta Nacional de Salud",
        "g_bloco_solic": "Datos del contratado solicitante",
        "g_cod_operadora": "Código en la aseguradora / CNPJ / CPF",
        "g_contratado": "Nombre del contratado",
        "g_cnes": "Código CNES",
        "g_profissional": "Nombre del profesional solicitante",
        "g_conselho": "Colegio",
        "g_num_conselho": "Número de colegiado",
        "g_uf": "Provincia / UF",
        "g_bloco_intern": "Datos del centro solicitado / datos del ingreso",
        "g_cod_hospital": "Código en la aseguradora / CNPJ",
        "g_prestador": "Nombre del centro",
        "g_carater": "Carácter del ingreso",
        "g_tipo_intern": "Tipo de ingreso",
        "g_regime": "Régimen de ingreso",
        "g_diarias": "Nº de estancias solicitadas",
        "g_indicacao": "Indicación clínica",
        "g_bloco_hipoteses": "Juicios diagnósticos",
        "g_tipo_doenca": "Tipo de enfermedad",
        "g_tempo_doenca": "Tiempo de evolución referido",
        "g_cid": "CIE-10 principal",
        "g_cid2": "CIE-10 (2)",
        "g_bloco_procs": "Procedimientos solicitados",
        "g_th_cod": "Código",
        "g_th_desc": "Descripción",
        "g_th_qtd_sol": "Cant. sol.",
        "g_th_qtd": "Cant.",
        "g_th_qtd_aut": "Cant. aut.",
        "g_bloco_opme": "Material implantable solicitado",
        "g_th_fab": "Fabricante",
        "g_th_valor": "Importe",
        "g_admissao": "Fecha probable de ingreso",
        "g_diarias_aut": "Nº de estancias autorizadas",
        "g_acomodacao": "Tipo de habitación autorizada",
        "g_obs": "Observaciones",
        "g_ass_medico": "Fecha y firma del médico solicitante",
        "g_ass_benef": "Fecha y firma del asegurado",
        "g_ass_aut": "Fecha y firma del responsable de la autorización",
        "g_rodape": "Guía rellenada por el Copiloto a partir de los datos facilitados por el cirujano. Revisa los códigos en la tabla de la aseguradora antes de presentarla.",
        "g_rodape_forn": " Fabricantes indicados: ",
    },
}

# ============================================================ SOLICITUD (ES)
# Rotulos EXCLUSIVOS do formulario espanhol. Nao existe na Espanha um padrao
# nacional equivalente ao TISS: cada aseguradora tem o seu impresso, e todos
# pedem o mesmo conjunto — asegurado, poliza, diagnostico CIE-10, procedimento,
# centro concertado, material implantavel e a firma do facultativo. E' esse
# denominador comum que sai aqui, com o informe clinico como anexo.
#
# Sem numeracao de campo de proposito: a numeracao da guia brasileira vem da
# ANS e nao teria significado nenhum num impresso espanhol.
SOLICITUD_ES = {
    "titulo": "SOLICITUD DE AUTORIZACIÓN DE INTERVENCIÓN QUIRÚRGICA",
    "aseguradora": "ASEGURADORA",
    "ref": "Nº de referencia / expediente",
    "emision": "Fecha de emisión",
    "b_asegurado": "Datos del asegurado",
    "poliza": "Nº de póliza",
    "modalidad": "Modalidad",
    "validez": "Validez de la póliza",
    "nombre": "Nombre y apellidos",
    "dni": "Documento de identidad",
    "edad": "Edad",
    "b_solicitante": "Datos del facultativo solicitante",
    "facultativo": "Facultativo solicitante",
    "colegiado": "Nº de colegiado",
    "poliza_hcm": "Nº de póliza (HCM)",
    "colegio": "Colegio",
    "especialidad": "Especialidad",
    "esp_valor": "Cirugía Oral y Maxilofacial",
    "b_centro": "Centro y régimen de ingreso",
    "centro": "Centro concertado",
    "cod_centro": "Código de centro",
    "caracter": "Carácter",
    "tipo": "Tipo de ingreso",
    "regimen": "Régimen",
    "estancias": "Estancias previstas",
    "b_diag": "Diagnóstico",
    "indicacion": "Indicación clínica",
    "cie": "CIE-10 principal",
    "cie2": "CIE-10 (2)",
    "evolucion": "Tiempo de evolución",
    "b_procs": "Procedimientos solicitados",
    "th_cod": "Código (nomenclátor)",
    "th_desc": "Descripción",
    "th_cant": "Cant.",
    "th_aut": "Autorizado",
    "b_material": "Material implantable",
    "th_fab": "Fabricante",
    "th_importe": "Importe",
    "fecha_prev": "Fecha prevista de la intervención",
    "obs": "Observaciones",
    "b_firmas": "Firmas",
    "firma_medico": "Fecha y firma del facultativo solicitante",
    "firma_asegurado": "Fecha y firma del asegurado",
    "firma_aut": "Fecha y firma del responsable de la autorización",
    "rodape": "Solicitud rellenada por el Copiloto a partir de los datos facilitados por el cirujano. Se adjunta informe médico justificativo. Revisa los códigos y los requisitos de tu aseguradora antes de presentarla.",
    "rodape_fab": " Fabricantes indicados: ",
    "anexo": "Se adjunta: informe médico justificativo.",
}


def textos(idioma):
    """Rotulos do idioma pedido, com o PT-BR cobrindo o que faltar."""
    base = dict(TEXTOS["pt"])
    if idioma == "es":
        base.update(TEXTOS["es"])
    return base

# O impresso e' o mesmo nos dois paises hispanos; o que muda sao tres rotulos.
# Na Venezuela a cirurgia e' autorizada pela apolice de HCM (Hospitalizacion,
# Cirugia y Maternidad) e o profissional se identifica pelo MPPS.
SOLICITUD_OVERRIDE = {
    "ve": {
        "poliza": "Nº de póliza (HCM)",
        "colegiado": "Nº de colegiado / MPPS",
        "cod_centro": "Código / RIF del centro",
        "centro": "Centro / clínica",
    },
}


def solicitud(pais):
    """Os rotulos do impresso hispano, com o ajuste do pais."""
    d = dict(SOLICITUD_ES)
    d.update(SOLICITUD_OVERRIDE.get(pais, {}))
    return d


# ============================================================ CRM E DOCUMENTOS
# As outras duas telas do painel. Mesma mecanica do pedido: @@chave@@ no HTML e
# o dicionario aqui, para nao existir uma segunda copia do HTML em espanhol.
#
# As CHAVES das etapas do funil (novo_lead, atendimento...) nao mudam nunca:
# elas sao o que esta gravado no banco de cada instalacao. So' o rotulo muda.
ETAPAS_ES = [
    ("novo_lead", "Nuevo contacto"),
    ("atendimento", "En atención"),
    ("agendou", "Cita agendada"),
    ("compareceu", "Asistió"),
    ("exames", "Pruebas"),
    ("cirurgia", "Cirugía"),
    ("finalizado", "Finalizado"),
]

# {{nome}} continua em portugues de proposito: e' um TOKEN que o codigo procura
# no texto, nao uma palavra que a pessoa le. Traduzi-lo quebraria a substituicao
# em toda instalacao que ja tem mensagem gravada.
MENSAGENS_ES = {
    "novo_lead": ("", 0),
    "atendimento": (
        "¡Hola {{nome}}! Hemos recibido tu mensaje y ya estamos contigo. "
        "Cualquier duda, escríbenos por aquí.",
        1,
    ),
    "agendou": (
        "¡Listo, {{nome}}! Tu cita ya está agendada. Si surge algún imprevisto, "
        "avísanos por aquí.",
        1,
    ),
    "compareceu": (
        "¡Ha sido un placer atenderte hoy, {{nome}}! Cualquier duda después de la "
        "consulta, escríbenos.",
        1,
    ),
    "exames": (
        "Hola {{nome}}, tus pruebas están en curso. En cuanto tengamos el "
        "resultado te avisamos por aquí.",
        1,
    ),
    "cirurgia": (
        "Tu cirugía ya está programada, {{nome}}. En breve te enviamos las "
        "indicaciones de preparación.",
        1,
    ),
    "finalizado": (
        "{{nome}}, ¡tu tratamiento con nosotros ha finalizado! Si necesitas algo, "
        "aquí estamos. 🙏",
        1,
    ),
}

TEXTOS_CRM = {
    "pt": {
        "_locale": "pt-BR",
        # --- CRM (funil)
        "crm_title_tag": "CRM — Copiloto",
        "crm_h1": "CRM — funil do consultório",
        "crm_sub": "arraste o card entre as colunas · toque no ✉️ pra editar a mensagem de cada etapa",
        "crm_nav_docs": "📄 Documentos",
        "crm_nav_pedido": "🦷 Pedido de cirurgia",
        "crm_btn_novo": "+ Novo Lead",
        "crm_dlg_novo": "Novo Lead",
        "crm_l_nome": "Nome",
        "crm_l_tel": "Telefone (com DDI, só números)",
        "crm_ph_tel": "5511999999999",
        "crm_l_obs": "Observações",
        "crm_btn_excluir": "Excluir",
        "crm_btn_cancelar": "Cancelar",
        "crm_btn_salvar": "Salvar",
        "crm_dlg_msg": "Mensagem da etapa",
        "crm_chk_auto": "Disparar automaticamente ao entrar nesta etapa",
        "crm_l_texto": "Texto (use {{nome}} para o nome do paciente)",
        "crm_title_msg": "Mensagem automática desta etapa",
        "crm_editar_lead": "Editar lead",
        "crm_novo_lead": "Novo lead",
        "crm_alerta_campos": "Preencha nome e telefone.",
        "crm_conf_excluir": "Excluir este lead?",
        "crm_msg_de": "Mensagem — ",
        # --- Documentos
        "doc_title_tag": "Documentos — Copiloto",
        "doc_h1": "Documentos e páginas publicadas",
        "doc_sub": "tudo que o Copiloto publicou em /s — edite, baixe ou mande no grupo",
        "doc_nav_pedido": "🦷 Pedido de cirurgia",
        "doc_nav_crm": "← CRM",
        "doc_dlg_editar": "Editar",
        "doc_btn_excluir": "Excluir",
        "doc_btn_abrir": "Abrir página",
        "doc_btn_guia": "📲 Guia",
        "doc_btn_rel": "📲 Relatório",
        "doc_btn_enviar": "📲 Enviar PDF no grupo",
        "doc_btn_fechar": "Fechar",
        "doc_btn_salvar": "Salvar",
        "doc_vazio": "Nenhum documento publicado ainda.",
        "doc_tag_pedido": "🦷 pedido de cirurgia",
        "doc_tag_documento": "documento",
        "doc_tag_pagina": "página",
        "doc_abrir": "abrir ↗",
        "doc_refazer": "Refazer no formulário",
        "doc_editar": "Editar",
        "doc_l_rotulo": "Rótulo",
        "doc_l_valor": "Valor",
        "doc_remover": "Remover",
        "doc_add_item": "+ item",
        "doc_secao": "Seção",
        "doc_remover_secao": "Remover seção",
        "doc_l_titulo_secao": "Título da seção",
        "doc_l_titulo_doc": "Título do documento",
        "doc_dados_paciente": "Dados do paciente",
        "doc_add_campo": "+ campo",
        "doc_add_secao": "+ seção",
        "doc_l_pendencias": "Pendências para o cirurgião confirmar",
        "doc_l_cirurgiao": "Nome do cirurgião",
        "doc_l_conselho": "CRO",
        "doc_novo_campo": "Novo campo",
        "doc_nova_secao": "Nova seção",
        "doc_toggle_html": "ver/editar HTML (avançado)",
        "doc_toggle_visual": "← voltar pro editor visual",
        "doc_carregando": "Carregando...",
        "doc_os_dois": "📲 Os dois",
        "doc_aviso_pedido": 'Isto é um pedido de cirurgia: para mudar os dados use "Refazer no formulário" (aqui você só ajusta o texto da versão completa).',
        "doc_sem_formato": "Essa página não tem o formato reconhecido — editando o HTML direto.",
        "doc_salvando": "Salvando...",
        "doc_salvo": "✅ Salvo.",
        "doc_falha_salvar": "❌ Falha ao salvar.",
        "doc_conf_excluir_a": 'Excluir "',
        "doc_conf_excluir_b": '"? (fica guardado como cópia de segurança)',
        "doc_a_guia": "a guia",
        "doc_o_rel": "o relatório",
        "doc_o_pdf": "o PDF",
        "doc_gerando_a": "Gerando ",
        "doc_gerando_b": " e enviando no grupo...",
        "doc_enviei_a": "✅ Enviei ",
        "doc_enviei_b": " no grupo.",
        "doc_falha_enviar": "❌ Falha ao enviar — confira se o WhatsApp está conectado.",
    },
    "es": {
        "_locale": "es-ES",
        # --- CRM (embudo)
        "crm_title_tag": "CRM — Copiloto",
        "crm_h1": "CRM — embudo de la consulta",
        "crm_sub": "arrastra la ficha entre las columnas · toca el ✉️ para editar el mensaje de cada etapa",
        "crm_nav_docs": "📄 Documentos",
        "crm_nav_pedido": "🦷 Solicitud de cirugía",
        "crm_btn_novo": "+ Nuevo contacto",
        "crm_dlg_novo": "Nuevo contacto",
        "crm_l_nome": "Nombre",
        "crm_l_tel": "Teléfono (con prefijo del país, solo números)",
        "crm_ph_tel": "584241234567",
        "crm_l_obs": "Observaciones",
        "crm_btn_excluir": "Eliminar",
        "crm_btn_cancelar": "Cancelar",
        "crm_btn_salvar": "Guardar",
        "crm_dlg_msg": "Mensaje de la etapa",
        "crm_chk_auto": "Enviar automáticamente al entrar en esta etapa",
        "crm_l_texto": "Texto (usa {{nome}} para el nombre del paciente)",
        "crm_title_msg": "Mensaje automático de esta etapa",
        "crm_editar_lead": "Editar contacto",
        "crm_novo_lead": "Nuevo contacto",
        "crm_alerta_campos": "Rellena nombre y teléfono.",
        "crm_conf_excluir": "¿Eliminar este contacto?",
        "crm_msg_de": "Mensaje — ",
        # --- Documentos
        "doc_title_tag": "Documentos — Copiloto",
        "doc_h1": "Documentos y páginas publicadas",
        "doc_sub": "todo lo que el Copiloto ha publicado en /s — edita, descarga o envíalo al grupo",
        "doc_nav_pedido": "🦷 Solicitud de cirugía",
        "doc_nav_crm": "← CRM",
        "doc_dlg_editar": "Editar",
        "doc_btn_excluir": "Eliminar",
        "doc_btn_abrir": "Abrir página",
        "doc_btn_guia": "📲 Solicitud",
        "doc_btn_rel": "📲 Informe",
        "doc_btn_enviar": "📲 Enviar PDF al grupo",
        "doc_btn_fechar": "Cerrar",
        "doc_btn_salvar": "Guardar",
        "doc_vazio": "Todavía no hay ningún documento publicado.",
        "doc_tag_pedido": "🦷 solicitud de cirugía",
        "doc_tag_documento": "documento",
        "doc_tag_pagina": "página",
        "doc_abrir": "abrir ↗",
        "doc_refazer": "Rehacer en el formulario",
        "doc_editar": "Editar",
        "doc_l_rotulo": "Etiqueta",
        "doc_l_valor": "Valor",
        "doc_remover": "Quitar",
        "doc_add_item": "+ elemento",
        "doc_secao": "Sección",
        "doc_remover_secao": "Quitar sección",
        "doc_l_titulo_secao": "Título de la sección",
        "doc_l_titulo_doc": "Título del documento",
        "doc_dados_paciente": "Datos del paciente",
        "doc_add_campo": "+ campo",
        "doc_add_secao": "+ sección",
        "doc_l_pendencias": "Pendiente de confirmar por el cirujano",
        "doc_l_cirurgiao": "Nombre del cirujano",
        "doc_l_conselho": "Nº de colegiado",
        "doc_novo_campo": "Nuevo campo",
        "doc_nova_secao": "Nueva sección",
        "doc_toggle_html": "ver/editar HTML (avanzado)",
        "doc_toggle_visual": "← volver al editor visual",
        "doc_carregando": "Cargando...",
        "doc_os_dois": "📲 Las dos",
        "doc_aviso_pedido": 'Esto es una solicitud de cirugía: para cambiar los datos usa "Rehacer en el formulario" (aquí solo ajustas el texto de la versión completa).',
        "doc_sem_formato": "Esta página no tiene el formato reconocido — estás editando el HTML directamente.",
        "doc_salvando": "Guardando...",
        "doc_salvo": "✅ Guardado.",
        "doc_falha_salvar": "❌ No se pudo guardar.",
        "doc_conf_excluir_a": '¿Eliminar "',
        "doc_conf_excluir_b": '"? (se guarda una copia de seguridad)',
        "doc_a_guia": "la solicitud",
        "doc_o_rel": "el informe",
        "doc_o_pdf": "el PDF",
        "doc_gerando_a": "Generando ",
        "doc_gerando_b": " y enviando al grupo...",
        "doc_enviei_a": "✅ He enviado ",
        "doc_enviei_b": " al grupo.",
        "doc_falha_enviar": "❌ No se pudo enviar — comprueba que WhatsApp esté conectado.",
    },
}


def textos_crm(idioma):
    """Rotulos do CRM e dos documentos, com o PT-BR cobrindo o que faltar."""
    base = dict(TEXTOS_CRM["pt"])
    if idioma == "es":
        base.update(TEXTOS_CRM["es"])
    return base
