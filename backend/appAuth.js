function isPublicHealth(req) {
  const path = String((req && req.path) || "");
  return req && req.method === "GET" && (path === "/health" || path === "/");
}

function expectedAppSecret() {
  return String(process.env.STRLIX_BACKEND_APP_SECRET || "").trim();
}

function requireAppSecret(req, res, next) {
  const expected = expectedAppSecret();
  if (!expected) return next();
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
  requireAppSecret,
  appAuthMiddleware,
};
