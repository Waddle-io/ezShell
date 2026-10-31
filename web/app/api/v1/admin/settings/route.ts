import { getWebSessionUser, recordAuditLog } from "@/lib/auth";
import { getPool } from "@/lib/db";
import { loadSettings } from "@/lib/settings";
import { send } from "@/lib/http";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  try {
    const admin = await getWebSessionUser(req.headers.get("cookie"));
    if (!admin || admin.role !== "admin") {
      return send({ status: 403, body: { error: "forbidden", message: "Accès réservé aux administrateurs." } });
    }

    const settings = await loadSettings(getPool());
    return send({ status: 200, body: { settings } });
  } catch (err) {
    console.error("[admin/settings:GET] Erreur :", err);
    return send({ status: 500, body: { error: "internal_error" } });
  }
}

export async function PATCH(req: Request) {
  try {
    const admin = await getWebSessionUser(req.headers.get("cookie"));
    if (!admin || admin.role !== "admin") {
      return send({ status: 403, body: { error: "forbidden", message: "Accès réservé aux administrateurs." } });
    }

    const body = await req.json().catch(() => ({}));
    const pool = getPool();

    if (body.kill_switch !== undefined) {
      const val = body.kill_switch ? "1" : "0";
      await pool.query(
        `INSERT INTO settings (key, value) VALUES ('kill_switch', $1)
         ON CONFLICT (key) DO UPDATE SET value = $1`,
        [val],
      );
      await recordAuditLog(admin.id, "toggle_kill_switch", null, { kill_switch: body.kill_switch }, admin.email);
    }

    if (body.anonymous_limit !== undefined) {
      await pool.query(
        `INSERT INTO settings (key, value) VALUES ('anonymous_limit', $1)
         ON CONFLICT (key) DO UPDATE SET value = $1`,
        [String(Number(body.anonymous_limit))],
      );
      await recordAuditLog(admin.id, "update_anonymous_limit", null, { limit: body.anonymous_limit }, admin.email);
    }

    if (body.free_limit !== undefined) {
      await pool.query(
        `INSERT INTO settings (key, value) VALUES ('free_limit', $1)
         ON CONFLICT (key) DO UPDATE SET value = $1`,
        [String(Number(body.free_limit))],
      );
      await recordAuditLog(admin.id, "update_free_limit", null, { limit: body.free_limit }, admin.email);
    }

    return send({ status: 200, body: { success: true, message: "Réglages mis à jour avec succès." } });
  } catch (err) {
    console.error("[admin/settings:PATCH] Erreur :", err);
    return send({ status: 500, body: { error: "internal_error" } });
  }
}
