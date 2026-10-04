export const runtime = "nodejs";

export async function GET() {
  const domain = (process.env.AUTH0_DOMAIN || "").replace(/\/$/, "");
  if (!domain) {
    return Response.json(
      { error: "AUTH0_DOMAIN is not configured" },
      { status: 503 },
    );
  }

  return Response.json({
    resource: "https://naang-phone-bridge.vercel.app",
    authorization_servers: ["https://" + domain + "/"],
    scopes_supported: ["phone:read", "phone:control"],
    resource_documentation: "https://github.com/NAANG360/naang-phone-bridge",
  }, {
    headers: {
      "cache-control": "public, max-age=300",
    },
  });
}
