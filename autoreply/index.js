require("dotenv").config({ path: __dirname + "/../.env" });

const db = require("./db");
const { start } = require("./whatsapp_client");

console.log("=".repeat(60));
console.log("Madlan CRM — WhatsApp auto-reply module (OPTIONAL, unofficial)");
console.log("=".repeat(60));
console.log("This uses whatsapp-web.js, an UNOFFICIAL WhatsApp client library.");
console.log("Your computer must stay on and this window open for it to work.");
console.log("The dashboard's master switch (default OFF) still gates all sending.");
console.log("");

if (!process.env.DATABASE_URL) {
  console.error("ERROR: DATABASE_URL is not set in .env — cannot start.");
  process.exit(1);
}

db.setConnectionStatus("disconnected").catch((err) =>
  console.error("[autoreply] failed to set initial connection status:", err)
); // will flip to 'linked' once the client is ready

start();

process.on("SIGINT", async () => {
  console.log("\n[autoreply] shutting down...");
  try {
    await db.setConnectionStatus("not_running");
  } finally {
    process.exit(0);
  }
});
