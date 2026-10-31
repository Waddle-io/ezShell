import { authenticate } from "@/lib/handlers";
import { getWebSessionUser } from "@/lib/auth";
import { getPool } from "@/lib/db";
import { loadSettings } from "@/lib/settings";
import { entitlement, UNLIMITED } from "@/lib/plans";
import { nextUtcMidnight, readDaily } from "@/lib/quota";
import { send } from "@/lib/http";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  try {
    const pool = getPool();
    const settings = await loadSettings(pool);

    // 1. Authentification soit via Bearer token (CLI), soit via Cookie (Web)
    let authedDevice = await authenticate(req.headers.get("authorization"));
    let webUser = null;

    if (!authedDevice) {
      webUser = await getWebSessionUser(req.headers.get("cookie"));
      if (webUser) {
        authedDevice = {
          id: `web-${webUser.id}`,
          user_id: webUser.id,
          plan: webUser.plan,
          status: webUser.status,
          daily_limit_override: webUser.daily_limit_override,
          override_expires_at: webUser.override_expires_at,
        };
      }
    }

    if (!authedDevice) {
      return send({ status: 401, body: { error: "unauthorized", message: "Veuillez vous authentifier." } });
    }

    const ent = entitlement(authedDevice, settings);
    if (ent.banned) {
      return send({ status: 403, body: { error: "banned", message: "Votre compte est suspendu." } });
    }

    const isUnlimited = ent.tier === "unlimited";
    const used = isUnlimited ? 0 : await readDaily(pool, ent.subjectType, ent.subjectId);
    const limit = isUnlimited ? null : ent.limit;
    const remaining = isUnlimited ? null : Math.max(0, ent.limit - used);

    // Informations utilisateur
    let userDetails: Record<string, unknown> | null = null;
    let registeredDevices: Array<Record<string, unknown>> = [];
    if (authedDevice.user_id) {
      const uRes = await pool.query(
        `SELECT id, email, github_login, plan, role, status, created_at
         FROM users WHERE id = $1`,
        [authedDevice.user_id],
      );
      if (uRes.rowCount) {
        userDetails = uRes.rows[0];
      }

      // Appareils connectés du compte
      const dRes = await pool.query(
        `SELECT id, created_at, last_seen_at
         FROM devices
         WHERE user_id = $1 AND revoked_at IS NULL
         ORDER BY last_seen_at DESC`,
        [authedDevice.user_id],
      );
      registeredDevices = dRes.rows;
    }

    return send({
      status: 200,
      body: {
        account_type: ent.tier === "anonymous" ? "anonymous" : "registered",
        user: userDetails,
        device_id: authedDevice.id,
        devices: registeredDevices,
        quota: {
          tier: ent.tier,
          daily_limit: limit,
          used_today: used,
          remaining_today: remaining,
          reset_at: nextUtcMidnight(),
        },
      },
    });
  } catch (err) {
    console.error("[usage] Erreur :", err);
    return send({ status: 500, body: { error: "internal_error" } });
  }
}
