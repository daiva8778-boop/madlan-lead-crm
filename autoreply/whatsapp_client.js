const { Client, LocalAuth } = require("whatsapp-web.js");
const qrcode = require("qrcode-terminal");

const db = require("./db");
const { normalizeWhatsAppId } = require("./phone_utils");
const { randomDelayMs, sleep } = require("./delay");
const { getAutoReplyTemplate, renderTemplate } = require("./read_template");

const pendingAutoReplies = new Set(); // extra in-memory guard atop the DB auto_reply_sent flag

function isEligibleForAutoReply(agency) {
  // Per spec: SENT or FOLLOW-UP DUE (which is just SENT + 3 days, computed) are eligible.
  return agency.status === "SENT";
}

async function handleIncomingMessage(message) {
  if (message.fromMe) return;
  if (message.from.endsWith("@g.us")) return; // ignore group messages

  const normalizedPhone = normalizeWhatsAppId(message.from);
  if (!normalizedPhone) return;

  const agency = await db.findAgencyByPhone(normalizedPhone);
  if (!agency) return; // never touch numbers not in the CRM

  if (agency.status === "DO_NOT_CONTACT") return; // defense-in-depth, spec emphasizes this must be bulletproof

  const settings = await db.getSettings();
  if (!settings.autoreply_enabled) {
    // Master switch OFF -> fully inert, no status change, no message (confirmed decision).
    return;
  }

  if (!isEligibleForAutoReply(agency)) return; // only SENT/FOLLOW-UP DUE trigger this

  // Status flip to REPLIED happens immediately, not delayed.
  await db.markReplied(agency.id);
  console.log(`[autoreply] ${agency.name} (${normalizedPhone}) replied -> marked REPLIED`);

  if (agency.auto_reply_sent) {
    console.log(`[autoreply] auto_reply already sent to ${agency.name} previously — skipping (never twice)`);
    return;
  }
  if (pendingAutoReplies.has(agency.id)) {
    return; // a reply is already scheduled for this agency in this run
  }
  pendingAutoReplies.add(agency.id);

  const delayMs = randomDelayMs(30000, 90000);
  console.log(`[autoreply] scheduling auto-reply to ${agency.name} in ${Math.round(delayMs / 1000)}s`);

  setTimeout(async () => {
    try {
      await sendAutoReply(agency.id, message.from);
    } finally {
      pendingAutoReplies.delete(agency.id);
    }
  }, delayMs);
}

async function sendAutoReply(agencyId, waTo) {
  const fresh = await db.getAgencyById(agencyId);
  if (!fresh || fresh.auto_reply_sent) return; // re-check right before sending — never twice
  if (fresh.status === "DO_NOT_CONTACT") return;

  const settings = await db.getSettings();
  if (settings.autoreply_connection_status !== "linked") {
    console.warn(`[autoreply] WARNING: connection not linked when trying to auto-reply to ${fresh.name} — aborting, queuing nothing.`);
    return;
  }
  if (!settings.autoreply_enabled) {
    return; // switch may have been turned off during the delay window
  }

  const template = getAutoReplyTemplate();
  const text = renderTemplate(template.text, fresh.name, fresh.deals_count);

  try {
    await global.__waClient.sendMessage(waTo, text);
    await db.markAutoReplySent(agencyId);
    await db.logAutoReplyMessage(agencyId, template.version, text);
    console.log(`[autoreply] sent auto_reply to ${fresh.name}`);
  } catch (err) {
    console.error(`[autoreply] FAILED to send auto_reply to ${fresh.name}:`, err.message);
  }
}

function start() {
  const client = new Client({
    authStrategy: new LocalAuth({ dataPath: __dirname + "/.wwebjs_auth" }),
  });
  global.__waClient = client;

  client.on("qr", (qr) => {
    console.log("\nScan this QR code with WhatsApp (Linked Devices) to connect:\n");
    qrcode.generate(qr, { small: true });
  });

  client.on("ready", () => {
    db.setConnectionStatus("linked").catch((err) => console.error("[autoreply] failed to update connection status:", err));
    console.log("[autoreply] WhatsApp client READY — connection status: linked");
  });

  client.on("disconnected", (reason) => {
    db.setConnectionStatus("disconnected").catch((err) => console.error("[autoreply] failed to update connection status:", err));
    console.warn("[autoreply] WhatsApp client DISCONNECTED:", reason, "— incoming replies will be marked REPLIED but auto-reply will be skipped until reconnected.");
  });

  client.on("message", (message) => {
    handleIncomingMessage(message).catch((err) => {
      console.error("[autoreply] error handling incoming message:", err);
    });
  });

  // Periodic self-check, in case a disconnect/reconnect isn't caught by the events above.
  setInterval(async () => {
    try {
      const state = await client.getState();
      const status = state === "CONNECTED" ? "linked" : "disconnected";
      await db.setConnectionStatus(status);
    } catch (err) {
      await db.setConnectionStatus("disconnected");
    }
  }, 30000);

  client.initialize();
  return client;
}

module.exports = { start };
