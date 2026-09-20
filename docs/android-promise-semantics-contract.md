# Android Contract — Promise Semantics v1

**Audience:** Android PolicyEngine / Accessibility owners  
**Rule:** AI compiles counsel. Android enforces law. Never the reverse.

---

## 1. What Android must treat as first-class fields

From `POST /compile-promise` DTO (`normalizeCompiledPromise`):

| Field | Meaning |
|-------|---------|
| `timeWindowKind` | `session_fixed` \| `calendar_day` \| `multi_day` \| `until_clock` \| `permanent` \| `session_fixed_default` |
| `sessionDurationMinutes` | Timer length. For `calendar_day`, may be 1440 (stand-in). Do **not** invent a second 60m timer. |
| `quotaBoundary` | Always `allow_first_n` when short-form count quotas exist |
| `contentRules` | Deterministic rules: surface/contentType/operator/value/unit/action |
| `scopePackages` | Packages in short-form category expansion (includes NewPipe) |
| `confirmationPreview` | User-facing bullets — show before Start |
| `clarificationQuestion` | If non-null → **block Start** until answered/edited |
| `suggestedAppRules` | App-level ALLOW/BLOCK hints; contentRules win for surfaces |

---

## 2. Short-form quota enforcement (law)

```text
IF contentRule matches short_form_video with unit=count:
  event = short-form PLAY only
           (Shorts / Reels / TikTok / Spotlight / NewPipe short / Chrome short embed)
  NOT counted: app open, homepage, search, comments, shelf peek

  IF adult/sexual signal → BLOCK immediately (ignore quota)

  ELSE IF play_count < N   → ALLOW   // events 1..N
  ELSE IF play_count >= N  → BLOCK   // event N+1+
  Reset play_count at local day boundary when period=day
```

Matching packages at minimum:  
`com.google.android.youtube`, `org.schabi.newpipe`, `com.instagram.android`,  
`com.facebook.katana`, `com.zhiliaoapp.musically`, `com.snapchat.android`,  
`com.android.chrome` — plus `VideoPlatformRegistry` updates.

Unknown entertainment video clone → **WARN** (or treat as short/long via surface detector), never silent ALLOW-as-harmless.

---

## 3. Confirm sheet (required before Start)

Show `confirmationPreview` lines, e.g.:

- Allowed: first 10 short-form videos today  
- Blocked always: adult/sexual short videos  
- After limit: block short-form until tomorrow  
- Still allowed: long educational YouTube videos  
- Applies to: short-video apps, social reels apps, and browser video pages  
- Interpretation note: “shorts” = all short-form (Change?)

**Rule:** Internal `scopePackages` may list concrete packages for PolicyEngine.  
User-facing confirmation must stay **category-level** — never dump `com.*` package IDs or NewPipe unless the user named it.

---

## 4. What Android must NOT do

- Do not map video **length** thresholds to entertainment **budget** counters.  
- Do not treat bare short-form **quota** as permanent `no_short_form_video` ban.  
- Do not invent a 60-minute Study World when `timeWindowKind=calendar_day`.  
- Do not let cloud AI override permanent adult/dating/emergency rules.  
- Do not enforce AI JSON directly without mapping through PolicyEngine.

---

## 5. Surfaces Android must detect (deterministic)

| Surface | Apps |
|---------|------|
| short_form play | YT Shorts, IG Reels, FB Reels, TikTok, Spotlight, NewPipe short, Chrome short |
| long_form / study player | YT/NewPipe/Chrome active player with lecture-length |
| social_dm | IG/WA messages |
| social_feed | Explore / Home / Stories / model pages |
| adult_sexual | NSFW signals (existing guardrail path) |
| install | Play Store / sideload gate (represent even if partial) |

Reuse `VideoPlatformRegistry`, `SurfaceDetector`, `PromiseIntentRules` — extend, don’t fork.

---

## 6. Acceptance examples (phone harness)

1. **10 shorts today + never adult + lectures OK** → allow first 10 short plays across YT/IG/NewPipe; adult blocks at 0; lecture ALLOW; no 60m session.  
2. **Neso 3h + no shorts + lock on drift** → 180m session; shorts BLOCK; drift → WARN/LOCK per strikePolicy; ask playlist confirm if unknown.  
3. **1 year no porn/dating/flirt installs** → permanent guardrails; rest phone normal; trusted recovery recommended.  
4. **IG college replies 7d** → DM ALLOW; Reels/Explore/Stories BLOCK; WA/Chrome not banned by default.

---

## 7. Ship gate

Compiler + normalize may ship as **counsel**.  
Cross-app short-form **counting** ships only after detectors pass phone harness for YT + NewPipe + IG + Chrome at minimum.
