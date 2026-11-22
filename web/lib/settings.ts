import type { Pool } from "pg";
import { env } from "./env";
import { ANONYMOUS_PLAN, PLANS } from "./plans";

/** Réglages modifiables SANS redéployer : la table `settings` prime sur les variables d'environnement. */
export interface Settings {
  killSwitch: boolean;
  anonymousLimit: number;
  freeLimit: number;
  globalCap: number;
  maxDevices: number;
  minClientVersion: string;
  latestVersion: string | null;
}

function intOr(raw: string | undefined, fallback: number): number {
  const n = Number.parseInt(raw ?? "", 10);
  return Number.isFinite(n) && n >= 0 ? n : fallback;
}

export async function loadSettings(pool: Pool): Promise<Settings> {
  const rows = (await pool.query(`SELECT key, value FROM settings`)).rows as Array<{ key: string; value: string }>;
  const db = new Map(rows.map((r) => [r.key, r.value]));
  return {
    killSwitch: env.killSwitchEnv || db.get("kill_switch") === "1",
    anonymousLimit: ANONYMOUS_PLAN.dailyQuota,
    freeLimit: PLANS.free.dailyQuota,
    globalCap: intOr(db.get("global_cap"), env.globalDailyCap),
    maxDevices: intOr(db.get("max_devices"), env.maxDevicesPerUser),
    minClientVersion: db.get("min_client_version") ?? "0.0.0",
    latestVersion: db.get("latest_client_version") ?? null,
  };
}
