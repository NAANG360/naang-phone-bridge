# NAANG Phone Bridge — Magisk module

This is the Android-side privileged/local component.

It binds only to 127.0.0.1:8765 and is not an internet-facing root service.

Typed operations include device.info, packages.list, process.list, system.logcat, app.launch, app.stop, app.current, ui.tap, ui.swipe, ui.keyevent, ui.back, ui.home, ui.recents, ui.text, ui.dump, ui.screenshot, fs.list, fs.read and policy.test.

The module creates /data/adb/naang_phone_bridge/token with restrictive permissions.

## Optional outbound relay

If /data/adb/naang_phone_bridge/relay.env exists, the service starts the packaged outbound device client inside the Termux mount namespace. The client accepts only the typed methods above and forwards them to localhost:8765; it does not expose a generic remote shell.

Use relay/relay.env.example as the template. Keep the real file mode 600 and never commit its contents.

The AccessibilityService APK remains a separate optional semantic UI component. The Magisk module is the privileged transport/executor layer.
