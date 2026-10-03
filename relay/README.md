# NAANG outbound relay

Transport layer between a future MCP endpoint and the phone bridge.

- Phone initiates the outbound connection.
- Device connection requires DEVICE_TOKEN.
- API calls require a separate ADMIN_TOKEN.
- Relay forwards typed bridge RPC methods rather than granting root directly.
- Secrets are deployment-only and never committed.

This is a transport skeleton, not the final production MCP endpoint. Production work still needs TLS at the edge, device-specific credentials, replay/request expiry, rate limits, persistent device registry, and a proper MCP adapter.
