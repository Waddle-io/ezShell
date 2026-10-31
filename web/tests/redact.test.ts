import { describe, expect, it } from "vitest";
import { redact } from "@/lib/redact";

const cases: Array<[string, string]> = [
  ["groq", "key gsk_abcdefghijklmnopqrstuvwxyz123456 end"],
  ["openai", "sk-abcdefghijklmnopqrstuvwxyz123456"],
  ["github", "ghp_abcdefghijklmnopqrstuvwxyz0123456789"],
  ["github-pat", "github_pat_11ABCDEFG0abcdefghijklmnopqrstuvwxyz"],
  ["aws", "AKIAIOSFODNN7EXAMPLE"],
  ["slack", "xoxb-1234567890-abcdefghij"],
  ["stripe", "sk_live_abcdefghijklmnop1234"],
  ["jwt", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijk123"],
  ["url-creds", "postgresql://neondb_owner:SuperSecret99@ep-cool-123.neon.tech/db?sslmode=require"],
  ["bearer", "curl -H 'Authorization: Bearer abcdefghijklmnopqrstuvwxyz1234' x"],
  ["assignment", "export DB_PASSWORD=hunter2hunter2"],
  ["api-key-eq", "api_key: 'abcd1234efgh'"],
  ["device-token", "ezd_abcdefghijklmnopqrstuvwxyz_0123456789"],
  ["pem", "-----BEGIN RSA PRIVATE KEY-----\nMIIBOgIBAAJBAK\n-----END RSA PRIVATE KEY-----"],
];

describe("redact", () => {
  it.each(cases)("masque %s", (_n, input) => {
    const out = redact(input);
    expect(out).toContain("SECRET_MASQUÉ");
    expect(out).not.toMatch(/SuperSecret99|hunter2hunter2|abcdefghijklmnopqrstuvwxyz|AKIAIOSFODNN7EXAMPLE|MIIBOgIBAAJBAK|abcd1234efgh/);
  });

  it("laisse intact un texte sans secret", () => {
    const t = "ls: cannot access '/tmp/x': No such file or directory";
    expect(redact(t)).toBe(t);
  });

  it("ne détruit pas le reste de la ligne", () => {
    expect(redact("deploy failed token=abcd1234 retry in 5s")).toContain("retry in 5s");
  });
});
