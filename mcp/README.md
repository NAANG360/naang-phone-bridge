# NAANG Phone MCP

Remote-facing typed MCP adapter for the phone bridge.

It deliberately exposes typed operations instead of a generic remote shell:

- device information
- package/process inspection
- logcat
- permitted filesystem inspection
- app launch/stop
- local policy testing

Required environment:

- MCP_TOKEN
- RELAY_URL
- ADMIN_TOKEN
- DEVICE_ID

The Android bridge remains the policy authority. Never expose port 8765 directly to the Internet.
