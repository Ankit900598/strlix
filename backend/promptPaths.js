const fs = require("fs");
const path = require("path");

function resolvePromptsDir() {
  const candidates = [
    path.join(__dirname, "evals", "prompts"),
    path.join(__dirname, "..", "evals", "prompts"),
  ];
  for (const dir of candidates) {
    if (fs.existsSync(dir)) return dir;
  }
  return candidates[1];
}

module.exports = { resolvePromptsDir };
