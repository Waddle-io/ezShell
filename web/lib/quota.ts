import type { Pool } from "pg";

export type Window = "minute" | "hour";

function nextBoundary(unit: Window): string {
  const d = new Date();
  if (unit === "minute") d.setUTCSeconds(0, 0), d.setUTCMinutes(d.getUTCMinutes() + 1);
  else d.setUTCMinutes(0, 0, 0), d.setUTCHours(d.getUTCHours() + 1);
  return d.toISOString();
}

export function nextUtcMidnight(): string {
  const d = new Date();
  d.setUTCHours(24, 0, 0, 0);
  return d.toISOString();
}

/**
 * Incrément ATOMIQUE sous plafond : la clause WHERE du DO UPDATE empêche tout dépassement,
 * même avec des requêtes simultanées (pas de « lire puis écrire »).
 */
export async function takeDaily(
  pool: Pool, type: "device" | "user" | "global", id: string, limit: number,
): Promise<{ ok: boolean; count: number }> {
  if (limit <= 0) return { ok: false, count: 0 };
  const r = await pool.query(
    `INSERT INTO usage_daily (subject_type, subject_id, day, count)
     VALUES ($1, $2, (now() AT TIME ZONE 'utc')::date, 1)
     ON CONFLICT (subject_type, subject_id, day)
     DO UPDATE SET count = usage_daily.count + 1 WHERE usage_daily.count < $3
     RETURNING count`,
    [type, id, limit],
  );
  return r.rowCount ? { ok: true, count: r.rows[0].count } : { ok: false, count: limit };
}

export async function refundDaily(pool: Pool, type: "device" | "user" | "global", id: string): Promise<void> {
  await pool.query(
    `UPDATE usage_daily SET count = GREATEST(count - 1, 0)
     WHERE subject_type = $1 AND subject_id = $2 AND day = (now() AT TIME ZONE 'utc')::date`,
    [type, id],
  );
}

export async function readDaily(pool: Pool, type: "device" | "user", id: string): Promise<number> {
  const r = await pool.query(
    `SELECT count FROM usage_daily
     WHERE subject_type = $1 AND subject_id = $2 AND day = (now() AT TIME ZONE 'utc')::date`,
    [type, id],
  );
  return r.rowCount ? r.rows[0].count : 0;
}

/** Limite de débit (rafale, enregistrements) sur fenêtre fixe, même principe atomique. */
export async function takeWindow(
  pool: Pool, subjectId: string, unit: Window, limit: number,
): Promise<{ ok: boolean; resetAt: string }> {
  if (limit <= 0) return { ok: false, resetAt: nextBoundary(unit) };
  const r = await pool.query(
    `INSERT INTO rate_hits (subject_id, window_start, count)
     VALUES ($1, date_trunc('${unit}', now()), 1)
     ON CONFLICT (subject_id, window_start)
     DO UPDATE SET count = rate_hits.count + 1 WHERE rate_hits.count < $2
     RETURNING count`,
    [subjectId, limit],
  );
  return { ok: !!r.rowCount, resetAt: nextBoundary(unit) };
}

/**
 * Ménage (cron ou `npm run admin -- purge`). Les compteurs journaliers sont gardés 35 jours (mesure d'usage),
 * les événements de mesure 90 jours ; les codes et liens expirés disparaissent au bout d'un jour.
 */
export async function purgeOld(pool: Pool): Promise<void> {
  await pool.query(`DELETE FROM rate_hits WHERE window_start < now() - interval '2 hours'`);
  await pool.query(`DELETE FROM usage_daily WHERE day < (now() AT TIME ZONE 'utc')::date - 35`);
  await pool.query(`DELETE FROM ask_metrics WHERE at < now() - interval '90 days'`);
  await pool.query(`DELETE FROM login_tokens WHERE expires_at < now() - interval '1 day'`);
  await pool.query(`DELETE FROM device_codes WHERE expires_at < now() - interval '1 day'`);
}
