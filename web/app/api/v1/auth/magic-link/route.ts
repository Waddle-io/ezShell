import { randomBytes } from "node:crypto";
import { getPool } from "@/lib/db";
import { env } from "@/lib/env";
import { hashToken } from "@/lib/tokens";
import { send } from "@/lib/http";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const email = (body.email || "").trim().toLowerCase();
    const userCode = (body.user_code || "").trim().toUpperCase() || null;

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return send({ status: 400, body: { error: "invalid_email", message: "Adresse e-mail invalide." } });
    }

    const token = "ezm_" + randomBytes(32).toString("base64url");
    const tokenHash = hashToken(token);
    const pool = getPool();

    await pool.query(
      `INSERT INTO login_tokens (token_hash, email, user_code, expires_at)
       VALUES ($1, $2, $3, now() + interval '15 minutes')`,
      [tokenHash, email, userCode],
    );

    const base = env.publicBaseUrl || "http://localhost:3000";
    const verifyUrl = `${base}/api/v1/auth/verify?token=${token}`;

    // Si Resend est configuré, envoyer l'email
    if (env.resendKey && env.emailFrom) {
      try {
        await fetch("https://api.resend.com/emails", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${env.resendKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            from: env.emailFrom,
            to: email,
            subject: "Votre lien de connexion à ezShell",
            html: `
              <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #0f172a;">Connexion à ezShell</h2>
                <p>Cliquez sur le bouton ci-dessous pour vous connecter à votre compte ezShell :</p>
                <div style="margin: 28px 0;">
                  <a href="${verifyUrl}" style="background-color: #0284c7; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">
                    Me connecter à ezShell
                  </a>
                </div>
                <p style="color: #64748b; font-size: 14px;">Ce lien expire dans 15 minutes. Si vous n'avez pas demandé ce lien, vous pouvez ignorer cet e-mail.</p>
              </div>
            `,
          }),
        });
      } catch (err) {
        console.error("[auth/magic-link] Erreur envoi Resend :", err);
      }
    }

    const responseBody: Record<string, unknown> = {
      success: true,
      message: "Un lien de connexion vous a été envoyé par e-mail.",
    };

    // Pour le développement local ou l'absence de clé Resend : exposer debug_url
    if (!env.resendKey) {
      responseBody.debug_url = verifyUrl;
    }

    return send({ status: 200, body: responseBody });
  } catch (err) {
    console.error("[auth/magic-link] Erreur :", err);
    return send({ status: 500, body: { error: "internal_error" } });
  }
}
