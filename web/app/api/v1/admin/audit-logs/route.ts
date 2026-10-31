import { getWebSessionUser } from "@/lib/auth";
import { getPool } from "@/lib/db";
import { send } from "@/lib/http";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  try {
    const admin = await getWebSessionUser(req.headers.get("cookie"));
    if (!admin || admin.role !== "admin") {
      return send({ status: 403, body: { error: "forbidden", message: "Accès réservé aux administrateurs." } });
    }

    const pool = getPool();
    const res = await pool.query(`
      SELECT id, at, actor_id, actor_email, action, target_id, details
      FROM audit_logs
      ORDER BY at DESC
      LIMIT 100
    `);

    return send({ status: 200, body: { logs: res.rows } });
  } catch (err) {
    console.error("[admin/audit-logs] Erreur :", err);
    return send({ status: 500, body: { error: "internal_error" } });
  }
}
