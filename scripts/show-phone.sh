#!/usr/bin/env bash
set -euo pipefail

SCRCPY="/home/box/.local/scrcpy/scrcpy"
exec "$SCRCPY" \
  --fullscreen \
  --window-title 'Strlix Phone' \
  --max-size 1200 \
  --stay-awake \
  --no-audio \
  -s 127.0.0.1:5555
