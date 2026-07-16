#!/usr/bin/env python3
"""Patches do Copiloto no bridge WhatsApp (Baileys) do Hermes base.
Uso: patch-bridge.py <bridge.js>
Idempotente: faz backup .bak-copiloto e nao duplica.

A) Debounce 10s + comando /main (ponto unico: onde o evento e' enfileirado).
B) No-echo: descarta no /send o eco de transcricao de audio (mic) e status do sistema.
C) From-me em grupo: o bridge base dropa toda mensagem do dono em grupo
   (fromMe && isGroup), o que impedia o /main e o uso normal no grupo.
"""
import sys, re

if len(sys.argv) < 2:
    print("uso: patch-bridge.py <bridge.js>"); sys.exit(1)

F = sys.argv[1]
s = open(F, encoding="utf-8").read()
open(F + ".bak-copiloto", "w", encoding="utf-8").write(s)
done = []

# ---------- A) helpers de debounce + /main ----------
if "Copiloto helpers" not in s:
    helpers = r"""
// ===== Copiloto helpers (debounce + /main) =====
const CP_MS = parseInt(process.env.WHATSAPP_DEBOUNCE_MS || '10000', 10);
const CP_MAX = parseInt(process.env.WHATSAPP_DEBOUNCE_MAX_MS || '60000', 10);
const cpPend = new Map();
function cpPush(e) {
  messageQueue.push(e);
  if (messageQueue.length > MAX_QUEUE_SIZE) messageQueue.shift();
}
function cpMerge(evs) {
  if (evs.length === 1) return evs[0];
  const last = evs[evs.length - 1];
  const parts = [];
  for (const e of evs) { if (e.body && e.body.trim()) parts.push(e.body.trim()); }
  const merged = { ...last };
  if (parts.length) merged.body = parts.join('\n');
  return merged;
}
function cpFlush(id) {
  const en = cpPend.get(id);
  if (!en) return;
  cpPend.delete(id);
  if (en.timer) clearTimeout(en.timer);
  if (en.events.length) cpPush(cpMerge(en.events));
}
function cpEnqueue(e, id) {
  if (!(CP_MS > 0) || e.hasMedia) {
    if (cpPend.has(id)) { clearTimeout(cpPend.get(id).timer); cpFlush(id); }
    cpPush(e);
    return;
  }
  let en = cpPend.get(id);
  if (!en) { en = { events: [], timer: null, firstAt: Date.now() }; cpPend.set(id, en); }
  en.events.push(e);
  if (en.timer) clearTimeout(en.timer);
  const w = Math.max(0, Math.min(CP_MS, CP_MAX - (Date.now() - en.firstAt)));
  en.timer = setTimeout(() => cpFlush(id), w);
}
function cpActivateMain(chatId) {
  // Manda tambem o nome real do grupo (subject); sem ele o home_channel fica
  // com o JID cru como nome e o agente exibe isso como nome do proprio canal.
  Promise.all([
    import('node:fs'),
    Promise.resolve().then(() => sock.groupMetadata(chatId)).catch(() => null),
  ]).then(([fs, md]) => {
    try {
      const name = (md && md.subject) ? String(md.subject) : '';
      fs.mkdirSync('/opt/data/whatsapp', { recursive: true });
      fs.writeFileSync('/opt/data/whatsapp/main_group.request',
        JSON.stringify({ chat_id: String(chatId), name }));
    } catch (err) {}
  }).catch(() => {});
}
function cpHandleInbound(event, chatId, isGroup, fromOwner) {
  const b = (event.body || '').trim();
  if (isGroup && fromOwner && /^\/main\b/i.test(b)) {
    cpActivateMain(chatId);
    try { sendWithTimeout(chatId, { text: '✅ Copiloto ativado neste grupo. A partir de agora respondo só aqui. (recarregando, aguarde alguns segundos)' }).catch(() => {}); } catch (err) {}
    return;
  }
  cpEnqueue(event, chatId);
}
"""
    anchor_a = "const messageQueue = [];"
    if anchor_a in s:
        s = s.replace(anchor_a, anchor_a + "\n" + helpers, 1)
        done.append("A1:helpers")
    else:
        done.append("A1:FALHOU-anchor-messageQueue")

# ---------- A2) troca o enqueue principal pelo handler ----------
if "Copiloto-enqueue" not in s:
    old = "messageStore.remember(msg);\n      messageQueue.push(event);"
    new = ("messageStore.remember(msg);\n"
           "      cpHandleInbound(event, chatId, isGroup, fromOwner || cpOwnerGroup); // Copiloto-enqueue")
    if old in s:
        s = s.replace(old, new, 1)
        done.append("A2:enqueue")
    else:
        done.append("A2:FALHOU-anchor-enqueue")

# ---------- C) from-me em grupo ----------
# O dono digita no proprio celular, entao a mensagem volta como fromMe. O bridge
# base dropa TODO fromMe em grupo (reason: from_me_group), o que impedia o /main
# de chegar no handler. Deixamos passar marcando fromOwner=true; recentlySentIds
# barra o eco das nossas proprias mensagens (anti-loop).
if "Copiloto from-me-group" not in s:
    old_c = (
        "      // Handle fromMe messages based on mode\n"
        "      let fromOwner = false;\n"
        "      if (msg.key.fromMe) {\n"
        "        if (isGroup || chatId.includes('status')) {"
    )
    new_c = (
        "      // Handle fromMe messages based on mode\n"
        "      let fromOwner = false;\n"
        "      // ===== Copiloto from-me-group =====\n"
        "      // NAO marcamos fromOwner: o adapter prefixa \'[owner reply] \' no texto\n"
        "      // quando fromOwner=true, e isso quebra os slash commands, porque\n"
        "      // MessageEvent.is_command() testa text.startswith(\'/\'). Aqui o dono e\'\n"
        "      // o usuario principal do grupo, nao uma intervencao num chat de cliente.\n"
        "      // recentlySentIds barra o eco das nossas proprias mensagens (anti-loop).\n"
        "      const cpOwnerGroup = msg.key.fromMe && isGroup && FORWARD_OWNER_MESSAGES\n"
        "        && !recentlySentIds.has(msg.key.id);\n"
        "      if (msg.key.fromMe && !cpOwnerGroup) {\n"
        "        if (isGroup || chatId.includes('status')) {"
    )
    if old_c in s:
        s = s.replace(old_c, new_c, 1)
        done.append("C:from-me-group")
    else:
        done.append("C:FALHOU-anchor-fromMe")

# ---------- B) no-echo no /send ----------
if "Copiloto no-echo" not in s:
    anchor_b = "const { chatId, message, replyTo } = req.body;"
    block_b = anchor_b + "\n" + (
        "  { // Copiloto no-echo: dropa eco de transcricao de audio e status de sistema\n"
        "    const _m = String(message == null ? '' : message);\n"
        "    if (/^\\s*\\uD83C\\uDF99/.test(_m)\n"
        "        || /Preflight compression|Compacting context|summarizing earlier conversation|rate limited, retrying/i.test(_m)\n"
        "        || /^\\s*(\\uD83D\\uDCE6|\\uD83D\\uDDDC)/.test(_m)) {\n"
        "      return res.json({ success: true, skipped: 'copiloto_system' });\n"
        "    }\n"
        "  }"
    )
    if anchor_b in s:
        s = s.replace(anchor_b, block_b, 1)
        done.append("B:no-echo")
    else:
        done.append("B:FALHOU-anchor-send")

open(F, "w", encoding="utf-8").write(s)
print("Copiloto patches:", ", ".join(done) if done else "(nada)")

# A2 referencia cpOwnerGroup, que o patch C declara: se um anchor sumir numa
# versao futura do Hermes, o bridge quebraria so em runtime (node --check nao
# pega ReferenceError). Falhar aqui mata o build cedo, com a causa na tela.
if any("FALHOU" in d for d in done):
    sys.exit(1)
