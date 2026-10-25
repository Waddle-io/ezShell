// Console d'administration minimale (DATABASE_URL requis). Usage : npm run admin -- <commande>
//   stats [--days 14]                         usage réel : de quoi fixer les plafonds
//   user list [--plan premium]                liste des comptes
//   user show <email|id>                      détail + usage du jour + appareils
//   user create <email> [--plan unlimited]    pré-crée un compte (lié au 1er login avec cet e-mail vérifié)
//   user set-plan <email|id> <free|premium|unlimited>
//   user set-limit <email|id> <n> [--days 7]  limite personnalisée (avec expiration optionnelle)
//   user clear-limit <email|id>
//   user ban <email|id> | user unban <email|id>
//   setting list | get <clé> | set <clé> <valeur> | unset <clé>
//   purge                                     ménage des compteurs et événements périmés
import { randomUUID } from "node:crypto";
import pg from "pg";

const [, , area, ...rest] = process.argv;
const url = process.env.DATABASE_URL;
if (!url) {
  console.error("DATABASE_URL manquante");
  process.exit(1);
}
const db = new pg.Client({ connectionString: url });
await db.connect();

const flag = (name, def) => {
  const i = rest.indexOf(`--${name}`);
  return i >= 0 ? rest[i + 1] : def;
};
const positional = rest.filter((a, i) => !a.startsWith("--") && !(i > 0 && rest[i - 1].startsWith("--")));
const SETTING_KEYS = ["kill_switch", "limit.anonymous", "limit.free", "limit.premium", "global_cap", "max_devices", "min_client_version", "latest_client_version"];

async function findUser(ref) {
  const r = await db.query(`SELECT * FROM users WHERE id = $1 OR lower(email) = lower($1) OR github_login = $1`, [ref]);
  if (!r.rowCount) throw new Error(`utilisateur introuvable : ${ref}`);
  return r.rows[0];
}

async function stats() {
  const days = Math.max(1, Math.min(90, Number.parseInt(flag("days", "14"), 10) || 14));
  const since = `(now() AT TIME ZONE 'utc')::date - ${days}`;
  console.log(`\n=== Usage des ${days} derniers jours ===\n`);

  console.log("Requêtes et sujets actifs par jour");
  console.table((await db.query(
    `SELECT day::text,
            sum(count) FILTER (WHERE subject_type = 'global')  AS requetes_total,
            count(*) FILTER (WHERE subject_type = 'device')     AS appareils_anonymes,
            count(*) FILTER (WHERE subject_type = 'user')       AS comptes
     FROM usage_daily WHERE day >= ${since} GROUP BY day ORDER BY day`)).rows);

  console.log("Distribution des requêtes par sujet et par jour (médiane, p90, max, part du top 10 %)");
  console.table((await db.query(
    `WITH x AS (SELECT subject_type, count, ntile(10) OVER (PARTITION BY subject_type ORDER BY count DESC) AS decile
                FROM usage_daily WHERE day >= ${since} AND subject_type IN ('device','user'))
     SELECT subject_type,
            count(*) AS observations,
            percentile_cont(0.5) WITHIN GROUP (ORDER BY count)::numeric(8,1) AS mediane,
            percentile_cont(0.9) WITHIN GROUP (ORDER BY count)::numeric(8,1) AS p90,
            max(count) AS max,
            round(100.0 * sum(count) FILTER (WHERE decile = 1) / NULLIF(sum(count), 0), 1) AS part_top10_pct
     FROM x GROUP BY subject_type`)).rows);

  console.log("Résultats par palier");
  console.table((await db.query(
    `SELECT tier, outcome, count(*) AS n FROM ask_metrics WHERE at >= now() - interval '${days} days'
     GROUP BY tier, outcome ORDER BY tier, n DESC`)).rows);

  console.log("Tokens par requête réussie");
  console.table((await db.query(
    `SELECT count(*) AS requetes,
            round(avg(prompt_tokens))     AS prompt_moy,
            round(avg(completion_tokens)) AS completion_moy,
            percentile_cont(0.95) WITHIN GROUP (ORDER BY coalesce(prompt_tokens,0) + coalesce(completion_tokens,0))::int AS total_p95,
            sum(coalesce(prompt_tokens,0) + coalesce(completion_tokens,0)) AS tokens_total,
            round(avg(latency_ms)) AS latence_ms_moy
     FROM ask_metrics WHERE outcome = 'ok' AND at >= now() - interval '${days} days'`)).rows);

  console.log("Demandes identiques (gain potentiel d'un cache)");
  console.table((await db.query(
    `SELECT count(*) AS reussies, count(DISTINCT fingerprint) AS uniques,
            round(100.0 * (1 - count(DISTINCT fingerprint)::numeric / NULLIF(count(*), 0)), 1) AS doublons_pct
     FROM ask_metrics WHERE outcome = 'ok' AND at >= now() - interval '${days} days'`)).rows);

  console.log("429 du fournisseur LLM par heure UTC (les 10 heures les plus chargées)");
  console.table((await db.query(
    `SELECT date_trunc('hour', at)::text AS heure, count(*) AS n FROM ask_metrics
     WHERE outcome = 'upstream_429' AND at >= now() - interval '${days} days' GROUP BY 1 ORDER BY n DESC LIMIT 10`)).rows);
}

async function user() {
  const [action, ref, arg] = positional;
  switch (action) {
    case "list": {
      const plan = flag("plan", null);
      console.table((await db.query(
        `SELECT id, email, github_login, plan, status, daily_limit_override AS limite, created_at::date::text AS cree
         FROM users WHERE ($1::text IS NULL OR plan = $1) ORDER BY created_at DESC LIMIT 200`, [plan])).rows);
      break;
    }
    case "show": {
      const u = await findUser(ref);
      console.log(u);
      console.log("Usage aujourd'hui :", (await db.query(
        `SELECT count FROM usage_daily WHERE subject_type = 'user' AND subject_id = $1 AND day = (now() AT TIME ZONE 'utc')::date`, [u.id])).rows[0]?.count ?? 0);
      console.table((await db.query(
        `SELECT id, created_at::text, last_seen_at::text, revoked_at::text FROM devices WHERE user_id = $1 ORDER BY last_seen_at DESC`, [u.id])).rows);
      break;
    }
    case "create": {
      const plan = flag("plan", "free");
      const id = randomUUID();
      await db.query(`INSERT INTO users (id, email, plan) VALUES ($1, lower($2), $3)`, [id, ref, plan]);
      console.log(`compte créé : ${ref} (${plan}) — il sera lié à la première connexion avec cet e-mail vérifié`);
      break;
    }
    case "set-plan": {
      if (!["free", "premium", "unlimited"].includes(arg)) throw new Error("plan : free | premium | unlimited");
      const u = await findUser(ref);
      await db.query(`UPDATE users SET plan = $2 WHERE id = $1`, [u.id, arg]);
      console.log(`${u.email ?? u.id} → ${arg}`);
      break;
    }
    case "set-limit": {
      const n = Number.parseInt(arg, 10);
      if (!Number.isInteger(n) || n < 0) throw new Error("limite : entier ≥ 0");
      const u = await findUser(ref);
      const days = flag("days", null);
      await db.query(
        `UPDATE users SET daily_limit_override = $2, override_expires_at = CASE WHEN $3::int IS NULL THEN NULL ELSE now() + ($3::int || ' days')::interval END WHERE id = $1`,
        [u.id, n, days ? Number.parseInt(days, 10) : null]);
      console.log(`${u.email ?? u.id} : limite ${n}/jour${days ? ` pendant ${days} jours` : ""}`);
      break;
    }
    case "clear-limit": {
      const u = await findUser(ref);
      await db.query(`UPDATE users SET daily_limit_override = NULL, override_expires_at = NULL WHERE id = $1`, [u.id]);
      console.log("limite personnalisée retirée");
      break;
    }
    case "ban":
    case "unban": {
      const u = await findUser(ref);
      await db.query(`UPDATE users SET status = $2 WHERE id = $1`, [u.id, action === "ban" ? "banned" : "active"]);
      console.log(`${u.email ?? u.id} : ${action === "ban" ? "banni" : "réactivé"}`);
      break;
    }
    default:
      throw new Error("user : list | show | create | set-plan | set-limit | clear-limit | ban | unban");
  }
}

async function setting() {
  const [action, key, value] = positional;
  if (action === "list") return console.table((await db.query(`SELECT key, value FROM settings ORDER BY key`)).rows);
  if (action === "get") return console.log((await db.query(`SELECT value FROM settings WHERE key = $1`, [key])).rows[0]?.value ?? "(non défini)");
  if (!SETTING_KEYS.includes(key)) throw new Error(`clé inconnue. Valides : ${SETTING_KEYS.join(", ")}`);
  if (action === "set") {
    if (value === undefined) throw new Error("valeur manquante");
    await db.query(`INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value`, [key, value]);
    return console.log(`${key} = ${value}`);
  }
  if (action === "unset") {
    await db.query(`DELETE FROM settings WHERE key = $1`, [key]);
    return console.log(`${key} supprimé (retour à la valeur de l'environnement)`);
  }
  throw new Error("setting : list | get <clé> | set <clé> <valeur> | unset <clé>");
}

async function purge() {
  await db.query(`DELETE FROM rate_hits WHERE window_start < now() - interval '2 hours'`);
  await db.query(`DELETE FROM usage_daily WHERE day < (now() AT TIME ZONE 'utc')::date - 35`);
  await db.query(`DELETE FROM ask_metrics WHERE at < now() - interval '90 days'`);
  await db.query(`DELETE FROM login_tokens WHERE expires_at < now() - interval '1 day'`);
  await db.query(`DELETE FROM device_codes WHERE expires_at < now() - interval '1 day'`);
  console.log("ménage effectué");
}

try {
  if (area === "stats") await stats();
  else if (area === "user") await user();
  else if (area === "setting") await setting();
  else if (area === "purge") await purge();
  else console.log(readHelp());
} catch (err) {
  console.error("erreur :", err.message);
  process.exitCode = 1;
} finally {
  await db.end();
}

function readHelp() {
  return "Commandes : stats | user (list, show, create, set-plan, set-limit, clear-limit, ban, unban) | setting (list, get, set, unset) | purge\nVoir l'en-tête de scripts/admin.mjs.";
}
