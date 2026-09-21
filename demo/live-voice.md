# Strlix Live Voice Mode

**Updated:** 2026-09-20 ~23:03 IST (Asia/Calcutta)

## Active TTS service (now)

| Item | Value |
|------|-------|
| Preference | `VOICE_TTS_PROVIDER=auto` |
| **Active now** | **Azure Speech** (`speech-zevi-strlix`, **S0**, **eastus2**, RG `rg-zevi-cloudphone` only) |
| Fallback 1 | AWS Polly neural (verified; Joanna / Kajal) |
| Fallback 2 | edge-tts Microsoft neural (last resort) |
| Playback | Host TTS → laptop browser WebAudio · phone silent · scrcpy `--no-audio` |

### Voices by language (shipped)

| ID | Name | Azure / edge | Polly neural |
|----|------|--------------|--------------|
| en-US | English | en-US-JennyNeural | Joanna |
| hi-IN | Hindi | hi-IN-SwaraNeural | Kajal |
| es-ES | Spanish | es-ES-ElviraNeural | Lucia |
| fr-FR | French | fr-FR-DeniseNeural | Lea |
| zh-CN | Mandarin | zh-CN-XiaoxiaoNeural | Zhiyu |
| ar-SA | Arabic | ar-SA-ZariyahNeural | Hala (ar-AE) |
| pt-BR | Portuguese | pt-BR-FranciscaNeural | Camila |
| ja-JP | Japanese | ja-JP-NanamiNeural | Kazuha |

## Multi-language UX

- **Web Live**: language `<select>` in the top bar; the in-bezel presence orb keeps transcript closed by default.
- **Android LiveActivity**: language remains selected from setup/`LangPrefs`; the Live surface is an orb strip with transcript off by default.
- Default: device/browser locale → catalog; else `en-US`.
- Switch updates STT + TTS immediately (no restart). Field `language` on `/voice/speak`, `/voice/turn`, `/voice/live`.
- Catalog: `app/languages.py` · `GET /voice/languages`.

## Latency (cloud — measured 2026-09-20 ~23:02 IST)

| Call | Lang | Provider / voice | TTS ms |
|------|------|------------------|--------|
| `/voice/speak` "Hello from Strlix…" | en-US | Azure JennyNeural | **411** |
| `/voice/speak` नमस्ते… | hi-IN | Azure SwaraNeural | **426** |
| `/voice/turn` "Say hi…" | en-US | Azure JennyNeural | **243** (+ LLM) |
| `/voice/turn` नमस्ते बोलो | hi-IN | Azure SwaraNeural | **503** (+ LLM) |
| Polly backup synth (direct) | en-US Joanna | Polly neural | ~322 |
| Polly backup synth (direct) | hi-IN Kajal | Polly neural | ~258 |

Voice quality: Azure neural is clear and natural for EN/HI; Polly neural backup is comparable for short phrases. Edge remains available if both clouds fail.

## Routing

```
Mic: laptop Azure Speech duplex PCM (Web Speech / phone SpeechRecognizer fallback)
  → POST /voice/turn (+ language)
  → Azure OpenAI chat
  → Host TTS: Azure Speech → AWS Polly → edge-tts
  → laptop WebAudio
Phone AudioTrack: never for assistant TTS · scrcpy --no-audio
```

## Provision notes

- Script: `scripts/provision-azure-speech.sh` (RG **rg-zevi-cloudphone** only; never phonecodex-*).
- F0 unavailable (subscription already has a free Speech account elsewhere) → created **S0**.
- Keys in `.env` (`chmod 600`); never printed to chat.
- Canonical TTS URL: `https://{region}.tts.speech.microsoft.com/cognitiveservices/v1` (cognitive `api.cognitive.microsoft.com/.../cognitiveservices/v1` returns 404 — code prefers region host).
- AWS Polly + Transcribe API reachable with `~/.aws/credentials` (account 787235610343, us-east-1). Azure Speech is the active host streaming STT path.

## Open issues

- Host streaming STT is wired at `/ws/stt` with the Azure Speech SDK and `speech-zevi-strlix`; browser Web Speech / Android SpeechRecognizer remain fallbacks when the SDK or credentials are unavailable.
- Emulator mic often missing; prefer laptop Live.
- Energy-VAD barge-in ships; Azure continuous recognition now receives 16 kHz mono PCM over the browser WebSocket.
- Azure Speech is **S0** (paid) because F0 quota already used on another Speech account in the subscription.

## Screenshots

- `demo/live-voice-phone.png` — LiveActivity with Language spinner
- `demo/live-voice-chat-chip.png` — Live chip on chat
