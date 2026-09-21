# Strlix golden-intent evaluation

This is the executable suite for the 12 golden intents named by `BILLION-USER-UI.md`.
It intentionally reports three different measures:

- **Contract**: the backend is reachable and returns the Android API/Pilot shape.
- **Plan**: the model proposes a relevant Accessibility action. This is not task completion.
- **E2E**: a seeded emulator fixture reaches a deterministic postcondition. This is the only score that can claim the 95% product target.

The default runner is read-only: it calls `android-api` and never executes returned tools. Destructive intents are always marked as requiring a disposable fixture and explicit final confirmation. The `pilot` backend is available for an explicit run, but Pilot tools are real ADB actions. The runner refuses it unless `--allow-device-actions` is supplied; do not use it against a personal device or an unseeded account.

## Usage

From the repository root:

```bash
# Safe API contract/proposal run; writes JSON + Markdown evidence.
python3 scripts/golden_intents_eval.py --backend android-api --base-url http://127.0.0.1:8788

# The legacy Pilot endpoint is supported explicitly; it may tap/type/swipe on its bound device.
python3 scripts/golden_intents_eval.py --backend pilot --base-url http://127.0.0.1:8787 --allow-device-actions

# Offline validation of the suite and runner wiring.
python3 scripts/golden_intents_eval.py --validate-only
```

Options include `--intent ID`, `--repeat N`, `--timeout SECONDS`, `--no-adb`, `--out PATH`, and `--report PATH`.
Reports default to `demo/ui-vision/golden-intent-eval/reports/` and contain the exact request, response summary, tool names, capability snapshot, fixture id, postcondition contract, and blockers (not secrets or bulky screenshots).

The fixture contract is `fixtures/manifest.json`. It is definition-only until a disposable provider installs `com.zevi.goldenfixture` and emits evidence. The runner only reads readiness; it never seeds data or executes proposed tools. This keeps plan passes separate from honest E2E completion. Override it with `--fixture-manifest PATH` for CI/provider integration. A provider run may supply `--postcondition-evidence PATH`; evidence is scored only when the exact fixture package, serial, fixture id, and every listed postcondition match.
