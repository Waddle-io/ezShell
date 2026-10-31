import { getPool } from "./db";

/** Journal d'audit (console admin). Ne lève jamais : un échec de log ne doit pas casser l'action. */
export async function recordAuditLog(
  actorId: string,
  action: string,
  targetId: string | null = null,
  details: Record<string, unknown> = {},
  actorEmail: string | null = null,
): Promise<void> {
  try {
    await getPool().query(
      `INSERT INTO audit_logs (actor_id, actor_email, action, target_id, details)
       VALUES ($1, $2, $3, $4, $5)`,
      [actorId, actorEmail, action, targetId, JSON.stringify(details)],
    );
  } catch (e) {
    console.error("[audit_log] Erreur enregistrement :", e);
  }
}
