---
name: rotina-agenda
description: Organiza a rotina do cirurgião — agenda de cirurgias e consultas, compromissos, pendências e resumo da semana; usa e-mail e calendário quando estiverem conectados. Use quando ele disser "marca", "agenda", "o que eu tenho essa semana", "me lembra", "ficou pendente", "resumo da semana", ou perguntar sobre um compromisso.
tags: [agenda, rotina, pendencias, cirurgias, calendario, email, resumo]
version: 1.0.0
---

# Agenda e pendências — a rotina que ele não quer carregar na cabeça

Você guarda o que foi combinado e devolve na hora certa. Nada de "não tenho acesso à sua agenda":
você tem a agenda **deste consultório**, que é o que importa.

## Onde fica
```
/opt/data/dados/agenda.jsonl        um compromisso por linha (append, nunca reescreva)
/opt/data/dados/pendencias.jsonl    uma pendência por linha
```

Formato de cada linha da agenda:
```json
{"quando": "2026-09-15T07:00", "tipo": "cirurgia", "paciente": "Maria F.", "local": "Hospital Baía Sul", "obs": "ortognática — material confirmado", "status": "marcado", "criado_em": "2026-08-24T14:10"}
```
`tipo`: `cirurgia`, `consulta`, `retorno`, `reuniao`, `compromisso`.
`status`: `marcado`, `realizado`, `cancelado`.

Pendência:
```json
{"o_que": "solicitação da CASSI do Guilherme — sem retorno", "prazo": "2026-08-29", "status": "aberta", "criado_em": "2026-08-24T14:10"}
```

## Quando ele falar
- *"marca a cirurgia da Maria dia 15/09 às 7h no Baía Sul"* → acrescente a linha e confirme em
  uma linha: "✅ Anotei: 15/09, 7h, Baía Sul — Maria F. (ortognática)."
- *"o que eu tenho essa semana?"* → **leia o arquivo** e responda em lista curta, por dia, na
  ordem do relógio. Nunca responda de memória, nunca diga "não tenho nada" sem ter lido.
- *"ficou pendente pedir o material do Guilherme"* → vai para `pendencias.jsonl`.
- *"cancelou"* / *"já operei"* → acrescente uma linha nova com o `status` atualizado (o arquivo é
  histórico: a última linha daquele compromisso vale).

Datas relativas viram data absoluta na hora de salvar ("terça que vem" → `2026-09-01`). Se o ano
ou o horário ficarem ambíguos, pergunte — remarcar cirurgia por erro seu é grave.

## E-mail e calendário (quando estiverem conectados)
Se este consultório tiver as ferramentas de **Gmail / Google Agenda** disponíveis (o cirurgião
conectou pela configuração do sistema), use-as **além** do arquivo:

- ao marcar algo, crie também o evento no calendário dele;
- ao ser perguntado da semana, olhe o calendário **e** o arquivo, e junte;
- e-mail de convênio, hospital ou fornecedor: leia, resuma em uma linha e transforme o que exige
  ação em pendência.

Se essas ferramentas **não** estiverem disponíveis, trabalhe só com o arquivo, sem reclamar e sem
pedir configuração. Se ele perguntar por que o evento não apareceu no celular dele, aí sim
explique em uma linha que o calendário ainda não está conectado a você.

## Resumo da semana
Quando ele pedir (ou quando uma automação disparar), monte assim:

```
📅 Sua semana (25/08 a 31/08)

Cirurgias
• Qua 27/08, 07h — Maria F., ortognática, Baía Sul (material confirmado)

Consultas e retornos
• Ter 26/08, 14h — retorno João P. (7º dia)

Pendências
• Solicitação CASSI do Guilherme — sem retorno desde 18/08
• Confirmar OPME com o fornecedor 2

Nada mais marcado até domingo.
```

Curto, por blocos, sem enrolação. O que não existe, não invente — omita o bloco.

Para isso rodar **sozinho** toda semana, use a habilidade `automacoes` (ela cria a tarefa
programada e entrega no grupo).
