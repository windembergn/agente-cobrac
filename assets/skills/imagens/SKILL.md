---
name: imagens
description: Cria imagens do zero e edita fotos que o cirurgião mandou (trocar/desfocar fundo, ajustar luz, limpar enquadramento, deixar o retrato profissional), usando a mesma chave da OpenAI. Use quando pedirem "gera uma imagem", "cria uma ilustração pra página", "melhora essa foto", "tira esse fundo", "deixa mais profissional", ou quando faltar imagem para uma página que você vai publicar.
tags: [imagem, foto, ilustracao, edicao, fundo, retrato, gpt-image]
version: 1.0.0
---

# Imagens — você cria e edita

Você tem gerador de imagem instalado (`gpt-image-2`, mesma chave da OpenAI que transcreve o
áudio dele). Ele faz **texto → imagem** e **edição de foto existente**. Nunca responda que não
tem essa capacidade.

## Criar do zero
Use a ferramenta de geração de imagem com uma descrição **detalhada** — quanto mais concreto,
melhor: assunto, ambiente, luz, cores, ângulo, e o que **não** deve aparecer.

> ✅ "Consultório odontológico moderno e minimalista, tons de cinza claro e azul, luz natural
> pela janela, cadeira odontológica ao fundo desfocada, sem pessoas, fotografia profissional"
>
> ❌ "uma imagem bonita de consultório"

Proporção: `landscape` (16:9, topo de página), `portrait` (retrato) ou `square` (post, ícone).

## Editar uma foto que ele mandou
As fotos do WhatsApp ficam em `/opt/data/image_cache/`. Passe o caminho do arquivo como imagem
de origem e descreva **só a mudança**, deixando claro o que preservar:

> "Deixe o fundo desfocado e neutro em cinza claro, mantendo a pessoa exatamente igual —
> retrato profissional para site de consultório"

Serve para: trocar ou desfocar fundo, limpar objeto atrás, ajustar luz e enquadramento,
padronizar retratos da equipe, adaptar a foto ao formato da página.

**Sempre diga o que preservar** ("mantendo a pessoa/o rosto exatamente igual"). Sem isso o
modelo redesenha o rosto — e aí não é mais o cirurgião na foto.

## Depois de gerar
- **Para uma página:** copie o arquivo para dentro da pasta do site
  (`/opt/data/sites/<nome>/`) e referencie pelo nome. Só assim ele fica no ar junto da página.
- **Para ele ver:** mande a imagem no grupo.
- **Não gostou?** Ajuste a descrição e gere de novo — mudanças pequenas e específicas
  ("mais claro", "sem a planta à direita") funcionam melhor que reescrever tudo.

## Regras que não se quebram
- **Foto de paciente é dado clínico.** Não gere nem edite rosto de paciente para divulgação sem
  ele confirmar, na mesma conversa, que tem autorização de imagem.
- **Nunca invente resultado cirúrgico.** Antes/depois só com a foto real do caso real —
  "melhorar" um depois é propaganda enganosa, e quem responde por isso é o cirurgião.
- **Não gere imagem que finge ser exame** (tomografia, panorâmica, foto intraoral). Ilustração
  para explicar o procedimento ao paciente pode; parecer um exame de verdade, não.
- Cada imagem tem custo na conta da OpenAI dele. Gere o que ele pediu, não meia dúzia de
  variações "para ele escolher" sem que ele tenha pedido.

## Se falhar
Diga em uma linha o que houve e ofereça o caminho alternativo (usar a foto original, ele mandar
uma imagem pronta). Nunca entregue uma imagem que não foi gerada, nunca diga que gerou sem ter
gerado.
