# NAANG Phone Bridge — Magisk module

This is the Android-side privileged/local component.

It binds only to 127.0.0.1:8765 and is not an internet-facing root service.

Typed operations include device.info, packages.list, process.list, system.logcat, app.launch, app.stop, ui.tap, ui.swipe, ui.keyevent, ui.text, fs.list and policy.test.

The module expects a private token at /data/adb/naang_phone_bridge/token. Create that token locally on the device.

The AccessibilityService APK remains a separate Android component for semantic UI-tree inspection. This Magisk module is the privileged transport/executor layer.
