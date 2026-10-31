import { getWebSessionUser, recordAuditLog } from "@/lib/auth";
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

    const url = new URL(req.url);
    const query = url.searchParams.get("q")?.toLowerCase() || "";
    const pool = getPool();

    let sql = `
      SELECT u.id, u.email, u.github_login, u.role, u.plan, u.status,
             u.daily_limit_override, u.override_expires_at, u.created_at,
             count(d.id)::int as devices_count
      FROM users u
      LEFT JOIN devices d ON d.user_id = u.id AND d.revoked_at IS NULL
    `;
    const params: unknown[] = [];

    if (query) {
      sql += ` WHERE lower(u.email) LIKE $1 OR lower(u.github_login) LIKE $1`;
      params.push(`%${query}%`);
    }

    sql += ` GROUP BY u.id ORDER BY u.created_at DESC LIMIT 100`;

    const res = await pool.query(sql, params);
    return send({ status: 200, body: { users: res.rows } });
  } catch (err) {
    console.error("[admin/users:GET] Erreur :", err);
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
    const targetUserId = body.user_id;

    if (!targetUserId) {
      return send({ status: 400, body: { error: "invalid_request", message: "user_id manquant." } });
    }

    const pool = getPool();
    const existing = await pool.query(`SELECT id, email, plan, status, role FROM users WHERE id = $1`, [targetUserId]);
    if (!existing.rowCount) {
      return send({ status: 404, body: { error: "not_found", message: "Utilisateur introuvable." } });
    }

    const updates: string[] = [];
    const params: unknown[] = [targetUserId];
    let idx = 2;

    if (body.plan && ["free", "premium", "unlimited"].includes(body.plan)) {
      updates.push(`plan = $${idx++}`);
      params.push(body.plan);
    }

    if (body.status && ["active", "banned"].includes(body.status)) {
      updates.push(`status = $${idx++}`);
      params.push(body.status);
    }

    if (body.role && ["user", "admin"].includes(body.role)) {
      updates.push(`role = $${idx++}`);
      params.push(body.role);
    }

    if (body.daily_limit_override !== undefined) {
      const overrideVal = body.daily_limit_override === null ? null : Number(body.daily_limit_override);
      updates.push(`daily_limit_override = $${idx++}`);
      params.push(overrideVal);
    }

    if (!updates.length) {
      return send({ status: 400, body: { error: "no_updates", message: "Aucune modification fournie." } });
    }

    await pool.query(
      `UPDATE users SET ${updates.join(", ")} WHERE id = $1`,
      params,
    );

    await recordAuditLog(
      admin.id,
      "admin_update_user",
      targetUserId,
      body,
      admin.email,
    );

    return send({ status: 200, body: { success: true, message: "Utilisateur mis à jour avec succès." } });
  } catch (err) {
    console.error("[admin/users:PATCH] Erreur :", err);
    return send({ status: 500, body: { error: "internal_error" } });
  }
}
