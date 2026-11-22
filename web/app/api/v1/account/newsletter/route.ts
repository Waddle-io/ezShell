import { getWebSessionUser, recordAuditLog } from "@/lib/auth";
import { getPool } from "@/lib/db";
import { send } from "@/lib/http";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function PATCH(req: Request) {
  try {
    const user = await getWebSessionUser(req.headers.get("cookie"));
    if (!user) {
      return send({ status: 401, body: { error: "unauthorized", message: "Connexion requise." } });
    }

    const body = await req.json().catch(() => ({}));
    if (typeof body.newsletterOptIn !== "boolean") {
      return send({ status: 400, body: { error: "invalid_request", message: "newsletterOptIn doit être booléen." } });
    }

    await getPool().query(
      `UPDATE users SET newsletter_opt_in = $1 WHERE id = $2`,
      [body.newsletterOptIn, user.id],
    );

    if (body.newsletterOptIn && user.email) {
      await getPool().query(
        `INSERT INTO waitlist (email, source) VALUES ($1, 'account')
         ON CONFLICT (email) DO NOTHING`,
        [user.email.toLowerCase()],
      );
    }

    await recordAuditLog(user.id, "newsletter_preference", user.id, { newsletterOptIn: body.newsletterOptIn }, user.email);
    return send({ status: 200, body: { success: true, newsletterOptIn: body.newsletterOptIn } });
  } catch (err) {
    console.error("[account/newsletter] Erreur :", err);
    return send({ status: 500, body: { error: "internal_error" } });
  }
}
