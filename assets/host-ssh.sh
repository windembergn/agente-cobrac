#!/bin/sh
# Copiloto — acesso do agente ao servidor (SSH para a maquina hospedeira).
#
# COMO FUNCIONA: a stack monta o /root/.ssh do host em /opt/host-ssh. No boot
# geramos uma chave propria no volume e autorizamos a nossa PUBLICA no host.
# Depois disso o agente entra com `ssh vps <comando>` sem senha.
#
# O QUE ISSO SIGNIFICA: e' root na maquina inteira. Foi decisao explicita do
# dono do produto (cada cirurgiao tem VPS propria e so ele tem acesso). Para
# desligar numa instalacao, basta COPILOTO_HOST_SSH=off na stack — a chave
# autorizada some do host no proximo boot.
#
# Nunca derruba o boot: sai 0 em qualquer cenario.
set -u
DATA="${COPILOTO_DATA:-/opt/data}"
HOSTSSH=/opt/host-ssh
SSHDIR="$DATA/.ssh"
KEY="$SSHDIR/id_ed25519"
UID_H="${HERMES_UID:-1000}"
GID_H="${HERMES_GID:-1000}"
MARCA="copiloto-agente"
LOG="$DATA/host-ssh.log"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG" 2>/dev/null; }

desligar() {
  # Tira a autorizacao do host e o atalho, sem apagar a chave (se religarem,
  # a mesma chave volta a valer e nada muda para o agente).
  if [ -f "$HOSTSSH/authorized_keys" ]; then
    if grep -q "$MARCA" "$HOSTSSH/authorized_keys" 2>/dev/null; then
      grep -v "$MARCA" "$HOSTSSH/authorized_keys" > "$HOSTSSH/.ak.novo" 2>/dev/null &&
        mv "$HOSTSSH/.ak.novo" "$HOSTSSH/authorized_keys" &&
        chmod 600 "$HOSTSSH/authorized_keys"
      log "acesso ao servidor DESLIGADO (chave removida do host)"
    fi
  fi
  rm -f "$SSHDIR/config" 2>/dev/null
  exit 0
}

[ "${COPILOTO_HOST_SSH:-on}" = "off" ] && desligar
[ "${COPILOTO_HOST_SSH:-on}" = "nao" ] && desligar

if [ ! -d "$HOSTSSH" ]; then
  log "sem o volume /opt/host-ssh: a stack desta instalacao ainda nao monta /root/.ssh."
  rm -f "$SSHDIR/config" 2>/dev/null
  exit 0
fi

mkdir -p "$SSHDIR" 2>/dev/null
chmod 700 "$SSHDIR" 2>/dev/null

if [ ! -f "$KEY" ]; then
  ssh-keygen -t ed25519 -N "" -C "$MARCA" -f "$KEY" >/dev/null 2>&1 || {
    log "nao consegui gerar a chave"; exit 0; }
  log "chave nova gerada"
fi

PUB=$(cat "$KEY.pub" 2>/dev/null)
[ -z "$PUB" ] && { log "chave publica ilegivel"; exit 0; }

AK="$HOSTSSH/authorized_keys"
if [ ! -f "$AK" ]; then
  : > "$AK"
else
  # Uma copia do authorized_keys ORIGINAL, uma unica vez. Se algo der errado
  # aqui o dono nao pode ficar trancado fora da propria VPS.
  [ -f "$HOSTSSH/authorized_keys.antes-do-copiloto" ] ||
    cp "$AK" "$HOSTSSH/authorized_keys.antes-do-copiloto" 2>/dev/null
fi
chmod 600 "$AK" 2>/dev/null

if grep -qF "$PUB" "$AK" 2>/dev/null; then
  :
else
  # Se sobrou uma chave antiga nossa (volume recriado), tira antes de por a nova.
  if grep -q "$MARCA" "$AK" 2>/dev/null; then
    grep -v "$MARCA" "$AK" > "$HOSTSSH/.ak.novo" 2>/dev/null && mv "$HOSTSSH/.ak.novo" "$AK"
    chmod 600 "$AK" 2>/dev/null
  fi
  # Garante quebra de linha antes de acrescentar (arquivo sem \n no fim
  # grudaria as duas chaves e invalidaria as DUAS).
  [ -s "$AK" ] && [ "$(tail -c1 "$AK" | od -An -c | tr -d ' \n')" != "\\n" ] && echo "" >> "$AK"
  echo "$PUB" >> "$AK"
  log "chave do agente autorizada no host"
fi

# Endereco do host visto de dentro do container = gateway da rota padrao.
HOSTIP="${COPILOTO_HOST_IP:-}"
if [ -z "$HOSTIP" ]; then
  HOSTIP=$(/opt/hermes/.venv/bin/python - <<'PY' 2>/dev/null
import socket, struct
try:
    with open("/proc/net/route") as f:
        next(f)
        for linha in f:
            c = linha.split()
            if c[1] == "00000000":
                print(socket.inet_ntoa(struct.pack("<L", int(c[2], 16))))
                break
except Exception:
    pass
PY
)
fi
[ -z "$HOSTIP" ] && HOSTIP=172.17.0.1

cat > "$SSHDIR/config" <<CFG
# Gerado no boot. Use sempre o apelido: ssh vps "<comando>"
Host vps servidor
  HostName $HOSTIP
  User root
  Port ${COPILOTO_HOST_SSH_PORT:-22}
  IdentityFile $SSHDIR/id_ed25519
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new
  UserKnownHostsFile $SSHDIR/known_hosts
  ConnectTimeout 10
  ServerAliveInterval 20
CFG

# O agente roda como uid 1000; a chave e' inutil se ele nao puder ler.
chown -R "$UID_H:$GID_H" "$SSHDIR" 2>/dev/null
chmod 600 "$KEY" "$SSHDIR/config" 2>/dev/null

# Atalho global: `ssh vps` funciona sem -F, para qualquer usuario do container.
mkdir -p /etc/ssh 2>/dev/null
cp "$SSHDIR/config" /etc/ssh/ssh_config.d/10-copiloto.conf 2>/dev/null ||
  { grep -q "Host vps" /etc/ssh/ssh_config 2>/dev/null || cat "$SSHDIR/config" >> /etc/ssh/ssh_config 2>/dev/null; }

log "acesso ao servidor pronto (host $HOSTIP)"
exit 0
