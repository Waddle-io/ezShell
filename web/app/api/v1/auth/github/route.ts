import { NextResponse } from "next/server";
import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const userCode = url.searchParams.get("user_code") || "";
  const base = env.publicBaseUrl || url.origin;

  if (!env.githubClientId) {
    return NextResponse.redirect(`${base}/login?error=github_not_configured`);
  }

  const state = Buffer.from(JSON.stringify({ user_code: userCode, rand: Math.random().toString(36) })).toString("base64url");
  const redirectUri = `${base}/api/v1/auth/github/callback`;

  const githubAuthUrl = new URL("https://github.com/login/oauth/authorize");
  githubAuthUrl.searchParams.set("client_id", env.githubClientId);
  githubAuthUrl.searchParams.set("redirect_uri", redirectUri);
  githubAuthUrl.searchParams.set("scope", "read:user user:email");
  githubAuthUrl.searchParams.set("state", state);

  return NextResponse.redirect(githubAuthUrl.toString());
}
