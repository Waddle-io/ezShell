import { getWebSessionUser } from "@/lib/auth";
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

    const pool = getPool();
    const settings = await loadSettings(pool);

    // 1. Compte des utilisateurs
    const usersCountRes = await pool.query(`
      SELECT
        count(*)::int as total,
        count(case when plan = 'free' then 1 end)::int as free,
        count(case when plan = 'premium' then 1 end)::int as premium,
        count(case when plan = 'unlimited' then 1 end)::int as unlimited,
        count(case when status = 'banned' then 1 end)::int as banned
      FROM users
    `);

    // 2. Compte des appareils actifs
    const devicesCountRes = await pool.query(`
      SELECT
        count(*)::int as total,
        count(case when user_id is not null then 1 end)::int as registered,
        count(case when user_id is null then 1 end)::int as anonymous
      FROM devices
      WHERE revoked_at IS NULL
    `);

    // 3. Métriques d'usage des dernières 24h
    const metricsRes = await pool.query(`
      SELECT
        count(*)::int as total_asks,
        count(case when outcome = 'ok' then 1 end)::int as successful_asks,
        avg(case when outcome = 'ok' then latency_ms end)::int as avg_latency_ms
      FROM ask_metrics
      WHERE at >= now() - interval '24 hours'
    `);

    return send({
      status: 200,
      body: {
        users: usersCountRes.rows[0] || {},
        devices: devicesCountRes.rows[0] || {},
        metrics_24h: metricsRes.rows[0] || {},
        kill_switch: settings.killSwitch,
      },
    });
  } catch (err) {
    console.error("[admin/stats] Erreur :", err);
    return send({ status: 500, body: { error: "internal_error" } });
  }
}
