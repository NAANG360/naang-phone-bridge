# NAANG Phone Bridge

A private root-capable Android bridge intended to expose safe phone-control tools to ChatGPT.

## Current prototype

- authenticated JSON-RPC over HTTP
- root execution through `su`
- device information
- logcat
- package listing
- filesystem read/list
- on-device destructive-command blocking
- audit log
- request/output/time limits

Default bind: 127.0.0.1:8765.

Set BRIDGE_TOKEN before starting. Do not expose the bridge directly to the public internet.

The long-term architecture is ChatGPT tool/connector -> authenticated bridge -> Magisk/root -> Android.

The safety policy is enforced on the phone, so a compromised remote caller cannot simply disable it.