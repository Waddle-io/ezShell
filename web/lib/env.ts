/** Lecture paresseuse des variables d'environnement (jamais exposées au client). */
function int(name: string, fallback: number): number {
  const v = Number.parseInt(process.env[name] ?? "", 10);
  return Number.isFinite(v) && v >= 0 ? v : fallback;
}

export const env = {
  get databaseUrl() { return process.env.DATABASE_URL ?? ""; },
  get groqKey() { return process.env.GROQ_API_KEY ?? ""; },
  get groqBaseUrl() { return process.env.GROQ_BASE_URL || "https://api.groq.com/openai/v1"; },
  get model() { return process.env.LLM_MODEL ?? ""; },
  get pepper() { return process.env.TOKEN_PEPPER ?? ""; },
  get anonDailyLimit() { return int("ANON_DAILY_LIMIT", 10); },
  get freeDailyLimit() { return int("FREE_DAILY_LIMIT", 50); },
  get burstPerMinute() { return int("BURST_PER_MINUTE", 10); },
  get registerPerIpHour() { return int("REGISTER_PER_IP_HOUR", 10); },
  get globalDailyCap() { return int("GLOBAL_DAILY_SPEND_CAP", 2000); },
  get killSwitchEnv() { return process.env.KILL_SWITCH === "1"; },
};

/** Variables indispensables : le serveur refuse de traiter un appel s'il en manque. */
export function missingConfig(): string[] {
  const missing: string[] = [];
  if (!env.databaseUrl) missing.push("DATABASE_URL");
  if (!env.pepper || env.pepper.length < 16) missing.push("TOKEN_PEPPER");
  return missing;
}
