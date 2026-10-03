#!/system/bin/sh
MODDIR=${0%/*}
LOG=/data/local/tmp/naang_bridge.log
STATE=/data/adb/naang_phone_bridge
TOKEN="$STATE/token"

mkdir -p "$STATE" /data/local/tmp
chmod 700 "$STATE" "$MODDIR"

log() {
  echo "[naang] $*" >> "$LOG"
}

log "service start"

if [ ! -s "$TOKEN" ]; then
  umask 077
  head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \\n' > "$TOKEN"
  chmod 600 "$TOKEN"
  log "generated device token"
fi

resetprop -w sys.boot_completed 0 >/dev/null 2>&1 || {
  while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 2; done
}

PYTHON="${NAANG_PYTHON:-}"
if [ -z "$PYTHON" ]; then
  for p in \
    /data/data/com.termux/files/usr/bin/python \
    /data/data/com.termux/files/usr/bin/python3 \
    /data/data/com.termux/files/usr/bin/python3.12 \
    /data/data/com.termux/files/usr/bin/python3.13 \
    /data/data/com.termux/files/usr/bin/python3.14; do
    if [ -x "$p" ]; then PYTHON="$p"; break; fi
  done
fi

if [ -z "$PYTHON" ] || [ ! -x "$PYTHON" ]; then
  log "ERROR: no Termux Python found"
  log "Install Python in Termux with: pkg install python"
  exit 0
fi

chmod 700 "$MODDIR/phone_bridge.py"
export BRIDGE_HOST=127.0.0.1
export BRIDGE_PORT=8765
export BRIDGE_TOKEN_FILE="$TOKEN"

log "starting bridge with $PYTHON"
while true; do
  "$PYTHON" "$MODDIR/phone_bridge.py" >>"$LOG" 2>&1 &
  PID=$!
  echo "$PID" > "$STATE/pid"
  wait "$PID"
  rc=$?
  rm -f "$STATE/pid"
  log "bridge exited rc=$rc; restarting in 5s"
  sleep 5
done
