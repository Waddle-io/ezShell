import { authenticate } from "@/lib/handlers";
import { getPool } from "@/lib/db";
import { getWebSessionUser, recordAuditLog } from "@/lib/auth";
import { send } from "@/lib/http";
import { hashToken, bearer } from "@/lib/tokens";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const authHeader = req.headers.get("authorization");
    const device = await authenticate(authHeader);
    const body = await req.json().catch(() => ({}));
    const pool = getPool();

    // Révocation directe par l'appareil lui-même (ezsh logout)
    if (device) {
      await pool.query(
        `UPDATE devices SET revoked_at = now() WHERE id = $1`,
        [device.id],
      );
      if (device.user_id) {
        await recordAuditLog(device.user_id, "device_revoked", device.id, { direct: true });
      }
      return send({ status: 200, body: { success: true, message: "Appareil révoqué avec succès." } });
    }

    // Révocation par l'utilisateur connecté via le dashboard pour un appareil spécifique
    const webUser = await getWebSessionUser(req.headers.get("cookie"));
    if (webUser && body.device_id) {
      const res = await pool.query(
        `UPDATE devices SET revoked_at = now() WHERE id = $1 AND user_id = $2 RETURNING id`,
        [body.device_id, webUser.id],
      );
      if (res.rowCount) {
        await recordAuditLog(webUser.id, "device_revoked", body.device_id, { from_dashboard: true });
        return send({ status: 200, body: { success: true, message: "Appareil révoqué." } });
      }
      return send({ status: 404, body: { error: "not_found", message: "Appareil introuvable." } });
    }

    return send({ status: 401, body: { error: "unauthorized" } });
  } catch (err) {
    console.error("[auth/device/revoke] Erreur :", err);
    return send({ status: 500, body: { error: "internal_error" } });
  }
}
