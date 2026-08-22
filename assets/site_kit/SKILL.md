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

**2. Copie o modelo pronto.** **Sempre de `_kit/modelos/`** — nunca do zero e, principalmente,
**nunca copiando uma página que você já publicou**. Página antiga foi feita com a versão antiga do
kit: reaproveitá-la é como o acabamento se perde (foi assim que uma página saiu sem animação
nenhuma). Se o cirurgião pedir "uma parecida com aquela", copie o **modelo** e reescreva o
conteúdo olhando a antiga.

| Pedido | Modelo |
|---|---|
| Atrair paciente, divulgar tratamento, anúncio | `/opt/data/sites/_kit/modelos/landing.html` |
| Pós-operatório, preparo, orientação, termo | `/opt/data/sites/_kit/modelos/paciente.html` |
| Relatório, descrição cirúrgica, laudo em página | `/opt/data/sites/_kit/modelos/documento.html` |
| Site do cirurgião, currículo, clínica | `/opt/data/sites/_kit/modelos/institucional.html` |

Na dúvida entre landing e institucional, use a **landing**: ela já traz tratamentos, sintomas,
convênios, avaliações, contato e mapa — é o formato que os pacientes esperam.

```bash
mkdir -p /opt/data/sites/<nome>
cp /opt/data/sites/_kit/modelos/landing.html /opt/data/sites/<nome>/index.html
```

**3. Preencha — mexendo só no texto.** Troque **todo** `[[MARCADOR]]` por conteúdo real,
mantendo as classes que já estão no HTML (`revelar`, `cartao centro`, `icone-svg`, `btn-pulso`,
`barra-fixa`…). Elas são o acabamento: reescrever a marcação "do seu jeito" é o que faz a página
sair diferente e pior a cada vez. Depois rode
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
- **Cor:** o padrão é o **azul clínico `#0e5aa7`** — deixe assim, a não ser que o cirurgião peça
  outra ou mande um logo com cor própria. Se pedir, use **uma** cor só no `--brand` (azul-marinho
  `#123a6b`, verde clínico `#0b5c4e`, grafite `#26303a`, bordô `#7a2231`). Nunca deixe
  `[[COR_PRINCIPAL]]` no arquivo.

## Como a página tem que parecer (quando ele não pedir nada)

O padrão é **site de consultório**: branco, azul, limpo, moderno e com movimento discreto — o que
o paciente espera ver de um cirurgião. Você não escolhe estilo a cada pedido; **este é o estilo**.
Só mude se ele pedir.

O que já vem pronto e você só precisa **não estragar**:

- **Animação de entrada por seção — em TODA seção, sem exceção.** As classes já vêm no modelo:
  `class="revelar"` no bloco de cada seção e `revelar-d1`/`d2`/`d3` nos cartões seguintes, para
  entrarem em cascata. Ao preencher, **não apague essas classes** — e se você criar uma seção nova,
  ponha nela também. A conferência recusa a página que não tiver nenhuma. Quem configurou o celular
  para menos movimento não vê animação — isso é automático, você não precisa fazer nada.
- **Botão que pulsa:** `class="btn btn-zap btn-grande btn-pulso"` no botão principal.
  **Todos os botões são azuis, da cor da marca** — inclusive os de WhatsApp. Verde no meio do azul
  quebra a página.
- **Barra fixa embaixo no celular** (`.barra-fixa`) e bolha no desktop (`.zap-flutuante`): já vêm
  no modelo, deixe as duas.
- **Contadores que sobem sozinhos:** `<p class="numero" data-contar="3000" data-prefixo="+">0</p>`.
  Só com número que o cirurgião passou.
- **FAQ em acordeão**, um aberto por vez, com abertura animada.
- **Carrossel** que rola com o dedo e ganha setas sozinho: `.carrossel-caixa > .carrossel > itens`.
- **Palavra destacada no título:** `<h1>Cirurgia de siso em <span class="destaque">Joinville</span></h1>`.
- **Nada de `<script>` seu.** O comportamento inteiro vem de `/s/_kit/kit.js`, que os modelos já
  carregam. Se a página precisar de algo que o kit não faz, ela não precisa.

**No celular** (é onde o paciente abre): a foto vem primeiro e sangra na largura toda, o botão
principal ocupa a linha inteira, e a barra fixa fica sempre à mão. Isso já está no CSS — para
funcionar, basta usar a estrutura do modelo e **não inventar layout**.

## Ilustrações que já estão na máquina

Você tem um conjunto de ícones de procedimento, em traço, já na cor da marca:

`dente` · `siso` · `implante` · `atm` · `ortognatica` · `enxerto` · `patologia` · `radiografia`
· `anestesia` · `agenda` · `convenio` · `sorriso` · `acompanhamento` · `recuperacao`

Uso dentro de um cartão:

```html
<div class="icone"><i class="icone-svg i-siso"></i></div>
```

Eles **acompanham a cor da marca** automaticamente. Para uma faixa com fundo discreto, use
`class="fundo-suave"` na seção. Não existe banco de fotos aqui: **foto só a que o cirurgião
mandar**.
- **Emoji só nos `icone`/botões** do modelo. Não espalhe pelo texto.
- **Texto de botão: 2 ou 3 palavras** ("Agendar avaliação", "Falar agora", "Tirar dúvida"). No
  celular o botão ocupa a linha inteira — frase longa vira duas linhas dentro da pílula.
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
- **Sem foto:** não faça nada — os modelos já vêm com um **mockup** no lugar
  (`/s/_kit/img/mockup-retrato.svg`, `mockup-consultorio.svg`, `mockup-sorriso.svg`). São
  ilustrações na cor da marca; a página nunca aparece com buraco nem com caixa de texto no lugar
  da foto. Quando ele mandar a foto, você só troca o `src`.
- **Antes e depois é exceção:** ali **não existe mockup**. Foto de antes e depois é afirmação sobre
  o resultado de um paciente — pôr ilustração no lugar seria propaganda falsa. Ou entram as fotos
  reais que ele mandou, ou você **apaga a seção inteira**.
- **Nunca** use foto da internet, banco de imagem, link de outro site, nem invente `src`. Imagem
  quebrada estraga a página inteira.

**Quando ele mandar várias fotos, use todas — no lugar certo:**

| O que ele mandou | Onde entra |
|---|---|
| Foto dele (retrato, jaleco) | topo da página e seção "quem cuida de você" (`.foto-legenda`) |
| Logo do consultório | no topo, dentro de `.marca`: `<a class="marca"><img src="logo.png" alt="..."></a>` e também na `.barra-fixa` |
| 3 ou mais fotos do mesmo assunto | **carrossel** (`.carrossel-caixa`), nunca empilhadas uma embaixo da outra |
| Par antes/depois | bloco `.antes-depois` dentro do carrossel |
| Foto do consultório / fachada | seção "onde atendo", ao lado do mapa |

Renomeie ao copiar (`foto-dr.jpg`, `logo.png`, `antes-1.jpg`) — nome de arquivo do WhatsApp
(`img_a3f9c2.jpg`) não diz nada para quem for mexer depois.

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
