---
name: recurso-glosa
description: Analisa negativa e glosa de convênio e monta o recurso (reconsideração / recurso de glosa) com a argumentação clínica, e aprende o padrão de cada operadora. Use quando falarem "negaram", "glosaram", "recusou a cirurgia", "auditoria pediu justificativa", "recurso pro convênio", ou quando mandarem a carta/print/PDF de negativa.
tags: [convenio, glosa, negativa, recurso, auditoria, operadora]
version: 1.0.0
---

# Negativa do convênio — analisar e recorrer

Negativa não é ponto final: quase sempre é **falta de justificativa no formato que o auditor
espera**. Seu trabalho é ler a negativa, entender o motivo real e devolver o recurso pronto.

## 1. Leia a negativa e extraia (sem inventar nada)
Da carta, print, e-mail ou PDF que ele mandou, tire:

- **operadora** e nº da guia / protocolo
- **procedimento(s) negado(s)** e código
- **motivo declarado** (o texto exato do auditor) e o código da glosa, se houver
- **prazo para recurso** (se estiver escrito)
- o que a operadora **está pedindo** (mais exame? laudo? justificativa? outro código?)

Se algo estiver ilegível, diga em uma linha e siga com o resto.

## 2. Classifique o motivo — o recurso muda conforme o tipo
| Motivo | O que o recurso precisa provar |
|---|---|
| Falta de justificativa clínica | o nexo entre quadro, exames e a necessidade do procedimento |
| Procedimento fora do rol / sem cobertura | indicação, ausência de alternativa terapêutica e o prejuízo de não operar |
| Diretriz de utilização não atendida | que o paciente cumpre cada critério da diretriz, item a item |
| Material (OPME) negado ou trocado | por que aquele material é necessário, e o que muda no resultado sem ele |
| Código incorreto / divergente | o código certo e por que o anterior não descreve o ato |
| Falta de documento | manda o documento; não é recurso, é complementação |

## 3. Consulte o que já sabemos daquela operadora
```bash
cat /opt/data/dados/operadoras/<operadora>.md 2>/dev/null
```
Ali ficam: o que essa operadora costuma negar, o que ela pede, que argumento já funcionou e o
canal/prazo de recurso. Se o arquivo não existir, siga sem ele — e crie no passo 6.

Consulte também os protocolos do cirurgião (`/opt/data/dados/protocolos/`): se ele tem um texto
que já usa para aquele procedimento, o recurso parte dele.

## 4. Monte o recurso
Estrutura que funciona:

```
RECURSO DE GLOSA / PEDIDO DE RECONSIDERAÇÃO
Operadora: [nome]        Guia/protocolo: [nº]
Beneficiário: [nome] — carteira [nº]
Procedimento negado: [descrição + código]
Motivo informado pela operadora: [citar o texto do auditor]

1. Quadro clínico
   [história, achados, exames — só o que o cirurgião passou]
2. Por que o procedimento é necessário
   [nexo direto entre o quadro e o ato cirúrgico; o que acontece se não operar]
3. Resposta ponto a ponto ao motivo da negativa
   [rebater exatamente o que o auditor escreveu, na ordem em que ele escreveu]
4. Documentos anexados
   [exames, laudos, fotos, relatório]
5. Pedido
   [reconsideração da negativa e liberação do procedimento e do material solicitado]

Dr(a). [nome] — CRO [nº]
```

Regras do texto:
- Tom **técnico e cordial**, nunca agressivo. Quem lê é um colega auditor.
- Rebata o motivo **declarado**, não um motivo que você imaginou.
- Fundamentação normativa (rol da ANS, diretriz de utilização, resolução) só entre se você tiver
  **certeza e conseguir conferir** — se não conferiu, sustente pela clínica e diga ao cirurgião
  que dá para reforçar com a norma se ele quiser. Norma citada errado enfraquece o recurso.
- Nunca invente evolução, exame ou dado que ele não passou. O que faltar vira pendência no fim.

## 5. Entregue
Publique como documento (habilidade `publicar-site`, modelo `documento.html`) e mande o link;
ofereça o PDF no grupo:
```bash
curl -s -u "$DASH_USER:$DASH_PASS" -X POST http://127.0.0.1:8101/documentos/api/<nome>/send-group
```

## 6. APRENDA — é isto que faz a próxima vez ser mais fácil
Depois de cada negativa, acrescente (nunca reescreva o arquivo inteiro) em
`/opt/data/dados/operadoras/<operadora>.md`:

```markdown
## 2026-08-24 — Ortognática (Le Fort + OSBM)
- Negou por: "ausência de diretriz de utilização atendida — falta polissonografia"
- O que resolveu: anexo da polissonografia + laudo do otorrino, recurso em 3 dias
- Aprendizado: nesta operadora, ortognática com apneia SEMPRE vai com polissonografia junto
```

E se o cirurgião mandar o **manual/normativa da operadora** (PDF), salve o resumo do que
interessa no mesmo arquivo — em texto seu, curto, com o que ela exige por tipo de procedimento.

Quando ele perguntar "o que a Unimed costuma pedir?", **leia o arquivo antes de responder**.
Nunca diga "não tenho essa informação" sem ter olhado.

## Prevenção vale mais que recurso
Se você já sabe que aquela operadora exige um exame, **avise na hora do pedido** (habilidade
`pedido-cirurgia`), antes de protocolar. Uma negativa evitada economiza semanas do paciente.
