import { z } from "zod";
import { createMcpHandler } from "mcp-handler";

const MCP_TOKEN = process.env.MCP_TOKEN;
const RELAY_URL = process.env.RELAY_URL;
const ADMIN_TOKEN = process.env.ADMIN_TOKEN;
const DEVICE_ID = process.env.DEVICE_ID;

async function callPhone(method, params = {}) {
  if (!RELAY_URL || !ADMIN_TOKEN || !DEVICE_ID) {
    throw new Error("Phone relay is not configured yet");
  }

  const response = await fetch(RELAY_URL.replace(/\/$/, "") + "/device/call", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      authorization: "Bearer " + ADMIN_TOKEN,
    },
    body: JSON.stringify({
      action: "device.call",
      device: DEVICE_ID,
      method,
      params,
    }),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Relay returned HTTP " + response.status);
  }

  const body = await response.json();
  if (!body.ok) throw new Error(body.error || "Relay request failed");
  return body.result;
}

function textResult(value) {
  return {
    content: [{ type: "text", text: JSON.stringify(value, null, 2) }],
  };
}

const handler = createMcpHandler(
  (server) => {
    server.tool(
      "device_info",
      "Read Android device information.",
      {},
      async () => textResult(await callPhone("device.info")),
    );

    server.tool(
      "list_packages",
      "List installed Android packages.",
      {},
      async () => textResult(await callPhone("packages.list")),
    );

    server.tool(
      "list_processes",
      "List Android processes.",
      {},
      async () => textResult(await callPhone("process.list")),
    );

    server.tool(
      "read_logcat",
      "Read recent Android logcat output.",
      { lines: z.number().int().min(1).max(2000).default(200) },
      async ({ lines }) => textResult(await callPhone("system.logcat", { lines })),
    );

    server.tool(
      "list_directory",
      "List a directory in the phone bridge's permitted filesystem locations.",
      { path: z.string().min(1).max(2048) },
      async ({ path }) => textResult(await callPhone("fs.list", { path })),
    );

    server.tool(
      "read_file",
      "Read a file in the phone bridge's permitted filesystem locations.",
      {
        path: z.string().min(1).max(2048),
        max_bytes: z.number().int().min(1).max(524288).default(65536),
      },
      async ({ path, max_bytes }) =>
        textResult(await callPhone("fs.read", { path, max_bytes })),
    );

    const packageName = z
      .string()
      .regex(/^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+$/);

    server.tool(
      "launch_app",
      "Launch an Android app by package name.",
      { package: packageName },
      async ({ package: pkg }) =>
        textResult(await callPhone("app.launch", { package: pkg })),
    );

    server.tool(
      "stop_app",
      "Stop an Android app by package name.",
      { package: packageName },
      async ({ package: pkg }) =>
        textResult(await callPhone("app.stop", { package: pkg })),
    );

    server.tool(
      "current_app",
      "Read the currently focused Android app.",
      {},
      async () => textResult(await callPhone("app.current")),
    );

    server.tool(
      "ui_tap",
      "Tap a coordinate on the Android screen.",
      { x: z.number().finite(), y: z.number().finite() },
      async ({ x, y }) => textResult(await callPhone("ui.tap", { x, y })),
    );

    server.tool(
      "ui_swipe",
      "Swipe between two Android screen coordinates.",
      {
        x1: z.number().finite(), y1: z.number().finite(),
        x2: z.number().finite(), y2: z.number().finite(),
        duration_ms: z.number().int().min(1).max(10000).default(300),
      },
      async (params) => textResult(await callPhone("ui.swipe", params)),
    );

    server.tool(
      "ui_keyevent",
      "Send a fixed Android key event.",
      { keycode: z.number().int().min(0).max(300) },
      async ({ keycode }) => textResult(await callPhone("ui.keyevent", { keycode })),
    );

    server.tool("ui_back", "Press Android Back.", {}, async () => textResult(await callPhone("ui.back")));
    server.tool("ui_home", "Press Android Home.", {}, async () => textResult(await callPhone("ui.home")));
    server.tool("ui_recents", "Open Android Recents.", {}, async () => textResult(await callPhone("ui.recents")));

    server.tool(
      "ui_text",
      "Enter text through the phone bridge's fixed Android text-input operation.",
      { text: z.string().max(4096) },
      async ({ text }) => textResult(await callPhone("ui.text", { text })),
    );

    server.tool(
      "ui_dump",
      "Dump the current Android UI hierarchy.",
      {},
      async () => textResult(await callPhone("ui.dump")),
    );

    server.tool(
      "ui_screenshot",
      "Capture an Android screenshot; returns metadata by default.",
      { include_base64: z.boolean().default(false) },
      async ({ include_base64 }) => textResult(await callPhone("ui.screenshot", { include_base64 })),
    );

    server.tool(
      "test_policy",
      "Check the phone bridge policy for a command without executing it.",
      { command: z.string().min(1).max(8192) },
      async ({ command }) =>
        textResult(await callPhone("policy.test", { command })),
    );
  },
  {},
  { basePath: "/api" },
);

async function authorized(request) {
  if (!MCP_TOKEN) return false;
  return request.headers.get("authorization") === "Bearer " + MCP_TOKEN;
}

async function guarded(request) {
  if (!(await authorized(request))) {
    return Response.json({ error: "unauthorized" }, { status: 401 });
  }
  return handler(request);
}

export async function GET(request) {
  return guarded(request);
}

export async function POST(request) {
  return guarded(request);
}

export async function DELETE(request) {
  return guarded(request);
}
