#!/usr/bin/env bash
set -euo pipefail
ROOT=/workspace/zevi-cloudphone/demo/cloud-phone-market
SOL="$ROOT/claude-solutions"
SPLIT="$ROOT/_mistakes_split"
LOG="$ROOT/_claude_loop.log"
CLAUDE=/home/box/.local/bin/claude
mkdir -p "$SOL"
: > "$LOG"
while read -r MID; do
  [ -z "$MID" ] && continue
  OUT="$SOL/${MID}.md"
  if [ -f "$OUT" ] && [ -s "$OUT" ]; then
    echo "SKIP $MID" | tee -a "$LOG"
    continue
  fi
  BODY=$(cat "$SPLIT/${MID}.md")
  PROMPT=$(cat <<EOF
You are designing Strlix cloud Android marketplace UI (phone-first, AI inside the phone, not outside chat).
Read this competitor MISTAKE and propose a CONCRETE Strlix solution.

$BODY

Respond in markdown with exactly these sections:
## Mistake restated
## Strlix solution (concrete UX + IA)
## File plan (paths under /workspace/zevi-cloudphone/, prefer web-market/ + reuse desktop-api :8789 stream)
## Android 7+ / graceful degradation notes
## Payment notes (only if relevant; test-mode Stripe/Razorpay stub, no real charges)
## Acceptance criteria (3-5 bullets)

Be specific. No fluff. Do not invent competitor pricing. Keep under 600 words.
EOF
)
  echo "RUN $MID $(date -Iseconds)" | tee -a "$LOG"
  # stdin from /dev/null; non-interactive print
  if "$CLAUDE" -p "$PROMPT" --bare --effort low </dev/null >"$OUT.tmp" 2>"$SOL/${MID}.err"; then
    {
      echo "# Claude solution — $MID"
      echo
      echo "SOURCE: claude-cli"
      echo "GENERATED: $(date -Iseconds)"
      echo
      cat "$OUT.tmp"
    } > "$OUT"
    rm -f "$OUT.tmp"
    echo "OK $MID ($(wc -c < "$OUT") bytes)" | tee -a "$LOG"
  else
    echo "FAIL $MID" | tee -a "$LOG"
    {
      echo "# Claude solution — $MID"
      echo
      echo "SOURCE: fallback (claude-cli failed)"
      echo "GENERATED: $(date -Iseconds)"
      echo
      echo "## Mistake restated"
      echo "$BODY" | head -20
      echo
      echo "## Strlix solution (concrete UX + IA)"
      echo "See CLAUDE-SOLUTION.md rollup / implementer judgment — Claude CLI failed for this id. Error:"
      echo '```'
      tail -30 "$SOL/${MID}.err" 2>/dev/null || true
      echo '```'
    } > "$OUT"
  fi
  sleep 1
done < "$ROOT/_mistake_ids.txt"
echo "DONE $(date -Iseconds)" | tee -a "$LOG"
