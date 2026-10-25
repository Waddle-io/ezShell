import { versionInfo } from "@/lib/handlers";
import { send } from "@/lib/http";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const from = new URL(req.url).searchParams.get("from");
  return send(await versionInfo(from && /^[0-9.]{1,20}$/.test(from) ? from : null));
}
