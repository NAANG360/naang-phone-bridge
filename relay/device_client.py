#!/usr/bin/env python3
"""Outbound device transport for the typed localhost Android bridge."""
import http.client
import json
import os
import socket
import ssl
import time

RELAY_HOST = os.getenv("RELAY_HOST")
RELAY_PORT = int(os.getenv("RELAY_PORT", "443"))
RELAY_PATH = os.getenv("RELAY_PATH", "/device")
DEVICE_TOKEN = os.getenv("DEVICE_TOKEN")
DEVICE_ID = os.getenv("DEVICE_ID")
BRIDGE_HOST = os.getenv("BRIDGE_HOST", "127.0.0.1")
BRIDGE_PORT = int(os.getenv("BRIDGE_PORT", "8765"))
BRIDGE_TOKEN_FILE = os.getenv("BRIDGE_TOKEN_FILE", "/data/adb/naang_phone_bridge/token")

ALLOWED_METHODS = frozenset({
    "bridge.status", "device.info", "packages.list", "process.list", "system.logcat",
    "app.launch", "app.stop", "app.current",
    "ui.tap", "ui.swipe", "ui.keyevent", "ui.back", "ui.home", "ui.recents",
    "ui.text", "ui.dump", "ui.screenshot",
    "fs.list", "fs.read", "policy.test",
})


def is_allowed_method(method):
    return isinstance(method, str) and method in ALLOWED_METHODS


def read_bridge_token():
    with open(BRIDGE_TOKEN_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def call_local_bridge(method, params):
    if not is_allowed_method(method):
        raise ValueError("method is not allowed")
    token = read_bridge_token()
    body = json.dumps({"method": method, "params": params or {}}).encode("utf-8")
    conn = http.client.HTTPConnection(BRIDGE_HOST, BRIDGE_PORT, timeout=35)
    try:
        conn.request("POST", "/rpc", body=body, headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "Content-Length": str(len(body)),
        })
        response = conn.getresponse()
        raw = response.read(1024 * 1024)
        if response.status != 200:
            raise RuntimeError("bridge HTTP %d: %s" % (response.status, raw.decode("utf-8", "replace")[:4096]))
        result = json.loads(raw.decode("utf-8"))
        if not result.get("ok"):
            raise RuntimeError(result.get("error", "bridge request failed"))
        return result.get("result")
    finally:
        conn.close()


def connect_relay():
    if not RELAY_HOST or not DEVICE_TOKEN or not DEVICE_ID:
        raise RuntimeError("RELAY_HOST, DEVICE_TOKEN and DEVICE_ID are required")
    raw = socket.create_connection((RELAY_HOST, RELAY_PORT), timeout=20)
    s = ssl.create_default_context().wrap_socket(raw, server_hostname=RELAY_HOST)
    request = (
        "GET %s HTTP/1.1\r\n"
        "Host: %s\r\n"
        "Authorization: Bearer %s\r\n"
        "Upgrade: naang-device\r\n"
        "Connection: Upgrade\r\n\r\n"
    ) % (RELAY_PATH, RELAY_HOST, DEVICE_TOKEN)
    s.sendall(request.encode("utf-8"))
    header = s.recv(4096)
    if b"101 Switching Protocols" not in header:
        s.close()
        raise RuntimeError("relay upgrade failed")
    s.sendall((json.dumps({"type": "hello", "device": DEVICE_ID}) + "\n").encode("utf-8"))
    return s


def serve_once():
    s = connect_relay()
    buffer = b""
    try:
        while True:
            chunk = s.recv(65536)
            if not chunk:
                raise RuntimeError("relay disconnected")
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line.strip():
                    continue
                message = json.loads(line.decode("utf-8"))
                request_id = message.get("id")
                method = message.get("method")
                params = message.get("params") or {}
                if not request_id or not is_allowed_method(method):
                    response = {"id": request_id, "ok": False, "error": "method is not allowed"}
                else:
                    try:
                        response = {"id": request_id, "ok": True, "result": call_local_bridge(method, params)}
                    except Exception as exc:
                        response = {"id": request_id, "ok": False, "error": str(exc)}
                s.sendall((json.dumps(response, separators=(",", ":")) + "\n").encode("utf-8"))
    finally:
        s.close()


def main():
    while True:
        try:
            serve_once()
        except Exception:
            time.sleep(5)


if __name__ == "__main__":
    main()
