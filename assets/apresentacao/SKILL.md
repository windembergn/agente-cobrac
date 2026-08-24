---
name: apresentacao
description: Modo apresentação — quando pedirem "/apresentacao" (ou "manda a apresentação", "modo apresentação", "mostra o que você faz"), manda o PDF de exemplo, o link da vitrine, o link do CRM e uma explicação completa de TODOS os comandos (incluindo modo áudio), para demonstrar o Copiloto a quem está vendo pela primeira vez.
tags: [apresentacao, demo, vitrine, capacidades, comandos]
version: 2.0.0
---

# Modo apresentação

## Quando usar
Sempre que alguém mandar **`/apresentacao`** (ou pedir em texto livre: "manda a apresentação",
"modo apresentação", "mostra o que você faz", "manda um exemplo de tudo que você faz") em
**qualquer grupo ativado** — não só no grupo principal.

## ⚠️ Siga EXATAMENTE os passos abaixo, nesta ordem, sem resumir nem improvisar
Isso é uma demonstração formal — pule uma parte e quem está vendo pela primeira vez sai com
impressão incompleta. As **quatro partes são obrigatórias**: PDF, vitrine, CRM, comandos.

### 1. Manda o PDF de exemplo (arquivo de verdade, não link)
Rode este comando no seu terminal — ele gera o PDF do documento de exemplo e já manda como
arquivo neste mesmo grupo (usa a mesma senha do painel, que já está no ambiente):

```bash
curl -s -u "$DASH_USER:$DASH_PASS" -X POST http://127.0.0.1:8101/documentos/api/exemplo-documento/send-group
```

Se der erro (`{"error": ...}`), avise em uma linha e mande o link `/s/exemplo-documento` como
alternativa — mas **tente o PDF primeiro sempre**, é isso que impressiona numa demo.

### 2. Manda o link da vitrine
```
https://[[SEU DOMINIO]]/s/agente-cobrac
```
(troque `[[SEU DOMINIO]]` pelo domínio real desta instalação — você já sabe qual é, é o mesmo
que usa pra publicar página). Uma linha curta: "essa página resume tudo que eu faço, pode
mandar pra outros médicos conhecerem."

### 3. Manda o link do CRM e explica o que ele faz
```
https://[[SEU DOMINIO]]/crm
```
Explique em poucas linhas, sem enrolar:
- É um funil visual (Novo Lead → Atendimento → Agendou → Compareceu → Exames → Cirurgia →
  Finalizado) — arrasta o card entre as colunas.
- Todo paciente que manda mensagem direta (não em grupo) já entra sozinho como "Novo Lead".
- **Cada etapa tem uma mensagem automática pré-configurada** que dispara pro paciente quando o
  card entra ali — e isso **precisa ser revisado e personalizado** antes de usar de verdade (as
  mensagens de fábrica são só um ponto de partida genérico). Diga isso explicitamente: "as
  mensagens de cada etapa já vêm prontas, mas dá uma olhada e ajusta pro seu jeito antes de usar
  com paciente de verdade — é só clicar no ✉️ de cada coluna."
- Tem também `/documentos` (mesmo login) — lista, edita, apaga e manda em PDF qualquer página
  já publicada.

### 4. Lista os comandos, todos, com o que cada um faz
Mande isto (adapte o tom, mas não corte nenhum comando):

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
• "ajusta [o que quiser mudar em mim]" — eu mesmo me configuro (peço confirmação, guardo cópia
  de segurança antes, e se ficar ruim é só falar "desfaz o último ajuste")
• "usa o Claude / GPT / Opus / Sonnet" — troco meu próprio "cérebro" na hora
• "publica uma página sobre [assunto]" — crio e já deixo no ar, com link pronto
• "faz o relatório de liberação de convênio do paciente [dados]" — gero a minuta formatada
• "descreve essa cirurgia" (mandando áudio) — transformo sua fala em descrição cirúrgica
  organizada

*Fora do chat:*
• Painel: https://[[SEU DOMINIO]] (mesma senha)
• CRM: https://[[SEU DOMINIO]]/crm
• Documentos: https://[[SEU DOMINIO]]/documentos
```

## O que NÃO fazer
- Não pule nenhuma das 4 partes, mesmo que ache redundante.
- Não resuma a lista de comandos "pra não ficar grande" — a lista completa é o ponto.
- Não use dado de paciente real no exemplo — o PDF já vem com paciente fictício.
- Não invente comando que não está nesta lista.
- Não repita esse fluxo inteiro se a pessoa só perguntar "o que você faz" em texto solto — aí
  responda direto, curto. O modo apresentação completo é só quando pedirem `/apresentacao`
  explicitamente.

## Manter atualizado
Sempre que você ganhar uma capacidade nova de verdade, depois de confirmar que funciona, ofereça
ao cirurgião atualizar esta lista de comandos e a página da vitrine (`/opt/data/sites/agente-cobrac/index.html`).
