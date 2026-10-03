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
