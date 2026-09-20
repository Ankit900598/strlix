const assert = require("assert");
const {
  normalizeAppClass,
  parsePlayHtml,
  playGenreToClass,
} = require("./appDossierService");

assert.strictEqual(normalizeAppClass("dating"), "DATING");
assert.strictEqual(normalizeAppClass("not-a-class"), "UNKNOWN");
assert.strictEqual(playGenreToClass("Dating"), "DATING");
assert.strictEqual(playGenreToClass("Music & Audio"), "MUSIC");
assert.strictEqual(playGenreToClass("Education"), "EDUCATION");

const parsed = parsePlayHtml(
  '<title>Connecto - Apps on Google Play</title>"applicationCategory":"Communication"'
);
assert.strictEqual(parsed.genre, "Communication");
assert.ok(parsed.title.toLowerCase().includes("connecto"));
assert.strictEqual(playGenreToClass(parsed.genre), "COMMUNICATION");

console.log("smoke_app_dossier ok");
