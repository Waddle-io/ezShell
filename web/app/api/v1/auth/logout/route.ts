import { NextResponse } from "next/server";
import { destroyWebSession } from "@/lib/auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST(req: Request) {
  const cookieHeader = req.headers.get("cookie");
  await destroyWebSession(cookieHeader);

  const res = NextResponse.json({ success: true, message: "Déconnecté avec succès." });
  res.cookies.set({
    name: "ezsh_session",
    value: "",
    httpOnly: true,
    expires: new Date(0),
    path: "/",
  });
  return res;
}
