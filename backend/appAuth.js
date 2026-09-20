function isPublicHealth(req) {
  const path = String((req && req.path) || "");
  return req && req.method === "GET" && (path === "/health" || path === "/");
}

function expectedAppSecret() {
  return String(process.env.STRLIX_BACKEND_APP_SECRET || "").trim();
}

function isHostedRuntime() {
  return Boolean(
    String(process.env.WEBSITE_HOSTNAME || "").trim() ||
      process.env.STRLIX_REQUIRE_APP_SECRET === "1"
  );
}

function assertHostedAppSecretConfigured() {
  if (isHostedRuntime() && !expectedAppSecret()) {
    throw new Error(
      "STRLIX_BACKEND_APP_SECRET is required on hosted POST routes"
    );
  }
}

function requireAppSecret(req, res, next) {
  const expected = expectedAppSecret();
  if (!expected) {
    if (isHostedRuntime()) {
      return res.status(503).json({ error: "app_secret_not_configured" });
    }
    return next();
  }
  const got = String((req && req.get && req.get("x-strlix-app-secret")) || "").trim();
  if (got !== expected) {
    return res.status(401).json({ error: "unauthorized" });
  }
  return next();
}

function appAuthMiddleware(req, res, next) {
  if (isPublicHealth(req)) return next();
  return requireAppSecret(req, res, next);
}

module.exports = {
  isPublicHealth,
  expectedAppSecret,
  isHostedRuntime,
  assertHostedAppSecretConfigured,
  requireAppSecret,
  appAuthMiddleware,
};
