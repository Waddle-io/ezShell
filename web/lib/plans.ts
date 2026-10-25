import type { Settings } from "./settings";

export type Tier = "anonymous" | "free" | "premium" | "unlimited";

/** « Illimité » = pas de quota journalier ; reste sous la limite de rafale. */
export const UNLIMITED = 1_000_000_000;

export interface AuthedDevice {
  id: string;
  user_id: string | null;
  plan: string | null;
  status: string | null;
  daily_limit_override: number | null;
  override_expires_at: Date | null;
}

export interface Entitlement {
  tier: Tier;
  subjectType: "device" | "user";
  subjectId: string;
  /** Limite journalière effective (UNLIMITED pour le palier illimité). */
  limit: number;
  banned: boolean;
}

export function entitlement(d: AuthedDevice, s: Settings, now: Date = new Date()): Entitlement {
  if (d.user_id === null) {
    return { tier: "anonymous", subjectType: "device", subjectId: d.id, limit: s.anonymousLimit, banned: false };
  }
  const tier: Tier = d.plan === "premium" ? "premium" : d.plan === "unlimited" ? "unlimited" : "free";
  const base = tier === "premium" ? s.premiumLimit : s.freeLimit;
  const overrideActive =
    d.daily_limit_override !== null && (d.override_expires_at === null || d.override_expires_at > now);
  const limit = tier === "unlimited" ? UNLIMITED : overrideActive ? (d.daily_limit_override as number) : base;
  return { tier, subjectType: "user", subjectId: d.user_id, limit, banned: d.status === "banned" };
}
