---
name: pedido-cirurgia
description: Monta o pedido de cirurgia completo (guia de solicitação de internação no padrão TISS no Brasil, ou Solicitud de Autorización na Venezuela e na Espanha, + relatório de justificativa) a partir do tipo de cirurgia, má oclusão, problemas associados, convênio, hospital, exames, material, fornecedor, quantidade e data. Use quando pedirem "faz o pedido da cirurgia", "monta a guia do convênio", "solicitação de internação", "pedido de OPME" ou quando mandarem os dados de um paciente para liberar procedimento.
tags: [convenio, guia, tiss, pedido, cirurgia, opme, internacao]
version: 1.0.0
---

# Pedido de cirurgia — a guia sai pronta

O cirurgião vai clicando (tipo de cirurgia → má oclusão → problemas associados → convênio →
hospital → exames → material → fornecedor → quantidade → data) e **sai o pedido**: uma página
com o **relatório médico de justificativa** e a **guia de solicitação de internação** no padrão
que a operadora espera, pronta para imprimir, assinar e protocolar.

Existem dois caminhos, e os dois produzem **exatamente a mesma guia**.

## Caminho 1 — ele está no computador: mande o formulário

```
https://[[SEU DOMINIO]]/crm/pedido
```

Uma linha: "é só ir clicando — tipo de cirurgia já traz CID, procedimentos e material
preenchidos; você confere e gera." (mesma senha do painel).

Use este caminho quando ele **pedir a tela**, quando forem vários pedidos seguidos, ou quando ele
estiver montando um caso novo com calma.

## Caminho 2 — ele mandou os dados no WhatsApp: monte você

É o caminho normal no dia a dia (ele dita por áudio no corredor do hospital). Faça assim:

### 1. Junte o que ele deu e veja o que falta
O mínimo para gerar: **nome do paciente** e **tipo de cirurgia**. Todo o resto o sistema
preenche com o padrão daquela cirurgia.

Se faltar algo importante (convênio, carteirinha, hospital, data, CRO), **faça UMA pergunta só**,
em lista curta, e siga. Nunca invente carteirinha, CID, código de procedimento, CRO ou fornecedor.

### 2. Chame o gerador
Rode no seu terminal (a senha do painel já está no ambiente):

```bash
curl -s -u "$DASH_USER:$DASH_PASS" -X POST http://127.0.0.1:8101/crm/api/pedido \
  -H 'Content-Type: application/json' \
  -d '{
    "tipo": "ortognatica",
    "paciente": "Guilherme Mickosz",
    "idade": "27",
    "convenio": "CASSI",
    "carteirinha": "123456789012",
    "maloclusao": "má-oclusão classe II",
    "associados": ["síndrome da apneia obstrutiva do sono"],
    "hospital": "HOSPITAL BAIA SUL",
    "data_procedimento": "2026-09-15",
    "exames": ["Tomografia computadorizada de feixe cônico", "Polissonografia"],
    "cirurgiao": "Dr. Matheus Spinella",
    "cro": "14187",
    "uf": "SC"
  }'
```

Ele responde `{"ok": true, "nome": "pedido-guilherme-mickosz", "url": "https://.../s/pedido-..."}`.

**Valores de `tipo`** (use a chave, não o nome):
`ortognatica`, `saos`, `terceiros-molares`, `enxerto-osseo`, `implantes`, `seio-maxilar`,
`atm`, `trauma`, `patologia`, `outra` (com `tipo_livre` descrevendo).

**`pais`** — qual formulário sai no fim. `br` (padrão) gera a **guia TISS/ANS**;
`ve` e `es` geram a **Solicitud de Autorización de Intervención Quirúrgica**, que é o
impresso que as seguradoras hispano-americanas esperam (sem numeração da ANS, com nº de
apólice, documento de identidade e nº de colegiado no lugar de carteirinha e CRO).

Não pergunte o país a cada pedido: **use o do pedido anterior** — quem opera num país
opera nele quase sempre. Só pergunte se ele citar uma seguradora de outro país, ou na
primeira vez. Com `pais` diferente de `br`, mande também `dni` (documento do paciente)
quando ele informar.

O **idioma** dos documentos não vem daqui: é o da instalação (`COPILOTO_IDIOMA`). Uma
instalação em espanhol emite a guia TISS brasileira com os rótulos em espanhol, e isso
está certo — o formulário é o do convênio, a língua é a de quem lê.

**Campos opcionais** que valem a pena quando ele informar:
`plano`, `cns`, `codigo_operadora`, `contratado`, `cnes`, `codigo_hospital`, `cid`, `cid_desc`,
`cid2`, `carater` (`E` eletiva / `U` urgência), `tipo_internacao`, `regime`, `diarias`,
`observacao`, `dni` (fora do Brasil), `fornecedores` (lista de até 3), `procedimentos`
(`[{"codigo": "...", "desc": "...", "qtd": "01"}]`), `materiais` (`[{"desc": "...", "qtd": "02"}]`).

Se ele ditou uma justificativa própria, mande em `justificativa` (e `indicacao` / `conduta`) —
o que ele escreveu **sempre ganha** do texto automático.

### 3. Devolva o link e ofereça o PDF
Mande o link e uma linha curta com o que você preencheu de padrão ("já entrou o material de
ortognática: miniplacas, 44 parafusos, placa reta, piezo e serra — se mudar algo eu ajusto").

**São duas peças, e o mesmo preenchimento gera as duas separadas:**

| Peça | Link | O que é |
|---|---|---|
| Guia | `/s/<nome>/guia.html` | o formulário **da operadora** (campos que ela preenche, 3 assinaturas) |
| Relatório | `/s/<nome>/relatorio.html` | o **anexo** que justifica, assinado só pelo cirurgião |
| As duas | `/s/<nome>` | versão combinada, para imprimir e grampear |

No portal da operadora costuma-se subir **um arquivo para cada**; no balcão vão juntas. Mande o
link da peça que ele pediu — na dúvida, mande o combinado e diga que dá para separar.

Para mandar o **PDF no grupo** (sem `?parte=` vai o combinado):
```bash
curl -s -u "$DASH_USER:$DASH_PASS" -X POST "http://127.0.0.1:8101/documentos/api/<nome>/send-group?parte=guia"
curl -s -u "$DASH_USER:$DASH_PASS" -X POST "http://127.0.0.1:8101/documentos/api/<nome>/send-group?parte=relatorio"
curl -s -u "$DASH_USER:$DASH_PASS" -X POST "http://127.0.0.1:8101/documentos/api/<nome>/send-group"
```

### 4. Ajuste é regenerar, não é refazer
"Troca o hospital", "põe 2 diárias", "tira o Bio-Oss": chame o **mesmo endpoint com o nome no
fim** (`.../crm/api/pedido/<nome>`) mandando o JSON completo já corrigido — a página é
substituída e o link continua o mesmo.

Para saber o que já está lá:
```bash
curl -s -u "$DASH_USER:$DASH_PASS" http://127.0.0.1:8101/crm/api/pedido/<nome>
```

## O que o pedido já traz de fábrica por tipo de cirurgia
CID sugerido, procedimentos (com código quando existe um consagrado), material típico com
quantidade, diárias, tipo e regime de internação, e o texto da justificativa clínica ligando
**má oclusão + problemas associados** à necessidade cirúrgica. Isso é ponto de partida: o
cirurgião confere.

## Regras que não se quebram
- **Código de procedimento que você não tem certeza fica em branco** — a página lista isso nas
  pendências. Código TUSS inventado volta como glosa.
- Nunca preencha senha, número da guia, data de autorização ou dados que **a operadora** preenche.
- Toda entrega termina lembrando, em uma linha, que é **minuta para revisão e assinatura**.
- Se o convênio negar depois, o caminho é a habilidade **`recurso-glosa`**.
- Se o cirurgião tem protocolo próprio para aquela cirurgia (material, texto, hospital de
  preferência), leia antes em `/opt/data/dados/protocolos/` — é a habilidade **`protocolos`**.
