import type pg from "pg";
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { POST as approve } from "@/app/api/v1/auth/device/approve/route";
import { POST as deviceCode } from "@/app/api/v1/auth/device/code/route";
import { POST as deviceToken } from "@/app/api/v1/auth/device/token/route";
import { GET as usage } from "@/app/api/v1/usage/route";
import { getAuth, resetAuthForTests } from "@/lib/better-auth";
import { closePool } from "@/lib/db";
import { resetDb, setupEnv } from "./helpers";

const sent = vi.hoisted(() => [] as Array<{ email: string; url: string }>);
vi.mock("@/lib/mailer", () => ({
  sendLoginEmail: async (email: string, url: string) => { sent.push({ email, url }); },
}));

const BASE = "http://localhost:3000";
let db: pg.Pool;

const json = (body: unknown, headers: Record<string, string> = {}) => ({
  method: "POST",
  headers: { "content-type": "application/json", ...headers },
  body: JSON.stringify(body),
});

async function login(email: string): Promise<string> {
  sent.length = 0;
  await getAuth().handler(new Request(`${BASE}/api/auth/sign-in/magic-link`, json({ email }, { origin: BASE })));
  const res = await getAuth().handler(new Request(sent[0].url, { headers: { origin: BASE } }));
  return res.headers.getSetCookie().map((c) => c.split(";")[0]).join("; ");
}

beforeAll(async () => { db = await resetDb(); });
afterAll(async () => { await closePool(); await db.end(); });
beforeEach(async () => {
  setupEnv({ BETTER_AUTH_SECRET: "test-secret-0123456789abcdef0123456789abcdef", PUBLIC_BASE_URL: BASE });
  resetAuthForTests();
  await db.query("TRUNCATE device_codes, audit_logs, devices, users CASCADE");
});

describe("connexion d'un terminal (device flow) avec une session Better Auth", () => {
  it("code → attente → approbation depuis le navigateur → jeton → quota", async () => {
    // 1. le terminal demande un code
    const codeRes = await deviceCode(new Request(`${BASE}/api/v1/auth/device/code`, json({})));
    expect(codeRes.status).toBe(200);
    const code = (await codeRes.json()) as { device_code: string; user_code: string; verification_uri_complete: string };
    expect(code.verification_uri_complete).toContain(`/activate?user_code=${code.user_code}`);

    // 2. pas encore approuvé
    const pending = await deviceToken(new Request(`${BASE}/api/v1/auth/device/token`, json({ device_code: code.device_code })));
    expect(pending.status).toBe(400);
    expect(((await pending.json()) as { error: string }).error).toBe("authorization_pending");

    // 3. l'utilisateur se connecte (lien magique) puis approuve le code
    const cookie = await login("cli@example.com");
    const ok = await approve(new Request(`${BASE}/api/v1/auth/device/approve`, json({ user_code: code.user_code }, { cookie })));
    expect(ok.status).toBe(200);

    // 4. le terminal récupère son accès
    const done = await deviceToken(new Request(`${BASE}/api/v1/auth/device/token`, json({ device_code: code.device_code })));
    expect(done.status).toBe(200);
    expect(((await done.json()) as { user: { email: string } }).user.email).toBe("cli@example.com");

    // 5. la page /activate et le dashboard lisent le compte via /usage avec le cookie
    const u = await usage(new Request(`${BASE}/api/v1/usage`, { headers: { cookie } }));
    expect(u.status).toBe(200);
    expect(((await u.json()) as { user: { email: string; plan: string } }).user).toMatchObject({ email: "cli@example.com", plan: "free" });
  });

  it("refuse l'approbation sans session et avec un faux code", async () => {
    const codeRes = await deviceCode(new Request(`${BASE}/api/v1/auth/device/code`, json({})));
    const code = (await codeRes.json()) as { user_code: string };

    const anon = await approve(new Request(`${BASE}/api/v1/auth/device/approve`, json({ user_code: code.user_code })));
    expect(anon.status).toBe(401);

    const cookie = await login("cli2@example.com");
    const bad = await approve(new Request(`${BASE}/api/v1/auth/device/approve`, json({ user_code: "ZZZZ-9999" }, { cookie })));
    expect(bad.status).toBeGreaterThanOrEqual(400);
  });

  it("/usage répond 401 sans session", async () => {
    const u = await usage(new Request(`${BASE}/api/v1/usage`));
    expect(u.status).toBe(401);
  });
});
