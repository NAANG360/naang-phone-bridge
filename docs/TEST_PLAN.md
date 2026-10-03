# Test plan

## Local bridge

1. Start the bridge with a non-empty bridge token.
2. Verify unauthenticated requests fail.
3. Verify authenticated JSON-RPC requests return structured responses.
4. Verify oversized request bodies are rejected.
5. Verify command timeouts are bounded.
6. Verify destructive-command policy rejects the documented patterns.
7. Verify filesystem access is restricted to the configured safe prefixes.
8. Verify audit records are written locally.

## Relay

1. Verify missing ADMIN_TOKEN/DEVICE_TOKEN prevents startup.
2. Verify unauthorized API requests fail.
3. Verify a device can register only with its device credential.
4. Verify requests expire instead of waiting forever.
5. Verify disconnected devices are removed.

## Production gate

Do not deploy until TLS, rate limiting, credential rotation, device identity, request expiry, and connector authentication are configured.
