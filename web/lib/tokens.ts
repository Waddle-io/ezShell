import { createHmac, randomBytes } from "node:crypto";
import { env } from "./env";

/** Jeton d'appareil : 32 octets aléatoires. Seul le HMAC est stocké (révocable). */
export function newDeviceToken(): string {
  return "ezd_" + randomBytes(32).toString("base64url");
}

export function hashToken(token: string): string {
  return createHmac("sha256", env.pepper).update(token).digest("hex");
}

/** IP hachée : sert uniquement à limiter les enregistrements d'appareils. */
export function hashIp(ip: string): string {
  return createHmac("sha256", env.pepper).update("ip:" + ip).digest("hex");
}

export function bearer(header: string | null): string | null {
  const m = /^Bearer\s+(ezd_[A-Za-z0-9_-]{20,100}|ezu_[A-Za-z0-9_-]{20,100})$/.exec(header ?? "");
  return m ? m[1] : null;
}
