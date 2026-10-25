import { approveDeviceAuthorization, getWebSessionUser } from "@/lib/auth";
import { authenticate } from "@/lib/handlers";
import { send } from "@/lib/http";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    // Authentification : soit via session cookie web, soit via Bearer token
    let userId: string | null = null;
    const cookieHeader = req.headers.get("cookie");
    const webUser = await getWebSessionUser(cookieHeader);
    if (webUser) {
      userId = webUser.id;
    } else {
      const authed = await authenticate(req.headers.get("authorization"));
      if (authed && authed.user_id) {
        userId = authed.user_id;
      }
    }

    if (!userId) {
      return send({ status: 401, body: { error: "unauthorized", message: "Veuillez vous connecter pour approuver cet appareil." } });
    }

    const body = await req.json().catch(() => ({}));
    const userCode = body.user_code;
    if (!userCode || typeof userCode !== "string") {
      return send({ status: 400, body: { error: "invalid_request", message: "Code d'activation manquant" } });
    }

    const result = await approveDeviceAuthorization(userCode, userId);
    if (!result.ok) {
      return send({ status: 400, body: { error: "approval_failed", message: result.error } });
    }

    return send({ status: 200, body: { success: true, message: "Appareil approuvé avec succès !" } });
  } catch (err) {
    console.error("[auth/device/approve] Erreur :", err);
    return send({ status: 500, body: { error: "internal_error" } });
  }
}
