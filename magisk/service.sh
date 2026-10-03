#!/system/bin/sh
MODDIR="$(dirname "$0")"

while [ "$(getprop sys.boot_completed)" != "1" ]; do
  sleep 2
done

PYTHON="${NAANG_PYTHON:-/data/data/com.termux/files/usr/bin/python}"
[ -x "$PYTHON" ] || exit 0
[ -f "$MODDIR/phone_bridge.py" ] || exit 0

mkdir -p /data/local/tmp /data/adb/naang_phone_bridge
chmod 700 "$MODDIR/phone_bridge.py"

export BRIDGE_HOST=127.0.0.1
export BRIDGE_PORT=8765
export BRIDGE_TOKEN_FILE=/data/adb/naang_phone_bridge/token

exec "$PYTHON" "$MODDIR/phone_bridge.py" >>/data/local/tmp/naang_bridge.log 2>&1
