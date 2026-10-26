import { NextResponse } from "next/server";
import { getPool } from "@/lib/db";
import { hashToken } from "@/lib/tokens";
import { approveDeviceAuthorization, createWebSession, recordAuditLog } from "@/lib/auth";
import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const token = url.searchParams.get("token");

  const base = env.publicBaseUrl || url.origin;

  if (!token) {
    return NextResponse.redirect(`${base}/login?error=token_missing`);
  }

  const tokenHash = hashToken(token);
  const pool = getPool();

  const tokenRes = await pool.query(
    `SELECT token_hash, email, user_code, expires_at, used_at
     FROM login_tokens
     WHERE token_hash = $1`,
    [tokenHash],
  );

  if (!tokenRes.rowCount) {
    return NextResponse.redirect(`${base}/login?error=token_invalid`);
  }

  const loginRow = tokenRes.rows[0];
  if (loginRow.used_at) {
    return NextResponse.redirect(`${base}/login?error=token_already_used`);
  }
  if (loginRow.expires_at < new Date()) {
    return NextResponse.redirect(`${base}/login?error=token_expired`);
  }

  // Marquer comme utilisé
  await pool.query(`UPDATE login_tokens SET used_at = now() WHERE token_hash = $1`, [tokenHash]);

  const email = loginRow.email.toLowerCase();

  // Trouver ou créer l'utilisateur
  let userRes = await pool.query(`SELECT id, role, status FROM users WHERE lower(email) = $1`, [email]);
  let userId: string;

  if (userRes.rowCount) {
    userId = userRes.rows[0].id;
    if (userRes.rows[0].status === "banned") {
      return NextResponse.redirect(`${base}/login?error=user_banned`);
    }
  } else {
    // Création du compte
    const ins = await pool.query(
      `INSERT INTO users (id, email, plan, role, status)
       VALUES (gen_random_uuid()::text, $1, 'free', $2, 'active')
       RETURNING id`,
      [email, env.adminEmails.includes(email) ? "admin" : "user"],
    );
    userId = ins.rows[0].id;
    await recordAuditLog(userId, "user_registered", userId, { method: "magic_link", email });
  }

  // Si un user_code d'appareil était fourni : lier immédiatement l'appareil
  if (loginRow.user_code) {
    const approval = await approveDeviceAuthorization(loginRow.user_code, userId);
    if (!approval.ok) {
      return NextResponse.redirect(`${base}/login?error=device_approval_failed`);
    }
  }

  // Création de la session web
  const sessionToken = await createWebSession(userId);
  await recordAuditLog(userId, "login", userId, { method: "magic_link" });

  const targetUrl = loginRow.user_code ? `${base}/activate?approved=1` : `${base}/dashboard`;
  const response = NextResponse.redirect(targetUrl);

  response.cookies.set({
    name: "ezsh_session",
    value: sessionToken,
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 30 * 24 * 60 * 60, // 30 jours
  });

  return response;
}
