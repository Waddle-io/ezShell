import { env, missingConfig } from "./env";
import { getPool } from "./db";
import { buildPrompts, GroqProvider, UpstreamError, type LLMProvider, type LLMResult } from "./llm";
import { fingerprint, recordAsk, type Outcome } from "./metrics";
import { entitlement, UNLIMITED, type AuthedDevice, type Entitlement } from "./plans";
import { nextUtcMidnight, readDaily, refundDaily, takeDaily, takeWindow } from "./quota";
import { redact } from "./redact";
import { AskRequest, InvalidModelResponse, parseModelJson } from "./schema";
import { loadSettings, type Settings } from "./settings";
import { bearer, hashIp, hashToken, newDeviceToken } from "./tokens";
import { compareVersions, latestReleased, notesBetween } from "./version";

export interface Result {
  status: number;
  body: Record<string, unknown>;
  headers?: Record<string, string>;
}

const unavailable = (): Result => ({ status: 503, body: { error: "unavailable" } });
const unauthorized = (): Result => ({ status: 401, body: { error: "unauthorized" } });
const banned = (): Result => ({ status: 403, body: { error: "banned" } });

/** Ajoute la dernière version publiée à une réponse : la CLI s'en sert pour son rappel quotidien. */
function withVersion(r: Result, s: Settings): Result {
  return { ...r, headers: { ...r.headers, "x-ezsh-latest": latestReleased(s.latestVersion) } };
}

/** Jeton valide et non révoqué (+ plan du compte), sinon null. Met à jour last_seen_at. */
export async function authenticate(authHeader: string | null): Promise<AuthedDevice | null> {
  const token = bearer(authHeader);
  if (!token) return null;
  const r = await getPool().query(
    `WITH d AS (
       UPDATE devices SET last_seen_at = now()
       WHERE token_hash = $1 AND revoked_at IS NULL RETURNING id, user_id
     )
     SELECT d.id, d.user_id, u.plan, u.status, u.daily_limit_override, u.override_expires_at
     FROM d LEFT JOIN users u ON u.id = d.user_id`,
    [hashToken(token)],
  );
  return r.rowCount ? (r.rows[0] as AuthedDevice) : null;
}

/** POST /device/register : crée un appareil anonyme et renvoie un jeton (stocké haché). */
export async function registerDevice(ip: string): Promise<Result> {
  if (missingConfig().length) return unavailable();
  const pool = getPool();
  const ipHash = hashIp(ip);
  const gate = await takeWindow(pool, `reg:${ipHash}`, "hour", env.registerPerIpHour);
  if (!gate.ok) return { status: 429, body: { scope: "register", reset_at: gate.resetAt } };
  const token = newDeviceToken();
  await pool.query(`INSERT INTO devices (token_hash, ip_hash) VALUES ($1, $2)`, [hashToken(token), ipHash]);
  const s = await loadSettings(pool);
  return { status: 201, body: { device_token: token, limits: { daily: s.anonymousLimit } } };
}

/** GET /version : publique. Dernière version publiée, version minimale, notes cumulées depuis `from`. */
export async function versionInfo(from: string | null): Promise<Result> {
  if (missingConfig().length) return unavailable();
  const s = await loadSettings(getPool());
  const latest = latestReleased(s.latestVersion);
  const releases = from ? notesBetween(from, latest) : notesBetween("0.0.0", latest).slice(-1);
  return { status: 200, body: { latest, min_supported: s.minClientVersion, releases } };
}

/** GET /me : état du compte (anonyme ou compte), plan, requêtes restantes. */
export async function me(authHeader: string | null): Promise<Result> {
  if (missingConfig().length) return unavailable();
  const device = await authenticate(authHeader);
  if (!device) return unauthorized();
  const pool = getPool();
  const s = await loadSettings(pool);
  const ent = entitlement(device, s);
  if (ent.banned) return withVersion(banned(), s);
  const unlimited = ent.tier === "unlimited";
  const used = unlimited ? 0 : await readDaily(pool, ent.subjectType, ent.subjectId);
  return withVersion(
    {
      status: 200,
      body: {
        kind: ent.tier === "anonymous" ? "anonymous" : "account",
        plan: ent.tier,
        limits: { daily: unlimited ? null : ent.limit },
        remaining: unlimited ? null : Math.max(0, ent.limit - used),
        reset_at: nextUtcMidnight(),
      },
    },
    s,
  );
}

function llmText(r: string | LLMResult): { text: string; prompt: number; completion: number } {
  if (typeof r === "string") return { text: r, prompt: 0, completion: 0 };
  return { text: r.text, prompt: r.usage?.promptTokens ?? 0, completion: r.usage?.completionTokens ?? 0 };
}

/** POST /ask : auth → réglages → coupe-circuit → validation → version → débit → quotas → masquage → modèle. */
export async function ask(
  authHeader: string | null,
  rawBody: unknown,
  llm: LLMProvider = new GroqProvider(),
): Promise<Result> {
  if (missingConfig().length) return unavailable();
  const device = await authenticate(authHeader);
  if (!device) return unauthorized();
  const pool = getPool();
  const settings = await loadSettings(pool);
  return withVersion(await askAuthed(device, settings, rawBody, llm), settings);
}

async function askAuthed(device: AuthedDevice, settings: Settings, rawBody: unknown, llm: LLMProvider): Promise<Result> {
  const pool = getPool();
  const ent = entitlement(device, settings);
  if (ent.banned) return banned();
  if (settings.killSwitch) return { status: 503, body: { error: "kill_switch" } };

  const parsed = AskRequest.safeParse(rawBody);
  if (!parsed.success) return { status: 400, body: { error: "invalid_request" } };
  const req = parsed.data;

  // Version minimale : un client trop ancien (ou sans version) est invité à se mettre à jour, sans rien consommer.
  const clientVersion = req.client_version || "0.0.0";
  if (compareVersions(clientVersion, settings.minClientVersion) < 0) {
    return {
      status: 426,
      body: { error: "update_required", min_supported: settings.minClientVersion, latest: latestReleased(settings.latestVersion) },
    };
  }
  if (llm instanceof GroqProvider && (!env.groqKey || !env.model)) return unavailable();

  const refused = (outcome: Outcome) => recordAsk(pool, { tier: ent.tier, mode: req.mode, outcome });

  const burst = await takeWindow(pool, `burst:${device.id}`, "minute", env.burstPerMinute);
  if (!burst.ok) {
    await refused("refused_burst");
    return { status: 429, body: { scope: "burst", reset_at: burst.resetAt } };
  }

  const daily = await takeDaily(pool, ent.subjectType, ent.subjectId, ent.limit);
  if (!daily.ok) {
    await refused("refused_quota");
    return { status: 429, body: { scope: ent.tier === "anonymous" ? "anonymous" : ent.tier, reset_at: nextUtcMidnight() } };
  }
  // Les comptes illimités (équipe) ne sont jamais bloqués par le plafond global, mais restent comptés.
  const global = await takeDaily(pool, "global", "all", ent.tier === "unlimited" ? UNLIMITED : settings.globalCap);
  if (!global.ok) {
    await refundDaily(pool, ent.subjectType, ent.subjectId);
    await refused("refused_global");
    return { status: 503, body: { error: "limited" } };
  }

  // Seconde passe de masquage : on ne fait pas confiance au client.
  const safe: AskRequest = {
    ...req,
    query: redact(req.query),
    context: {
      ...req.context,
      cwd: redact(req.context.cwd),
      last_command: redact(req.context.last_command),
      stderr_tail: redact(req.context.stderr_tail),
    },
  };
  const { system, user } = buildPrompts(safe);
  const fp = fingerprint(req.mode, safe.query, safe.context.last_command, safe.context.stderr_tail);
  const started = Date.now();
  let promptTokens = 0;
  let completionTokens = 0;

  const failed = async (outcome: Outcome) => {
    await refundDaily(pool, ent.subjectType, ent.subjectId);
    await refundDaily(pool, "global", "all");
    await recordAsk(pool, {
      tier: ent.tier, mode: req.mode, outcome, fingerprint: fp, latencyMs: Date.now() - started,
      promptTokens: promptTokens || null, completionTokens: completionTokens || null,
    });
  };

  try {
    for (let attempt = 0; attempt < 2; attempt++) {
      const out = llmText(await llm.complete(system, user));
      promptTokens += out.prompt;
      completionTokens += out.completion;
      try {
        const answer = parseModelJson(out.text);
        await recordAsk(pool, {
          tier: ent.tier, mode: req.mode, outcome: "ok", fingerprint: fp, latencyMs: Date.now() - started,
          promptTokens: promptTokens || null, completionTokens: completionTokens || null,
        });
        const headers: Record<string, string> =
          ent.tier === "unlimited" ? {} : { "x-ezsh-remaining": String(Math.max(0, ent.limit - daily.count)) };
        return { status: 200, body: { ...answer }, headers };
      } catch (err) {
        if (!(err instanceof InvalidModelResponse)) throw err; // sinon : un nouvel essai, puis échec propre
      }
    }
    await failed("invalid_model_response");
    return { status: 502, body: { error: "invalid_model_response" } };
  } catch (err) {
    // Le service ne doit pas facturer un appel raté. Aucun contenu n'est journalisé.
    const msg = err instanceof Error ? err.message : "inconnu";
    await failed(/status 429/.test(msg) ? "upstream_429" : "upstream_error");
    console.error("[ask] échec amont :", msg);
    return { status: 502, body: { error: err instanceof UpstreamError ? "upstream" : "internal" } };
  }
}

export type { Entitlement };
