#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="$ROOT/dist"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$OUT" "$TMP/META-INF/com/google/android"

cp "$ROOT/magisk/module.prop" "$TMP/"
cp "$ROOT/magisk/service.sh" "$TMP/"
cp "$ROOT/magisk/phone_bridge.py" "$TMP/"
cp "$ROOT/relay/device_client.py" "$TMP/device_client.py"
cp "$ROOT/magisk/README.md" "$TMP/"
cp "$ROOT/META-INF/com/google/android/update-binary" "$TMP/META-INF/com/google/android/"
cp "$ROOT/META-INF/com/google/android/updater-script" "$TMP/META-INF/com/google/android/"

chmod 700 "$TMP/service.sh" "$TMP/phone_bridge.py" "$TMP/device_client.py" "$TMP/META-INF/com/google/android/update-binary"

rm -f "$OUT/naang-phone-bridge-magisk.zip"
(
  cd "$TMP"
  zip -9qr "$OUT/naang-phone-bridge-magisk.zip" .
)

echo "$OUT/naang-phone-bridge-magisk.zip"
