---
name: publicar-site
description: Criar e publicar páginas e sites no ar (landing de captação, orientações para o paciente, documento em página, site institucional) no domínio do próprio consultório
tags: [site, página, landing, publicar, web, marketing, paciente]
version: 1.0.0
---

# Publicar um site

## Quando usar
Sempre que pedirem **página, site, landing, link para mandar pro paciente, orientação em página,
currículo, ou "põe isso no ar"**. Você não manda HTML por WhatsApp: você **publica** e devolve o link.

## ⛔ O jeito errado (não faça, custa horas e sai pior)

Publicar uma página aqui é **escrever um arquivo**. Só isso. Não existe build, não existe deploy,
não existe espera.

**Nunca**, para publicar uma página:
- criar projeto **Next.js, React, Vite, Astro** ou rodar `npm install` / `npx` / `next build`;
- construir **imagem Docker**, criar **serviço** ou mexer em **rota do Traefik**;
- rodar `docker service update`, "forçar rebuild", "limpar cache", `docker stack deploy`;
- prometer "fica pronto em 1–2 minutos" ou agendar cron para avisar quando subir.

Isso já foi tentado: gastou horas, deu timeout, serviu build velho e a página saiu pior do que
um HTML simples. **Um arquivo `index.html` na pasta certa já está no ar, na hora, sem cache.**

Se você se pegar rodando `npm`, `docker` ou `ssh` para publicar uma página, **pare** — está no
caminho errado. Escreva o arquivo.

## O endereço
Tudo que você põe em `/opt/data/sites/<nome>/` fica **no ar na hora**, sem reiniciar nada:

```
/opt/data/sites/<nome>/index.html   →   https://<SEU_DOMINIO>/s/<nome>
```

`<nome>` = minúsculas, sem acento, com hífen (`implante-dentario`, `pos-operatorio-siso`).
Descubra a URL exata com `/opt/data/copiloto site listar`. Nunca invente o domínio.

## O processo (siga nesta ordem, sempre)

**1. Junte o material antes de escrever.** Pergunte no máximo o essencial em **uma** mensagem curta:
para quem é a página, qual o objetivo, e se ele quer mandar foto. Se ele já disse o suficiente, não
pergunte nada — faça e mostre.

**2. Copie o modelo pronto.** Nunca comece do zero:

| Pedido | Modelo |
|---|---|
| Atrair paciente, divulgar tratamento, anúncio | `/opt/data/sites/_kit/modelos/landing.html` |
| Pós-operatório, preparo, orientação, termo | `/opt/data/sites/_kit/modelos/paciente.html` |
| Relatório, descrição cirúrgica, laudo em página | `/opt/data/sites/_kit/modelos/documento.html` |
| Site do cirurgião, currículo, clínica | `/opt/data/sites/_kit/modelos/institucional.html` |

```bash
mkdir -p /opt/data/sites/<nome>
cp /opt/data/sites/_kit/modelos/landing.html /opt/data/sites/<nome>/index.html
```

**3. Preencha.** Troque **todo** `[[MARCADOR]]` por conteúdo real. Depois rode
`grep -o "\[\[[A-Z_]*\]\]" /opt/data/sites/<nome>/index.html` — se sobrou marcador, a página está
quebrada. Seção que não faz sentido para o caso: **apague a seção inteira**, não deixe vazia.

**4. Confira antes de mostrar.** Roda a conferência automática:
```bash
/opt/data/copiloto site conferir <nome>
```
Ela acusa marcador esquecido, link vazio, imagem faltando e HTML quebrado. **Só mostre o link
depois que passar.** Se você tiver navegador disponível, abra a URL e olhe a página de verdade
antes de entregar.

**5. Entregue.** Uma linha, com o link e o que a página tem. Ofereça ajuste ("quer trocar a foto,
o texto do botão, a cor?"). Nada de caminho de arquivo nem nome de comando pro cirurgião.

## Regras de aparência (é isto que faz a página não sair feia)

- **Você NÃO escreve CSS.** O visual vem do kit (`/s/_kit/base.css`), que o modelo já carrega.
  Nada de `<style>` com layout, nada de `style="..."` no meio do HTML. A **única** exceção é a
  linha que já vem no modelo: `:root { --brand: #cor; }`.
- **Use as classes do kit**, não invente nomes: `container`, `estreito`, `pilha`, `grade grade-3`,
  `duas-colunas`, `cartao`, `selo`, `rotulo`, `lede`, `btn`, `btn-vazado`, `btn-claro`, `faixa`,
  `cta`, `passos`, `faq`, `checklist`, `aviso`, `documento`, `dados`, `galeria`, `numero`,
  `hero-figura`, `retrato`, `figura-vazia`, `zap-flutuante`, `tabela-rolavel`, `centro`, `muted`,
  `small`. A lista completa está comentada em `/opt/data/sites/_kit/base.css`.
- **Cor:** escolha **uma** cor de marca coerente com o consultório e escreva no `--brand`. Verde
  clínico `#0b5c4e`, azul `#12456b`, grafite `#26303a`, bordô `#7a2231`. Uma só. Nunca deixe
  `[[COR_PRINCIPAL]]`.
- **Emoji só nos `icone`/botões** do modelo. Não espalhe pelo texto.
- **Só o título é curto.** A frase do hero tem até ~10 palavras. O resto da página, não: veja a
  seção de conteúdo abaixo.

## Conteúdo — página rasa é tão ruim quanto página feia

O modelo é o **piso**, não o teto. Ele te dá a estrutura e o acabamento; o valor da página é o que
você escreve dentro. Uma página com um parágrafo por seção não serve para ninguém: o paciente lê em
15 segundos, não tira nenhuma dúvida e liga no consultório do mesmo jeito.

**Escreva como quem explica ao paciente sentado na cadeira.** Concreto, com número, prazo, exemplo e
o porquê. "Evite canudo" é uma instrução; "evite canudo por 7 dias — a sucção puxa o coágulo que
está fechando a ferida, e é essa a causa da dor forte que costuma aparecer no terceiro dia" é uma
orientação que o paciente entende e cumpre.

**Alvo por tipo de página** (contando só o texto visível):

| Página | Tamanho | O que não pode faltar |
|---|---|---|
| Landing de captação | **900–1500 palavras** | dor do paciente, como o tratamento resolve, como é o passo a passo, o que está incluso, quanto tempo leva, recuperação, quem é o cirurgião, 6–10 perguntas frequentes |
| Material do paciente | **800–1400 palavras** | sinais de alerta, dia a dia da recuperação, o que é normal e o que não é, medicação, alimentação com exemplos, higiene, retorno, 8–12 dúvidas |
| Institucional | **700–1200 palavras** | cada tratamento explicado de verdade (o que é, quando é indicado, como é feito, recuperação), formação, onde atende |
| Documento/relatório | o que o caso pedir | não invente volume: aqui, completo é melhor que longo |

**Acrescente seções.** O modelo traz um esqueleto; se o assunto pede mais, **duplique os blocos** e
crie seções novas com as mesmas classes. Uma landing boa costuma ter 8–10 seções, não 5. Um FAQ com
3 perguntas é um FAQ pela metade — escreva 6 a 12, respondendo o que o paciente pergunta de verdade
("dói?", "quanto tempo fico inchado?", "posso trabalhar no dia seguinte?", "meu convênio cobre?",
"e se eu tiver pressão alta / diabetes?").

**Cada resposta e cada parágrafo com substância:** 3 a 6 linhas, com o motivo junto. Resposta de uma
linha em FAQ é desperdício de pergunta.

**O que continua proibido:** encher linguiça. "Excelência, qualidade e compromisso", "tecnologia de
ponta", "equipe altamente qualificada" — isso não é conteúdo denso, é conteúdo vazio, e é pior que
texto curto. Se você não sabe o dado (preço, prazo do convênio, marca do implante), **não invente**:
escreva o que é verdade em geral e deixe o específico para o cirurgião confirmar.

**Página longa precisa de respiro:** alterne `faixa` (fundo alternado) entre as seções, use
`grade-3` para listas de itens, `passos` para sequência, `checklist` para o que fazer/evitar,
`tabela-rolavel` para comparação e `aviso` para o que é crítico. É isso que faz 1200 palavras
parecerem leves em vez de um paredão.

## Imagens

- **Foto que o cirurgião mandou no WhatsApp** fica em `/opt/data/image_cache/` (a mais recente é a
  dele). Copie para a pasta do site e referencie pelo nome:
  ```bash
  cp /opt/data/image_cache/img_XXXX.jpg /opt/data/sites/<nome>/foto.jpg
  ```
  no HTML: `<img class="retrato" src="foto.jpg" alt="...">`
- **Sem foto:** troque a `<img>` por uma caixa do kit, que já sai bonita:
  ```html
  <div class="hero-figura figura-vazia">Cirurgia bucomaxilofacial<br>com acompanhamento de perto</div>
  ```
- **Nunca** use foto da internet, banco de imagem, link de outro site, nem invente `src`. Imagem
  quebrada estraga a página inteira.

## Nunca invente

Depoimento, número de pacientes, anos de experiência, prêmio, CRO, nota de avaliação: **só se o
cirurgião tiver falado**. Se ele não passou, corte a seção. É a regra da casa — vale para site
igual vale para documento.

## Vários arquivos

Pode ter mais de uma página no mesmo site: `sobre.html`, `contato.html` viram
`https://<dominio>/s/<nome>/sobre.html`. Link entre elas com caminho relativo (`href="sobre.html"`).

## Comandos seus

| Comando | O que faz |
|---|---|
| `/opt/data/copiloto site listar` | todos os sites publicados, com a URL de cada um |
| `/opt/data/copiloto site conferir <nome>` | checa marcador esquecido, link vazio, imagem faltando |
| `/opt/data/copiloto site remover <nome>` | tira do ar (guarda cópia antes) |

Antes de **mudar** um site que já está no ar, tire a cópia de segurança de sempre:
`/opt/data/copiloto ajuste "site <nome>: <o que muda>"`.
