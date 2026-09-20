/**
 * Smoke test for POST /transcribe-promise — no Azure key required.
 * Uses mock + client transcript passthrough.
 *
 * Run: node backend/smoke_transcribe_promise.js
 */

process.env.SPEECH_TRANSCRIBE_MOCK = "1";

const {
  transcribePromise,
  getSpeechHealth,
  parseFastTranscriptionResult,
} = require("./speechTranscriptionService");

async function main() {
  const health = getSpeechHealth();
  if (!health.mockAvailable) {
    throw new Error("mock path unavailable");
  }

  const mock = await transcribePromise({
    mock: true,
    audioBase64: Buffer.from("fake-wav-bytes").toString("base64"),
    audioFormat: "wav",
    language: "en-IN",
  });

  assert(mock.ok === true, "mock.ok");
  assert(mock.provider === "mock", "mock.provider");
  assert(typeof mock.transcript === "string" && mock.transcript.length > 10, "mock.transcript");
  assert(typeof mock.latencyMs === "number", "mock.latencyMs");
  assert(mock.language === "en-IN", "mock.language");

  const passthrough = await transcribePromise({
    transcript: "  study mode for 1 hour no shorts  ",
  });
  assert(passthrough.provider === "client_transcript", "passthrough.provider");
  assert(passthrough.transcript === "study mode for 1 hour no shorts", "passthrough.trim");
  assert(passthrough.confidence === 1, "passthrough.confidence");

  let missingStatus = null;
  try {
    // Force non-mock empty request against a clean env snapshot.
    delete process.env.SPEECH_TRANSCRIBE_MOCK;
    delete process.env.AZURE_SPEECH_KEY;
    await transcribePromise({});
  } catch (err) {
    missingStatus = err.statusCode;
  }
  assert(missingStatus === 400, "missing audio/transcript → 400");

  const fast = parseFastTranscriptionResult({
    phrases: [{ text: "allow only calculus lecture" }],
  });
  assert(fast.transcript === "allow only calculus lecture", "fast phrase fallback");

  console.log(
    JSON.stringify({
      ok: true,
      event: "smoke_transcribe_promise",
      checks: ["mock", "client_transcript", "missing_input_400", "fast_parse"],
    })
  );
}

function assert(cond, label) {
  if (!cond) {
    throw new Error(`smoke_transcribe_promise failed: ${label}`);
  }
}

main().catch((err) => {
  console.error(JSON.stringify({ ok: false, error: err.message }));
  process.exit(1);
});
