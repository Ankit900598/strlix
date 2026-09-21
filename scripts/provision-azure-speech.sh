#!/usr/bin/env bash
# Create Azure Speech in rg-zevi-cloudphone ONLY (requires az login).
# Does NOT touch phonecodex-* or other RGs. Does NOT sign out.
set -euo pipefail
SUB="${AZURE_SUBSCRIPTION_ID:-a3dc5296-f948-427e-8656-c6bc52afee21}"
RG=rg-zevi-cloudphone
NAME="${AZURE_SPEECH_NAME:-speech-zevi-strlix}"
LOC="${AZURE_SPEECH_LOCATION:-eastus2}"

echo "Creating/fetching Speech resource $NAME in $RG (subscription $SUB, location $LOC)…"
az account set --subscription "$SUB"

# Safety: refuse if RG is wrong
RG_CHECK=$(az group show -n "$RG" --query name -o tsv)
[[ "$RG_CHECK" == "rg-zevi-cloudphone" ]] || { echo "Refusing: unexpected RG $RG_CHECK"; exit 1; }

if ! az cognitiveservices account show -g "$RG" -n "$NAME" &>/dev/null; then
  # F0 free tier first; fall back to S0 if F0 unavailable in region
  if ! az cognitiveservices account create \
      -g "$RG" -n "$NAME" -l "$LOC" \
      --kind SpeechServices --sku F0 \
      --yes 2>/tmp/speech-create.err; then
    echo "F0 create failed; trying S0…"
    cat /tmp/speech-create.err >&2 || true
    az cognitiveservices account create \
      -g "$RG" -n "$NAME" -l "$LOC" \
      --kind SpeechServices --sku S0 \
      --yes
  fi
fi

KEY=$(az cognitiveservices account keys list -g "$RG" -n "$NAME" --query key1 -o tsv)
ENDPOINT=$(az cognitiveservices account show -g "$RG" -n "$NAME" --query properties.endpoint -o tsv)
REGION=$(az cognitiveservices account show -g "$RG" -n "$NAME" --query location -o tsv)

ENV=/workspace/zevi-cloudphone/.env
# Preserve non-speech keys; replace speech + TTS provider lines
grep -vE '^(AZURE_SPEECH_|VOICE_TTS_PROVIDER=|VOICE_EDGE_VOICE=)' "$ENV" > /tmp/strlix.env.$$ || true
cat /tmp/strlix.env.$$ > "$ENV"
cat >> "$ENV" <<E
VOICE_TTS_PROVIDER=auto
VOICE_EDGE_VOICE=en-US-JennyNeural
AZURE_SPEECH_KEY=${KEY}
AZURE_SPEECH_ENDPOINT=${ENDPOINT}
AZURE_SPEECH_REGION=${REGION}
AZURE_SPEECH_VOICE=en-US-JennyNeural
E
chmod 600 "$ENV"
rm -f /tmp/strlix.env.$$ /tmp/speech-create.err
echo "Wrote Azure Speech into .env (chmod 600) — restart pilot. Endpoint=$ENDPOINT Region=$REGION"
# Never print the key
echo "KEY_SET=yes (length=${#KEY})"
