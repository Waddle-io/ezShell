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
  get freeDailyLimit() { return int("FREE_DAILY_LIMIT", 25); },
  get premiumDailyLimit() { return int("PREMIUM_DAILY_LIMIT", 45); },
  get maxDevicesPerUser() { return int("MAX_DEVICES_PER_USER", 5); },
  get burstPerMinute() { return int("BURST_PER_MINUTE", 10); },
  get registerPerIpHour() { return int("REGISTER_PER_IP_HOUR", 10); },
  get globalDailyCap() { return int("GLOBAL_DAILY_SPEND_CAP", 2000); },
  get publicBaseUrl() { return (process.env.PUBLIC_BASE_URL ?? "").replace(/\/$/, ""); },
  get githubClientId() { return process.env.GITHUB_CLIENT_ID ?? ""; },
  get githubClientSecret() { return process.env.GITHUB_CLIENT_SECRET ?? ""; },
  get resendKey() { return process.env.RESEND_API_KEY ?? ""; },
  get emailFrom() { return process.env.EMAIL_FROM ?? ""; },
  get killSwitchEnv() { return process.env.KILL_SWITCH === "1"; },
  get adminEmails(): string[] {
    return (process.env.ADMIN_EMAILS ?? "")
      .split(",")
      .map((e) => e.trim().toLowerCase())
      .filter(Boolean);
  },
};

/** Variables indispensables : le serveur refuse de traiter un appel s'il en manque. */
export function missingConfig(): string[] {
  const missing: string[] = [];
  if (!env.databaseUrl) missing.push("DATABASE_URL");
  if (!env.pepper || env.pepper.length < 16) missing.push("TOKEN_PEPPER");
  return missing;
}
