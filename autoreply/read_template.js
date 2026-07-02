// Reads the auto_reply template straight out of ../message_templates.py so there is
// exactly ONE place (that Python file) where the user edits message wording.

const fs = require("fs");
const path = require("path");

const TEMPLATES_PATH = path.join(__dirname, "..", "message_templates.py");

function getAutoReplyTemplate() {
  const src = fs.readFileSync(TEMPLATES_PATH, "utf-8");

  const blockMatch = src.match(/["']auto_reply["']\s*:\s*{([\s\S]*?)\n\s*},/);
  if (!blockMatch) {
    throw new Error("Could not find 'auto_reply' block in message_templates.py");
  }
  const block = blockMatch[1];

  const versionMatch = block.match(/["']version["']\s*:\s*["']([^"']+)["']/);
  const textMatch = block.match(/["']text["']\s*:\s*"""([\s\S]*?)"""/);

  if (!versionMatch || !textMatch) {
    throw new Error("Could not parse version/text for 'auto_reply' template");
  }

  return { version: versionMatch[1], text: textMatch[1] };
}

function renderTemplate(text, agencyName, dealCount) {
  let rendered = text.replace(/\[AGENCY_NAME\]/g, agencyName || "");
  rendered = rendered.replace(/\[DEAL_COUNT\]/g, dealCount != null ? String(dealCount) : "");
  return rendered;
}

module.exports = { getAutoReplyTemplate, renderTemplate };
