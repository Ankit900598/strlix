#!/usr/bin/env bash
ROOT=/workspace/zevi-cloudphone/demo/cloud-phone-market
while true; do
  n=$(ls "$ROOT/claude-solutions"/M*.md 2>/dev/null | wc -l)
  done_flag=$(tail -1 "$ROOT/_claude_loop.log" 2>/dev/null | grep -c '^DONE' || true)
  echo "$(date -Iseconds) solutions=$n" >> "$ROOT/_watch.log"
  if grep -q '^DONE' "$ROOT/_claude_loop.log" 2>/dev/null; then
    python3 - << 'PY'
from pathlib import Path
root=Path('/workspace/zevi-cloudphone/demo/cloud-phone-market')
sol=root/'claude-solutions'
completed=[p for p in sol.glob('M*.md') if p.stat().st_size>100]
# append completion note
status=root/'IMPLEMENTATION-STATUS.md'
t=status.read_text()
note=f"\n\n## Claude loop completed\n- Solutions on disk: {len(completed)}\n- Re-run verification script recommended.\n- Finished: see `_claude_loop.log`\n"
if 'Claude loop completed' not in t:
    status.write_text(t+note)
print('loop complete', len(completed))
PY
    break
  fi
  sleep 60
done
