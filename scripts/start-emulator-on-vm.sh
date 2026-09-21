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
  nohup emulator -avd strlix -no-window -no-audio -no-boot-anim -gpu swiftshader_indirect -accel on -memory 3072 -cores 2 -port 5554 >/tmp/emulator.log 2>&1 &
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
