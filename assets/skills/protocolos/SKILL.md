---
name: protocolos
description: Aprende e aplica os protocolos do próprio cirurgião — medicações, pós-operatório, orientações, condutas e modelos de documento que ele usa. Use quando ele disser "meu protocolo é", "sempre prescrevo", "anota que eu faço assim", "usa meu modelo", ou quando você for gerar receita, orientação, descrição ou pedido e existir protocolo dele para aquilo.
tags: [protocolo, pos-operatorio, prescricao, conduta, modelo, personalizacao]
version: 1.0.0
---

# Os protocolos são DELE — você reproduz, não improvisa

Cada cirurgião tem o seu jeito: a medicação que prescreve, o pós-operatório que orienta, o texto
que usa na descrição, o hospital e o material de preferência. Quando você sabe isso, o documento
sai **do jeito dele** — e é aí que ele para de reescrever o que você entrega.

## Onde ficam
```
/opt/data/dados/protocolos/<slug>.md      um arquivo por protocolo
/opt/data/dados/protocolos/INDICE.md      uma linha por protocolo (título + quando usar)
```

## Quando ele ensinar um protocolo
Gatilhos: *"meu protocolo de terceiro molar é..."*, *"sempre prescrevo..."*, *"anota que eu
faço assim"*, *"no meu pós-op de ortognática..."*, ou quando ele **corrige** um documento seu
("tira a dexametasona, eu uso...").

Faça:

1. `/opt/data/copiloto ajuste "protocolo: <assunto>"` (cópia de segurança antes de escrever).
2. Escreva/atualize `/opt/data/dados/protocolos/<slug>.md`:

```markdown
# Pós-operatório de terceiros molares
Atualizado em: 24/08/2026 — ditado pelo Dr. Fulano

## Quando se aplica
Exodontia de terceiros molares inclusos, adulto sem comorbidade.

## Prescrição
- [medicação, dose, via, intervalo, duração — exatamente como ele ditou]

## Orientações ao paciente
- [gelo, dieta, higiene, repouso, o que evitar, quando retornar]

## Sinais de alerta (procurar o cirurgião)
- [...]

## Observações do cirurgião
- [as exceções que ele mencionou]
```

3. Atualize o `INDICE.md` com uma linha.
4. Confirme em uma linha humana: "✅ Guardei seu protocolo de pós-op de terceiro molar — daqui
   pra frente eu já escrevo com ele."

**Transcreva a prescrição exatamente como ele ditou.** Se algo veio truncado ou dúbio (dose,
intervalo, duração), pergunte antes de salvar — não complete por conta própria. Você não decide
medicação; você guarda a decisão dele.

## Quando for GERAR alguma coisa
**Antes** de escrever receita, orientação pós-operatória, descrição cirúrgica, relatório de
convênio ou pedido de cirurgia:

```bash
ls /opt/data/dados/protocolos/ 2>/dev/null && cat /opt/data/dados/protocolos/INDICE.md 2>/dev/null
```

Se existir protocolo para aquele assunto, **use o dele** e diga em uma linha que usou ("saiu com
o seu protocolo de ortognática"). Se não existir, escreva o padrão e ofereça: "quer que eu guarde
esse como o seu protocolo?".

Nunca troque dose, medicação ou conduta de um protocolo dele por iniciativa própria. Se ele pedir
uma mudança, atualize o arquivo — protocolo velho aplicado é erro grave.

## Perguntas que ele vai fazer
- *"quais protocolos você tem?"* → leia o `INDICE.md` e liste, curto.
- *"como é meu pós-op de enxerto?"* → leia o arquivo e responda com o conteúdo, não de memória.
- *"esquece esse protocolo"* → faça a cópia de segurança e apague o arquivo (e a linha do índice).

## Protocolo também é modelo de documento
Se ele disser "eu escrevo a descrição assim", guarde o **modelo de texto** dele em
`/opt/data/dados/protocolos/modelo-<tipo>.md` e passe a usar essa estrutura naquele tipo de
documento — inclusive a ordem das seções e o vocabulário que ele prefere.

Se ele quiser mudar o seu jeito **em geral** (tom, formato padrão de toda descrição), aí não é
protocolo: é persona — edite o `/opt/data/SOUL.md`, como manda o seu manual.
