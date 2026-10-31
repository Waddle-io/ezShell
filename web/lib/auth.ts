import { randomBytes } from "node:crypto";
import { recordAuditLog } from "./audit";
import { getAuth } from "./better-auth";
import { getPool } from "./db";
import { env } from "./env";
import { hashToken, newDeviceToken } from "./tokens";

// Conservé ici pour ne pas toucher aux imports existants (admin/*, github/callback, verify…).
export { recordAuditLog };

const CODE_CHARS = "BCDFGHJKLMNPQRSTVWXZ23456789";

function generateUserCode(): string {
  let part1 = "";
  let part2 = "";
  const bytes = randomBytes(8);
  for (let i = 0; i < 4; i++) {
    part1 += CODE_CHARS[bytes[i] % CODE_CHARS.length];
    part2 += CODE_CHARS[bytes[i + 4] % CODE_CHARS.length];
  }
  return `${part1}-${part2}`;
}

export interface UserRecord {
  id: string;
  email: string | null;
  github_id: string | null;
  github_login: string | null;
  role: "user" | "admin";
  plan: "free" | "premium" | "unlimited";
  daily_limit_override: number | null;
  override_expires_at: Date | null;
  status: "active" | "banned";
  created_at: Date;
}

export async function requestDeviceAuthorization(clientDeviceToken: string | null, ipHash: string, origin?: string) {
  const pool = getPool();
  let deviceId: string;
  let rawDeviceToken = clientDeviceToken;

  if (clientDeviceToken) {
    const existing = await pool.query(
      `SELECT id FROM devices WHERE token_hash = $1 AND revoked_at IS NULL`,
      [hashToken(clientDeviceToken)],
    );
    if (existing.rowCount && existing.rows[0]) {
      deviceId = existing.rows[0].id;
    } else {
      rawDeviceToken = newDeviceToken();
      const ins = await pool.query(
        `INSERT INTO devices (token_hash, ip_hash) VALUES ($1, $2) RETURNING id`,
        [hashToken(rawDeviceToken), ipHash],
      );
      deviceId = ins.rows[0].id;
    }
  } else {
    rawDeviceToken = newDeviceToken();
    const ins = await pool.query(
      `INSERT INTO devices (token_hash, ip_hash) VALUES ($1, $2) RETURNING id`,
      [hashToken(rawDeviceToken), ipHash],
    );
    deviceId = ins.rows[0].id;
  }

  const deviceCode = "ezdc_" + randomBytes(32).toString("base64url");
  const userCode = generateUserCode();
  const expiresIn = 900; // 15 minutes
  const interval = 3; // 3 secondes

  await pool.query(
    `INSERT INTO device_codes (device_code_hash, user_code, device_id, expires_at)
     VALUES ($1, $2, $3, now() + interval '15 minutes')`,
    [hashToken(deviceCode), userCode, deviceId],
  );

  const base = (env.publicBaseUrl || origin || "").replace(/\/$/, "");
  if (!base) {
    throw new Error("PUBLIC_BASE_URL ou l'origine de la requête est requis pour créer un lien d'activation");
  }
  const verificationUri = `${base}/activate`;
  const verificationUriComplete = `${base}/activate?user_code=${userCode}`;

  return {
    device_code: deviceCode,
    user_code: userCode,
    device_token: rawDeviceToken,
    verification_uri: verificationUri,
    verification_uri_complete: verificationUriComplete,
    expires_in: expiresIn,
    interval: interval,
  };
}

export async function pollDeviceAuthorization(deviceCode: string) {
  const pool = getPool();
  const codeHash = hashToken(deviceCode);

  const res = await pool.query(
    `SELECT dc.status, dc.expires_at, dc.device_id, dc.user_id, d.token_hash,
            u.id as u_id, u.email as u_email, u.plan as u_plan, u.role as u_role, u.status as u_status
     FROM device_codes dc
     JOIN devices d ON d.id = dc.device_id
     LEFT JOIN users u ON u.id = dc.user_id
     WHERE dc.device_code_hash = $1`,
    [codeHash],
  );

  if (!res.rowCount) {
    return { status: 400, body: { error: "invalid_grant", error_description: "Code d'appareil inconnu" } };
  }

  const row = res.rows[0];
  const now = new Date();

  if (row.expires_at < now || row.status === "expired") {
    return { status: 400, body: { error: "expired_token", error_description: "Le code d'autorisation a expiré" } };
  }

  if (row.status === "denied") {
    return { status: 403, body: { error: "access_denied", error_description: "Autorisation refusée" } };
  }

  if (row.status === "pending") {
    return { status: 400, body: { error: "authorization_pending", error_description: "En attente d'approbation" } };
  }

  if (row.status === "approved") {
    // Si l'utilisateur est banni
    if (row.u_status === "banned") {
      return { status: 403, body: { error: "banned", error_description: "Compte suspendu" } };
    }

    return {
      status: 200,
      body: {
        token_type: "Bearer",
        user: {
          id: row.u_id,
          email: row.u_email,
          plan: row.u_plan,
          role: row.u_role,
        },
      },
    };
  }

  return { status: 400, body: { error: "invalid_request" } };
}

export async function approveDeviceAuthorization(userCode: string, userId: string): Promise<{ ok: boolean; error?: string }> {
  const pool = getPool();
  const cleanCode = userCode.trim().toUpperCase();

  const codeRes = await pool.query(
    `SELECT dc.device_id, dc.status, dc.expires_at FROM device_codes dc WHERE dc.user_code = $1`,
    [cleanCode],
  );

  if (!codeRes.rowCount) {
    return { ok: false, error: "Code d'activation introuvable ou erroné." };
  }

  const row = codeRes.rows[0];
  if (row.expires_at < new Date()) {
    return { ok: false, error: "Ce code a expiré. Relancez la commande 'ezsh login'." };
  }

  if (row.status !== "pending") {
    return { ok: false, error: `Ce code a déjà été traité (${row.status}).` };
  }

  // Vérifier limite d'appareils par utilisateur
  const devCount = await pool.query(
    `SELECT count(*)::int as count FROM devices WHERE user_id = $1 AND revoked_at IS NULL`,
    [userId],
  );
  if (devCount.rows[0].count >= env.maxDevicesPerUser) {
    return { ok: false, error: `Nombre maximal d'appareils atteint (${env.maxDevicesPerUser}). Révoquez un appareil depuis votre dashboard.` };
  }

  // Lier l'appareil et approuver
  await pool.query(
    `UPDATE devices SET user_id = $1 WHERE id = $2`,
    [userId, row.device_id],
  );

  await pool.query(
    `UPDATE device_codes SET status = 'approved', user_id = $1 WHERE user_code = $2`,
    [userId, cleanCode],
  );

  await recordAuditLog(userId, "device_approved", row.device_id, { user_code: cleanCode });

  return { ok: true };
}

const USER_COLUMNS = `u.id, u.email, u.github_id, u.github_login, u.role, u.plan,
            u.daily_limit_override, u.override_expires_at, u.status, u.created_at`;

/** Cookie de session Better Auth (préfixe « ezsh », préfixé par __Secure- en HTTPS). */
const BETTER_AUTH_COOKIE = /(?:^|;\s*)(?:__Secure-)?ezsh\.session_token=/;

async function betterAuthUserId(cookieHeader: string): Promise<string | null> {
  if (!BETTER_AUTH_COOKIE.test(cookieHeader)) return null;
  try {
    const session = await getAuth().api.getSession({ headers: new Headers({ cookie: cookieHeader }) });
    return session?.user.id ?? null;
  } catch (e) {
    console.error("[auth] Lecture de la session Better Auth impossible :", e);
    return null;
  }
}

async function loadUserRecord(userId: string): Promise<UserRecord | null> {
  const pool = getPool();
  const res = await pool.query(`SELECT ${USER_COLUMNS} FROM users u WHERE u.id = $1`, [userId]);
  if (!res.rowCount) return null;
  const user = res.rows[0] as UserRecord;

  // Si l'email est dans env.adminEmails, accorder le rôle admin
  if (user.email && env.adminEmails.includes(user.email.toLowerCase()) && user.role !== "admin") {
    user.role = "admin";
    await pool.query(`UPDATE users SET role = 'admin' WHERE id = $1`, [user.id]);
  }
  return user;
}

/** Utilisateur de la session web (cookie), ou null. Même forme de retour qu'avant la migration. */
export async function getWebSessionUser(cookieHeader: string | null): Promise<UserRecord | null> {
  if (!cookieHeader) return null;
  const userId = await betterAuthUserId(cookieHeader);
  return userId ? loadUserRecord(userId) : null;
}
