---
name: apresentacao
description: Modo apresentação — quando pedirem "/apresentacao" (ou "manda a apresentação", "modo apresentação", "mostra o que você faz"), envia a página de capacidades e um exemplo real de documento gerado, para demonstrar o Copiloto a quem está vendo pela primeira vez.
tags: [apresentacao, demo, vitrine, capacidades]
version: 1.0.0
---

# Modo apresentação

## Quando usar
Sempre que alguém mandar **`/apresentacao`** (ou pedir em texto livre: "manda a apresentação",
"modo apresentação", "mostra o que você faz", "manda um exemplo de tudo que você faz") em
**qualquer grupo ativado** — não só no grupo principal. É para o cirurgião mostrar o Copiloto a
um colega, a um paciente curioso, ou a quem estiver conhecendo agora.

## O que você manda (nesta ordem, sempre as duas partes)

**1. O link da vitrine.** Já vem publicada de fábrica:

```
https://[[SEU DOMINIO]]/s/agente-cobrac
```

Troque `[[SEU DOMINIO]]` pelo domínio real desta instalação (você sabe qual é — é o mesmo que
você usa para publicar qualquer página). Antes de mandar, confira que ainda está no ar:
`/opt/data/copiloto site conferir agente-cobrac`.

**2. Um exemplo real, pronto.** Também já vem publicado de fábrica, um exemplo de documento
gerado (minuta de liberação de convênio com paciente fictício), formatado e com o visual do
sistema — não é texto solto de WhatsApp:

```
https://[[SEU DOMINIO]]/s/exemplo-documento
```

Mande os dois links, um por mensagem, com uma linha curta cada explicando o que é. Feche
oferecendo mostrar mais alguma coisa específica — sem lista longa, sem emoji espalhado, tom de
quem está mostrando o trabalho, não vendendo.

## O que NÃO fazer
- Não invente outro link, outra página ou outro domínio.
- Não repita esse fluxo inteiro se a pessoa só perguntar "o que você faz" em texto solto — aí
  responda direto, curto, sem forçar o link. O modo apresentação (com os dois links) é para
  quando pedirem explicitamente por ele.
- Não edite as páginas `agente-cobrac` ou `exemplo-documento` sem o cirurgião pedir — elas vêm
  prontas da instalação. Se ele quiser personalizar (nome, foto, cores), aí sim ajuste e
  reconfira antes de mostrar de novo.

## Manter a vitrine atualizada
Sempre que você ganhar uma capacidade nova de verdade (ex.: passou a responder por áudio, ganhou
um mini-CRM), depois de confirmar que está funcionando, ofereça ao cirurgião: "quer que eu
atualize a página de apresentação com isso?" — e, se ele topar, edite
`/opt/data/sites/agente-cobrac/index.html` acrescentando um item na seção de capacidades (mesmo
estilo visual dos cartões existentes), rode `/opt/data/copiloto site conferir agente-cobrac` e só
então avise que está atualizado.
