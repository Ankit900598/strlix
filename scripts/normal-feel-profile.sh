#!/usr/bin/env bash
# Balanced "normal phone" guest profile for the soft-launch emulator.
# Idempotent; safe to re-run after an AVD rebuild. Usage: scripts/normal-feel-profile.sh [serial]
# - Animations 0.5x (gaming profile had them at 0): Launcher Recents / swipe-to-dismiss
#   and Chrome's tab switcher rely on animators; 0.5x keeps transitions short so the
#   encoder isn't flooded but the system behaves like a normal phone.
# - Wider Back-gesture edge (1.6x ≈ 100 px of 1080): through a browser frame the
#   default ~63 px edge is ~20 CSS px, which a phone's own edge gesture eats.
# - Window blurs off: software (swiftshader) blur behind Recents/shade costs
#   100s of ms per frame on this VM and slows every Recents interaction.
# - Gesture navigation stays on (navbar.gestural), like a current Pixel.
set -euo pipefail
S="${1:-${ADB_SERIAL:-emulator-5554}}"
A=(adb -s "$S" shell)
"${A[@]}" settings put global window_animation_scale 0.5
"${A[@]}" settings put global transition_animation_scale 0.5
"${A[@]}" settings put global animator_duration_scale 0.5
"${A[@]}" settings put secure back_gesture_inset_scale_left 1.6
"${A[@]}" settings put secure back_gesture_inset_scale_right 1.6
"${A[@]}" settings put global disable_window_blurs 1
"${A[@]}" cmd overlay enable-exclusive --category com.android.internal.systemui.navbar.gestural >/dev/null 2>&1 || true
for k in "global window_animation_scale" "global transition_animation_scale" "global animator_duration_scale" \
         "secure back_gesture_inset_scale_left" "secure back_gesture_inset_scale_right" "global disable_window_blurs" "secure navigation_mode"; do
  echo "$k = $("${A[@]}" settings get $k | tr -d '\r')"
done
