import { NextResponse } from "next/server";
import { getPool } from "@/lib/db";
import { approveDeviceAuthorization, createWebSession, recordAuditLog } from "@/lib/auth";
import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const base = env.publicBaseUrl || url.origin;

  if (!code) {
    return NextResponse.redirect(`${base}/login?error=github_code_missing`);
  }

  let userCode: string | null = null;
  if (state) {
    try {
      const decoded = JSON.parse(Buffer.from(state, "base64url").toString("utf8"));
      userCode = decoded.user_code || null;
    } catch { }
  }

  try {
    // 1. Échange du code contre un access token GitHub
    const tokenRes = await fetch("https://github.com/login/oauth/access_token", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        client_id: env.githubClientId,
        client_secret: env.githubClientSecret,
        code,
      }),
    });

    const tokenData = await tokenRes.json();
    if (!tokenData.access_token) {
      console.error("[github/callback] Pas d'access_token :", tokenData);
      return NextResponse.redirect(`${base}/login?error=github_token_exchange_failed`);
    }

    const accessToken = tokenData.access_token;

    // 2. Profil utilisateur GitHub
    const userProfileRes = await fetch("https://api.github.com/user", {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "User-Agent": "ezShell-Auth",
      },
    });
    const ghUser = await userProfileRes.json();
    const githubId = String(ghUser.id);
    const githubLogin = ghUser.login || null;
    let email: string | null = ghUser.email || null;

    // Si email public non renseigné, interroger /user/emails
    if (!email) {
      try {
        const emailsRes = await fetch("https://api.github.com/user/emails", {
          headers: {
            Authorization: `Bearer ${accessToken}`,
            "User-Agent": "ezShell-Auth",
          },
        });
        const emails = await emailsRes.json();
        if (Array.isArray(emails)) {
          const primary = emails.find((e: { primary: boolean; verified: boolean }) => e.primary && e.verified);
          if (primary) email = primary.email;
          else if (emails[0]?.email) email = emails[0].email;
        }
      } catch (e) {
        console.error("[github/callback] Erreur récupération emails :", e);
      }
    }

    const pool = getPool();
    let userId: string;

    // 3. Recherche ou création utilisateur
    const byGh = await pool.query(`SELECT id, status, role FROM users WHERE github_id = $1`, [githubId]);
    if (byGh.rowCount) {
      userId = byGh.rows[0].id;
      if (byGh.rows[0].status === "banned") {
        return NextResponse.redirect(`${base}/login?error=user_banned`);
      }
      // Mise à jour éventuelle de l'email ou du login GitHub
      await pool.query(
        `UPDATE users SET github_login = $1, email = COALESCE(email, $2) WHERE id = $3`,
        [githubLogin, email, userId],
      );
    } else if (email) {
      const byEmail = await pool.query(`SELECT id, status, role FROM users WHERE lower(email) = $1`, [email.toLowerCase()]);
      if (byEmail.rowCount) {
        userId = byEmail.rows[0].id;
        if (byEmail.rows[0].status === "banned") {
          return NextResponse.redirect(`${base}/login?error=user_banned`);
        }
        await pool.query(`UPDATE users SET github_id = $1, github_login = $2 WHERE id = $3`, [githubId, githubLogin, userId]);
      } else {
        const ins = await pool.query(
          `INSERT INTO users (id, email, github_id, github_login, plan, role, status)
           VALUES (gen_random_uuid()::text, $1, $2, $3, 'free', $4, 'active')
           RETURNING id`,
          [email.toLowerCase(), githubId, githubLogin, env.adminEmails.includes(email.toLowerCase()) ? "admin" : "user"],
        );
        userId = ins.rows[0].id;
        await recordAuditLog(userId, "user_registered", userId, { method: "github", githubLogin });
      }
    } else {
      const ins = await pool.query(
        `INSERT INTO users (id, github_id, github_login, plan, role, status)
         VALUES (gen_random_uuid()::text, $1, $2, 'free', 'user', 'active')
         RETURNING id`,
        [githubId, githubLogin],
      );
      userId = ins.rows[0].id;
      await recordAuditLog(userId, "user_registered", userId, { method: "github", githubLogin });
    }

    // 4. Si un user_code d'appareil est présent, approuver l'appareil
    if (userCode) {
      await approveDeviceAuthorization(userCode, userId);
    }

    // 5. Création de session web
    const sessionToken = await createWebSession(userId);
    await recordAuditLog(userId, "login", userId, { method: "github" });

    const targetUrl = userCode ? `${base}/activate?approved=1` : `${base}/dashboard`;
    const response = NextResponse.redirect(targetUrl);

    response.cookies.set({
      name: "ezsh_session",
      value: sessionToken,
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax",
      path: "/",
      maxAge: 30 * 24 * 60 * 60,
    });

    return response;
  } catch (err) {
    console.error("[github/callback] Erreur inattendue :", err);
    return NextResponse.redirect(`${base}/login?error=github_internal_error`);
  }
}
