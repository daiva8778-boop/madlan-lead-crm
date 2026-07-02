// Uses Node's built-in node:sqlite (requires Node >=22.5.0) — no native compilation
// step needed, unlike better-sqlite3, which keeps setup to a plain `npm install`.
const path = require("path");
const { DatabaseSync } = require("node:sqlite");

const DB_PATH = path.join(__dirname, "..", "data", "madlan_crm.db");

let db = null;

function getDb() {
  if (!db) {
    db = new DatabaseSync(DB_PATH);
    db.exec("PRAGMA journal_mode = WAL;");
    db.exec("PRAGMA busy_timeout = 5000;");
  }
  return db;
}

function nowIso() {
  return new Date().toISOString().slice(0, 19);
}

function findAgencyByPhone(normalizedPhone) {
  const row = getDb()
    .prepare(
      `SELECT * FROM agencies
       WHERE direct_mobile = ? OR phone_used = ? OR phone_raw = ?
       LIMIT 1`
    )
    .get(normalizedPhone, normalizedPhone, normalizedPhone);
  return row || null;
}

function markReplied(agencyId) {
  getDb()
    .prepare(`UPDATE agencies SET status='REPLIED', replied_at=?, updated_at=? WHERE id=?`)
    .run(nowIso(), nowIso(), agencyId);
}

function markAutoReplySent(agencyId) {
  getDb()
    .prepare(
      `UPDATE agencies SET auto_reply_sent=1, auto_reply_sent_at=?, updated_at=? WHERE id=?`
    )
    .run(nowIso(), nowIso(), agencyId);
}

function getAgencyById(agencyId) {
  return getDb().prepare(`SELECT * FROM agencies WHERE id=?`).get(agencyId) || null;
}

function logAutoReplyMessage(agencyId, templateVersion, messageText) {
  getDb()
    .prepare(
      `INSERT INTO message_log (agency_id, template_key, template_version, message_text, triggered_by, sent_at)
       VALUES (?, 'auto_reply', ?, ?, 'auto_reply_module', ?)`
    )
    .run(agencyId, templateVersion, messageText, nowIso());
}

function getSettings() {
  return getDb().prepare(`SELECT * FROM settings WHERE id=1`).get();
}

function setConnectionStatus(status) {
  getDb()
    .prepare(`UPDATE settings SET autoreply_connection_status=?, updated_at=? WHERE id=1`)
    .run(status, nowIso());
}

module.exports = {
  findAgencyByPhone,
  markReplied,
  markAutoReplySent,
  getAgencyById,
  logAutoReplyMessage,
  getSettings,
  setConnectionStatus,
};
