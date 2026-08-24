---
name: pesquisa-cientifica
description: Pesquisa e resume artigos científicos (PubMed), organiza referências em Vancouver e ajuda a estruturar dados de casos para trabalhos, aulas e apresentações. Use quando pedirem "o que diz a literatura sobre", "acha artigo de", "me resume esse paper", "monta as referências", "vou apresentar um caso/trabalho", "revisão sobre".
tags: [pesquisa, artigo, pubmed, referencias, vancouver, trabalho, aula, congresso]
version: 1.0.0
---

# Produção científica — literatura de verdade, referência que existe

## Buscar
O PubMed é indexado em inglês: **traduza os termos** antes de buscar, mesmo que ele tenha
perguntado em português.

```bash
/opt/hermes/.venv/bin/python /opt/data/skills/pesquisa-cientifica/pubmed.py \
  "orthognathic surgery obstructive sleep apnea" --n 8 --anos 5
```

Opções: `--n` (quantos), `--anos` (últimos N anos), `--json` (para processar).
O script devolve título, autores, revista, ano, tipo de estudo, link, resumo e a **referência
já em Vancouver**.

Faça 2 ou 3 buscas com termos diferentes quando a pergunta for ampla — uma busca só costuma
deixar de fora o que interessa. Se quiser ler o artigo inteiro, abra o link com o navegador.

## Responder
Formato padrão da resposta (adapte o tamanho ao que ele pediu):

```
📚 [pergunta clínica, em uma linha]

O que a literatura mostra
• [achado 1] — [tipo de estudo, n, ano]
• [achado 2] ...

Onde os autores divergem
• [...]  (se não houver divergência relevante, pule este bloco)

Limitações
• [amostra pequena, seguimento curto, estudo em outra população...]

Referências
1. [Vancouver, com PMID e link]
2. ...
```

Regras que não se quebram:
- **Só cite o que apareceu na busca ou no artigo que você abriu.** Nunca reconstrua uma
  referência de memória: PMID, DOI e ano têm que vir da consulta.
- Diga o **tipo de estudo** (revisão sistemática, ensaio clínico, série de casos) — muda o peso.
- Se a busca não encontrou nada relevante, diga isso. "Não achei estudo específico sobre X" é
  uma resposta científica; inventar não é.
- Você resume evidência, **não define conduta**. Quem decide é o cirurgião.

## Guardar
Referências e resumos que ele quiser manter:
```
/opt/data/dados/referencias/<tema>.md
```
Acrescente (nunca reescreva): referência em Vancouver, link, 2 ou 3 linhas do que interessou e a
data. Quando ele voltar ao tema meses depois, **leia esse arquivo antes** de sair buscando de novo.

## Dados de casos para trabalho / apresentação
Quando ele estiver juntando casos (série de casos, TCC, painel de congresso), monte uma planilha
em `/opt/data/dados/casos/<estudo>.csv`, com uma linha por caso e as colunas que ele definir —
o padrão útil é:

```
id,idade,sexo,diagnostico,cid,procedimento,data_cirurgia,material,intercorrencia,seguimento_meses,desfecho,obs
```

Regras: **iniciais, nunca nome completo**; nada de carteirinha, CPF ou telefone dentro do
arquivo de estudo. Trabalho publicado com dado identificável é problema ético, não detalhe.

Ele pode pedir para você **acrescentar um caso por áudio** ("põe o caso de hoje: paciente 32
anos, classe III..."). Acrescente a linha e confirme em uma linha o que entrou.

Quando ele pedir, gere a partir do CSV: contagem por diagnóstico, média de idade, taxa de
intercorrência, tempo médio de seguimento — cálculo simples, feito **em cima do arquivo**, nunca
estimado de cabeça.

## Apresentação
Se ele pedir os slides/resumo em página, use a habilidade `publicar-site` (modelo
`institucional.html` ou `documento.html`) e mande o link. Estrutura de resumo de congresso:
introdução, objetivo, método, resultados, conclusão — cada um em um parágrafo curto.
