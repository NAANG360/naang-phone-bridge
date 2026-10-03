import { createMcpExpressApp } from "@modelcontextprotocol/express";
import { toNodeHandler } from "@modelcontextprotocol/node";
import { createMcpHandler } from "@modelcontextprotocol/server";
import { McpServer } from "@modelcontextprotocol/server";
import { z } from "zod/v4";

const PORT = Number(process.env.PORT || 3000);
const MCP_TOKEN = process.env.MCP_TOKEN;
const RELAY_URL = process.env.RELAY_URL;
const ADMIN_TOKEN = process.env.ADMIN_TOKEN;
const DEVICE_ID = process.env.DEVICE_ID;

if (!MCP_TOKEN || !RELAY_URL || !ADMIN_TOKEN || !DEVICE_ID) {
  throw new Error("MCP_TOKEN, RELAY_URL, ADMIN_TOKEN and DEVICE_ID are required");
}

async function callPhone(method, params = {}) {
  const r = await fetch(RELAY_URL.replace(/\/$/, "") + "/device/call", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      authorization: "Bearer " + ADMIN_TOKEN
    },
    body: JSON.stringify({ action: "device.call", device: DEVICE_ID, method, params })
  });
  if (!r.ok) throw new Error("relay returned HTTP " + r.status);
  const body = await r.json();
  if (!body.ok) throw new Error(body.error || "relay request failed");
  return body.result;
}

const server = new McpServer({ name: "naang-phone", version: "0.1.0" });

server.registerTool("device_info", {
  description: "Read Android device information.",
  inputSchema: {}
}, async () => ({ content: [{ type: "text", text: JSON.stringify(await callPhone("device.info"), null, 2) }] }));

server.registerTool("list_packages", {
  description: "List installed Android packages.",
  inputSchema: {}
}, async () => ({ content: [{ type: "text", text: JSON.stringify(await callPhone("packages.list"), null, 2) }] }));

server.registerTool("list_processes", {
  description: "List Android processes.",
  inputSchema: {}
}, async () => ({ content: [{ type: "text", text: JSON.stringify(await callPhone("process.list"), null, 2) }] }));

server.registerTool("read_logcat", {
  description: "Read recent Android logcat output.",
  inputSchema: { lines: z.number().int().min(1).max(2000).default(200) }
}, async ({ lines }) => ({ content: [{ type: "text", text: JSON.stringify(await callPhone("system.logcat", { lines }), null, 2) }] }));

server.registerTool("list_directory", {
  description: "List a directory within the bridge's permitted filesystem locations.",
  inputSchema: { path: z.string().min(1).max(2048) }
}, async ({ path }) => ({ content: [{ type: "text", text: JSON.stringify(await callPhone("fs.list", { path }), null, 2) }] }));

server.registerTool("read_file", {
  description: "Read a file within the bridge's permitted filesystem locations.",
  inputSchema: { path: z.string().min(1).max(2048), max_bytes: z.number().int().min(1).max(524288).default(65536) }
}, async ({ path, max_bytes }) => ({ content: [{ type: "text", text: JSON.stringify(await callPhone("fs.read", { path, max_bytes }), null, 2) }] }));

const packageName = z.string().regex(/^[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+$/);

server.registerTool("launch_app", {
  description: "Launch an Android app by package name.",
  inputSchema: { package: packageName }
}, async ({ package: pkg }) => ({ content: [{ type: "text", text: JSON.stringify(await callPhone("app.launch", { package: pkg }), null, 2) }] }));

server.registerTool("stop_app", {
  description: "Stop an Android app by package name.",
  inputSchema: { package: packageName }
}, async ({ package: pkg }) => ({ content: [{ type: "text", text: JSON.stringify(await callPhone("app.stop", { package: pkg }), null, 2) }] }));


server.registerTool("current_app", {
  description: "Read the current foreground Android package and activity.",
  inputSchema: {}
}, async () => ({ content: [{ type: "text", text: JSON.stringify(await callPhone("app.current"), null, 2) }] }));

server.registerTool("ui_tap", {
  description: "Tap a fixed screen coordinate on the Android device.",
  inputSchema: { x: z.number().int().min(0).max(10000), y: z.number().int().min(0).max(10000) }
}, async ({ x, y }) => ({ content: [{ type: "text", text: JSON.stringify(await callPhone("ui.tap", { x, y }), null, 2) }] }));

server.registerTool("ui_swipe", {
  description: "Swipe between two screen coordinates.",
  inputSchema: {
    x1: z.number().int().min(0).max(10000), y1: z.number().int().min(0).max(10000),
    x2: z.number().int().min(0).max(10000), y2: z.number().int().min(0).max(10000),
    duration_ms: z.number().int().min(1).max(10000).default(300)
  }
}, async (p) => ({ content: [{ type: "text", text: JSON.stringify(await callPhone("ui.swipe", p), null, 2) }] }));

server.registerTool("ui_keyevent", {
  description: "Send a bounded Android key event.",
  inputSchema: { keycode: z.number().int().min(0).max(300) }
}, async ({ keycode }) => ({ content: [{ type: "text", text: JSON.stringify(await callPhone("ui.keyevent", { keycode }), null, 2) }] }));

server.registerTool("ui_back", { description: "Press Android Back.", inputSchema: {} }, async () => ({ content: [{ type: "text", text: JSON.stringify(await callPhone("ui.back"), null, 2) }] }));
server.registerTool("ui_home", { description: "Press Android Home.", inputSchema: {} }, async () => ({ content: [{ type: "text", text: JSON.stringify(await callPhone("ui.home"), null, 2) }] }));
server.registerTool("ui_recents", { description: "Open Android Recents.", inputSchema: {} }, async () => ({ content: [{ type: "text", text: JSON.stringify(await callPhone("ui.recents"), null, 2) }] }));

server.registerTool("ui_text", {
  description: "Type bounded text using Android's input interface.",
  inputSchema: { text: z.string().max(4096) }
}, async ({ text }) => ({ content: [{ type: "text", text: JSON.stringify(await callPhone("ui.text", { text }), null, 2) }] }));

server.registerTool("ui_dump", {
  description: "Read the Android UI accessibility hierarchy as XML.",
  inputSchema: {}
}, async () => ({ content: [{ type: "text", text: JSON.stringify(await callPhone("ui.dump"), null, 2) }] }));

server.registerTool("ui_screenshot", {
  description: "Capture the Android screen. Set include_base64 only when an image payload is needed.",
  inputSchema: { include_base64: z.boolean().default(false) }
}, async ({ include_base64 }) => {
  const result = await callPhone("ui.screenshot", { include_base64 });
  if (include_base64 && result.base64) {
    return { content: [{ type: "image", data: result.base64, mimeType: result.mime || "image/png" }] };
  }
  return { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] };
});

server.registerTool("test_policy", {
  description: "Ask the phone bridge whether a command matches its local safety policy. This does not execute it.",
  inputSchema: { command: z.string().min(1).max(8192) }
}, async ({ command }) => ({ content: [{ type: "text", text: JSON.stringify(await callPhone("policy.test", { command }), null, 2) }] }));

const handler = createMcpHandler(server, { responseMode: "json" });
const app = createMcpExpressApp({ host: "0.0.0.0", allowedHosts: ["*"] });
app.get("/health", (_req, res) => res.json({ ok: true }));
app.all("/mcp", (req, res, next) => {
  if (req.headers.authorization !== "Bearer " + MCP_TOKEN) return res.status(401).json({ error: "unauthorized" });
  return toNodeHandler(handler)(req, res, next);
});
app.listen(PORT, "0.0.0.0", () => console.log("NAANG phone MCP listening on " + PORT));
