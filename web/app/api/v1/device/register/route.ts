import { registerDevice } from "@/lib/handlers";
import { clientIp, send } from "@/lib/http";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  return send(await registerDevice(clientIp(req)));
}
