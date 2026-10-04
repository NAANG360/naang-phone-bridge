#!/usr/bin/env python3
"""Outbound WebSocket device transport for the typed localhost Android bridge."""

import base64
import hashlib
import http.client
import json
import os
import socket
import ssl
import struct
import time


def load_relay_env():
    try:
        with open(
            "/data/adb/naang_phone_bridge/relay.env",
            encoding="utf-8",
        ) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()
    except OSError:
        pass


load_relay_env()

RELAY_HOST = os.getenv("RELAY_HOST")
RELAY_PORT = int(os.getenv("RELAY_PORT", "443"))
RELAY_PATH = os.getenv("RELAY_PATH", "/device")
DEVICE_TOKEN = os.getenv("DEVICE_TOKEN")
DEVICE_ID = os.getenv("DEVICE_ID")

BRIDGE_HOST = os.getenv("BRIDGE_HOST", "127.0.0.1")
BRIDGE_PORT = int(os.getenv("BRIDGE_PORT", "8765"))
BRIDGE_TOKEN_FILE = os.getenv(
    "BRIDGE_TOKEN_FILE",
    "/data/adb/naang_phone_bridge/token",
)

ALLOWED_METHODS = frozenset({
    "bridge.status",
    "device.info",
    "packages.list",
    "process.list",
    "system.logcat",
    "app.launch",
    "app.stop",
    "app.current",
    "ui.tap",
    "ui.swipe",
    "ui.keyevent",
    "ui.back",
    "ui.home",
    "ui.recents",
    "ui.text",
    "ui.dump",
    "ui.screenshot",
    "fs.list",
    "fs.read",
    "policy.test",
})


def is_allowed_method(method):
    return isinstance(method, str) and method in ALLOWED_METHODS


def read_bridge_token():
    with open(BRIDGE_TOKEN_FILE, encoding="utf-8") as f:
        return f.read().strip()


def call_local_bridge(method, params):
    if not is_allowed_method(method):
        raise ValueError("method is not allowed")

    body = json.dumps({
        "method": method,
        "params": params or {},
    }).encode()

    c = http.client.HTTPConnection(
        BRIDGE_HOST,
        BRIDGE_PORT,
        timeout=35,
    )

    try:
        c.request(
            "POST",
            "/rpc",
            body=body,
            headers={
                "Authorization": "Bearer " + read_bridge_token(),
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
            },
        )

        r = c.getresponse()
        raw = r.read(1024 * 1024)

        if r.status != 200:
            raise RuntimeError(
                "bridge HTTP %d: %s"
                % (
                    r.status,
                    raw.decode("utf-8", "replace")[:4096],
                )
            )

        x = json.loads(raw.decode())

        if not x.get("ok"):
            raise RuntimeError(
                x.get("error", "bridge request failed")
            )

        return x.get("result")

    finally:
        c.close()


def recv_exact(sock, size):
    out = b""

    while len(out) < size:
        chunk = sock.recv(size - len(out))

        if not chunk:
            raise RuntimeError("relay disconnected")

        out += chunk

    return out


def ws_send(sock, payload, opcode=1):
    if isinstance(payload, str):
        payload = payload.encode()

    mask = os.urandom(4)
    length = len(payload)

    if length < 126:
        header = struct.pack(
            "!BB",
            0x80 | opcode,
            0x80 | length,
        )
    elif length < 65536:
        header = struct.pack(
            "!BBH",
            0x80 | opcode,
            0x80 | 126,
            length,
        )
    else:
        header = struct.pack(
            "!BBQ",
            0x80 | opcode,
            0x80 | 127,
            length,
        )

    masked = bytes(
        b ^ mask[i % 4]
        for i, b in enumerate(payload)
    )

    sock.sendall(header + mask + masked)


def ws_recv(sock):
    b1, b2 = recv_exact(sock, 2)

    opcode = b1 & 0x0F
    masked = bool(b2 & 0x80)
    length = b2 & 0x7F

    if length == 126:
        length = struct.unpack(
            "!H",
            recv_exact(sock, 2),
        )[0]

    elif length == 127:
        length = struct.unpack(
            "!Q",
            recv_exact(sock, 8),
        )[0]

    mask = recv_exact(sock, 4) if masked else b""
    data = recv_exact(sock, length)

    if masked:
        data = bytes(
            b ^ mask[i % 4]
            for i, b in enumerate(data)
        )

    return opcode, data


def connect_relay():
    if not RELAY_HOST or not DEVICE_TOKEN or not DEVICE_ID:
        raise RuntimeError("relay configuration incomplete")

    raw = socket.create_connection(
        (RELAY_HOST, RELAY_PORT),
        timeout=20,
    )

    sock = ssl.create_default_context().wrap_socket(
        raw,
        server_hostname=RELAY_HOST,
    )

    key = base64.b64encode(
        os.urandom(16)
    ).decode()

    request = (
        "GET %s HTTP/1.1\r\n"
        "Host: %s\r\n"
        "Authorization: Bearer %s\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "Sec-WebSocket-Key: %s\r\n"
        "\r\n"
        % (
            RELAY_PATH,
            RELAY_HOST,
            DEVICE_TOKEN,
            key,
        )
    )

    sock.sendall(request.encode())

    headers = b""

    while b"\r\n\r\n" not in headers:
        chunk = sock.recv(4096)

        if not chunk:
            raise RuntimeError(
                "relay disconnected during handshake"
            )

        headers += chunk

        if len(headers) > 16384:
            raise RuntimeError(
                "relay handshake too large"
            )

    expected = base64.b64encode(
        hashlib.sha1(
            (
                key
                + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
            ).encode()
        ).digest()
    ).decode()

    header_text = headers.decode(
        "iso-8859-1",
        "replace",
    )

    if (
        "101 Switching Protocols" not in header_text
        or ("Sec-WebSocket-Accept: " + expected).lower()
        not in header_text.lower()
    ):
        sock.close()
        raise RuntimeError(
            "relay websocket upgrade failed"
        )

    ws_send(
        sock,
        json.dumps({
            "type": "hello",
            "device": DEVICE_ID,
        }),
    )

    return sock


def serve_once():
    sock = connect_relay()

    try:
        while True:
            opcode, data = ws_recv(sock)

            if opcode == 8:
                raise RuntimeError(
                    "relay closed websocket"
                )

            if opcode == 9:
                ws_send(sock, data, 10)
                continue

            if opcode != 1:
                continue

            message = json.loads(data.decode())

            request_id = message.get("id")
            method = message.get("method")
            params = message.get("params") or {}

            if (
                not request_id
                or not is_allowed_method(method)
            ):
                output = {
                    "id": request_id,
                    "ok": False,
                    "error": "method is not allowed",
                }

            else:
                try:
                    output = {
                        "id": request_id,
                        "ok": True,
                        "result": call_local_bridge(
                            method,
                            params,
                        ),
                    }

                except Exception as exc:
                    output = {
                        "id": request_id,
                        "ok": False,
                        "error": str(exc),
                    }

            ws_send(
                sock,
                json.dumps(
                    output,
                    separators=(",", ":"),
                ),
            )

    finally:
        sock.close()


def main():
    while True:
        try:
            serve_once()

        except Exception:
            time.sleep(5)


if __name__ == "__main__":
    main()
