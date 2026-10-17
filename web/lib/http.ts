import { NextResponse } from "next/server";
import type { Result } from "./handlers";

export const MAX_BODY_BYTES = 32 * 1024;

export function send(r: Result): NextResponse {
  return NextResponse.json(r.body, { status: r.status, headers: { "cache-control": "no-store", ...r.headers } });
}

/** IP du client : sur Vercel, x-forwarded-for est posé par la plateforme. */
export function clientIp(req: Request): string {
  const xff = req.headers.get("x-forwarded-for");
  return (xff ? xff.split(",")[0].trim() : req.headers.get("x-real-ip")) || "unknown";
}

/** Corps JSON borné ; undefined si illisible ou trop gros (=> 400 en aval). */
export async function readJson(req: Request): Promise<unknown> {
  const text = await req.text();
  if (text.length > MAX_BODY_BYTES) return undefined;
  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}
