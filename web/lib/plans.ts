import type { Settings } from "./settings";

export type PlanId = "free" | "silver" | "gold" | "student";
export type Tier = "anonymous" | PlanId;

export interface PlanConfig {
  id: PlanId;
  name: string;
  dailyQuota: number;
  priceFcfa: number;
  currency: "FCFA";
  period: "month" | "3_months";
  durationMonths?: number;
  saleNote?: string;
  highlighted?: boolean;
}

export const PLANS: Readonly<Record<PlanId, PlanConfig>> = {
  free: { id: "free", name: "Compte gratuit", dailyQuota: 5, priceFcfa: 0, currency: "FCFA", period: "month" },
  silver: { id: "silver", name: "Silver", dailyQuota: 35, priceFcfa: 600, currency: "FCFA", period: "month", highlighted: true },
  gold: { id: "gold", name: "Gold", dailyQuota: 150, priceFcfa: 1200, currency: "FCFA", period: "month", highlighted: true },
  student: { id: "student", name: "Pass étudiant", dailyQuota: 35, priceFcfa: 1500, currency: "FCFA", period: "3_months", durationMonths: 3, saleNote: "soit 500 FCFA/mois" },
};

export const ANONYMOUS_PLAN: Readonly<PlanConfig> = {
  id: "free",
  name: "Sans compte",
  dailyQuota: 3,
  priceFcfa: 0,
  currency: "FCFA",
  period: "month",
};

export function formatFcfa(amount: number): string {
  return `${new Intl.NumberFormat("fr-FR").format(amount)} FCFA`;
}

export interface AuthedDevice {
  id: string;
  user_id: string | null;
  plan: string | null;
  status: string | null;
  daily_limit_override: number | null;
  override_expires_at: Date | null;
  plan_started_at?: Date | null;
  plan_expires_at?: Date | null;
  ip_hash?: string | null;
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
    return { tier: "anonymous", subjectType: "device", subjectId: d.ip_hash ? `ip:${d.ip_hash}` : d.id, limit: ANONYMOUS_PLAN.dailyQuota, banned: false };
  }
  let tier: Tier = d.plan === "silver" || d.plan === "gold" || d.plan === "student" ? d.plan : "free";
  if (tier === "student" && d.plan_expires_at && d.plan_expires_at <= now) tier = "free";
  const base = PLANS[tier].dailyQuota;
  const limit = base;
  return { tier, subjectType: "user", subjectId: d.user_id, limit, banned: d.status === "banned" };
}
