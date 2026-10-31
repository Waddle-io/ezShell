import { randomUUID } from "node:crypto";
import { betterAuth } from "better-auth";
import { magicLink } from "better-auth/plugins/magic-link";
import { recordAuditLog } from "./audit";
import { getPool } from "./db";
import { env } from "./env";
import { sendLoginEmail } from "./mailer";

/**
 * Better Auth, branché sur le schéma existant :
 *  - le modèle « user » est la table `users` (mêmes ids → devices, quotas et plans restent liés) ;
 *  - session / account / verification sont les tables snake_case créées par db/schema.sql ;
 *  - role, plan, status… sont des champs additionnels, jamais modifiables par le client (input: false).
 *
 * Création paresseuse (getAuth) : `next build` importe les routes sans que les variables
 * d'environnement soient forcément présentes.
 */
function createAuth() {
  // Sans URL publique fixe, Better Auth déduit l'adresse du lien magique de l'en-tête Host de la requête :
  // un attaquant pourrait alors faire envoyer à une victime un lien vers son propre domaine.
  if (process.env.NODE_ENV === "production" && !env.publicBaseUrl) {
    throw new Error("PUBLIC_BASE_URL est obligatoire en production (adresse des liens de connexion).");
  }

  const githubEnabled = Boolean(env.githubClientId && env.githubClientSecret);

  return betterAuth({
    appName: "ezShell",
    baseURL: env.publicBaseUrl || undefined,
    secret: env.betterAuthSecret || undefined,
    database: getPool(),

    advanced: {
      cookiePrefix: "ezsh", // cookie « ezsh.session_token » (l'ancien cookie était « ezsh_session »)
      database: { generateId: () => randomUUID() }, // ids texte uuid, comme users.id
    },

    session: {
      expiresIn: 60 * 60 * 24 * 30, // 30 jours, comme avant
      fields: {
        expiresAt: "expires_at",
        createdAt: "created_at",
        updatedAt: "updated_at",
        ipAddress: "ip_address",
        userAgent: "user_agent",
        userId: "user_id",
      },
    },

    user: {
      modelName: "users",
      fields: {
        emailVerified: "email_verified",
        createdAt: "created_at",
        updatedAt: "updated_at",
      },
      additionalFields: {
        role: { type: "string", required: false, defaultValue: "user", input: false },
        plan: { type: "string", required: false, defaultValue: "free", input: false },
        status: { type: "string", required: false, defaultValue: "active", input: false },
        githubId: { type: "string", required: false, input: false, fieldName: "github_id" },
        githubLogin: { type: "string", required: false, input: false, fieldName: "github_login" },
        dailyLimitOverride: { type: "number", required: false, input: false, fieldName: "daily_limit_override" },
        overrideExpiresAt: { type: "date", required: false, input: false, fieldName: "override_expires_at" },
      },
    },

    account: {
      fields: {
        accountId: "account_id",
        providerId: "provider_id",
        userId: "user_id",
        accessToken: "access_token",
        refreshToken: "refresh_token",
        idToken: "id_token",
        accessTokenExpiresAt: "access_token_expires_at",
        refreshTokenExpiresAt: "refresh_token_expires_at",
        createdAt: "created_at",
        updatedAt: "updated_at",
      },
      encryptOAuthTokens: true,
      accountLinking: { enabled: true, trustedProviders: ["github"] },
    },

    verification: {
      fields: {
        expiresAt: "expires_at",
        createdAt: "created_at",
        updatedAt: "updated_at",
      },
    },

    socialProviders: githubEnabled
      ? {
          github: {
            clientId: env.githubClientId,
            clientSecret: env.githubClientSecret,
            mapProfileToUser: (profile) => ({
              githubId: String(profile.id),
              githubLogin: profile.login,
            }),
          },
        }
      : {},

    plugins: [
      magicLink({
        expiresIn: 15 * 60,
        storeToken: "hashed", // seul le haché du jeton est stocké, comme avant
        sendMagicLink: async ({ email, url }) => {
          await sendLoginEmail(email, url);
        },
      }),
    ],

    databaseHooks: {
      user: {
        create: {
          before: async (user) => {
            const email = (user.email ?? "").toLowerCase();
            return {
              data: {
                ...user,
                email,
                name: user.name || email.split("@")[0] || "",
                // Bootstrap admin : ADMIN_EMAILS (même règle qu'avant).
                role: email && env.adminEmails.includes(email) ? "admin" : "user",
              },
            };
          },
          after: async (user, ctx) => {
            await recordAuditLog(user.id, "user_registered", user.id, { method: methodOf(ctx?.path), email: user.email });
          },
        },
      },
      session: {
        create: {
          // Un compte suspendu ne peut plus ouvrir de session.
          before: async (session) => {
            const res = await getPool().query(`SELECT status FROM users WHERE id = $1`, [session.userId]);
            if (res.rows[0]?.status === "banned") return false;
          },
          after: async (session, ctx) => {
            await recordAuditLog(session.userId, "login", session.userId, { method: methodOf(ctx?.path) });
          },
        },
      },
    },
  });
}

function methodOf(path: string | undefined): string {
  if (!path) return "unknown";
  if (path.includes("magic-link")) return "magic_link";
  if (path.includes("callback")) return "github";
  return "unknown";
}

export type Auth = ReturnType<typeof createAuth>;

let instance: Auth | null = null;

export function getAuth(): Auth {
  if (!instance) instance = createAuth();
  return instance;
}

/** Pour les tests : force la recréation (variables d'environnement modifiées). */
export function resetAuthForTests(): void {
  instance = null;
}
