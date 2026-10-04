#!/system/bin/sh
MODDIR=${0%/*}
LOG=/data/local/tmp/naang_bridge.log
STATE=/data/adb/naang_phone_bridge
TOKEN="$STATE/token"
RELAY_ENV="$STATE/relay.env"
MAGISK=/debug_ramdisk/magisk

mkdir -p "$STATE" /data/local/tmp
chmod 700 "$STATE" "$MODDIR"
log(){ echo "[naang] $*" >> "$LOG"; }

while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 2; done
if [ ! -s "$TOKEN" ]; then
  umask 077
  head -c 32 /dev/urandom | od -An -tx1 | tr -d ' 
' > "$TOKEN"
  chmod 600 "$TOKEN"
fi

while true; do
  TPID="$(pidof com.termux 2>/dev/null | awk '{print $1}')"
  if [ -z "$TPID" ]; then sleep 5; continue; fi

  if ! ps -A 2>/dev/null | grep -q '[p]hone_bridge.py'; then
    "$MAGISK" su --target "$TPID" --shell /system/bin/sh -c 'export BRIDGE_HOST=127.0.0.1; export BRIDGE_PORT=8765; export BRIDGE_TOKEN_FILE=/data/adb/naang_phone_bridge/token; export PATH=/data/data/com.termux/files/usr/bin:/system/bin:/system/xbin; export LD_PRELOAD=/data/data/com.termux/files/usr/lib/libtermux-exec.so; exec /data/data/com.termux/files/usr/bin/python /data/adb/modules/naang_phone_bridge/phone_bridge.py' >>"$LOG" 2>&1 &
    log "started local bridge"
  fi

  if [ -s "$RELAY_ENV" ] && ! ps -A 2>/dev/null | grep -q '[d]evice_client.py'; then
    "$MAGISK" su --target "$TPID" --shell /system/bin/sh -c 'set -a; . /data/adb/naang_phone_bridge/relay.env; set +a; export BRIDGE_HOST=127.0.0.1; export BRIDGE_PORT=8765; export BRIDGE_TOKEN_FILE=/data/adb/naang_phone_bridge/token; export PATH=/data/data/com.termux/files/usr/bin:/system/bin:/system/xbin; export LD_PRELOAD=/data/data/com.termux/files/usr/lib/libtermux-exec.so; exec /data/data/com.termux/files/usr/bin/python /data/adb/modules/naang_phone_bridge/device_client.py' >>"$LOG" 2>&1 &
    log "started relay client"
  fi
  sleep 5
done
