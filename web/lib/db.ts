import pg from "pg";
import { env } from "./env";

let pool: pg.Pool | null = null;

/** Pool unique par instance serverless. Neon : utiliser la chaîne « pooled ». */
export function getPool(): pg.Pool {
  if (!pool) {
    pool = new pg.Pool({
      connectionString: env.databaseUrl,
      max: 3,
      idleTimeoutMillis: 10_000,
      connectionTimeoutMillis: 5_000,
    });
  }
  return pool;
}

export async function closePool(): Promise<void> {
  if (pool) {
    await pool.end();
    pool = null;
  }
}
