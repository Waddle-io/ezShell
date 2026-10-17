import { env, missingConfig } from "./env";
import { getPool } from "./db";
import { buildPrompts, GroqProvider, UpstreamError, type LLMProvider } from "./llm";
import { nextUtcMidnight, readDaily, refundDaily, takeDaily, takeWindow } from "./quota";
import { redact } from "./redact";
import { AskRequest, InvalidModelResponse, parseModelJson } from "./schema";
import { bearer, hashIp, hashToken, newDeviceToken } from "./tokens";

export interface Result {
  status: number;
  body: Record<string, unknown>;
  headers?: Record<string, string>;
}

const unavailable = (): Result => ({ status: 503, body: { error: "unavailable" } });
const unauthorized = (): Result => ({ status: 401, body: { error: "unauthorized" } });

interface Device {
  id: string;
  user_id: string | null;
}

/** Jeton valide et non révoqué, sinon null. Met à jour last_seen_at. */
async function authenticate(authHeader: string | null): Promise<Device | null> {
  const token = bearer(authHeader);
  if (!token) return null;
  const r = await getPool().query(
    `UPDATE devices SET last_seen_at = now()
     WHERE token_hash = $1 AND revoked_at IS NULL RETURNING id, user_id`,
    [hashToken(token)],
  );
  return r.rowCount ? (r.rows[0] as Device) : null;
}

async function killSwitchOn(): Promise<boolean> {
  if (env.killSwitchEnv) return true;
  const r = await getPool().query(`SELECT value FROM settings WHERE key = 'kill_switch'`);
  return !!r.rowCount && r.rows[0].value === "1";
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
  return { status: 201, body: { device_token: token, limits: { daily: env.anonDailyLimit } } };
}

/** GET /me : état du compte (anonyme ou compte), requêtes restantes. */
export async function me(authHeader: string | null): Promise<Result> {
  if (missingConfig().length) return unavailable();
  const device = await authenticate(authHeader);
  if (!device) return unauthorized();
  const account = device.user_id !== null;
  const limit = account ? env.freeDailyLimit : env.anonDailyLimit;
  const used = await readDaily(getPool(), account ? "user" : "device", account ? device.user_id! : device.id);
  return {
    status: 200,
    body: { kind: account ? "account" : "anonymous", limits: { daily: limit }, remaining: Math.max(0, limit - used), reset_at: nextUtcMidnight() },
  };
}

/** POST /ask : auth → coupe-circuit → validation → débit → quotas → masquage → modèle → validation. */
export async function ask(
  authHeader: string | null,
  rawBody: unknown,
  llm: LLMProvider = new GroqProvider(),
): Promise<Result> {
  if (missingConfig().length) return unavailable();
  const device = await authenticate(authHeader);
  if (!device) return unauthorized();

  if (await killSwitchOn()) return { status: 503, body: { error: "kill_switch" } };

  const parsed = AskRequest.safeParse(rawBody);
  if (!parsed.success) return { status: 400, body: { error: "invalid_request" } };
  const req = parsed.data;
  if (llm instanceof GroqProvider && (!env.groqKey || !env.model)) return unavailable();

  const pool = getPool();
  const burst = await takeWindow(pool, `burst:${device.id}`, "minute", env.burstPerMinute);
  if (!burst.ok) return { status: 429, body: { scope: "burst", reset_at: burst.resetAt } };

  const account = device.user_id !== null;
  const subjectType = account ? "user" : "device";
  const subjectId = account ? device.user_id! : device.id;
  const limit = account ? env.freeDailyLimit : env.anonDailyLimit;
  const daily = await takeDaily(pool, subjectType, subjectId, limit);
  if (!daily.ok) {
    return { status: 429, body: { scope: account ? "free" : "anonymous", reset_at: nextUtcMidnight() } };
  }
  const global = await takeDaily(pool, "global", "all", env.globalDailyCap);
  if (!global.ok) {
    await refundDaily(pool, subjectType, subjectId);
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

  try {
    let lastInvalid = false;
    for (let attempt = 0; attempt < 2; attempt++) {
      const raw = await llm.complete(system, user);
      try {
        const answer = parseModelJson(raw);
        return { status: 200, body: { ...answer }, headers: { "x-ezsh-remaining": String(Math.max(0, limit - daily.count)) } };
      } catch (err) {
        if (!(err instanceof InvalidModelResponse)) throw err;
        lastInvalid = true; // un nouvel essai, puis échec propre
      }
    }
    void lastInvalid;
    await refundDaily(pool, subjectType, subjectId);
    await refundDaily(pool, "global", "all");
    return { status: 502, body: { error: "invalid_model_response" } };
  } catch (err) {
    // Le service ne doit pas facturer un appel raté. Aucun contenu n'est journalisé.
    await refundDaily(pool, subjectType, subjectId);
    await refundDaily(pool, "global", "all");
    return { status: 502, body: { error: err instanceof UpstreamError ? "upstream" : "internal" } };
  }
}
