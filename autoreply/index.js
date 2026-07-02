const db = require("./db");
const { start } = require("./whatsapp_client");

console.log("=".repeat(60));
console.log("Madlan CRM — WhatsApp auto-reply module (OPTIONAL, unofficial)");
console.log("=".repeat(60));
console.log("This uses whatsapp-web.js, an UNOFFICIAL WhatsApp client library.");
console.log("Your computer must stay on and this window open for it to work.");
console.log("The dashboard's master switch (default OFF) still gates all sending.");
console.log("");

db.setConnectionStatus("disconnected"); // will flip to 'linked' once the client is ready

start();

process.on("SIGINT", () => {
  console.log("\n[autoreply] shutting down...");
  db.setConnectionStatus("not_running");
  process.exit(0);
});
