#!/usr/bin/env bash
# Read current trycloudflare URL from VM and print the streamUrl line to paste / sed.
set -euo pipefail
KEY="${VM_KEY:-$HOME/Downloads/vm-zevi-cloudphone-key.pem}"
VM="${VM_SSH:-azureuser@20.115.117.71}"
URL=$(ssh -i "$KEY" -o StrictHostKeyChecking=no "$VM" 'cat ~/strlix/demo/public-desktop-url.txt')
echo "streamUrl: \"$URL\""
echo "Update web-market/index.html and rebuild market-api image."
