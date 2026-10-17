/**
 * Seconde passe de masquage côté serveur (DEVELOPMENT.md §7.2).
 * Le client masque déjà avant l'envoi ; on ne fait jamais confiance au client.
 * Chaque motif ajouté exige un test (tests/redact.test.ts).
 */
const MASK = "[SECRET_MASQUÉ]";
const PATTERNS: Array<[RegExp, string]> = [
  [/-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----/g, MASK],
  [/\b[a-z][a-z0-9+.-]*:\/\/[^\s:@/]+:[^\s@/]+@[^\s'"]+/gi, MASK], // postgres://user:pass@host
  [/\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b/g, MASK], // JWT
  [/\bgsk_[A-Za-z0-9]{20,}\b/g, MASK],
  [/\bsk-[A-Za-z0-9_-]{20,}\b/g, MASK],
  [/\bgh[pousr]_[A-Za-z0-9]{20,}\b/g, MASK],
  [/\bgithub_pat_[A-Za-z0-9_]{20,}\b/g, MASK],
  [/\bxox[abprs]-[A-Za-z0-9-]{10,}\b/g, MASK],
  [/\b(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{16,}\b/g, MASK],
  [/\b(?:AKIA|ASIA)[0-9A-Z]{16}\b/g, MASK],
  [/\bez[du]_[A-Za-z0-9_-]{20,}\b/g, MASK],
  [/(authorization\s*[:=]\s*)(?:bearer|basic)\s+\S+/gi, "$1" + MASK],
  [/\bbearer\s+[A-Za-z0-9._~+/=-]{16,}/gi, "Bearer " + MASK],
  [/\b([A-Za-z0-9_]*(?:key|token|secret|password|passwd|pwd)[A-Za-z0-9_]*)\s*[:=]\s*(['"]?)[^\s'"]{4,}\2/gi, "$1=" + MASK],
];

export function redact(text: string): string {
  let out = text ?? "";
  for (const [re, repl] of PATTERNS) out = out.replace(re, repl);
  return out;
}
