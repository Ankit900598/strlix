# Strlix split backends

| Service | Port | Owns |
|---------|-----:|------|
| `android-api` | 8788 | In-phone chat, voice hooks, Accessibility tool protocol |
| `desktop-api` | 8789 | Viewer H.264/JPEG stream, tap/swipe, session bind |
| `session-broker` | 8791 | Device pool lease → desktop JWT |
| *(legacy)* `app/` pilot | 8787 | Monolith — keep until cutover |

Shared: `packages/common` (`strlix_common`).

```bash
../scripts/run-split.sh
```

See `../demo/scale/SPLIT-PLAN.md` and `../demo/scale/ARCHITECTURE-claude.md`.

| `market-api` | 8792 | Catalog, auth stub, test checkout, pollable job status |

