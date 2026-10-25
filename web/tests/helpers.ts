import { readFileSync } from "node:fs";
import pg from "pg";
import type { LLMProvider, LLMResult } from "@/lib/llm";

export const TEST_DB = process.env.TEST_DATABASE_URL ?? "postgresql://postgres:pw@localhost:5433/ezsh_test";

export function setupEnv(extra: Record<string, string> = {}) {
  Object.assign(process.env, {
    DATABASE_URL: TEST_DB,
    TOKEN_PEPPER: "test-pepper-0123456789abcdef",
    GROQ_API_KEY: "test-key",
    LLM_MODEL: "test-model",
    ANON_DAILY_LIMIT: "5",
    FREE_DAILY_LIMIT: "20",
    PREMIUM_DAILY_LIMIT: "30",
    MAX_DEVICES_PER_USER: "2",
    BURST_PER_MINUTE: "100",
    REGISTER_PER_IP_HOUR: "100",
    GLOBAL_DAILY_SPEND_CAP: "1000",
    KILL_SWITCH: "0",
    ...extra,
  });
}

export async function resetDb(): Promise<pg.Pool> {
  const pool = new pg.Pool({ connectionString: TEST_DB, max: 2 });
  await pool.query("DROP TABLE IF EXISTS ask_metrics, login_tokens, device_codes, usage_daily, rate_hits, settings, devices, users CASCADE");
  await pool.query(readFileSync(new URL("../db/schema.sql", import.meta.url), "utf8"));
  return pool;
}

export const GOOD = JSON.stringify({
  command: "git pull --rebase origin main", explanation: "En retard sur origin.", cause: "Commits distants.",
  risk: "low", risk_reason: "Local uniquement.", assumptions: ["git installé"], confidence: "high",
});

export class FakeLLM implements LLMProvider {
  calls: Array<{ system: string; user: string }> = [];
  constructor(private reply: string | LLMResult | (() => string | LLMResult | Promise<string | LLMResult>) = GOOD) {}
  async complete(system: string, user: string): Promise<string | LLMResult> {
    this.calls.push({ system, user });
    return typeof this.reply === "function" ? this.reply() : this.reply;
  }
}

export const body = (over: Record<string, unknown> = {}) => ({
  mode: "explain_error", query: "", lang: "fr",
  context: { os: "linux", shell: "bash", cwd: "~", last_command: "git push", exit_code: 1, stderr_tail: "rejected" },
  ...over,
});
