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
  getCompilerDeploymentChain,
  getClassifierDeploymentChain,
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
assert(getClassifierProvider().deployment === "pc-lab-terra", "classify uses terra");
assert(
  getPromiseCompilerProvider().deployment === "pc-lab-astra",
  "compiler uses astra"
);
assert(getVisionDeployment() === "pc-lab-astra", "vision uses astra");
assert(
  getVisionDeploymentChain()[0] === "pc-lab-astra",
  "vision chain starts at astra"
);
assert(getCompilerDeploymentChain()[0] === "pc-lab-astra", "compiler chain starts astra");
assert(getCompilerDeploymentChain().includes("pc-lab-best"), "compiler falls back to sol");
assert(getClassifierDeploymentChain()[0] === "pc-lab-terra", "classifier chain starts terra");
assert(getClassifierDeploymentChain().includes("pc-lab-luna"), "classifier falls back to luna");
assert(isReasoningDeployment("pc-lab-best"), "best is reasoning-style");
assert(isReasoningDeployment("pc-lab-terra"), "terra is reasoning-style");
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
