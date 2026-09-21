# Voice brief — Strlix cloud phone market (spoken)

We researched VS Phone Cloud and about twenty peer cloud phones, cloud phone browsers, and device farms. We logged fifty-five distinct mistakes — things like buy-before-try wallets, fake latency, outside AI chat, and opaque pricing — and for each mistake we ask why it hurts and why vendors still charge that way.

Separately, we catalogued one hundred sixty-six best-in-class apps from Apple Design Awards, Gummble, and known product leaders, then deduped into over five hundred unique UI practices.

Claude Code finished one focused pass per mistake — fifty-five real claude-cli files under claude-solutions. Verification is caught up: most ACCEPTed; five REVISE items push honesty on latency, datacenter labels, no anti-detect Identity merge, defer fleet sync, and default non-root. Accepted ideas feed the rollup in CLAUDE-SOLUTION.

We shipped a premium web-market homepage: a small phone entry expands to fullscreen bezel, with Android, RAM, and ROM filters, published dollar-per-hour prices, a live RTT-estimated latency chip, datacenter honesty chips, plus a Stripe-style test checkout stub that cannot charge real money. market-api is a FastAPI skeleton on sqlite locally and also serves the UI at /market; Azure Postgres and Redis bicep stays unapplied to protect credits.

Three-platform plan: shared web shell, Capacitor or TWA for Android, Tauri for desktop, WKWebView stub for iOS — documented under wrappers.

Open locally on port 8765, or via market-api at 8792/market — port 8790 is occupied by the sandbox egress tunnel on this box. Screenshots remain under shipped.
