import { getAuth } from "@/lib/better-auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// Toutes les routes Better Auth (/api/auth/sign-in/magic-link, /api/auth/callback/github, /api/auth/sign-out, …)
const handler = (req: Request) => getAuth().handler(req);

export { handler as GET, handler as POST };
