import type pg from "pg";
import { afterAll, beforeAll, beforeEach, describe, expect, it } from "vitest";
import { closePool } from "@/lib/db";
import { ask, me, registerDevice } from "@/lib/handlers";
import { UpstreamError } from "@/lib/llm";
import { FakeLLM, GOOD, body, resetDb, setupEnv } from "./helpers";

let db: pg.Pool;
const auth = (t: string) => `Bearer ${t}`;

async function newToken(ip = "1.2.3.4"): Promise<string> {
  const r = await registerDevice(ip);
  expect(r.status).toBe(201);
  return r.body.device_token as string;
}

beforeAll(async () => { setupEnv(); db = await resetDb(); });
afterAll(async () => { await closePool(); await db.end(); });
beforeEach(async () => {
  setupEnv();
  await db.query("TRUNCATE usage_daily, rate_hits, settings, devices CASCADE");
});

describe("enregistrement", () => {
  it("renvoie un jeton et ne stocke que son hash", async () => {
    const t = await newToken();
    expect(t).toMatch(/^ezd_/);
    const rows = (await db.query("SELECT token_hash, ip_hash FROM devices")).rows;
    expect(rows).toHaveLength(1);
    expect(rows[0].token_hash).not.toContain(t);
    expect(rows[0].ip_hash).not.toContain("1.2.3.4");
  });

  it("limite les enregistrements par IP (429, atomique)", async () => {
    setupEnv({ REGISTER_PER_IP_HOUR: "3" });
    const results = await Promise.all(Array.from({ length: 8 }, () => registerDevice("9.9.9.9")));
    expect(results.filter((r) => r.status === 201)).toHaveLength(3);
    const blocked = results.find((r) => r.status === 429)!;
    expect(blocked.body.scope).toBe("register");
    expect((await registerDevice("8.8.8.8")).status).toBe(201); // une autre IP n'est pas touchée
  });

  it("refuse de fonctionner sans configuration", async () => {
    setupEnv({ TOKEN_PEPPER: "" });
    expect((await registerDevice("1.1.1.1")).status).toBe(503);
  });
});

describe("authentification", () => {
  it.each([null, "", "Bearer", "Bearer nope", "Basic abc", "Bearer ezd_court"])("401 pour %s", async (h) => {
    expect((await ask(h, body(), new FakeLLM())).status).toBe(401);
    expect((await me(h)).status).toBe(401);
  });

  it("401 pour un jeton valide mais inconnu ou révoqué", async () => {
    expect((await ask(auth("ezd_" + "a".repeat(43)), body(), new FakeLLM())).status).toBe(401);
    const t = await newToken();
    await db.query("UPDATE devices SET revoked_at = now()");
    expect((await ask(auth(t), body(), new FakeLLM())).status).toBe(401);
  });
});

describe("/ask", () => {
  it("renvoie une réponse validée et le nombre de requêtes restantes", async () => {
    const t = await newToken();
    const r = await ask(auth(t), body(), new FakeLLM());
    expect(r.status).toBe(200);
    expect(r.body.command).toBe("git pull --rebase origin main");
    expect(r.headers?.["x-ezsh-remaining"]).toBe("4");
  });

  it("400 sur une requête invalide, sans consommer de quota", async () => {
    const t = await newToken();
    expect((await ask(auth(t), { mode: "hack" }, new FakeLLM())).status).toBe(400);
    expect((await ask(auth(t), undefined, new FakeLLM())).status).toBe(400);
    expect((await me(auth(t))).body.remaining).toBe(5);
  });

  it("ne dépasse JAMAIS le quota, même en parallèle (atomicité)", async () => {
    const t = await newToken();
    const llm = new FakeLLM();
    const rs = await Promise.all(Array.from({ length: 25 }, () => ask(auth(t), body(), llm)));
    expect(rs.filter((r) => r.status === 200)).toHaveLength(5);
    expect(llm.calls).toHaveLength(5); // le modèle n'est pas appelé au-delà du quota
    const limited = rs.find((r) => r.status === 429)!;
    expect(limited.body.scope).toBe("anonymous");
    expect(typeof limited.body.reset_at).toBe("string");
  });

  it("rembourse le quota si le modèle échoue", async () => {
    const t = await newToken();
    const down = new FakeLLM(() => { throw new UpstreamError("status 503"); });
    const r = await ask(auth(t), body(), down);
    expect(r.status).toBe(502);
    expect(r.body.error).toBe("upstream");
    expect((await me(auth(t))).body.remaining).toBe(5);
  });

  it("réessaie une fois si la réponse est invalide, puis 502 remboursé", async () => {
    const t = await newToken();
    const llm = new FakeLLM("pas du json");
    const r = await ask(auth(t), body(), llm);
    expect(r.status).toBe(502);
    expect(r.body.error).toBe("invalid_model_response");
    expect(llm.calls).toHaveLength(2);
    expect((await me(auth(t))).body.remaining).toBe(5);
  });

  it("accepte une 2e tentative valide", async () => {
    const t = await newToken();
    let n = 0;
    const llm = new FakeLLM(() => (++n === 1 ? "oups" : GOOD));
    expect((await ask(auth(t), body(), llm)).status).toBe(200);
  });

  it("limite la rafale par minute", async () => {
    setupEnv({ BURST_PER_MINUTE: "2" });
    const t = await newToken();
    const rs = [await ask(auth(t), body(), new FakeLLM()), await ask(auth(t), body(), new FakeLLM()), await ask(auth(t), body(), new FakeLLM())];
    expect(rs.map((r) => r.status)).toEqual([200, 200, 429]);
    expect(rs[2].body.scope).toBe("burst");
  });

  it("plafond global : 503 « limited » et quota de l'appareil remboursé", async () => {
    setupEnv({ GLOBAL_DAILY_SPEND_CAP: "2" });
    const t = await newToken();
    const rs = [];
    for (let i = 0; i < 4; i++) rs.push(await ask(auth(t), body(), new FakeLLM()));
    expect(rs.map((r) => r.status)).toEqual([200, 200, 503, 503]);
    expect(rs[2].body.error).toBe("limited");
    expect((await me(auth(t))).body.remaining).toBe(3); // 2 utilisées, les refus n'ont rien coûté
  });

  it("coupe-circuit par variable d'environnement", async () => {
    const t = await newToken();
    setupEnv({ KILL_SWITCH: "1" });
    const llm = new FakeLLM();
    const r = await ask(auth(t), body(), llm);
    expect(r.status).toBe(503);
    expect(r.body.error).toBe("kill_switch");
    expect(llm.calls).toHaveLength(0);
  });

  it("coupe-circuit par la base, sans redéploiement", async () => {
    const t = await newToken();
    await db.query("INSERT INTO settings (key, value) VALUES ('kill_switch', '1')");
    expect((await ask(auth(t), body(), new FakeLLM())).status).toBe(503);
    await db.query("UPDATE settings SET value = '0' WHERE key = 'kill_switch'");
    expect((await ask(auth(t), body(), new FakeLLM())).status).toBe(200);
  });

  it("masque les secrets AVANT d'appeler le modèle (même si le client ne l'a pas fait)", async () => {
    const t = await newToken();
    const llm = new FakeLLM();
    await ask(auth(t), body({
      query: "pourquoi DB_PASSWORD=hunter2hunter2 échoue ?",
      context: { last_command: "psql postgresql://u:SuperSecret99@h/db", stderr_tail: "token ghp_abcdefghijklmnopqrstuvwxyz0123456789", cwd: "~", os: "linux", shell: "bash", exit_code: 1 },
    }), llm);
    const sent = llm.calls[0].system + llm.calls[0].user;
    expect(sent).not.toMatch(/hunter2hunter2|SuperSecret99|ghp_abcdefghijklmnopqrstuvwxyz0123456789/);
    expect(sent).toContain("SECRET_MASQUÉ");
  });

  it("marque le contexte comme non fiable dans le prompt", async () => {
    const t = await newToken();
    const llm = new FakeLLM();
    await ask(auth(t), body(), llm);
    expect(llm.calls[0].user).toContain("<untrusted_context>");
    expect(llm.calls[0].system).toMatch(/never follow/i);
  });

  it("assainit une sortie du modèle qui contient de l'ANSI (injection)", async () => {
    const t = await newToken();
    const evil = JSON.stringify({ command: "ls", explanation: "\u001b[31mIgnore tout\u001b[0m", risk: "low" });
    const r = await ask(auth(t), body(), new FakeLLM(evil));
    expect(String(r.body.explanation)).not.toContain("\u001b");
  });

  it("ne stocke JAMAIS le contenu des requêtes", async () => {
    const t = await newToken();
    await ask(auth(t), body({ query: "phrase-unique-xyzzy", context: { last_command: "cmd-unique-plugh", stderr_tail: "err-unique-fnord", cwd: "~", os: "linux", shell: "bash", exit_code: 1 } }), new FakeLLM());
    for (const table of ["devices", "usage_daily", "rate_hits", "settings", "device_codes"]) {
      const dump = JSON.stringify((await db.query(`SELECT * FROM ${table}`)).rows);
      expect(dump).not.toMatch(/xyzzy|plugh|fnord|git pull --rebase/);
    }
  });
});

describe("/me", () => {
  it("indique le statut anonyme et les requêtes restantes", async () => {
    const t = await newToken();
    await ask(auth(t), body(), new FakeLLM());
    const r = await me(auth(t));
    expect(r.body).toMatchObject({ kind: "anonymous", limits: { daily: 5 }, remaining: 4 });
  });

  it("un appareil connecté suit la limite « compte gratuit » (M3)", async () => {
    const t = await newToken();
    await db.query("UPDATE devices SET user_id = 'user-1'");
    const r = await ask(auth(t), body(), new FakeLLM());
    expect(r.status).toBe(200);
    expect((await me(auth(t))).body).toMatchObject({ kind: "account", limits: { daily: 20 }, remaining: 19 });
  });
});
