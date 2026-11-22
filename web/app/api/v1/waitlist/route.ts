import { getPool } from "@/lib/db";
import { send } from "@/lib/http";
import { sendWaitlistConfirmation } from "@/lib/mailer";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  try {
    const body = await req.json().catch(() => ({}));
    const email = typeof body.email === "string" ? body.email.trim().toLowerCase() : "";
    const source = typeof body.source === "string" ? body.source.slice(0, 40) : "landing";

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || email.length > 254) {
      return send({ status: 400, body: { error: "invalid_email", message: "Adresse e-mail invalide." } });
    }

    await getPool().query(
      `INSERT INTO waitlist (email, source)
       VALUES ($1, $2)
       ON CONFLICT (email) DO UPDATE SET source = EXCLUDED.source`,
      [email, source],
    );

    await sendWaitlistConfirmation(email);
    return send({ status: 200, body: { success: true } });
  } catch (err) {
    console.error("[waitlist] Erreur :", err);
    return send({ status: 500, body: { error: "internal_error" } });
  }
}
