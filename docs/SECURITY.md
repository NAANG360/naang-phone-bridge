# Security model

The phone is the trust anchor. The bridge must never rely on a remote caller to enforce safety.

## Current protections
- Binds to localhost by default.
- Requires a bearer token when enabled.
- Refuses to start without BRIDGE_TOKEN.
- Caps request size, command timeout, and response size.
- Blocks a set of obviously destructive root commands.
- Writes an audit record for every RPC request.
- Uses named RPC methods instead of treating every operation as safe.

## Remote transport
Do not expose TCP/8765 directly to the Internet. A future connector should use an outbound authenticated tunnel or relay with TLS, device identity, request expiry, replay protection, and per-device credentials.

## High-risk operations
Package installation, app launch/stop, file writes, rebooting, boot-state changes, and arbitrary root shell should be separate capabilities. They must not silently become generic remote shell access.

## Filesystem privacy
Remote filesystem reads should use an allowlist of safe roots. Credential stores, browser profiles, private keys, tokens, and Android keystore material should be denied by default.

## Audit
/data/local/tmp/naang_bridge_audit.log records JSONL audit events. Future versions should rotate logs and make remote export explicit.
