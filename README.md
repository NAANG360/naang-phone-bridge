# NAANG Phone Bridge

Private Android root bridge for a future ChatGPT connector.

## Prototype
- Authenticated JSON-RPC over localhost
- Root execution through su
- Device information
- Logcat
- Package listing
- Filesystem read/list
- On-device destructive-command blocking
- Audit log
- Request/output/time limits
- Magisk module packaging script
- Basic policy tests

## Build
Run Python unittest discovery, then run build_magisk_zip.sh. The resulting module is written to dist/.

## Important
The bridge intentionally binds to 127.0.0.1. Do not expose port 8765 directly to the Internet. Remote ChatGPT control needs an authenticated outbound relay/tunnel.

See docs/SECURITY.md and docs/CONNECTOR.md.
