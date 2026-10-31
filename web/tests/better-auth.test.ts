import { readFileSync } from "node:fs";
import type pg from "pg";
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { getWebSessionUser } from "@/lib/auth";
import { getAuth, resetAuthForTests } from "@/lib/better-auth";
import { closePool } from "@/lib/db";
import { resetDb, setupEnv } from "./helpers";

// On intercepte l'envoi d'e-mail pour récupérer le lien magique.
const sent = vi.hoisted(() => [] as Array<{ email: string; url: string }>);
vi.mock("@/lib/mailer", () => ({
  sendLoginEmail: async (email: string, url: string) => { sent.push({ email, url }); },
}));

const BASE = "http://localhost:3000";
let db: pg.Pool;

function env() {
  setupEnv({
    BETTER_AUTH_SECRET: "test-secret-0123456789abcdef0123456789abcdef",
    PUBLIC_BASE_URL: BASE,
    ADMIN_EMAILS: "boss@example.com",
  });
}

/** Parcours complet : demande du lien → clic sur le lien → cookie de session. */
async function signInWithMagicLink(email: string): Promise<{ cookie: string | null; location: string | null }> {
  sent.length = 0;
  const ask = await getAuth().handler(new Request(`${BASE}/api/auth/sign-in/magic-link`, {
    method: "POST",
    headers: { "content-type": "application/json", origin: BASE },
    body: JSON.stringify({ email, callbackURL: "/dashboard" }),
  }));
  expect(ask.status).toBe(200);
  expect(sent).toHaveLength(1);

  const verify = await getAuth().handler(new Request(sent[0].url, { headers: { origin: BASE } }));
  const cookies = verify.headers.getSetCookie().map((c) => c.split(";")[0]);
  return { cookie: cookies.length ? cookies.join("; ") : null, location: verify.headers.get("location") };
}

beforeAll(async () => { env(); db = await resetDb(); });
afterAll(async () => { await closePool(); await db.end(); });
beforeEach(async () => {
  env();
  resetAuthForTests();
  await db.query("TRUNCATE audit_logs, users CASCADE");
  process.env.ADMIN_EMAILS = "boss@example.com";
});

describe("connexion par lien magique", () => {
  it("crée l'utilisateur, ouvre une session et getWebSessionUser la reconnaît", async () => {
    const { cookie, location } = await signInWithMagicLink("Alice@Example.com");
    expect(cookie).toContain("ezsh.session_token=");
    expect(location).toContain("/dashboard");

    const user = await getWebSessionUser(cookie);
    expect(user).toMatchObject({ email: "alice@example.com", role: "user", plan: "free", status: "active" });
    expect(user?.id).toBeTruthy();
    expect(user?.created_at).toBeInstanceOf(Date);

    const audit = await db.query("SELECT action FROM audit_logs ORDER BY id");
    expect(audit.rows.map((r) => r.action)).toEqual(["user_registered", "login"]);
  });

  it("promeut en admin un e-mail listé dans ADMIN_EMAILS", async () => {
    const { cookie } = await signInWithMagicLink("boss@example.com");
    expect((await getWebSessionUser(cookie))?.role).toBe("admin");
  });

  it("garde l'id, le plan et les appareils d'un compte existant", async () => {
    await db.query(
      `INSERT INTO users (id, email, plan, email_verified) VALUES ('legacy-user-1', 'bob@example.com', 'premium', true)`,
    );
    const { cookie } = await signInWithMagicLink("bob@example.com");
    const user = await getWebSessionUser(cookie);
    expect(user).toMatchObject({ id: "legacy-user-1", plan: "premium" });
    expect((await db.query("SELECT count(*)::int AS n FROM users")).rows[0].n).toBe(1);
  });

  it("n'ouvre pas de session pour un compte suspendu", async () => {
    await db.query(`INSERT INTO users (id, email, status, email_verified) VALUES ('u-banned', 'eve@example.com', 'banned', true)`);
    sent.length = 0;
    await getAuth().handler(new Request(`${BASE}/api/auth/sign-in/magic-link`, {
      method: "POST",
      headers: { "content-type": "application/json", origin: BASE },
      body: JSON.stringify({ email: "eve@example.com" }),
    }));
    const verify = await getAuth().handler(new Request(sent[0].url, { headers: { origin: BASE } }));
    const cookies = verify.headers.getSetCookie().map((c) => c.split(";")[0]).join("; ");
    expect(await getWebSessionUser(cookies || null)).toBeNull();
    expect((await db.query("SELECT count(*)::int AS n FROM session")).rows[0].n).toBe(0);
  });

  it("le lien est à usage unique", async () => {
    sent.length = 0;
    await getAuth().handler(new Request(`${BASE}/api/auth/sign-in/magic-link`, {
      method: "POST",
      headers: { "content-type": "application/json", origin: BASE },
      body: JSON.stringify({ email: "once@example.com" }),
    }));
    const url = sent[0].url;
    const first = await getAuth().handler(new Request(url, { headers: { origin: BASE } }));
    const second = await getAuth().handler(new Request(url, { headers: { origin: BASE } }));
    expect(first.headers.getSetCookie().length).toBeGreaterThan(0);
    expect(second.headers.getSetCookie().length).toBe(0);
  });
});

describe("configuration de production", () => {
  it("refuse de démarrer sans PUBLIC_BASE_URL (sinon lien magique piégeable via l'en-tête Host)", () => {
    const previous = process.env.NODE_ENV;
    const base = process.env.PUBLIC_BASE_URL;
    try {
      (process.env as Record<string, string>).NODE_ENV = "production";
      delete process.env.PUBLIC_BASE_URL;
      resetAuthForTests();
      expect(() => getAuth()).toThrow(/PUBLIC_BASE_URL/);
    } finally {
      (process.env as Record<string, string>).NODE_ENV = previous ?? "test";
      if (base) process.env.PUBLIC_BASE_URL = base;
      resetAuthForTests();
    }
  });
});

describe("connexion GitHub", () => {
  it("redirige vers GitHub avec le nouveau callback /api/auth/callback/github", async () => {
    setupEnv({ GITHUB_CLIENT_ID: "gh-id", GITHUB_CLIENT_SECRET: "gh-secret" });
    resetAuthForTests();
    const res = await getAuth().handler(new Request(`${BASE}/api/auth/sign-in/social`, {
      method: "POST",
      headers: { "content-type": "application/json", origin: BASE },
      body: JSON.stringify({ provider: "github", callbackURL: "/dashboard" }),
    }));
    expect(res.status).toBe(200);
    const { url } = (await res.json()) as { url: string };
    const target = new URL(url);
    expect(target.origin + target.pathname).toBe("https://github.com/login/oauth/authorize");
    expect(target.searchParams.get("client_id")).toBe("gh-id");
    expect(target.searchParams.get("redirect_uri")).toBe(`${BASE}/api/auth/callback/github`);
    delete process.env.GITHUB_CLIENT_ID;
    delete process.env.GITHUB_CLIENT_SECRET;
  });
});

describe("getWebSessionUser", () => {
  it("renvoie null sans cookie, avec un cookie inconnu ou falsifié", async () => {
    expect(await getWebSessionUser(null)).toBeNull();
    expect(await getWebSessionUser("foo=bar")).toBeNull();
    expect(await getWebSessionUser("ezsh.session_token=forge.signature")).toBeNull();
  });

  it("ignore l'ancien cookie de session maison (supprimé)", async () => {
    await db.query(`INSERT INTO users (id, email, email_verified) VALUES ('old-1', 'old@example.com', true)`);
    expect(await getWebSessionUser("ezsh_session=ezs_nimportequoi")).toBeNull();
  });
});

describe("rôle admin (ADMIN_EMAILS)", () => {
  it("promeut un compte déjà existant dont l'e-mail est ajouté plus tard à ADMIN_EMAILS", async () => {
    const { cookie } = await signInWithMagicLink("later@example.com");
    expect((await getWebSessionUser(cookie))?.role).toBe("user");

    process.env.ADMIN_EMAILS = "boss@example.com, later@example.com";
    expect((await getWebSessionUser(cookie))?.role).toBe("admin");
    expect((await db.query("SELECT role FROM users WHERE email = 'later@example.com'")).rows[0].role).toBe("admin");
  });

  it("ne promeut pas les autres comptes", async () => {
    const { cookie } = await signInWithMagicLink("simple@example.com");
    expect((await getWebSessionUser(cookie))?.role).toBe("user");
  });

  it("lie un compte créé par `npm run admin -- user create` (e-mail non vérifié) à la première connexion", async () => {
    await db.query(`INSERT INTO users (id, email, plan) VALUES ('pre-1', 'pre@example.com', 'premium')`);
    const { cookie } = await signInWithMagicLink("pre@example.com");
    expect(await getWebSessionUser(cookie)).toMatchObject({ id: "pre-1", plan: "premium" });
    expect((await db.query("SELECT email_verified FROM users WHERE id = 'pre-1'")).rows[0].email_verified).toBe(true);
  });
});

describe("migration du schéma existant", () => {
  it("rattrape les comptes déjà présents (e-mail vérifié, nom, e-mail GitHub, account)", async () => {
    // On remet la base dans l'état d'avant Better Auth, avec des comptes réels.
    await db.query("DROP TABLE IF EXISTS session, account, verification CASCADE");
    await db.query("ALTER TABLE users DROP COLUMN name, DROP COLUMN email_verified, DROP COLUMN image, DROP COLUMN updated_at");
    await db.query("CREATE TABLE web_sessions (id text PRIMARY KEY)");
    await db.query("CREATE TABLE login_tokens (token_hash text PRIMARY KEY)");
    await db.query(`INSERT INTO users (id, email, github_id, github_login) VALUES ('a', 'a@example.com', '111', 'alice-gh')`);
    await db.query(`INSERT INTO users (id, email) VALUES ('b', 'b@example.com')`);
    await db.query(`INSERT INTO users (id, github_id, github_login) VALUES ('c', '333', 'no-mail')`);

    const schema = readFileSync(new URL("../db/schema.sql", import.meta.url), "utf8");
    await db.query(schema);
    await db.query(schema); // idempotent : une 2e exécution ne change rien

    const users = (await db.query("SELECT id, email, email_verified, name FROM users ORDER BY id")).rows;
    expect(users).toEqual([
      { id: "a", email: "a@example.com", email_verified: true, name: "alice-gh" },
      { id: "b", email: "b@example.com", email_verified: true, name: "b" },
      { id: "c", email: "333+no-mail@users.noreply.github.com", email_verified: false, name: "no-mail" },
    ]);

    const legacy = await db.query(
      "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema() AND table_name IN ('web_sessions', 'login_tokens')",
    );
    expect(legacy.rowCount).toBe(0);

    const accounts = (await db.query("SELECT provider_id, account_id, user_id FROM account ORDER BY user_id")).rows;
    expect(accounts).toEqual([
      { provider_id: "github", account_id: "111", user_id: "a" },
      { provider_id: "github", account_id: "333", user_id: "c" },
    ]);
  });
});
