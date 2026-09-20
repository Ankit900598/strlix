/**
 * Live Azure deployment ladder on ay186mnc-1561-resource.
 * Do not invent new Azure accounts. Override via env if a deploy name changes.
 */
const OpenAI = require("openai");

const DEFAULT_STRONG_DEPLOYMENT = "pc-lab-strong";
const DEFAULT_BEST_DEPLOYMENT = "pc-lab-best";
const DEFAULT_VISION_DEPLOYMENT = "pc-lab-astra";
const DEFAULT_VISION_FALLBACKS = ["pc-lab-vision", "pc-lab-best", "pc-lab-strong"];
const FALLBACK_OPENAI_MODEL = "gpt-4o-mini";

const REASONING_DEPLOYMENTS = new Set([
  DEFAULT_BEST_DEPLOYMENT,
  "pc-lab-astra",
  "gpt-5.6-sol",
  "gpt-5.5",
  "gpt-5.4",
]);

function envOr(name, fallback) {
  const value = String(process.env[name] || "").trim();
  return value || fallback;
}

function unique(list) {
  return [...new Set(list.filter(Boolean))];
}

function hasAzureConfig() {
  return Boolean(
    process.env.AZURE_OPENAI_ENDPOINT &&
      process.env.AZURE_OPENAI_API_KEY &&
      process.env.AZURE_OPENAI_DEPLOYMENT &&
      process.env.AZURE_OPENAI_API_VERSION
  );
}

function getStrongDeployment() {
  return envOr("AZURE_OPENAI_STRONG_DEPLOYMENT", DEFAULT_STRONG_DEPLOYMENT);
}

function getBestDeployment() {
  return envOr("AZURE_OPENAI_BEST_DEPLOYMENT", DEFAULT_BEST_DEPLOYMENT);
}

function getCompilerDeployment() {
  return envOr("AZURE_PROMISE_COMPILER_DEPLOYMENT", getBestDeployment());
}

function getClassifierDeployment() {
  return envOr("AZURE_CLASSIFIER_DEPLOYMENT", getStrongDeployment());
}

function getVisionDeployment() {
  return envOr("AZURE_VISION_DEPLOYMENT", DEFAULT_VISION_DEPLOYMENT);
}

function getVisionDeploymentChain() {
  const extras = String(process.env.AZURE_VISION_FALLBACKS || "")
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
  return unique([
    getVisionDeployment(),
    ...extras,
    ...DEFAULT_VISION_FALLBACKS,
  ]);
}

function isReasoningDeployment(deployment) {
  const name = String(deployment || "").toLowerCase();
  return (
    REASONING_DEPLOYMENTS.has(deployment) ||
    name.includes("gpt-5") ||
    name.includes("astra") ||
    name.includes("best")
  );
}

function createAzureClient(deployment) {
  const endpoint = process.env.AZURE_OPENAI_ENDPOINT.replace(/\/$/, "");
  return new OpenAI({
    apiKey: process.env.AZURE_OPENAI_API_KEY,
    baseURL: `${endpoint}/openai/deployments/${deployment}`,
    defaultQuery: { "api-version": process.env.AZURE_OPENAI_API_VERSION },
  });
}

function getAzureProvider(deployment) {
  if (!hasAzureConfig()) return null;
  return {
    kind: "azure",
    deployment,
    apiVersion: process.env.AZURE_OPENAI_API_VERSION,
  };
}

function getClassifierProvider() {
  const azure = getAzureProvider(getClassifierDeployment());
  if (azure) return azure;
  if (process.env.OPENAI_API_KEY) {
    return {
      kind: "openai",
      deployment: FALLBACK_OPENAI_MODEL,
      apiVersion: null,
    };
  }
  return null;
}

function getPromiseCompilerProvider() {
  const azure = getAzureProvider(getCompilerDeployment());
  if (azure) return azure;
  if (process.env.OPENAI_API_KEY) {
    return {
      kind: "openai",
      deployment: FALLBACK_OPENAI_MODEL,
      apiVersion: null,
    };
  }
  return null;
}

function createClassifierClient(provider, deploymentOverride) {
  if (provider.kind === "azure") {
    return createAzureClient(deploymentOverride || provider.deployment);
  }
  return new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
}

function buildChatBody({ model, messages, maxTokens, temperature = 0, reasoning }) {
  const body = {
    model,
    messages,
    response_format: { type: "json_object" },
  };
  if (reasoning) {
    body.max_completion_tokens = maxTokens;
  } else {
    body.max_tokens = maxTokens;
    body.temperature = temperature;
  }
  return body;
}

async function completeJsonChat({
  client,
  model,
  messages,
  maxTokens,
  temperature = 0,
}) {
  const preferReasoning = isReasoningDeployment(model);
  const attempts = preferReasoning ? [true, false] : [false, true];
  let lastErr = null;
  for (const reasoning of attempts) {
    try {
      return await client.chat.completions.create(
        buildChatBody({
          model,
          messages,
          maxTokens,
          temperature,
          reasoning,
        })
      );
    } catch (err) {
      lastErr = err;
      const message = String(err && err.message ? err.message : err);
      const retryable =
        /max_tokens|max_completion_tokens|temperature|unsupported/i.test(
          message
        );
      if (!retryable) throw err;
    }
  }
  throw lastErr;
}

async function completeJsonChatWithFallback({
  provider,
  deployments,
  messages,
  maxTokens,
  temperature = 0,
}) {
  const chain = unique(
    provider.kind === "azure" ? deployments : [provider.deployment]
  );
  let lastErr = null;
  for (const deployment of chain) {
    const client = createClassifierClient(provider, deployment);
    const model =
      provider.kind === "azure" ? deployment : provider.deployment;
    try {
      const completion = await completeJsonChat({
        client,
        model,
        messages,
        maxTokens,
        temperature,
      });
      const content = completion && completion.choices && completion.choices[0]
        ? completion.choices[0].message && completion.choices[0].message.content
        : "";
      if (!content || !String(content).trim()) {
        throw new Error(`Empty model response from ${deployment}`);
      }
      return { completion, deployment, client, model };
    } catch (err) {
      lastErr = err;
      console.log(
        JSON.stringify({
          event: "azure_deployment_fallback",
          failedDeployment: deployment,
          message: err && err.message ? err.message : String(err),
        })
      );
    }
  }
  throw lastErr || new Error("No Azure deployment succeeded");
}

module.exports = {
  DEFAULT_STRONG_DEPLOYMENT,
  DEFAULT_BEST_DEPLOYMENT,
  DEFAULT_VISION_DEPLOYMENT,
  DEFAULT_VISION_FALLBACKS,
  FALLBACK_OPENAI_MODEL,
  hasAzureConfig,
  getStrongDeployment,
  getBestDeployment,
  getCompilerDeployment,
  getClassifierDeployment,
  getVisionDeployment,
  getVisionDeploymentChain,
  isReasoningDeployment,
  createAzureClient,
  getClassifierProvider,
  getPromiseCompilerProvider,
  createClassifierClient,
  completeJsonChat,
  completeJsonChatWithFallback,
};
