#!/usr/bin/env bash
set -euo pipefail
KEY="${SSH_KEY:-/home/box/Downloads/vm-zevi-cloudphone-key.pem}"
HOST="${SSH_HOST:-20.115.117.71}"
ssh -o StrictHostKeyChecking=no -i "$KEY" azureuser@"$HOST" 'bash -s' <<'REMOTE'
set -e
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
export ANDROID_HOME=/opt/android-sdk
export PATH=$JAVA_HOME/bin:$PATH:$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools
sudo chmod 666 /dev/kvm || true
if ! pgrep -f qemu-system >/dev/null; then
  # Do not pass -no-audio. The Opus "Decoding error" was a flags=0 OpusHead
  # packet, not a missing HAL. A null Pulse sink keeps guest playback audible
  # to scrcpy without host speakers.
  if command -v pulseaudio >/dev/null 2>&1; then
    pulseaudio --start || true
    pactl load-module module-null-sink sink_name=strlix rate=48000 channels=2 >/dev/null 2>&1 || true
    export PULSE_SINK=strlix
  fi
  nohup emulator -avd strlix -no-window -no-boot-anim -gpu swiftshader_indirect -accel on -memory 3072 -cores 2 -port 5554 >/tmp/emulator.log 2>&1 &
  echo started $!
else
  echo already running
fi
for i in $(seq 1 60); do
  b=$(adb -e shell getprop sys.boot_completed 2>/dev/null | tr -d "\r")
  echo "boot=$b"
  [ "$b" = "1" ] && exit 0
  sleep 3
done
exit 1
REMOTE
