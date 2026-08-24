#!/usr/bin/env python3
"""Patches do Copiloto no bridge WhatsApp (Baileys) do Hermes base.
Uso: patch-bridge.py <bridge.js>
Idempotente: faz backup .bak-copiloto e nao duplica.

A) Debounce 10s + comandos de grupo (ponto unico: onde o evento e' enfileirado):
   /main   ativa o copiloto neste grupo (SOMA — um numero atende N grupos)
   /sair   desativa o copiloto neste grupo
   /grupos lista os grupos ativos DESTE numero
   Cada bridge atende um numero e se identifica pelo --session, entao os
   pedidos saem com o caminho da sessao e o watcher sabe de qual numero veio.
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
// Este bridge atende UM numero. SESSION_DIR identifica qual — e' assim que
// o watcher descobre em qual slot (numero) o comando foi dado.
const CP_REQ_DIR = '/opt/data/whatsapp/requests';
const CP_SLOTS = '/opt/data/whatsapp/slots.json';
function cpRequest(action, chatId) {
  // Manda tambem o nome real do grupo (subject); sem ele o home_channel fica
  // com o JID cru como nome e o agente exibe isso como nome do proprio canal.
  Promise.all([
    import('node:fs'),
    Promise.resolve().then(() => sock.groupMetadata(chatId)).catch(() => null),
  ]).then(([fs, md]) => {
    try {
      const name = (md && md.subject) ? String(md.subject) : '';
      fs.mkdirSync(CP_REQ_DIR, { recursive: true });
      // Um arquivo por pedido: dois numeros podem mandar /main ao mesmo
      // tempo, e um caminho unico faria um sobrescrever o outro.
      const uniq = Date.now() + '-' + Math.random().toString(36).slice(2, 8);
      fs.writeFileSync(CP_REQ_DIR + '/' + uniq + '.json', JSON.stringify({
        action, session: SESSION_DIR, chat_id: String(chatId), name,
      }));
    } catch (err) {}
  }).catch(() => {});
}
function cpMyGroups() {
  // Le o slots.json e devolve os grupos DESTE numero (casando SESSION_DIR).
  // readFileSync ja vem do import estatico do topo — o bridge e' ESM, entao
  // require() nao existe aqui.
  try {
    const cfg = JSON.parse(readFileSync(CP_SLOTS, 'utf8'));
    const norm = (p) => String(p || '').replace(/\/+$/, '');
    for (const s of (cfg.slots || [])) {
      const n = String(s.id || '').match(/(\d+)$/);
      const idx = n ? parseInt(n[1], 10) : 1;
      let sess;
      if (s.mode === 'isolated') sess = '/opt/data/profiles/' + s.id + '/platforms/whatsapp/session';
      else sess = '/opt/data/platforms/' + (idx === 1 ? 'whatsapp' : 'whatsapp' + idx) + '/session';
      if (norm(sess) === norm(SESSION_DIR)) return s;
    }
  } catch (err) {}
  return null;
}
let cpCacheGrupos = { quando: 0, ids: [] };
function cpGrupoAtivado(chatId) {
  // O grupo ja passou pelo /main? Le do slots.json, com cache de 5s porque isto
  // roda a CADA mensagem recebida — inclusive as dos grupos que nao sao nossos.
  const agora = Date.now();
  if (agora - cpCacheGrupos.quando > 5000) {
    let ids = [];
    try {
      const slot = cpMyGroups();
      ids = ((slot && slot.groups) || []).map((g) => String(g.id || ''));
    } catch (err) {}
    cpCacheGrupos = { quando: agora, ids };
  }
  return cpCacheGrupos.ids.indexOf(String(chatId)) !== -1;
}
const CP_TURNO = '/opt/data/whatsapp/turno_atual.json';
function cpMarkTurno(chatId, quem) {
  // Marca de qual grupo veio a mensagem que o agente vai atender AGORA. O
  // script de auto-ajuste le isso e so aceita mudanca vinda do grupo principal;
  // sem marcador fresco ele recusa (fail-closed). Escrita atomica: dois numeros
  // podem receber mensagem ao mesmo tempo.
  import('node:fs').then((fs) => {
    try {
      fs.mkdirSync('/opt/data/whatsapp', { recursive: true });
      const tmp = CP_TURNO + '.' + process.pid + '.tmp';
      fs.writeFileSync(tmp, JSON.stringify({
        chat_id: String(chatId), sender: String(quem || ''), ts: Date.now(),
      }));
      fs.renameSync(tmp, CP_TURNO);
    } catch (err) {}
  }).catch(() => {});
}
function cpSay(chatId, text) {
  try { sendWithTimeout(chatId, { text }).catch(() => {}); } catch (err) {}
}
function cpHandleInbound(event, chatId, isGroup, fromOwner, quem) {
  const b = (event.body || '').trim();
  if (isGroup && fromOwner && /^\/main\b/i.test(b)) {
    cpRequest('add', chatId);
    cpSay(chatId, '✅ Copiloto ativado neste grupo. (recarregando, aguarde alguns segundos)');
    return;
  }
  if (isGroup && fromOwner && /^\/sair\b/i.test(b)) {
    cpRequest('remove', chatId);
    cpSay(chatId, '👋 Saindo deste grupo. Para reativar, mande /main. (recarregando)');
    return;
  }
  if (isGroup && fromOwner && /^\/grupos\b/i.test(b)) {
    const slot = cpMyGroups();
    if (!slot) { cpSay(chatId, 'Não consegui ler a configuração deste número.'); return; }
    const gs = slot.groups || [];
    const linhas = gs.map((g) => (g.id === chatId ? '• ' : '• ')
      + (g.name || g.id) + (g.id === chatId ? '  ← este' : ''));
    cpSay(chatId, gs.length
      ? ('*' + (slot.label || 'Este número') + '* está ativo em ' + gs.length
         + ' grupo(s):\n' + linhas.join('\n')
         + '\n\nUse /main para ativar num grupo novo e /sair para desativar.')
      : 'Este número ainda não está ativo em nenhum grupo. Mande /main no grupo desejado.');
    return;
  }
  if (isGroup) cpMarkTurno(chatId, fromOwner ? 'dono' : quem);
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
           "      cpHandleInbound(event, chatId, isGroup, fromOwner || cpOwnerGroup, senderId); // Copiloto-enqueue")
    if old in s:
        s = s.replace(old, new, 1)
        done.append("A2:enqueue")
    else:
        done.append("A2:FALHOU-anchor-enqueue")

# ---------- E) todo mundo fala dentro do grupo ativado ----------
# O bridge base checa TODA mensagem que nao e' do dono contra
# WHATSAPP_ALLOWED_USERS. Essa lista existe para barrar estranho no PRIVADO —
# mas, sem ela preenchida, tambem cala os participantes do grupo: o copiloto
# ficava respondendo so ao dono, e a secretaria ou o socio falavam no vazio
# (log: reason "allowlist_mismatch" com o chatId do proprio grupo ativado).
# Aqui o grupo E' o canal: quem esta num grupo que passou pelo /main fala com
# ele. Privado e grupo nao ativado seguem barrados exatamente como antes.
if "Copiloto-grupo-aberto" not in s:
    old_e = ("        if (WHATSAPP_DM_POLICY !== 'pairing' "
             "&& !matchesAllowedUser(senderId, ALLOWED_USERS, SESSION_DIR)) {")
    new_e = ("        const cpGrupoAberto = isGroup && cpGrupoAtivado(chatId); // Copiloto-grupo-aberto\n"
             "        if (!cpGrupoAberto && WHATSAPP_DM_POLICY !== 'pairing' "
             "&& !matchesAllowedUser(senderId, ALLOWED_USERS, SESSION_DIR)) {")
    if old_e in s:
        s = s.replace(old_e, new_e, 1)
        done.append("E:grupo-aberto")
    else:
        done.append("E:FALHOU-anchor-allowlist")

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

# ---------- F) lead ping do mini-CRM ----------
# Registra TODO contato direto (nao-grupo) que manda mensagem, mesmo quando o
# WHATSAPP_DM_POLICY bloqueia a resposta do agente (default do produto: DM
# desligado, so grupo ativado responde). Sem isto, um lead que so manda DM
# nunca aparece no funil "Novo Lead" do CRM. So escreve um arquivo — nao muda
# em nada se o agente responde ou nao; o crm_server.py e' quem le e decide.
if "Copiloto CRM lead ping" not in s:
    anchor_f = "const senderNumber = senderId.replace(/@.*/, '');"
    block_f = anchor_f + "\n" + (
        "      // ===== Copiloto CRM lead ping =====\n"
        "      if (!msg.key.fromMe && !isGroup) {\n"
        "        import('node:fs').then((fs) => {\n"
        "          try {\n"
        "            const dir = '/opt/data/crm/inbound_pings';\n"
        "            fs.mkdirSync(dir, { recursive: true });\n"
        "            const uniq = Date.now() + '-' + Math.random().toString(36).slice(2, 8);\n"
        "            fs.writeFileSync(dir + '/' + uniq + '.json', JSON.stringify({\n"
        "              phone: senderNumber, chat_id: String(chatId),\n"
        "              push_name: String(msg.pushName || ''), ts: Date.now(),\n"
        "            }));\n"
        "          } catch (err) {}\n"
        "        }).catch(() => {});\n"
        "      }"
    )
    if anchor_f in s:
        s = s.replace(anchor_f, block_f, 1)
        done.append("F:crm-lead-ping")
    else:
        done.append("F:FALHOU-anchor-senderNumber")

# ---------- G) rota /resolve (numero -> JID certo, resolve LID) ----------
# O WhatsApp vem migrando contatos pro endereçamento LID (Linked Identity).
# Mandar direto pra "<numero>@s.whatsapp.net" sem essa migracao aplicada da
# "sucesso" na API (sock.sendMessage nao lanca erro) mas a mensagem NUNCA
# chega — sem erro nenhum pra avisar. sock.onWhatsApp() consulta o servidor
# da WhatsApp de verdade e devolve o JID atual e correto (LID quando for o
# caso). O CRM (crm_server.py) chama essa rota ANTES de mandar qualquer
# mensagem pra um numero novo. Achado investigando 24/08: card do CRM e teste
# direto no numero do cirurgiao e da esposa dele — os dois "sucesso" na API,
# nenhum chegou; so o numero que ja tinha lid-mapping em cache funcionava.
if "Copiloto rota /resolve" not in s:
    anchor_g = "// Send a message\napp.post('/send', async (req, res) => {"
    block_g = (
        "// ===== Copiloto rota /resolve =====\n"
        "// POST {phone: \"5511999999999\"} -> {jid, exists} — o JID de verdade pra\n"
        "// mandar mensagem (pode ser @lid). exists=false quando o numero nao tem\n"
        "// WhatsApp; nesse caso devolve o JID @s.whatsapp.net como fallback mesmo\n"
        "// assim, pra quem chamou decidir o que fazer.\n"
        "app.post('/resolve', async (req, res) => {\n"
        "  if (!sock || connectionState !== 'connected') {\n"
        "    return res.status(503).json({ error: 'Not connected to WhatsApp' });\n"
        "  }\n"
        "  const { phone } = req.body;\n"
        "  if (!phone) return res.status(400).json({ error: 'phone is required' });\n"
        "  const digits = String(phone).replace(/\\D/g, '');\n"
        "  const fallbackJid = `${digits}@s.whatsapp.net`;\n"
        "  try {\n"
        "    const results = await sock.onWhatsApp(fallbackJid);\n"
        "    const found = results && results[0];\n"
        "    if (found && found.exists) {\n"
        "      return res.json({ jid: found.jid, exists: true });\n"
        "    }\n"
        "    return res.json({ jid: fallbackJid, exists: false });\n"
        "  } catch (err) {\n"
        "    return res.json({ jid: fallbackJid, exists: null, error: err.message });\n"
        "  }\n"
        "});\n"
        "\n"
        "// Send a message\napp.post('/send', async (req, res) => {"
    )
    if anchor_g in s:
        s = s.replace(anchor_g, block_g, 1)
        done.append("G:resolve-lid")
    else:
        done.append("G:FALHOU-anchor-send-comment")

open(F, "w", encoding="utf-8").write(s)
print("Copiloto patches:", ", ".join(done) if done else "(nada)")

# A2 referencia cpOwnerGroup, que o patch C declara: se um anchor sumir numa
# versao futura do Hermes, o bridge quebraria so em runtime (node --check nao
# pega ReferenceError). Falhar aqui mata o build cedo, com a causa na tela.
if any("FALHOU" in d for d in done):
    sys.exit(1)
