import { describe, expect, it } from "vitest";
import { hashToken, newDeviceToken, bearer } from "../lib/tokens";
import { setupEnv } from "./helpers";

setupEnv();

describe("Tokens et Sécurité", () => {
  it("génère des jetons d'appareil avec préfixe ezd_", () => {
    const token = newDeviceToken();
    expect(token.startsWith("ezd_")).toBe(true);
    expect(token.length).toBeGreaterThan(30);
  });

  it("hache les jetons avec HMAC-SHA256 déterministe", () => {
    const t = "ezd_testtoken1234567890abcdef";
    const h1 = hashToken(t);
    const h2 = hashToken(t);
    expect(h1).toBe(h2);
    expect(h1).toHaveLength(64);
  });

  it("extrait correctement les jetons Bearer", () => {
    expect(bearer("Bearer ezd_validtoken1234567890")).toBe("ezd_validtoken1234567890");
    expect(bearer("Bearer invalid")).toBeNull();
    expect(bearer(null)).toBeNull();
  });
});
