---
name: automacoes
description: Cria tarefas que rodam sozinhas no horário combinado — conferir convênios pendentes toda sexta, organizar as cirurgias e o material antes da semana começar, agenda do dia, relatórios periódicos. Use quando ele disser "toda sexta", "todo dia de manhã", "me avisa antes", "automatiza", "deixa programado", "sempre no começo do mês".
tags: [automacao, rotina, agendado, cron, lembrete, relatorio]
version: 1.0.0
---

# Tarefas que rodam sozinhas

Você tem agendador próprio (ferramenta `cronjob`). Quando ele descrever uma rotina — *"toda
sexta confere as solicitações de convênio que não voltaram"* — **crie a tarefa**, não anote um
lembrete para você mesmo.

## Antes de criar
1. Confirme em uma frase o que vai rodar e quando: *"então: toda sexta, 17h, eu confiro as
   solicitações sem retorno e te mando aqui no grupo. Fecho assim?"*
2. Crie só depois do "pode". Automação que ele não pediu vira spam no grupo dele.

## Criando
Use a ferramenta `cronjob` com `action: "create"`:
- **`schedule`**: `0 17 * * 5` (sexta 17h), `0 8 * * *` (todo dia 8h), `0 18 * * 0` (domingo 18h),
  `every 2h`, ou uma data ISO para uma vez só.
- **`prompt`**: escreva **completo e autossuficiente** — na hora que a tarefa roda, o texto da
  conversa de hoje não existe mais. Diga qual arquivo ler, o que comparar e como avisar.
- **`name`**: nome curto e humano ("convênios pendentes — sexta").
- **`deliver`**: **omita** — assim a entrega cai no grupo onde ele pediu.
- **`skills`**: liste as habilidades que a tarefa precisa (ex.: `["rotina-agenda"]`).

Exemplo de `prompt` bom:

```
Toda sexta: leia /opt/data/dados/pendencias.jsonl e /opt/data/dados/agenda.jsonl.
Liste as solicitações de convênio com status "aberta" há mais de 5 dias e as cirurgias
da semana seguinte cujo material ainda não está confirmado.
Se não houver nada em aberto, mande só: "✅ Nada pendente de convênio pra essa semana."
Nunca invente pendência que não esteja no arquivo.
```

## Receitas que valem para qualquer consultório
| Quando | O que a tarefa faz |
|---|---|
| Sexta 17h | solicitações de convênio sem retorno + material não confirmado da semana seguinte |
| Domingo 18h | resumo da semana que vem: cirurgias, consultas, pendências (habilidade `rotina-agenda`) |
| Todo dia 7h | agenda do dia, em 3 linhas |
| Dia 1º do mês | quantas cirurgias no mês passado, por convênio e por tipo |
| 2 dias antes de cada cirurgia | checar exames, material e risco cirúrgico daquele paciente |

## Depois de criar
Registre em `/opt/data/dados/automacoes.md` (acrescentando):
```markdown
- **Convênios pendentes** — sexta 17h — lê pendencias.jsonl, avisa no grupo — criada em 24/08/2026
```
E confirme em uma linha: "✅ Pronto. Toda sexta às 17h eu te mando as pendências de convênio aqui."

## Mexer nas que existem
- *"quais automações eu tenho?"* → `cronjob` com `action: "list"` (e o arquivo acima).
- *"para de me mandar isso"* → `action: "pause"` ou `"remove"`, e atualize o arquivo.
- *"muda pra quinta"* → `action: "update"`.
- *"roda agora pra eu ver"* → `action: "run"` — ótimo para demonstrar na hora que ele pediu.

## Limites
- A entrega depende do WhatsApp conectado. Se ele reclamar que não chegou, confira se a tarefa
  existe (`list`) antes de dizer qualquer outra coisa.
- Não crie automação que **mande mensagem para paciente** por conta própria: mensagem automática
  para paciente é o CRM (`/crm`), com o texto que ele revisou.
- Nada de automação que apague arquivo, mexa em stack, container ou reinicie o sistema.
- Se a tarefa depender de e-mail ou calendário e eles não estiverem conectados, diga isso **na
  hora de criar** — não crie uma tarefa que vai falhar em silêncio toda semana.
