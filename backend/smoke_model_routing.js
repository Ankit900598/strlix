/**
 * Offline routing smoke — no Azure key required.
 * Run: node backend/smoke_model_routing.js
 */

process.env.AZURE_OPENAI_ENDPOINT = "https://example.openai.azure.com/";
process.env.AZURE_OPENAI_API_KEY = "test-key";
process.env.AZURE_OPENAI_DEPLOYMENT = "pc-lab-cheap";
process.env.AZURE_OPENAI_API_VERSION = "2024-08-01-preview";

const {
  getClassifierProvider,
  getPromiseCompilerProvider,
  getVisionDeployment,
  getVisionDeploymentChain,
  getBestDeployment,
  getStrongDeployment,
  isReasoningDeployment,
} = require("./azureModelRouting");
const {
  parseFastTranscriptionResult,
} = require("./speechTranscriptionService");

function assert(cond, label) {
  if (!cond) {
    throw new Error(`smoke_model_routing failed: ${label}`);
  }
}

assert(getStrongDeployment() === "pc-lab-strong", "strong default");
assert(getBestDeployment() === "pc-lab-best", "best default");
assert(getClassifierProvider().deployment === "pc-lab-strong", "classify ignores cheap");
assert(
  getPromiseCompilerProvider().deployment === "pc-lab-best",
  "compiler uses best"
);
assert(getVisionDeployment() === "pc-lab-astra", "vision uses astra");
assert(
  getVisionDeploymentChain()[0] === "pc-lab-astra",
  "vision chain starts at astra"
);
assert(isReasoningDeployment("pc-lab-best"), "best is reasoning-style");
assert(!isReasoningDeployment("pc-lab-cheap"), "cheap is not reasoning");

const parsed = parseFastTranscriptionResult({
  combinedPhrases: [{ text: " monk mode for 4 hours ", confidence: 0.93 }],
});
assert(parsed.transcript === "monk mode for 4 hours", "fast transcript trim");
assert(parsed.confidence === 0.93, "fast transcript confidence");

console.log(
  JSON.stringify({
    ok: true,
    event: "smoke_model_routing",
    compiler: getPromiseCompilerProvider().deployment,
    classifier: getClassifierProvider().deployment,
    vision: getVisionDeployment(),
  })
);
