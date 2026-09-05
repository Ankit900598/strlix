const fs = require("fs");
const path = require("path");
const OpenAI = require("openai");

const PROMPT_VERSION = "v04";
const PROMPT_PATH = path.join(
  __dirname,
  "..",
  "evals",
  "prompts",
  "classifier_v04.txt"
);
const ESCALATION_CONFIDENCE_THRESHOLD = 0.75;
const FALLBACK_OPENAI_MODEL = "gpt-4o-mini";

let cachedPrompt = null;

function loadClassifierPrompt() {
  if (cachedPrompt) {
    return cachedPrompt;
  }
  cachedPrompt = fs.readFileSync(PROMPT_PATH, "utf8");
  return cachedPrompt;
}

function hasAzureConfig() {
  return Boolean(
    process.env.AZURE_OPENAI_ENDPOINT &&
      process.env.AZURE_OPENAI_API_KEY &&
      process.env.AZURE_OPENAI_DEPLOYMENT &&
      process.env.AZURE_OPENAI_API_VERSION
  );
}

function getClassifierProvider() {
  if (hasAzureConfig()) {
    return {
      kind: "azure",
      deployment: process.env.AZURE_OPENAI_DEPLOYMENT,
      apiVersion: process.env.AZURE_OPENAI_API_VERSION,
    };
  }
  if (process.env.OPENAI_API_KEY) {
    return {
      kind: "openai",
      deployment: FALLBACK_OPENAI_MODEL,
      apiVersion: null,
    };
  }
  return null;
}

function createClassifierClient(provider) {
  if (provider.kind === "azure") {
    const endpoint = process.env.AZURE_OPENAI_ENDPOINT.replace(/\/$/, "");
    const deployment = process.env.AZURE_OPENAI_DEPLOYMENT;
    return new OpenAI({
      apiKey: process.env.AZURE_OPENAI_API_KEY,
      baseURL: `${endpoint}/openai/deployments/${deployment}`,
      defaultQuery: { "api-version": process.env.AZURE_OPENAI_API_VERSION },
    });
  }

  return new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
}

function buildClassifierUserPayload(body) {
  const packageName = body.packageName;
  const screenText = body.screenText;
  const goal = body.goal;

  return {
    packageName,
    appLabel:
      typeof body.appLabel === "string" && body.appLabel.trim()
        ? body.appLabel.trim()
        : packageName,
    screenText,
    userGoal: goal,
    strictnessLevel:
      typeof body.strictnessLevel === "string"
        ? body.strictnessLevel.toUpperCase()
        : "SMART",
    activeGuardrails: Array.isArray(body.activeGuardrails)
      ? body.activeGuardrails
      : [],
    commitmentType:
      typeof body.commitmentType === "string"
        ? body.commitmentType
        : "focus_session",
    sessionCounters:
      body.sessionCounters && typeof body.sessionCounters === "object"
        ? body.sessionCounters
        : null,
    limitState:
      typeof body.limitState === "string" ? body.limitState : null,
  };
}

function parseClassifierJson(raw) {
  const trimmed = raw.trim();
  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)\s*```/i);
  const jsonText = fenced ? fenced[1].trim() : trimmed;
  return JSON.parse(jsonText);
}

function normalizeClassifierResult(parsed) {
  const decision = String(parsed.decision || "WARN").toUpperCase();
  const validDecisions = new Set(["ALLOW", "WARN", "BLOCK", "LOCK"]);

  if (!validDecisions.has(decision)) {
    throw new Error("Invalid decision from model");
  }

  const confidence = Number(parsed.confidence);
  if (!Number.isFinite(confidence)) {
    throw new Error("Invalid confidence from model");
  }

  const reason =
    typeof parsed.reason === "string" ? parsed.reason : "No reason provided.";

  const reasonCategory =
    typeof parsed.reasonCategory === "string"
      ? parsed.reasonCategory
      : "ambiguous";

  return { decision, confidence, reason, reasonCategory };
}

function shouldEscalate(decision, confidence, reasonCategory) {
  return (
    confidence < ESCALATION_CONFIDENCE_THRESHOLD ||
    (decision === "BLOCK" && reasonCategory === "ambiguous")
  );
}

function redactForLog(text, maxLen) {
  if (typeof text !== "string") {
    return { length: 0, preview: "" };
  }
  const collapsed = text.replace(/\s+/g, " ").trim();
  return {
    length: collapsed.length,
    preview:
      collapsed.length <= maxLen
        ? collapsed
        : `${collapsed.slice(0, maxLen)}…`,
  };
}

function logClassifyEvent({
  provider,
  deployment,
  latencyMs,
  decision,
  reasonCategory,
  confidence,
  wouldEscalate,
  packageName,
  goal,
  screenText,
}) {
  const goalSafe = redactForLog(goal, 60);
  const screenSafe = redactForLog(screenText, 40);

  console.log(
    JSON.stringify({
      event: "classify",
      provider,
      deployment,
      promptVersion: PROMPT_VERSION,
      latencyMs: Math.round(latencyMs),
      decision,
      reasonCategory,
      confidence: Number(confidence.toFixed(3)),
      would_escalate: wouldEscalate,
      packageName,
      goalLength: goalSafe.length,
      goalPreview: goalSafe.preview,
      screenTextLength: screenSafe.length,
      screenTextPreview: screenSafe.preview,
    })
  );
}

async function classifyActivity(body) {
  const provider = getClassifierProvider();
  if (!provider) {
    const err = new Error(
      "No classifier configured: set Azure OpenAI env vars or OPENAI_API_KEY"
    );
    err.statusCode = 500;
    throw err;
  }

  const client = createClassifierClient(provider);
  const userPayload = buildClassifierUserPayload(body);
  const model =
    provider.kind === "azure"
      ? process.env.AZURE_OPENAI_DEPLOYMENT
      : FALLBACK_OPENAI_MODEL;

  const started = Date.now();
  const completion = await client.chat.completions.create({
    model,
    temperature: 0,
    max_tokens: 300,
    response_format: { type: "json_object" },
    messages: [
      { role: "system", content: loadClassifierPrompt() },
      { role: "user", content: JSON.stringify(userPayload) },
    ],
  });
  const latencyMs = Date.now() - started;

  const raw = completion.choices[0]?.message?.content;
  if (!raw) {
    const err = new Error("Empty model response");
    err.statusCode = 502;
    throw err;
  }

  let parsed;
  try {
    parsed = parseClassifierJson(raw);
  } catch (_parseErr) {
    const err = new Error("Model did not return valid JSON");
    err.statusCode = 502;
    err.raw = raw;
    throw err;
  }

  const normalized = normalizeClassifierResult(parsed);
  const wouldEscalate = shouldEscalate(
    normalized.decision,
    normalized.confidence,
    normalized.reasonCategory
  );

  logClassifyEvent({
    provider: provider.kind,
    deployment: provider.deployment,
    latencyMs,
    decision: normalized.decision,
    reasonCategory: normalized.reasonCategory,
    confidence: normalized.confidence,
    wouldEscalate,
    packageName: body.packageName,
    goal: body.goal,
    screenText: body.screenText,
  });

  if (wouldEscalate) {
    console.log(
      JSON.stringify({
        event: "classify_escalation_placeholder",
        would_escalate: true,
        targetDeployment: "pc-lab-strong",
        promptVersion: PROMPT_VERSION,
        reason:
          normalized.confidence < ESCALATION_CONFIDENCE_THRESHOLD
            ? "low_confidence"
            : "ambiguous_block",
      })
    );
  }

  return {
    decision: normalized.decision,
    confidence: normalized.confidence,
    reason: normalized.reason,
    reasonCategory: normalized.reasonCategory,
    would_escalate: wouldEscalate,
    meta: {
      provider: provider.kind,
      deployment: provider.deployment,
      promptVersion: PROMPT_VERSION,
      latencyMs: Math.round(latencyMs),
    },
  };
}

module.exports = {
  PROMPT_VERSION,
  PROMPT_PATH,
  ESCALATION_CONFIDENCE_THRESHOLD,
  getClassifierProvider,
  classifyActivity,
};
