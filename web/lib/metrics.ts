import { createHmac } from "node:crypto";
import type { Pool } from "pg";
import { env } from "./env";
import type { Tier } from "./plans";

export type Outcome =
  | "ok"
  | "invalid_model_response"
  | "upstream_error"
  | "upstream_429"
  | "refused_burst"
  | "refused_quota"
  | "refused_global";

export interface AskMetric {
  tier: Tier;
  mode: string;
  outcome: Outcome;
  promptTokens?: number | null;
  completionTokens?: number | null;
  latencyMs?: number | null;
  fingerprint?: string | null;
}

/**
 * Empreinte d'une demande : forme normalisée (chiffres → #, espaces réduits) puis HMAC avec le pepper.
 * Elle permet de mesurer la part de demandes identiques (gain d'un cache) SANS stocker de contenu.
 */
export function fingerprint(mode: string, query: string, lastCommand: string, stderrTail: string): string {
  const norm = (s: string) => s.toLowerCase().replace(/\d+/g, "#").replace(/\s+/g, " ").trim();
  const tail = stderrTail.split("\n").slice(-4).join("\n").slice(-400);
  const material = [mode, mode === "explain_error" ? "" : norm(query), norm(lastCommand), norm(tail)].join("|");
  return createHmac("sha256", env.pepper).update("fp:" + material).digest("hex").slice(0, 32);
}

/** La mesure ne doit JAMAIS casser une requête : toute erreur est avalée. */
export async function recordAsk(pool: Pool, m: AskMetric): Promise<void> {
  try {
    await pool.query(
      `INSERT INTO ask_metrics (tier, mode, outcome, prompt_tokens, completion_tokens, latency_ms, fingerprint)
       VALUES ($1, $2, $3, $4, $5, $6, $7)`,
      [m.tier, m.mode, m.outcome, m.promptTokens ?? null, m.completionTokens ?? null, m.latencyMs ?? null, m.fingerprint ?? null],
    );
  } catch {
    /* mesure best-effort */
  }
}
