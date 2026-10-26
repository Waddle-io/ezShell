import { randomBytes } from "node:crypto";
import { NextResponse } from "next/server";
import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const userCode = url.searchParams.get("user_code") || "";
  const base = env.publicBaseUrl || url.origin;

  if (!env.githubClientId || !env.githubClientSecret) {
    return NextResponse.redirect(`${base}/login?error=github_not_configured`);
  }

  const nonce = randomBytes(32).toString("base64url");
  const state = Buffer.from(JSON.stringify({ user_code: userCode, nonce })).toString("base64url");
  const redirectUri = `${base}/api/v1/auth/github/callback`;

  const githubAuthUrl = new URL("https://github.com/login/oauth/authorize");
  githubAuthUrl.searchParams.set("client_id", env.githubClientId);
  githubAuthUrl.searchParams.set("redirect_uri", redirectUri);
  githubAuthUrl.searchParams.set("scope", "read:user user:email");
  githubAuthUrl.searchParams.set("state", state);

  const response = NextResponse.redirect(githubAuthUrl.toString());
  response.cookies.set({
    name: "ezsh_github_state",
    value: nonce,
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/api/v1/auth/github/callback",
    maxAge: 10 * 60,
  });
  return response;
}
