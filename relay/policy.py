ALLOWED_METHODS = frozenset({
    "bridge.status", "device.info", "packages.list", "process.list", "system.logcat",
    "app.launch", "app.stop", "app.current",
    "ui.tap", "ui.swipe", "ui.keyevent", "ui.back", "ui.home", "ui.recents",
    "ui.text", "ui.dump", "ui.screenshot",
    "fs.list", "fs.read", "policy.test",
})


def is_allowed_method(method):
    return isinstance(method, str) and method in ALLOWED_METHODS
