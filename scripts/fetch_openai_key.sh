#!/usr/bin/env bash
# Requires: az login. Writes key to .env (chmod 600). Never echoes the key.
set -euo pipefail
cd /workspace/zevi-cloudphone
SUB="${AZURE_SUBSCRIPTION_ID:-a3dc5296-f948-427e-8656-c6bc52afee21}"
RG=rg-zevi-cloudphone
NAME=oai-zevi-phonepilot
az account set --subscription "$SUB"
KEY=$(az cognitiveservices account keys list -g "$RG" -n "$NAME" --query key1 -o tsv)
ENDPOINT=$(az cognitiveservices account show -g "$RG" -n "$NAME" --query properties.endpoint -o tsv)
umask 077
cat > .env <<EOF
AZURE_OPENAI_ENDPOINT=${ENDPOINT}
AZURE_OPENAI_API_KEY=${KEY}
AZURE_OPENAI_DEPLOYMENT=gpt-5.6-sol
AZURE_OPENAI_API_VERSION=2024-12-01-preview
ADB_SERIAL=127.0.0.1:5555
SSH_HOST=20.115.117.71
SSH_USER=azureuser
SSH_KEY=/home/box/Downloads/vm-zevi-cloudphone-key.pem
PILOT_HOST=0.0.0.0
PILOT_PORT=8787
EOF
chmod 600 .env
echo "Wrote .env (key length ${#KEY}, endpoint $ENDPOINT)"
