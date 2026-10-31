import { requestDeviceAuthorization } from "@/lib/auth";
import { hashIp, bearer } from "@/lib/tokens";
import { send } from "@/lib/http";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "127.0.0.1";
    const authHeader = req.headers.get("authorization");
    const deviceToken = bearer(authHeader);

    const result = await requestDeviceAuthorization(deviceToken, hashIp(ip), new URL(req.url).origin);
    return send({ status: 200, body: result });
  } catch (err) {
    console.error("[auth/device/code] Erreur :", err);
    return send({ status: 500, body: { error: "internal_error" } });
  }
}
