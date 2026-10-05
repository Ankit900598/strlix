#!/bin/sh
# perf1: raise the initial congestion/receive window on the default route so a
# new connection can send the first H.264 key frame (~16 KB) and the gzipped
# viewer in one flight instead of two (initcwnd 10 ≈ 14 KB). Idempotent.
set -eu
R=$(ip route show default | head -1 | sed -E 's/ (initcwnd|initrwnd) [0-9]+//g')
[ -n "$R" ] || exit 0
# shellcheck disable=SC2086
ip route change $R initcwnd ${INITCWND:-32} initrwnd ${INITRWND:-32}
ip route show default | head -1
