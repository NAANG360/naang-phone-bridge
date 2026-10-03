#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="$ROOT/dist"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$OUT" "$TMP/naang-phone-bridge"
cp "$ROOT/magisk/module.prop" "$TMP/naang-phone-bridge/"
cp "$ROOT/magisk/service.sh" "$TMP/naang-phone-bridge/"
cp "$ROOT/magisk/phone_bridge.py" "$TMP/naang-phone-bridge/"
cp "$ROOT/magisk/README.md" "$TMP/naang-phone-bridge/"

chmod 700 "$TMP/naang-phone-bridge/service.sh" "$TMP/naang-phone-bridge/phone_bridge.py"

(
  cd "$TMP/naang-phone-bridge"
  zip -qr "$OUT/naang-phone-bridge-magisk.zip" .
)

echo "$OUT/naang-phone-bridge-magisk.zip"
