#!/system/bin/sh
MODDIR=${0%/*}
LOG=/data/local/tmp/naang_bridge.log
STATE=/data/adb/naang_phone_bridge
TOKEN="$STATE/token"

mkdir -p "$STATE" /data/local/tmp
chmod 700 "$STATE" "$MODDIR"

log() { echo "[naang] $*" >> "$LOG"; }

log "service start"

if [ ! -s "$TOKEN" ]; then
  umask 077
  head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \\n' > "$TOKEN"
  chmod 600 "$TOKEN"
  log "generated device token"
fi

while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 2; done

MAGISK="$(command -v magisk 2>/dev/null)"
if [ -z "$MAGISK" ] || [ ! -x "$MAGISK" ]; then
  for p in /sbin/magisk /debug_ramdisk/magisk /data/adb/magisk/magisk; do
    if [ -x "$p" ]; then MAGISK="$p"; break; fi
  done
fi

if [ -z "$MAGISK" ] || [ ! -x "$MAGISK" ]; then
  log "ERROR: Magisk binary not found"
  exit 0
fi

export BRIDGE_HOST=127.0.0.1
export BRIDGE_PORT=8765
export BRIDGE_TOKEN_FILE="$TOKEN"
chmod 700 "$MODDIR/phone_bridge.py"

while true; do
  TERMUX_PID="$(pidof com.termux 2>/dev/null | awk '{print $1}')"
  if [ -z "$TERMUX_PID" ]; then
    log "Termux process not running; open Termux once, then bridge will start"
    sleep 5
    continue
  fi

  log "using Termux mount namespace pid=$TERMUX_PID"
  "$MAGISK" su --target "$TERMUX_PID" --shell /system/bin/sh -c     "export BRIDGE_HOST=127.0.0.1; export BRIDGE_PORT=8765; export BRIDGE_TOKEN_FILE='$TOKEN'; export PATH=/data/data/com.termux/files/usr/bin:/system/bin:/system/xbin; export LD_PRELOAD=/data/data/com.termux/files/usr/lib/libtermux-exec.so; exec /data/data/com.termux/files/usr/bin/python '$MODDIR/phone_bridge.py'"     >>"$LOG" 2>&1
  rc=$?
  log "bridge exited rc=$rc; retrying in 5s"
  sleep 5
done
