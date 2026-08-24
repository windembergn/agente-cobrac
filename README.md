# Copiloto do Cirurgião — agente de WhatsApp (Hands On COBRAC)

Imagem Docker **auto-configurável** de um copiloto de IA para cirurgiões bucomaxilofaciais, que vive dentro de um grupo de WhatsApp. Você sobe a imagem, preenche 5 variáveis, abre a página de QR e escaneia — o resto (persona, comportamento humano, silêncio, gating de grupo) já vem pronto dentro da imagem.

Imagem publicada em: **`ghcr.io/windembergn/copiloto-cirurgiao:latest`**

Base técnica: [Hermes Agent](https://hermes-agent.nousresearch.com) (Nous Research) + cérebro **OpenAI (gpt-5)**.

---

## O que a imagem já faz sozinha

No primeiro boot, um script de `cont-init` gera toda a configuração a partir das variáveis de ambiente:

| Recurso | Como |
|---|---|
| **Painel protegido por senha** | hash gerado a partir de `DASH_PASS` |
| **Cérebro OpenAI** | `gpt-5` (raciocínio, visão) + Whisper (áudio) |
| **Silêncio total** | só a resposta final vai pro grupo — nada de "pensamento", ferramentas ou status |
| **Persona cirúrgica** | foco em descrição cirúrgica, evolução e **solicitação de liberação de cirurgia no convênio** |
| **Espera humana (10s)** | junta mensagens picotadas e responde 10s após a última |
| **from-me** | responde inclusive quando o próprio dono escreve no grupo |
| **Só um grupo** | ativado pelo comando `/main`; nunca responde em conversa privada nem em outros grupos |
| **QR num link fixo** | página `/whatsapp` (protegida pela senha do painel) com QR que se atualiza e avisa "Conectado com sucesso" |
| **Modo apresentação** | `/apresentacao` no grupo manda o link da vitrine (`/s/agente-cobrac`) e um exemplo de documento (`/s/exemplo-documento`), já publicados de fábrica |
| **Mini-CRM** | funil visual em `/crm` — Novo Lead → Atendimento → Agendou → Compareceu → Exames → Cirurgia → Finalizado, com mensagem automática (editável) por etapa |
| **Gerenciador de documentos** | `/documentos` — lista tudo publicado em `/s`, edita o conteúdo, exclui (com cópia de segurança) e manda o PDF direto no grupo principal |

---

## Como usar (resumo)

Requisitos: uma VPS com **Docker Swarm + Traefik + Portainer** já instalados, e um domínio apontado.

1. No Portainer, crie a stack colando o `docker-compose.yml` (veja o exemplo neste repo) e preencha as variáveis.
2. Faça o deploy e abra `https://SEU-DOMINIO/whatsapp` (login = usuário/senha do painel).
3. Escaneie o QR com o número dedicado do copiloto.
4. Adicione o número a um grupo e envie **`/main`** nesse grupo. Pronto — ele passa a responder só ali.

O tutorial visual completo (instalação da VPS do zero) acompanha o Hands On.

### Variáveis obrigatórias

| Variável | Exemplo | Descrição |
|---|---|---|
| `OPENAI_API_KEY` | `sk-...` | chave da OpenAI (com créditos) |
| `DASH_USER` | `admin` | usuário do painel |
| `DASH_PASS` | `SenhaForte2026` | senha do painel (letras+números, sem aspas nem `$`) |
| `WHATSAPP_OWNER_NUMBER` | `5586999990000` | número do dono (DDI+DDD, só dígitos) |
| `WHATSAPP_OWNER_NAME` | `Dr. Fulano` | nome usado pela persona |

As demais (`HERMES_DASHBOARD`, `WHATSAPP_MODE=bot`, `WHATSAPP_ENABLED`, `WHATSAPP_FORWARD_OWNER_MESSAGES`, `WHATSAPP_DEBOUNCE_MS=10000`, `COPILOTO_QR_PORT=8099`) já têm padrão na imagem.

### Roteamento no Traefik

A stack expõe três caminhos no mesmo domínio (veja `docker-compose.yml`):
- `/` → painel do agente (porta 9119)
- `/whatsapp` e `/s` → página de QR e sites publicados (porta 8099), com **prioridade maior** para não cair no painel
- `/crm` → mini-CRM (porta 8101), mesma senha do painel, também com prioridade maior

---

## Segurança

- A página `/whatsapp` fica **protegida pela senha do painel** (basic auth) — um QR de pareamento público permitiria que qualquer um vinculasse o próprio WhatsApp ao agente.
- O agente **não** tem acesso SSH ao servidor nem ao Docker. Ele ajusta apenas os próprios arquivos (persona/config). Rotas, domínios e infraestrutura são tarefa da equipe técnica.
- Chaves de API ficam como variáveis de ambiente da stack — proteja o acesso ao Portainer/VPS.
- Ferramenta de **apoio à documentação**: todo documento gerado é uma minuta para o cirurgião revisar e assinar. Não substitui julgamento clínico.

---

## Estrutura do repositório

```
Dockerfile                       # FROM hermes-agent + patches + config no boot
docker-compose.yml               # stack de exemplo (Swarm + Traefik)
assets/
  SOUL.md                        # persona cirúrgica
  patch-bridge.py                # patches do bridge (debounce 10s, /main, no-echo, lead ping do CRM)
  qr_server.py                   # servidor da página /whatsapp (QR + vigia do /main)
  crm_server.py                  # servidor do mini-CRM (/crm) — funil + mensagem automática por etapa
  apresentacao/                  # skill do modo apresentação (/apresentacao)
  sites_padrao/                  # vitrine + exemplo de documento, publicados no primeiro boot
cont-init/
  03-copiloto                    # gera config.yaml/SOUL/patch no primeiro boot
s6/
  copiloto-qr/                   # serviço s6 do servidor de QR
  copiloto-crm/                  # serviço s6 do mini-CRM
```

## Build a partir do código

```bash
docker build -t ghcr.io/windembergn/copiloto-cirurgiao:latest .
docker push ghcr.io/windembergn/copiloto-cirurgiao:latest
```

---

*Projeto do Hands On COBRAC — Eagle Mídia.*
