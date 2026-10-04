import { GET as apiGet, POST as apiPost, DELETE as apiDelete } from "../api/mcp/route.js";

const MCP_TOKEN = process.env.MCP_TOKEN;

function authorizedByUrl(request) {
  if (!MCP_TOKEN) return false;
  const key =
    new URL(request.url).searchParams.get("key") ||
    new URL(request.url).searchParams.get("token");
  return key === MCP_TOKEN;
}

async function forward(request, handler) {
  if (!authorizedByUrl(request)) {
    return new Response("Not Found", { status: 404 });
  }

  const headers = new Headers(request.headers);
  headers.set("authorization", "Bearer " + MCP_TOKEN);

  const init = {
    method: request.method,
    headers,
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  return handler(new Request(request.url, init));
}

export async function GET(request) {
  return forward(request, apiGet);
}

export async function POST(request) {
  return forward(request, apiPost);
}

export async function DELETE(request) {
  return forward(request, apiDelete);
}
