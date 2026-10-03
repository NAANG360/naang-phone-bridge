#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
OUT="$ROOT/dist"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$OUT" "$TMP/naang-phone-bridge/bridge"
cp "$ROOT/magisk/module.prop" "$TMP/naang-phone-bridge/"
cp "$ROOT/magisk/service.sh" "$TMP/naang-phone-bridge/"
cp "$ROOT/magisk/post-fs-data.sh" "$TMP/naang-phone-bridge/"
cp "$ROOT/bridge/phone_bridge.py" "$TMP/naang-phone-bridge/bridge/"
cp "$ROOT/magisk/phone_bridge.py" "$TMP/naang-phone-bridge/"
( cd "$TMP/naang-phone-bridge" && zip -qr "$OUT/naang-phone-bridge-magisk.zip" . )
echo "$OUT/naang-phone-bridge-magisk.zip"
