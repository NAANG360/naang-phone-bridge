#!/usr/bin/env python3
import base64
import json
import os
import re
import subprocess
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = os.getenv("BRIDGE_HOST", "127.0.0.1")
PORT = int(os.getenv("BRIDGE_PORT", "8765"))
TOKEN_FILE = os.getenv("BRIDGE_TOKEN_FILE", "/data/adb/naang_phone_bridge/token")
MAX_BODY = 256 * 1024
MAX_TEXT = 524288
MAX_FILE = 524288
MAX_SCREENSHOT = 8 * 1024 * 1024

def read_token():
    try:
        with open(TOKEN_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""

def run(args, timeout=30):
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       text=True, timeout=max(1, min(int(timeout), 120)))
    return {"code": p.returncode, "stdout": p.stdout[-MAX_TEXT:], "stderr": p.stderr[-MAX_TEXT:]}

PKG_RE = re.compile(r"^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+$")
SAFE_PATH_PREFIXES = ("/sdcard/", "/storage/emulated/0/", "/data/local/tmp/")

def pkg(v):
    if not isinstance(v, str) or not PKG_RE.fullmatch(v):
        raise ValueError("invalid package")
    return v

def integer(v, lo, hi, name):
    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
        raise ValueError("invalid " + name)
    return v

def safe_path(v):
    if not isinstance(v, str) or len(v) > 1024 or not any(v.startswith(p) for p in SAFE_PATH_PREFIXES):
        raise ValueError("path outside permitted locations")
    if "\x00" in v:
        raise ValueError("invalid path")
    return v

def parse_current_activity(line):
    m = re.search(r"(?:mCurrentFocus=|mResumedActivity:).*?\bu\d+\s+([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+)/([^\s}]+)", line)
    if not m:
        return None
    return {"package": m.group(1), "activity": m.group(2)}

def current_activity():
    r = run(["dumpsys", "activity", "activities"], timeout=10)
    for line in r["stdout"].splitlines():
        parsed = parse_current_activity(line)
        if parsed:
            return parsed
    return {"package": None, "activity": None}

def screenshot(include_base64=False):
    p = subprocess.run(["screencap", "-p"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.decode("utf-8", "replace")[:4096] or "screencap failed")
    if len(p.stdout) > MAX_SCREENSHOT:
        raise ValueError("screenshot too large")
    out = {"mime": "image/png", "bytes": len(p.stdout)}
    if include_base64:
        out["base64"] = base64.b64encode(p.stdout).decode("ascii")
    return out

def ui_dump():
    fd, path = tempfile.mkstemp(prefix="naang_ui_", suffix=".xml", dir="/data/local/tmp")
    os.close(fd)
    try:
        r = run(["uiautomator", "dump", "--compressed", path], timeout=20)
        if r["code"] != 0:
            raise RuntimeError(r["stderr"] or r["stdout"] or "uiautomator dump failed")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = f.read(MAX_TEXT)
        return {"xml": data, "truncated": len(data) >= MAX_TEXT}
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass

def file_read(path, max_bytes=MAX_FILE):
    path = safe_path(path)
    n = integer(max_bytes, 1, MAX_FILE, "max_bytes")
    with open(path, "rb") as f:
        data = f.read(n + 1)
    return {"path": path, "bytes": min(len(data), n), "truncated": len(data) > n,
            "encoding": "utf-8", "content": data[:n].decode("utf-8", "replace")}

def call(method, p):
    if method == "bridge.status":
        return {"uid": os.getuid(), "pid": os.getpid(), "host": HOST, "port": PORT,
                "token_configured": bool(read_token()), "python": os.sys.version.split()[0]}
    if method == "device.info":
        keys = ("ro.product.manufacturer", "ro.product.model", "ro.build.version.release",
                "ro.build.version.sdk", "ro.product.cpu.abi")
        return {k: subprocess.run(["getprop", k], capture_output=True, text=True).stdout.strip() for k in keys}
    if method == "packages.list":
        return run(["cmd", "package", "list", "packages"])
    if method == "process.list":
        return run(["ps", "-A"])
    if method == "system.logcat":
        return run(["logcat", "-d", "-t", str(integer(p.get("lines", 200), 1, 2000, "lines"))])
    if method == "app.launch":
        return run(["monkey", "-p", pkg(p.get("package")), "-c", "android.intent.category.LAUNCHER", "1"])
    if method == "app.stop":
        return run(["am", "force-stop", pkg(p.get("package"))])
    if method == "app.current":
        return current_activity()
    if method == "ui.tap":
        return run(["input", "tap", str(integer(p.get("x"), 0, 10000, "x")),
                    str(integer(p.get("y"), 0, 10000, "y"))])
    if method == "ui.swipe":
        a = [integer(p.get(k), 0, 10000, k) for k in ("x1", "y1", "x2", "y2")]
        return run(["input", "swipe", *(str(x) for x in a),
                    str(integer(p.get("duration_ms", 300), 1, 10000, "duration_ms"))])
    if method == "ui.keyevent":
        return run(["input", "keyevent", str(integer(p.get("keycode"), 0, 300, "keycode"))])
    if method == "ui.back":
        return run(["input", "keyevent", "4"])
    if method == "ui.home":
        return run(["input", "keyevent", "3"])
    if method == "ui.recents":
        return run(["input", "keyevent", "187"])
    if method == "ui.text":
        t = p.get("text")
        if not isinstance(t, str) or len(t) > 4096:
            raise ValueError("invalid text")
        encoded = t.replace("%", "%25").replace(" ", "%s").replace("&", "\&")
        return run(["input", "text", encoded])
    if method == "ui.dump":
        return ui_dump()
    if method == "ui.screenshot":
        include_base64 = p.get("include_base64", False)
        if not isinstance(include_base64, bool):
            raise ValueError("invalid include_base64")
        return screenshot(include_base64)
    if method == "fs.list":
        return run(["ls", "-la", safe_path(p.get("path"))])
    if method == "fs.read":
        return file_read(p.get("path"), p.get("max_bytes", MAX_FILE))
    if method == "policy.test":
        c = p.get("command")
        if not isinstance(c, str) or len(c) > 8192:
            raise ValueError("invalid command")
        blocked = [
            r"rm\s+-rf\s+/(?:\s|$)", r"mkfs(?:\.[A-Za-z0-9_-]+)?\s+/dev/block",
            r"dd\s+.*of=/dev/block", r"fastboot\s+(?:flash|erase|format)",
            r"parted\s+/dev/block", r"sgdisk\s+.*(?:zap|delete)",
            r"shred\s+.*?/dev/block", r"reboot\s+(?:bootloader|edl)",
            r"factory.?reset", r"wipe\s+(?:data|userdata)"
        ]
        return {"allowed": not any(re.search(x, c, re.I) for x in blocked)}
    raise ValueError("unknown method")

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send_json(self, status, obj):
        raw = json.dumps(obj, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/health":
            return self.send_json(200, {"ok": True, "service": "naang_phone_bridge"})
        return self.send_json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if self.path != "/rpc":
            return self.send_json(404, {"ok": False, "error": "not found"})
        if self.headers.get("Authorization") != "Bearer " + read_token():
            return self.send_json(401, {"ok": False, "error": "unauthorized"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            if n < 1 or n > MAX_BODY:
                raise ValueError("invalid body size")
            body = json.loads(self.rfile.read(n))
            if not isinstance(body, dict) or not isinstance(body.get("method"), str):
                raise ValueError("invalid request")
            params = body.get("params") or {}
            if not isinstance(params, dict):
                raise ValueError("invalid request")
            self.send_json(200, {"ok": True, "result": call(body["method"], params)})
        except Exception as e:
            self.send_json(400, {"ok": False, "error": str(e)})

if __name__ == "__main__":
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
