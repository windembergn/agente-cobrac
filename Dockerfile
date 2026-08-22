FROM nousresearch/hermes-agent:latest
USER root

# Navegador de verdade para o agente: o Hermes ja traz o CLI `agent-browser`,
# mas ele nao abre nada sem um Chromium no sistema. Com isto o agente consegue
# ABRIR a pagina que acabou de publicar e conferir como ficou — alem de
# pesquisar na web. Container nao tem user namespace: sem --no-sandbox o
# Chromium morre no start, por isso o CHROMIUM_FLAGS.
RUN apt-get update && \
    apt-get install -y --no-install-recommends chromium fonts-liberation fonts-dejavu-core && \
    rm -rf /var/lib/apt/lists/*

# O CLI que o Hermes usa para dirigir o navegador. Sem ele as ferramentas de
# browser respondem "instale o agent-browser" — e' o par do chromium acima.
RUN npm install -g --silent agent-browser@^0.26.0 >/dev/null 2>&1 || true

RUN /opt/hermes/.venv/bin/pip install --no-cache-dir "qrcode[pil]" >/dev/null 2>&1 || true
COPY assets/ /opt/copiloto/
COPY cont-init/03-copiloto /etc/cont-init.d/03-copiloto
COPY s6/copiloto-qr /etc/s6-overlay/s6-rc.d/copiloto-qr
RUN chmod +x /etc/cont-init.d/03-copiloto /etc/s6-overlay/s6-rc.d/copiloto-qr/run /opt/copiloto/*.py /opt/copiloto/*.sh 2>/dev/null || true;     printf longrun > /etc/s6-overlay/s6-rc.d/copiloto-qr/type;     touch /etc/s6-overlay/s6-rc.d/user/contents.d/copiloto-qr;     /opt/hermes/.venv/bin/python /opt/copiloto/patch-bridge.py /opt/hermes/scripts/whatsapp-bridge/bridge.js;     node --check /opt/hermes/scripts/whatsapp-bridge/bridge.js
ENV HERMES_DASHBOARD=1     HERMES_DASHBOARD_HOST=0.0.0.0     HERMES_DASHBOARD_PORT=9119     WHATSAPP_MODE=bot     WHATSAPP_ENABLED=true     WHATSAPP_FORWARD_OWNER_MESSAGES=true     WHATSAPP_DEBOUNCE_MS=10000     WHATSAPP_DEBOUNCE_MAX_MS=60000     COPILOTO_QR_PORT=8099     HERMES_GATEWAY_BUSY_ACK_ENABLED=false     AGENT_BROWSER_EXECUTABLE_PATH=/usr/bin/chromium     CHROMIUM_FLAGS="--no-sandbox --disable-dev-shm-usage --disable-gpu"
CMD ["gateway", "run"]
