// Shared Postgres database (same one the local/cloud Flask app uses), via the
// DATABASE_URL env var — read from ../.env at startup by index.js.
const { Pool } = require("pg");
const dns = require("dns");

let pool = null;

// Some local networks' default DNS resolver fails to resolve the database
// host even though the hostname itself is fine (confirmed: Google's DNS
// resolves it instantly) — same issue handled on the Python side. Query
// 8.8.8.8/1.1.1.1 directly for just this one lookup rather than changing
// system-wide DNS settings.
function resolveViaPublicDns(hostname) {
  return new Promise((resolve) => {
    const resolver = new dns.promises.Resolver();
    resolver.setServers(["8.8.8.8", "1.1.1.1"]);
    resolver
      .resolve4(hostname)
      .then((addresses) => resolve(addresses[0]))
      .catch(() => resolve(null));
  });
}

async function getPool() {
  if (pool) return pool;

  const url = new URL(process.env.DATABASE_URL);
  const resolvedIp = await resolveViaPublicDns(url.hostname);

  pool = new Pool({
    host: resolvedIp || url.hostname,
    port: url.port || 5432,
    user: url.username,
    password: url.password,
    database: url.pathname.replace(/^\//, ""),
    ssl: { require: true, rejectUnauthorized: false, servername: url.hostname },
  });
  return pool;
}

function nowIso() {
  return new Date().toISOString().slice(0, 19);
}

async function findAgencyByPhone(normalizedPhone) {
  const p = await getPool();
  const { rows } = await p.query(
    `SELECT * FROM agencies
     WHERE direct_mobile = $1 OR phone_used = $1 OR phone_raw = $1
     LIMIT 1`,
    [normalizedPhone]
  );
  return rows[0] || null;
}

async function markReplied(agencyId) {
  const p = await getPool();
  await p.query(
    `UPDATE agencies SET status='REPLIED', replied_at=$1, updated_at=$2 WHERE id=$3`,
    [nowIso(), nowIso(), agencyId]
  );
}

async function markAutoReplySent(agencyId) {
  const p = await getPool();
  await p.query(
    `UPDATE agencies SET auto_reply_sent=1, auto_reply_sent_at=$1, updated_at=$2 WHERE id=$3`,
    [nowIso(), nowIso(), agencyId]
  );
}

async function getAgencyById(agencyId) {
  const p = await getPool();
  const { rows } = await p.query(`SELECT * FROM agencies WHERE id=$1`, [agencyId]);
  return rows[0] || null;
}

async function logAutoReplyMessage(agencyId, templateVersion, messageText) {
  const p = await getPool();
  await p.query(
    `INSERT INTO message_log (agency_id, template_key, template_version, message_text, triggered_by, sent_at)
     VALUES ($1, 'auto_reply', $2, $3, 'auto_reply_module', $4)`,
    [agencyId, templateVersion, messageText, nowIso()]
  );
}

async function getSettings() {
  const p = await getPool();
  const { rows } = await p.query(`SELECT * FROM settings WHERE id=1`);
  return rows[0];
}

async function setConnectionStatus(status) {
  const p = await getPool();
  await p.query(
    `UPDATE settings SET autoreply_connection_status=$1, updated_at=$2 WHERE id=1`,
    [status, nowIso()]
  );
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
