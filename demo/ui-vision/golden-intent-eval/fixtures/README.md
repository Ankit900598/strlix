# Golden-intent fixture contract

`manifest.json` is the fixture/postcondition contract for the 12 golden intents. This checkout includes a minimal offline `com.zevi.goldenfixture` APK under `android/` and a provider runner that installs it and verifies each postcondition through the fixture UI.

The included provider is intentionally synthetic and offline. It does not open real apps or accounts; it exercises a deterministic review-safe fixture screen. A production-grade disposable fixture provider must:

1. Install the exact fixture package on a disposable emulator.
2. Seed only synthetic accounts, messages, photos, carts, reminders, and notifications.
3. Expose the fixture id and write evidence for every listed postcondition after the phone executes the proposed Accessibility tools.
4. Leave destructive/financial operations at the review screen unless a separate explicit confirmation test is being run.

The evaluator only reads package/evidence state. It does not seed data, execute returned tools, or infer completion from an API response. This prevents a plan pass from being reported as an E2E pass.


Evidence consumed by `--postcondition-evidence` has this minimal shape (the provider owns its production):

```json
{
  "fixture_package": "com.zevi.goldenfixture",
  "serial": "127.0.0.1:5555",
  "intents": {
    "fill_form": {
      "fixture_id": "golden.fill_form",
      "postconditions": {
        "fixture.form.fields_match_saved_contact": true,
        "fixture.form.not_submitted": true
      }
    }
  }
}
```

Missing, mismatched, or partial evidence is **not** a failure or a pass; it remains unscored.


## Included provider run

```bash
# Build the minimal fixture APK
cd demo/ui-vision/golden-intent-eval/fixtures/android
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ANDROID_HOME=/home/box/Android
./gradlew :app:assembleDebug

# Install, exercise all 12 fixture flows, and emit strict evidence
cd /workspace/zevi-cloudphone
python3 scripts/run_golden_fixture.py

# Score the android-api run against that evidence
python3 scripts/golden_intents_eval.py --backend android-api --base-url http://127.0.0.1:8788 \
  --postcondition-evidence demo/ui-vision/golden-intent-eval/fixtures/postcondition-evidence.json
```

The resulting score is fixture-backed E2E evidence, not a claim that real Gmail/Chrome/Photos accounts were changed. Destructive cases remain review-safe and no final confirmation is performed.
