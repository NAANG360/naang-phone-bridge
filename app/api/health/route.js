export async function GET() {
  return Response.json({
    ok: true,
    service: "naang-phone-bridge",
    mcp: "/api/mcp",
    relayConfigured: Boolean(process.env.RELAY_URL && process.env.ADMIN_TOKEN && process.env.DEVICE_ID),
  });
}
