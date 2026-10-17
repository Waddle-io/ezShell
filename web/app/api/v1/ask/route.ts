import { ask } from "@/lib/handlers";
import { readJson, send } from "@/lib/http";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;

export async function POST(req: Request) {
  const body = await readJson(req);
  return send(await ask(req.headers.get("authorization"), body));
}
