FROM nousresearch/hermes-agent:latest
USER root
RUN /opt/hermes/.venv/bin/pip install --no-cache-dir "qrcode[pil]" >/dev/null 2>&1 || true
COPY assets/ /opt/copiloto/
COPY cont-init/03-copiloto /etc/cont-init.d/03-copiloto
COPY s6/copiloto-qr /etc/s6-overlay/s6-rc.d/copiloto-qr
RUN chmod +x /etc/cont-init.d/03-copiloto /etc/s6-overlay/s6-rc.d/copiloto-qr/run /opt/copiloto/*.py 2>/dev/null || true;     printf longrun > /etc/s6-overlay/s6-rc.d/copiloto-qr/type;     touch /etc/s6-overlay/s6-rc.d/user/contents.d/copiloto-qr;     /opt/hermes/.venv/bin/python /opt/copiloto/patch-bridge.py /opt/hermes/scripts/whatsapp-bridge/bridge.js;     node --check /opt/hermes/scripts/whatsapp-bridge/bridge.js
ENV HERMES_DASHBOARD=1     HERMES_DASHBOARD_HOST=0.0.0.0     HERMES_DASHBOARD_PORT=9119     WHATSAPP_MODE=bot     WHATSAPP_ENABLED=true     WHATSAPP_FORWARD_OWNER_MESSAGES=true     WHATSAPP_DEBOUNCE_MS=10000     WHATSAPP_DEBOUNCE_MAX_MS=60000     COPILOTO_QR_PORT=8099
CMD ["gateway", "run"]
