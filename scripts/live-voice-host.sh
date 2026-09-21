#!/usr/bin/env bash
# Start / verify Strlix live-voice host path (TTS on host, playback on laptop browser).
set -euo pipefail
cd /workspace/zevi-cloudphone
set -a
# shellcheck disable=SC1091
source .env
set +a

export VOICE_TTS_PROVIDER="${VOICE_TTS_PROVIDER:-edge}"
export VOICE_EDGE_VOICE="${VOICE_EDGE_VOICE:-en-US-JennyNeural}"
export ADB_BIN="${ADB_BIN:-/workspace/zevi-cloudphone/platform-tools/adb}"

mkdir -p demo/voice-audio

echo "== Live voice host =="
echo "TTS provider: $VOICE_TTS_PROVIDER"
echo "Edge voice:   $VOICE_EDGE_VOICE"
if [[ -n "${AZURE_SPEECH_KEY:-}" ]]; then
  echo "Azure Speech: key set (region=${AZURE_SPEECH_REGION:-?} endpoint=${AZURE_SPEECH_ENDPOINT:-?})"
else
  echo "Azure Speech: not configured — using edge-tts (Microsoft neural voices)"
fi
echo "AWS Polly:    not wired (no AWS credentials on this box)"
echo
echo "Audio routing:"
echo "  Mic:     laptop browser getUserMedia / Web Speech (preferred)"
echo "           phone SpeechRecognizer (fallback UI)"
echo "  Playback: laptop browser WebAudio via /voice/speak + /ws/live"
echo "  Phone speaker: SILENT for assistant TTS"
echo "  scrcpy: keep --no-audio (do not forward phone audio)"
echo

# Quick TTS smoke (writes demo/voice-audio)
./.venv/bin/python - <<'PY'
import asyncio, sys
sys.path.insert(0, ".")
from app.voice import synthesize, provider_status
print("status:", provider_status())
async def main():
    r = await synthesize("Strlix live voice is ready on the laptop speakers.")
    print("smoke:", r)
asyncio.run(main())
PY

PORT="${PILOT_PORT:-8787}"
if curl -sf "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
  echo
  echo "Pilot already up on :${PORT}"
  curl -s "http://127.0.0.1:${PORT}/voice/status" | ./.venv/bin/python -m json.tool || true
  echo
  echo "Open http://127.0.0.1:${PORT}/ → tap Live"
else
  echo
  echo "Starting pilot (includes live voice endpoints)…"
  exec ./scripts/run-pilot.sh
fi
