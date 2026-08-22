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
- **Texto curto e concreto.** Frase de hero com no máximo 10 palavras. Parágrafo de 2 a 3 linhas.
  Nada de "excelência, qualidade e compromisso" — diga o que o paciente ganha, em português de gente.
- **Emoji só nos `icone`/botões** do modelo. Não espalhe pelo texto.

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
