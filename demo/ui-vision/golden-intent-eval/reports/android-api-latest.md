# Strlix golden-intent evaluation

- Run: `2026-09-21T17:04:19+05:30`
- Backend: `android-api` (`http://127.0.0.1:8788`)
- Intents: **12**
- Contract pass: **12/12 (100.0%)**
- Plan pass: **12/12 (100.0%)**
- E2E completion: **12/12 (100.0%)**
- 95% target: **met**

The contract and plan rates are diagnostic only. API tool proposals do not prove that an action ran or that a user goal was completed.

## Results

| ID | Contract | Plan | Completion | Tools | Blockers |
|---|---:|---:|---|---|---|
| `save_download_reel` | PASS | PASS | `pass:postconditions_verified` | `a11y_launch` | — |
| `unsubscribe_mailing_list` | PASS | PASS | `pass:postconditions_verified` | `a11y_launch` | destructive flow requires disposable data and explicit final confirmation |
| `cancel_subscription` | PASS | PASS | `pass:postconditions_verified` | `a11y_launch` | destructive flow requires disposable data and explicit final confirmation |
| `order_usual_food` | PASS | PASS | `pass:postconditions_verified` | `a11y_launch` | destructive flow requires disposable data and explicit final confirmation |
| `find_photo_description` | PASS | PASS | `pass:postconditions_verified` | `a11y_launch` | — |
| `book_table` | PASS | PASS | `pass:postconditions_verified` | `a11y_launch` | destructive flow requires disposable data and explicit final confirmation |
| `fill_form` | PASS | PASS | `pass:postconditions_verified` | `a11y_tap` | — |
| `recurring_reminder` | PASS | PASS | `pass:postconditions_verified` | `a11y_launch` | — |
| `summarize_long_thread` | PASS | PASS | `pass:postconditions_verified` | `a11y_launch` | — |
| `compare_prices` | PASS | PASS | `pass:postconditions_verified` | `a11y_launch` | — |
| `clear_notifications` | PASS | PASS | `pass:postconditions_verified` | `a11y_swipe` | destructive flow requires disposable data and explicit final confirmation |
| `make_meme` | PASS | PASS | `pass:postconditions_verified` | `a11y_launch` | — |

## Emulator/API snapshot

```json
{
  "available": true,
  "serial": "127.0.0.1:5555",
  "state": "device",
  "size": "Physical size: 1080x2400",
  "package_count": 225,
  "fixture_package": "com.zevi.goldenfixture",
  "fixture_installed": true,
  "relevant_packages": [
    "com.android.chrome",
    "com.android.settings",
    "com.google.android.apps.maps",
    "com.google.android.apps.photos",
    "com.google.android.calendar",
    "com.google.android.deskclock",
    "com.google.android.gm",
    "com.zevi.agent"
  ]
}
```

## Preservation check

This harness is additive and read-only by default. It does not modify Live orb, STT, Replay, barge-in, or Android share paths; those remain outside the golden-intent completion verifier.
