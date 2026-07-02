// Mirrors scraper/phone_utils.py exactly — keep both in sync if either changes.

function normalizeIlPhone(raw) {
  if (!raw) return null;
  const digits = String(raw).replace(/\D/g, "");
  if (!digits) return null;
  let normalized;
  if (digits.startsWith("972")) {
    normalized = digits;
  } else if (digits.startsWith("0")) {
    normalized = "972" + digits.slice(1);
  } else {
    normalized = "972" + digits;
  }
  if (normalized.length !== 12) return null;
  return normalized;
}

// whatsapp-web.js message.from looks like "972501234567@c.us"
function normalizeWhatsAppId(waId) {
  const digits = waId.split("@")[0];
  return normalizeIlPhone(digits);
}

module.exports = { normalizeIlPhone, normalizeWhatsAppId };
