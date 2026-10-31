import { env } from "./env";

/**
 * Envoie le lien de connexion (utilisé par le plugin magic link de Better Auth).
 * - Resend configuré : envoi réel.
 * - Resend absent en développement : le lien est affiché dans la console du serveur.
 * - Resend absent en production : erreur (même comportement que l'ancienne route magic-link).
 */
export async function sendLoginEmail(email: string, url: string): Promise<void> {
  const configured = Boolean(env.resendKey && env.emailFrom);

  if (!configured) {
    if (process.env.NODE_ENV === "production") {
      throw new Error("email_not_configured");
    }
    console.info(`[auth] Lien de connexion pour ${email} : ${url}`);
    return;
  }

  const res = await fetch("https://api.resend.com/emails", {
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
            <a href="${url}" style="background-color: #0284c7; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; font-weight: 600; display: inline-block;">
              Me connecter à ezShell
            </a>
          </div>
          <p style="color: #64748b; font-size: 14px;">Ce lien expire dans 15 minutes. Si vous n'avez pas demandé ce lien, vous pouvez ignorer cet e-mail.</p>
        </div>
      `,
    }),
  });

  if (!res.ok) {
    console.error("[auth] Resend a refusé l'envoi :", res.status);
    throw new Error("email_delivery_failed");
  }
}
