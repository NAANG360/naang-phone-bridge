import http from "node:http";
import crypto from "node:crypto";

const PORT = 8080;

const ADMIN_TOKEN = process.env.ADMIN_TOKEN;
const DEVICE_TOKEN = process.env.DEVICE_TOKEN;

if (!ADMIN_TOKEN || !DEVICE_TOKEN) {
  throw new Error(
    "ADMIN_TOKEN and DEVICE_TOKEN are required"
  );
}

const devices = new Map();
const pending = new Map();

const ALLOWED_METHODS = new Set([
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
]);

const isAllowedMethod = (method) =>
  typeof method === "string" &&
  ALLOWED_METHODS.has(method);

const json = (res, status, obj) => {
  const body = JSON.stringify(obj);

  res.writeHead(status, {
    "content-type": "application/json",
    "content-length": Buffer.byteLength(body),
  });

  res.end(body);
};

const auth = (req, token) =>
  req.headers.authorization === "Bearer " + token;

function id() {
  return crypto.randomBytes(16).toString("hex");
}

function wsAccept(key) {
  return crypto
    .createHash("sha1")
    .update(
      key +
      "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    )
    .digest("base64");
}

function wsFrame(payload, opcode = 1) {
  if (!Buffer.isBuffer(payload)) {
    payload = Buffer.from(payload);
  }

  const length = payload.length;

  if (length < 126) {
    return Buffer.concat([
      Buffer.from([
        0x80 | opcode,
        length,
      ]),
      payload,
    ]);
  }

  if (length < 65536) {
    const header = Buffer.alloc(4);

    header[0] = 0x80 | opcode;
    header[1] = 126;
    header.writeUInt16BE(length, 2);

    return Buffer.concat([
      header,
      payload,
    ]);
  }

  const header = Buffer.alloc(10);

  header[0] = 0x80 | opcode;
  header[1] = 127;
  header.writeBigUInt64BE(
    BigInt(length),
    2,
  );

  return Buffer.concat([
    header,
    payload,
  ]);
}

function wsSend(socket, value) {
  const payload =
    typeof value === "string"
      ? value
      : JSON.stringify(value);

  socket.write(wsFrame(payload, 1));
}

function parseFrames(buffer) {
  const frames = [];
  let offset = 0;

  while (buffer.length - offset >= 2) {
    const b1 = buffer[offset];
    const b2 = buffer[offset + 1];

    const opcode = b1 & 0x0f;
    const masked = !!(b2 & 0x80);

    let length = b2 & 0x7f;
    let headerLength = 2;

    if (length === 126) {
      if (buffer.length - offset < 4) {
        break;
      }

      length = buffer.readUInt16BE(offset + 2);
      headerLength = 4;

    } else if (length === 127) {
      if (buffer.length - offset < 10) {
        break;
      }

      const bigLength =
        buffer.readBigUInt64BE(offset + 2);

      if (bigLength > BigInt(0x7fffffff)) {
        throw new Error("websocket frame too large");
      }

      length = Number(bigLength);
      headerLength = 10;
    }

    const maskLength = masked ? 4 : 0;
    const frameLength =
      headerLength +
      maskLength +
      length;

    if (
      buffer.length - offset <
      frameLength
    ) {
      break;
    }

    let payloadStart =
      offset + headerLength;

    let mask;

    if (masked) {
      mask = buffer.subarray(
        payloadStart,
        payloadStart + 4,
      );

      payloadStart += 4;
    }

    let payload = buffer.subarray(
      payloadStart,
      payloadStart + length,
    );

    if (masked) {
      const decoded = Buffer.alloc(length);

      for (let i = 0; i < length; i++) {
        decoded[i] =
          payload[i] ^
          mask[i % 4];
      }

      payload = decoded;
    }

    frames.push({
      opcode,
      payload,
    });

    offset += frameLength;
  }

  return {
    frames,
    rest: buffer.subarray(offset),
  };
}

function sendDevice(device, request) {
  const socket = devices.get(device);

  if (!socket) {
    throw new Error("device offline");
  }

  const requestId = id();

  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pending.delete(requestId);
      reject(new Error("device timeout"));
    }, 30000);

    pending.set(requestId, {
      resolve,
      reject,
      timer,
    });

    wsSend(socket, {
      ...request,
      id: requestId,
    });
  });
}

const server = http.createServer(
  (req, res) => {
    if (
      req.method === "GET" &&
      req.url === "/health"
    ) {
      return json(res, 200, {
        ok: true,
        devices: [...devices.keys()],
      });
    }

    if (req.method !== "POST") {
      return json(res, 405, {
        error: "method not allowed",
      });
    }

    if (!auth(req, ADMIN_TOKEN)) {
      return json(res, 401, {
        error: "unauthorized",
      });
    }

    let body = "";

    req.on("data", (chunk) => {
      body += chunk;

      if (body.length > 65536) {
        req.destroy();
      }
    });

    req.on("end", async () => {
      try {
        const x = JSON.parse(body);

        if (x.action === "device.call") {
          if (
            typeof x.device !== "string" ||
            !isAllowedMethod(x.method)
          ) {
            return json(res, 400, {
              error: "invalid request",
            });
          }

          return json(res, 200, {
            ok: true,
            result: await sendDevice(
              x.device,
              {
                jsonrpc: "2.0",
                method: x.method,
                params: x.params || {},
              },
            ),
          });
        }

        return json(res, 400, {
          error: "unknown action",
        });

      } catch (e) {
        return json(res, 502, {
          error: e.message,
        });
      }
    });
  },
);

server.on("upgrade", (req, socket) => {
  const upgrade =
    req.headers.upgrade?.toLowerCase();

  const connection =
    req.headers.connection?.toLowerCase();

  const key =
    req.headers["sec-websocket-key"];

  if (
    req.url !== "/device" ||
    req.headers.authorization !==
      "Bearer " + DEVICE_TOKEN ||
    upgrade !== "websocket" ||
    !connection?.includes("upgrade") ||
    !key
  ) {
    socket.destroy();
    return;
  }

  socket.write(
    "HTTP/1.1 101 Switching Protocols\r\n" +
    "Upgrade: websocket\r\n" +
    "Connection: Upgrade\r\n" +
    "Sec-WebSocket-Accept: " +
    wsAccept(key) +
    "\r\n\r\n",
  );

  let device = "";
  let buffer = Buffer.alloc(0);

  socket.on("data", (chunk) => {
    buffer = Buffer.concat([
      buffer,
      chunk,
    ]);

    let parsed;

    try {
      parsed = parseFrames(buffer);
    } catch {
      socket.destroy();
      return;
    }

    buffer = parsed.rest;

    for (const frame of parsed.frames) {
      if (frame.opcode === 9) {
        socket.write(
          wsFrame(frame.payload, 10),
        );
        continue;
      }

      if (frame.opcode === 8) {
        socket.end();
        continue;
      }

      if (frame.opcode !== 1) {
        continue;
      }

      try {
        const message = JSON.parse(
          frame.payload.toString(),
        );

        if (message.type === "hello") {
          device = message.device;

          if (device) {
            devices.set(device, socket);
          }

          continue;
        }

        if (
          message.id &&
          pending.has(message.id)
        ) {
          const pendingRequest =
            pending.get(message.id);

          pending.delete(message.id);

          clearTimeout(
            pendingRequest.timer,
          );

          pendingRequest.resolve(message);
        }

      } catch {
        // Ignore malformed application messages.
      }
    }
  });

  socket.on("close", () => {
    if (
      device &&
      devices.get(device) === socket
    ) {
      devices.delete(device);
    }
  });

  socket.on("error", () => {
    if (
      device &&
      devices.get(device) === socket
    ) {
      devices.delete(device);
    }
  });
});

server.listen(
  PORT,
  () =>
    console.log(
      "NAANG RELAY v3 websocket listening on :" +
      PORT,
    ),
);
