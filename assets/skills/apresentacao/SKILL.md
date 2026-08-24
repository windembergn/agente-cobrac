---
name: apresentacao
description: Modo apresentação — quando pedirem "/apresentacao" (ou "manda a apresentação", "modo apresentação", "mostra o que você faz"), manda os PDFs de exemplo (guia de convênio e documento clínico), o link da vitrine, o pedido de cirurgia, o CRM, os documentos e a lista completa de comandos e capacidades, para demonstrar o Copiloto a quem está vendo pela primeira vez.
tags: [apresentacao, demo, vitrine, capacidades, comandos, handson]
version: 3.0.0
---

# Modo apresentação

## Quando usar
Sempre que alguém mandar **`/apresentacao`** (ou pedir em texto livre: "manda a apresentação",
"modo apresentação", "mostra o que você faz", "manda um exemplo de tudo que você faz") em
**qualquer grupo ativado** — não só no grupo principal.

## ⚠️ Siga EXATAMENTE os passos abaixo, nesta ordem, sem resumir nem improvisar
É uma demonstração formal — pular uma parte deixa quem está vendo pela primeira vez com
impressão incompleta. As **seis partes são obrigatórias**: 2 PDFs, pedido de cirurgia, vitrine,
CRM/documentos, capacidades, comandos.

### 1. Manda os DOIS PDFs de exemplo (arquivo de verdade, não link)
Primeiro a **guia de solicitação de convênio** — é o que impressiona cirurgião:

```bash
curl -s -u "$DASH_USER:$DASH_PASS" -X POST http://127.0.0.1:8101/documentos/api/exemplo-solicitacao-convenio/send-group
```

Uma linha antes ou depois: "esse é o pedido de cirurgia saindo pronto: relatório de justificativa
na primeira folha, guia de internação preenchida na segunda — é só conferir, assinar e protocolar."

Depois o **documento clínico**:
```bash
curl -s -u "$DASH_USER:$DASH_PASS" -X POST http://127.0.0.1:8101/documentos/api/exemplo-documento/send-group
```

Se algum der erro (`{"error": ...}`), avise em uma linha e mande o link (`/s/<nome>`) como
alternativa — mas **tente o PDF primeiro sempre**.

### 2. Mostra de onde sai o pedido — o formulário
```
https://[[SEU DOMINIO]]/crm/pedido
```
Explique curto: "esse PDF sai daqui. Você vai clicando: tipo de cirurgia, tipo de má oclusão,
problemas associados, convênio, hospital, exames anexados, fornecedor, material, quantidade e
data — e o pedido sai pronto. Escolhendo a cirurgia, o CID, os procedimentos e o material já
vêm preenchidos; você só confere. Se preferir, me manda os dados por áudio aqui no grupo que eu
monto igual."

### 3. Manda o link da vitrine
```
https://[[SEU DOMINIO]]/s/agente-cobrac
```
(troque `[[SEU DOMINIO]]` pelo domínio real desta instalação — o mesmo que você usa para
publicar página). Uma linha: "essa página resume tudo que eu faço, pode mandar pra outros
colegas conhecerem."

### 4. Manda o CRM e os documentos
```
https://[[SEU DOMINIO]]/crm
https://[[SEU DOMINIO]]/documentos
```
Em poucas linhas, sem enrolar:
- Funil visual (Novo Lead → Atendimento → Agendou → Compareceu → Exames → Cirurgia →
  Finalizado) — arrasta o card entre as colunas.
- Todo paciente que manda mensagem direta (não em grupo) já entra sozinho como "Novo Lead".
- **Cada etapa tem mensagem automática pré-configurada** que dispara pro paciente quando o card
  entra ali — e isso **precisa ser revisado antes de usar de verdade**. Diga explicitamente: "as
  mensagens de cada etapa já vêm prontas, mas dá uma olhada e ajusta pro seu jeito antes de usar
  com paciente de verdade — é só clicar no ✉️ de cada coluna."
- `/documentos`: lista, edita, apaga e manda em PDF qualquer página ou pedido já publicado.

### 5. Lista o que ele faz além do documento
Mande isto (pode adaptar o tom, não corte itens):

```
Além de escrever documento, eu também:

🦷 *Pedido de cirurgia* — você clica (tipo de cirurgia, má oclusão, convênio, hospital,
   material, fornecedor, data) e sai a guia de internação + a justificativa, prontas.
📄 *Descrição cirúrgica e evolução* — você dita por áudio, eu devolvo formatado.
⚖️ *Negativa de convênio* — me manda a carta de glosa que eu analiso o motivo e monto o
   recurso; e eu vou aprendendo o que cada operadora costuma exigir.
🧠 *Seus protocolos* — "meu pós-op de terceiro molar é assim": eu guardo e passo a escrever
   com o SEU protocolo, sua medicação, seu texto.
📅 *Agenda e pendências* — "marca a cirurgia da Maria dia 15 às 7h", "o que eu tenho essa
   semana", "ficou pendente o material do Guilherme".
📚 *Produção científica* — busco e resumo artigos (PubMed), monto as referências em Vancouver
   e organizo os dados dos seus casos para trabalho e apresentação.
⏰ *Automações* — "toda sexta confere as solicitações de convênio pendentes", "domingo à noite
   me manda a semana": eu deixo rodando sozinho e te aviso aqui.
🌐 *Páginas no ar* — orientação pro paciente, página de captação, currículo: eu escrevo,
   publico e te mando o link pronto.
```

### 6. Lista os comandos, todos, com o que cada um faz
```
Meus comandos:

*No grupo (WhatsApp):*
• /main — me ativa neste grupo (só o dono pode)
• /sair — me desativa deste grupo
• /grupos — lista os grupos em que este número está ativo
• /voice on — ligo a responder por voz E ouvir sua voz (voz-a-voz)
• /voice tts — passo a responder SEMPRE por áudio
• /voice off — volto a responder só em texto
• /apresentacao — essa demonstração que você acabou de ver

*Comigo, em conversa normal (não são comando, é só pedir):*
• "faz o pedido de cirurgia do [paciente]" — monto a guia do convênio + a justificativa
• "negaram a cirurgia do [paciente]" (mandando a carta) — analiso e monto o recurso
• "meu protocolo de [assunto] é..." — guardo e passo a usar o seu
• "marca [compromisso]" / "o que eu tenho essa semana" — sua agenda e suas pendências
• "o que diz a literatura sobre [tema]" — busco no PubMed e resumo com as referências
• "toda sexta [tarefa]" — deixo rodando sozinho e te aviso aqui
• "publica uma página sobre [assunto]" — crio e já deixo no ar, com link pronto
• "descreve essa cirurgia" (mandando áudio) — transformo sua fala em descrição organizada
• "ajusta [o que quiser mudar em mim]" — eu mesmo me configuro (guardo cópia de segurança
  antes; se ficar ruim é só falar "desfaz o último ajuste")
• "usa o Claude / GPT / Opus / Sonnet" — troco meu próprio "cérebro" na hora

*Fora do chat:*
• Pedido de cirurgia: https://[[SEU DOMINIO]]/crm/pedido
• CRM: https://[[SEU DOMINIO]]/crm
• Documentos: https://[[SEU DOMINIO]]/documentos
• Painel: https://[[SEU DOMINIO]] (mesma senha)
```

## Se for um Hands-on / demonstração ao vivo
Depois das seis partes, ofereça **fazer na hora** com um caso que a plateia der:
"me manda um caso agora — tipo de cirurgia, convênio e hospital — que eu monto o pedido aqui na
frente de vocês." Use dados fictícios; nunca use paciente real na demonstração.

## O que NÃO fazer
- Não pule nenhuma das 6 partes, mesmo que ache redundante.
- Não resuma a lista de comandos "pra não ficar grande" — a lista completa é o ponto.
- Não use dado de paciente real no exemplo — os PDFs já vêm com paciente fictício.
- Não invente comando nem capacidade que não está nesta lista.
- Não repita esse fluxo inteiro se a pessoa só perguntar "o que você faz" em texto solto — aí
  responda direto, curto. O modo apresentação completo é só quando pedirem `/apresentacao`.

## Manter atualizado
Sempre que você ganhar uma capacidade nova de verdade, depois de confirmar que funciona, ofereça
ao cirurgião atualizar esta lista e a vitrine (`/opt/data/sites/agente-cobrac/index.html`).
