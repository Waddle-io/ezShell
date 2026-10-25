import type pg from "pg";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { closePool } from "@/lib/db";
import { ask, me, registerDevice, versionInfo } from "@/lib/handlers";
import { compareVersions, latestReleased } from "@/lib/version";
import { FakeLLM, body, resetDb, setupEnv } from "./helpers";

let db: pg.Pool;
const auth = (t: string) => `Bearer ${t}`;

async function newToken(ip = "1.2.3.4"): Promise<string> {
  const r = await registerDevice(ip);
  return r.body.device_token as string;
}

/** Rattache l'appareil du jeton à un utilisateur du plan donné. */
async function accountFor(plan: "free" | "premium" | "unlimited", extra = ""): Promise<string> {
  const t = await newToken(`10.0.${Math.floor(Math.random() * 250)}.${Math.floor(Math.random() * 250)}`);
  const u = (await db.query(`INSERT INTO users (id, email, plan ${extra ? ", " + extra.split("=")[0] : ""}) VALUES (gen_random_uuid()::text, $1, $2 ${extra ? ", " + extra.split("=")[1] : ""}) RETURNING id`,
    [`u${Math.random()}@x.io`, plan])).rows[0].id;
  await db.query("UPDATE devices SET user_id = $1 WHERE id = (SELECT id FROM devices ORDER BY created_at DESC LIMIT 1)", [u]);
  return t;
}

beforeAll(async () => { setupEnv(); db = await resetDb(); });
afterAll(async () => { await closePool(); await db.end(); });
beforeEach(async () => {
  setupEnv();
  await db.query("TRUNCATE ask_metrics, login_tokens, usage_daily, rate_hits, settings, devices, users CASCADE");
});

describe("plans et limites", () => {
  it("gratuit : limite du compte ; premium : limite premium", async () => {
    const free = await accountFor("free");
    const prem = await accountFor("premium");
    expect((await me(auth(free))).body).toMatchObject({ kind: "account", plan: "free", limits: { daily: 20 }, remaining: 20 });
    expect((await me(auth(prem))).body).toMatchObject({ kind: "account", plan: "premium", limits: { daily: 30 }, remaining: 30 });
  });

  it("le quota premium est bien appliqué (429 avec scope premium)", async () => {
    setupEnv({ PREMIUM_DAILY_LIMIT: "2" });
    const t = await accountFor("premium");
    const llm = new FakeLLM();
    expect((await ask(auth(t), body(), llm)).status).toBe(200);
    expect((await ask(auth(t), body(), llm)).status).toBe(200);
    const blocked = await ask(auth(t), body(), llm);
    expect(blocked.status).toBe(429);
    expect(blocked.body.scope).toBe("premium");
  });

  it("illimité : pas de quota journalier, mais la rafale s'applique toujours", async () => {
    setupEnv({ BURST_PER_MINUTE: "4" });
    const t = await accountFor("unlimited");
    const llm = new FakeLLM();
    const rs = [];
    for (let i = 0; i < 6; i++) rs.push(await ask(auth(t), body(), llm));
    expect(rs.slice(0, 4).every((r) => r.status === 200)).toBe(true);
    expect(rs[4].status).toBe(429);
    expect(rs[4].body.scope).toBe("burst");
    expect((await me(auth(t))).body).toMatchObject({ plan: "unlimited", limits: { daily: null }, remaining: null });
  });

  it("illimité : n'est pas bloqué par le plafond global", async () => {
    setupEnv({ GLOBAL_DAILY_SPEND_CAP: "1" });
    const normal = await newToken("5.5.5.5");
    const team = await accountFor("unlimited");
    expect((await ask(auth(normal), body(), new FakeLLM())).status).toBe(200);
    expect((await ask(auth(normal), body(), new FakeLLM())).status).toBe(503);
    expect((await ask(auth(team), body(), new FakeLLM())).status).toBe(200);
  });

  it("limite personnalisée, avec expiration", async () => {
    const t = await accountFor("free", "daily_limit_override=3");
    expect((await me(auth(t))).body.remaining).toBe(3);
    await db.query("UPDATE users SET override_expires_at = now() - interval '1 hour'");
    expect((await me(auth(t))).body.remaining).toBe(20); // expirée : retour à la limite du plan
    await db.query("UPDATE users SET override_expires_at = now() + interval '1 hour'");
    expect((await me(auth(t))).body.remaining).toBe(3);
  });

  it("compte banni : 403 partout, sans consommer de quota", async () => {
    const t = await accountFor("premium");
    await db.query("UPDATE users SET status = 'banned'");
    const llm = new FakeLLM();
    expect((await ask(auth(t), body(), llm)).status).toBe(403);
    expect((await me(auth(t))).status).toBe(403);
    expect(llm.calls).toHaveLength(0);
  });

  it("les limites en base priment sur l'environnement (sans redéployer)", async () => {
    const t = await accountFor("free");
    await db.query("INSERT INTO settings (key, value) VALUES ('limit.free', '7'), ('limit.premium', '9')");
    expect((await me(auth(t))).body.remaining).toBe(7);
    const anon = await newToken("7.7.7.7");
    await db.query("INSERT INTO settings (key, value) VALUES ('limit.anonymous', '2')");
    expect((await me(auth(anon))).body.remaining).toBe(2);
  });
});

describe("versions", () => {
  it("compare les versions", () => {
    expect(compareVersions("0.2.0", "0.10.0")).toBe(-1);
    expect(compareVersions("1.0.0", "0.9.9")).toBe(1);
    expect(compareVersions("v0.3", "0.3.0")).toBe(0);
    expect(compareVersions("", "0.0.1")).toBe(-1);
  });

  it("annonce la dernière version publiée (et seulement elle)", () => {
    expect(latestReleased()).toBe("0.3.0");
    expect(latestReleased("0.9.0")).toBe("0.9.0"); // surcharge explicite (réglage en base)
    expect(latestReleased("pas-une-version")).toBe("0.3.0");
  });

  it("GET /version : dernière version, minimale, notes cumulées", async () => {
    await db.query("INSERT INTO settings (key, value) VALUES ('min_client_version', '0.2.0')");
    const r = await versionInfo("0.1.0");
    expect(r.status).toBe(200);
    expect(r.body).toMatchObject({ latest: "0.3.0", min_supported: "0.2.0" });
    expect((r.body.releases as Array<{ version: string }>).map((x) => x.version)).toEqual(["0.2.0", "0.3.0"]);
    expect(((await versionInfo("0.2.0")).body.releases as Array<{ version: string }>).map((x) => x.version)).toEqual(["0.3.0"]); // seule la version suivante est nouvelle
  });

  it("x-ezsh-latest est renvoyé avec les réponses authentifiées", async () => {
    const t = await newToken();
    expect((await ask(auth(t), body(), new FakeLLM())).headers?.["x-ezsh-latest"]).toBe("0.3.0");
    expect((await me(auth(t))).headers?.["x-ezsh-latest"]).toBe("0.3.0");
  });

  it("426 pour un client sous la version minimale, sans consommer de quota", async () => {
    await db.query("INSERT INTO settings (key, value) VALUES ('min_client_version', '0.2.0')");
    const t = await newToken();
    const llm = new FakeLLM();
    const old = await ask(auth(t), body({ client_version: "0.1.0" }), llm);
    expect(old.status).toBe(426);
    expect(old.body).toMatchObject({ error: "update_required", min_supported: "0.2.0" });
    expect((await ask(auth(t), body(), llm)).status).toBe(426); // sans version : traité comme très ancien
    expect(llm.calls).toHaveLength(0);
    expect((await me(auth(t))).body.remaining).toBe(5);
    expect((await ask(auth(t), body({ client_version: "0.2.0" }), llm)).status).toBe(200);
  });
});

describe("mesure sans contenu", () => {
  it("enregistre tokens, latence, palier et empreinte, jamais le contenu", async () => {
    const t = await newToken();
    const llm = new FakeLLM({ text: JSON.stringify({ command: "ls", explanation: "e", cause: "c", risk: "low", risk_reason: "r", assumptions: [], confidence: "high" }), usage: { promptTokens: 120, completionTokens: 40 } });
    await ask(auth(t), body({ query: "mot-secret-zzz", context: { last_command: "cmd-zzz", stderr_tail: "err-zzz", cwd: "~", os: "linux", shell: "bash", exit_code: 1 } }), llm);
    const rows = (await db.query("SELECT * FROM ask_metrics")).rows;
    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({ tier: "anonymous", mode: "explain_error", outcome: "ok", prompt_tokens: 120, completion_tokens: 40 });
    expect(rows[0].latency_ms).toBeGreaterThanOrEqual(0);
    expect(rows[0].fingerprint).toMatch(/^[0-9a-f]{32}$/);
    expect(JSON.stringify(rows)).not.toMatch(/zzz/);
  });

  it("la même erreur (chiffres différents) donne la même empreinte", async () => {
    const t = await newToken();
    const mk = (n: number) => body({ context: { last_command: "npm install", stderr_tail: `ENOENT line ${n}`, cwd: "~", os: "linux", shell: "bash", exit_code: 1 } });
    await ask(auth(t), mk(12), new FakeLLM());
    await ask(auth(t), mk(98), new FakeLLM());
    const fps = (await db.query("SELECT fingerprint FROM ask_metrics")).rows.map((r) => r.fingerprint);
    expect(fps[0]).toBe(fps[1]);
  });

  it("note les refus (quota, rafale) et les erreurs amont (dont 429 Groq)", async () => {
    setupEnv({ ANON_DAILY_LIMIT: "1" });
    const t = await newToken();
    await ask(auth(t), body(), new FakeLLM());
    await ask(auth(t), body(), new FakeLLM()); // refus quota
    await db.query("TRUNCATE usage_daily");
    const { UpstreamError } = await import("@/lib/llm");
    await ask(auth(t), body(), new FakeLLM(() => { throw new UpstreamError("status 429"); }));
    await ask(auth(t), body(), new FakeLLM(() => { throw new UpstreamError("status 503"); }));
    const outcomes = (await db.query("SELECT outcome FROM ask_metrics ORDER BY id")).rows.map((r) => r.outcome);
    expect(outcomes).toEqual(["ok", "refused_quota", "upstream_429", "upstream_error"]);
  });

  it("une panne de la table de mesure ne casse jamais /ask", async () => {
    const t = await newToken();
    await db.query("ALTER TABLE ask_metrics RENAME TO ask_metrics_off");
    try {
      expect((await ask(auth(t), body(), new FakeLLM())).status).toBe(200);
    } finally {
      await db.query("ALTER TABLE ask_metrics_off RENAME TO ask_metrics");
    }
  });
});
