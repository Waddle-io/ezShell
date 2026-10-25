import { pollDeviceAuthorization } from "@/lib/auth";
import { send } from "@/lib/http";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const deviceCode = body.device_code;

    if (!deviceCode || typeof deviceCode !== "string") {
      return send({ status: 400, body: { error: "invalid_request", error_description: "device_code manquant" } });
    }

    const res = await pollDeviceAuthorization(deviceCode);
    return send(res);
  } catch (err) {
    console.error("[auth/device/token] Erreur :", err);
    return send({ status: 500, body: { error: "internal_error" } });
  }
}
