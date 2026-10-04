export const runtime = "nodejs";

import { z } from "zod";
import { createMcpHandler } from "mcp-handler";
import { createRemoteJWKSet, jwtVerify } from "jose";

const MCP_TOKEN = process.env.MCP_TOKEN;
const RELAY_URL = process.env.RELAY_URL;
const ADMIN_TOKEN = process.env.ADMIN_TOKEN;
const DEVICE_ID = process.env.DEVICE_ID;
const AUTH0_DOMAIN = (process.env.AUTH0_DOMAIN || "").replace(/\/$/, "");
const AUTH0_AUDIENCE = process.env.AUTH0_AUDIENCE || "https://naang-phone-bridge.vercel.app";
const AUTH0_ISSUER = AUTH0_DOMAIN ? "https://" + AUTH0_DOMAIN + "/" : "";
const AUTH0_JWKS = AUTH0_DOMAIN
  ? createRemoteJWKSet(new URL("https://" + AUTH0_DOMAIN + "/.well-known/jwks.json"))
  : null;

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

const packageName = z
  .string()
  .regex(/^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+$/);

const handler = createMcpHandler((server) => {
  server.registerTool(
    "device_info",
    {
      title: "Device info",
      description: "Read Android device information.",
      inputSchema: z.object({}),
    },
    async () => textResult(await callPhone("device.info")),
  );

  server.registerTool(
    "list_packages",
    {
      title: "List packages",
      description: "List installed Android packages.",
      inputSchema: z.object({}),
    },
    async () => textResult(await callPhone("packages.list")),
  );

  server.registerTool(
    "list_processes",
    {
      title: "List processes",
      description: "List Android processes.",
      inputSchema: z.object({}),
    },
    async () => textResult(await callPhone("process.list")),
  );

  server.registerTool(
    "read_logcat",
    {
      title: "Read logcat",
      description: "Read recent Android logcat output.",
      inputSchema: z.object({
        lines: z.number().int().min(1).max(2000).default(200),
      }),
    },
    async ({ lines }) =>
      textResult(await callPhone("system.logcat", { lines })),
  );

  server.registerTool(
    "list_directory",
    {
      title: "List directory",
      description: "List a directory in the phone bridge's permitted filesystem locations.",
      inputSchema: z.object({
        path: z.string().min(1).max(2048),
      }),
    },
    async ({ path }) => textResult(await callPhone("fs.list", { path })),
  );

  server.registerTool(
    "read_file",
    {
      title: "Read file",
      description: "Read a file in the phone bridge's permitted filesystem locations.",
      inputSchema: z.object({
        path: z.string().min(1).max(2048),
        max_bytes: z.number().int().min(1).max(524288).default(65536),
      }),
    },
    async ({ path, max_bytes }) =>
      textResult(await callPhone("fs.read", { path, max_bytes })),
  );

  server.registerTool(
    "launch_app",
    {
      title: "Launch app",
      description: "Launch an Android app by package name.",
      inputSchema: z.object({ package: packageName }),
    },
    async ({ package: pkg }) =>
      textResult(await callPhone("app.launch", { package: pkg })),
  );

  server.registerTool(
    "stop_app",
    {
      title: "Stop app",
      description: "Stop an Android app by package name.",
      inputSchema: z.object({ package: packageName }),
    },
    async ({ package: pkg }) =>
      textResult(await callPhone("app.stop", { package: pkg })),
  );

  server.registerTool(
    "current_app",
    {
      title: "Current app",
      description: "Read the currently focused Android app.",
      inputSchema: z.object({}),
    },
    async () => textResult(await callPhone("app.current")),
  );

  server.registerTool(
    "ui_tap",
    {
      title: "UI tap",
      description: "Tap a coordinate on the Android screen.",
      inputSchema: z.object({
        x: z.number().finite(),
        y: z.number().finite(),
      }),
    },
    async ({ x, y }) => textResult(await callPhone("ui.tap", { x, y })),
  );

  server.registerTool(
    "ui_swipe",
    {
      title: "UI swipe",
      description: "Swipe between two Android screen coordinates.",
      inputSchema: z.object({
        x1: z.number().finite(),
        y1: z.number().finite(),
        x2: z.number().finite(),
        y2: z.number().finite(),
        duration_ms: z.number().int().min(1).max(10000).default(300),
      }),
    },
    async (params) => textResult(await callPhone("ui.swipe", params)),
  );

  server.registerTool(
    "ui_keyevent",
    {
      title: "UI key event",
      description: "Send a fixed Android key event.",
      inputSchema: z.object({
        keycode: z.number().int().min(0).max(300),
      }),
    },
    async ({ keycode }) =>
      textResult(await callPhone("ui.keyevent", { keycode })),
  );

  server.registerTool(
    "ui_back",
    {
      title: "UI back",
      description: "Press Android Back.",
      inputSchema: z.object({}),
    },
    async () => textResult(await callPhone("ui.back")),
  );

  server.registerTool(
    "ui_home",
    {
      title: "UI home",
      description: "Press Android Home.",
      inputSchema: z.object({}),
    },
    async () => textResult(await callPhone("ui.home")),
  );

  server.registerTool(
    "ui_recents",
    {
      title: "UI recents",
      description: "Open Android Recents.",
      inputSchema: z.object({}),
    },
    async () => textResult(await callPhone("ui.recents")),
  );

  server.registerTool(
    "ui_text",
    {
      title: "UI text",
      description: "Enter text through the phone bridge's fixed Android text-input operation.",
      inputSchema: z.object({
        text: z.string().max(4096),
      }),
    },
    async ({ text }) => textResult(await callPhone("ui.text", { text })),
  );

  server.registerTool(
    "ui_dump",
    {
      title: "UI dump",
      description: "Dump the current Android UI hierarchy.",
      inputSchema: z.object({}),
    },
    async () => textResult(await callPhone("ui.dump")),
  );

  server.registerTool(
    "ui_screenshot",
    {
      title: "UI screenshot",
      description: "Capture an Android screenshot; returns metadata by default.",
      inputSchema: z.object({
        include_base64: z.boolean().default(false),
      }),
    },
    async ({ include_base64 }) =>
      textResult(await callPhone("ui.screenshot", { include_base64 })),
  );

  server.registerTool(
    "test_policy",
    {
      title: "Test policy",
      description: "Check the phone bridge policy for a command without executing it.",
      inputSchema: z.object({
        command: z.string().min(1).max(8192),
      }),
    },
    async ({ command }) =>
      textResult(await callPhone("policy.test", { command })),
  );
});

async function authorized(request) {
  const authorization = request.headers.get("authorization") || "";

  // Keep the existing static token working for local/curl testing.
  if (MCP_TOKEN && authorization === "Bearer " + MCP_TOKEN) {
    return true;
  }

  // ChatGPT uses OAuth Bearer tokens. Verify Auth0-issued JWTs.
  if (!AUTH0_DOMAIN || !AUTH0_JWKS || !authorization.startsWith("Bearer ")) {
    return false;
  }

  const token = authorization.slice("Bearer ".length).trim();
  if (!token) return false;

  try {
    const { payload } = await jwtVerify(token, AUTH0_JWKS, {
      issuer: AUTH0_ISSUER,
      audience: AUTH0_AUDIENCE,
    });

    const scopeText = typeof payload.scope === "string" ? payload.scope : "";
    const permissions = Array.isArray(payload.permissions) ? payload.permissions : [];
    return (
      scopeText.split(/\s+/).includes("phone:read") ||
      scopeText.split(/\s+/).includes("phone:control") ||
      permissions.includes("phone:read") ||
      permissions.includes("phone:control")
    );
  } catch {
    return false;
  }
}

async function guarded(request) {
  if (!(await authorized(request))) {
    const metadata =
      "https://naang-phone-bridge.vercel.app/.well-known/oauth-protected-resource";
    return new Response(JSON.stringify({ error: "unauthorized" }), {
      status: 401,
      headers: {
        "content-type": "application/json",
        "WWW-Authenticate": 'Bearer resource_metadata="' + metadata + '", scope="phone:read phone:control"',
      },
    });
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
