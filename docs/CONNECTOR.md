# Future ChatGPT connector

The bridge speaks authenticated JSON-RPC over localhost. ChatGPT cannot directly reach a phone-bound localhost socket.

Intended topology:

ChatGPT tool call -> HTTPS/MCP relay -> authenticated outbound phone connection -> localhost bridge -> root policy -> Android

The phone should initiate the outbound connection, avoiding an exposed listening port.

Typed connector tools should include device_info, list_packages, list_processes, read_logcat, read_file, list_directory, launch_app, stop_app, and capture_screenshot. Arbitrary shell should be a separately gated capability.

Authentication should use a per-device secret, short-lived request IDs/timestamps, replay protection, and server-side rate limits. Never put the device secret in GitHub.
