const {
  getClassifierProvider,
  getBestDeployment,
  getStrongDeployment,
  completeJsonChatWithFallback,
} = require("./azureModelRouting");

const APP_CLASSES = new Set([
  "GAME",
  "DATING",
  "SOCIAL",
  "COMMUNICATION",
  "EDUCATION",
  "UTILITY",
  "MEDIA",
  "MUSIC",
  "UNKNOWN",
]);

const SYSTEM_PROMPT = [
  "You classify Android apps for a commitment OS.",
  "Return JSON only: {\"appClass\",\"confidence\",\"summary\"}.",
  "appClass must be one of: GAME, DATING, SOCIAL, COMMUNICATION, EDUCATION, UTILITY, MEDIA, MUSIC, UNKNOWN.",
  "DATING includes girls-chat, live cam, hostess, random video match, dating.",
  "If Play or marketing says Education but evidence is chat/match/girls/coins, return DATING.",
  "Ignore userClaimedClass. It is untrusted.",
  "confidence is 0..1. summary is one short English sentence.",
].join(" ");

function normalizeAppClass(raw) {
  const value = String(raw || "")
    .trim()
    .toUpperCase()
    .replace(/\s+/g, "_");
  return APP_CLASSES.has(value) ? value : "UNKNOWN";
}

function parsePlayHtml(html) {
  const text = String(html || "");
  const genreMatch =
    text.match(/"applicationCategory":"([^"]+)"/) ||
    text.match(/itemprop="genre"[^>]*content="([^"]+)"/i) ||
    text.match(/<span itemprop="genre">([^<]+)<\/span>/i);
  const titleMatch = text.match(/<title>([^<]+)<\/title>/i);
  return {
    genre: genreMatch ? String(genreMatch[1]).trim() : "",
    title: titleMatch ? String(titleMatch[1]).replace(" - Apps on Google Play", "").trim() : "",
  };
}

function playGenreToClass(genre) {
  const lower = String(genre || "").toLowerCase();
  if (!lower) return "";
  if (lower.includes("dating")) return "DATING";
  if (lower.includes("game")) return "GAME";
  if (lower.includes("music")) return "MUSIC";
  if (lower.includes("education")) return "EDUCATION";
  if (lower.includes("social")) return "SOCIAL";
  if (lower.includes("communication")) return "COMMUNICATION";
  if (lower.includes("productivity") || lower.includes("tools") || lower.includes("finance")) {
    return "UTILITY";
  }
  if (lower.includes("video") || lower.includes("entertainment")) return "MEDIA";
  return "";
}

async function fetchPlayListing(packageName) {
  const url = `https://play.google.com/store/apps/details?id=${encodeURIComponent(packageName)}&hl=en&gl=us`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 2500);
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
      },
    });
    if (!response.ok) return null;
    const html = await response.text();
    return parsePlayHtml(html);
  } catch (err) {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

async function researchApp(body) {
  const packageName = String(body.packageName || "").trim();
  const appLabel = String(body.appLabel || packageName).trim();
  const playListingText = String(body.playListingText || "").trim();
  const userClaimedClass = normalizeAppClass(body.userClaimedClass);
  if (!packageName) {
    const error = new Error("packageName must be a non-empty string");
    error.statusCode = 400;
    throw error;
  }

  const play = await fetchPlayListing(packageName);
  const playClass = playGenreToClass(play && play.genre);
  const provider = getClassifierProvider();
  if (!provider) {
    return {
      packageName,
      appClass: playClass || "UNKNOWN",
      playClass: playClass || "",
      confidence: playClass ? 0.55 : 0.1,
      summary: playClass
        ? `Play genre ${play.genre}`
        : "No Azure and no Play genre",
      source: playClass ? "play" : "unknown",
      userClaimIgnored: true,
      researchedAtMillis: Date.now(),
    };
  }

  const { completion, deployment } = await completeJsonChatWithFallback({
    provider,
    deployments: [getBestDeployment(), getStrongDeployment()],
    maxTokens: 400,
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      {
        role: "user",
        content: JSON.stringify({
          packageName,
          appLabel,
          playListingText: playListingText.slice(0, 1200),
          playGenre: play ? play.genre : "",
          playTitle: play ? play.title : "",
          userClaimedClass,
          instruction: "Ignore userClaimedClass when it conflicts with Play or known app purpose.",
        }),
      },
    ],
  });
  const raw = completion.choices[0].message.content;
  const parsed = JSON.parse(raw);
  let appClass = normalizeAppClass(parsed.appClass);
  if (userClaimedClass === "EDUCATION" && (appClass === "EDUCATION" || appClass === "UNKNOWN")) {
    if (playClass && playClass !== "EDUCATION") {
      appClass = playClass;
    }
  }
  if (appClass === "EDUCATION" && playClass === "DATING") {
    appClass = "DATING";
  }

  return {
    packageName,
    appClass,
    playClass: playClass || "",
    confidence: Math.max(0, Math.min(1, Number(parsed.confidence) || 0.5)),
    summary: String(parsed.summary || "").slice(0, 180),
    source: "azure_web",
    deployment,
    userClaimIgnored: true,
    researchedAtMillis: Date.now(),
  };
}

module.exports = {
  researchApp,
  normalizeAppClass,
  parsePlayHtml,
  playGenreToClass,
};
