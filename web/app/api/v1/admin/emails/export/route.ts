import { getWebSessionUser } from "@/lib/auth";
import { getPool } from "@/lib/db";
import { send } from "@/lib/http";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const admin = await getWebSessionUser(req.headers.get("cookie"));
  if (!admin || admin.role !== "admin") {
    return send({ status: 403, body: { error: "forbidden", message: "Accès réservé aux administrateurs." } });
  }

  const optIn = new URL(req.url).searchParams.get("optIn");
  const pool = getPool();
  let result;

  if (optIn === "true") {
    result = await pool.query(`
      SELECT email, created_at, 'account' AS source
      FROM users
      WHERE email IS NOT NULL AND newsletter_opt_in = true
      UNION
      SELECT email, created_at, source
      FROM waitlist
      ORDER BY created_at DESC
    `);
  } else if (optIn === "false") {
    result = await pool.query(`
      SELECT email, created_at, 'account' AS source
      FROM users
      WHERE email IS NOT NULL AND newsletter_opt_in = false
    `);
  } else {
    result = await pool.query(`
      SELECT email, created_at, 'account' AS source
      FROM users
      WHERE email IS NOT NULL
      UNION
      SELECT email, created_at, source
      FROM waitlist
      ORDER BY created_at DESC
    `);
  }

  const escape = (value: unknown) => `"${String(value ?? "").replace(/"/g, '""')}"`;
  const rows = ["email,source,created_at", ...result.rows.map((row) =>
    [escape(row.email), escape(row.source), escape(row.created_at)].join(","),
  )];

  return new Response(`\ufeff${rows.join("\n")}`, {
    status: 200,
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": 'attachment; filename="ezshell-emails.csv"',
    },
  });
}
