import { me } from "@/lib/handlers";
import { send } from "@/lib/http";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  return send(await me(req.headers.get("authorization")));
}
