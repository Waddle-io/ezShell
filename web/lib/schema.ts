import { z } from "zod";

// Borne les tailles : le contexte utile tient dans ~4 Ko (DEVELOPMENT.md §7.1).
export const AskRequest = z.object({
  mode: z.enum(["explain_error", "translate", "explain_command"]),
  query: z.string().max(2000).default(""),
  context: z
    .object({
      os: z.string().max(80).default(""),
      shell: z.string().max(40).default(""),
      cwd: z.string().max(300).default(""),
      last_command: z.string().max(2000).default(""),
      exit_code: z.number().int().nullable().default(null),
      stderr_tail: z.string().max(8192).default(""),
    })
    .default({}),
  lang: z.enum(["fr", "en"]).default("fr"),
  client_version: z.string().max(40).default(""),
});
export type AskRequest = z.infer<typeof AskRequest>;

const level = z.enum(["low", "medium", "high"]);

export const AskResponse = z.object({
  command: z.string().max(2000).default(""),
  explanation: z.string().max(1200).default(""),
  cause: z.string().max(800).default(""),
  risk: level.default("medium"),
  risk_reason: z.string().max(400).default(""),
  assumptions: z.array(z.string().max(300)).max(8).default([]),
  confidence: level.default("medium"),
});
export type AskResponse = z.infer<typeof AskResponse>;

/** Retire ANSI et caractères de contrôle d'un texte venant du modèle. */
export function stripControl(s: string, keepNewlines = true): string {
  // eslint-disable-next-line no-control-regex
  const noAnsi = s.replace(/\x1b\[[0-?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]/g, "");
  const norm = noAnsi.replace(/\r\n?/g, "\n");
  // eslint-disable-next-line no-control-regex
  return keepNewlines ? norm.replace(/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, "") : norm.replace(/[\x00-\x1f\x7f]/g, " ");
}

export function cleanResponse(r: AskResponse): AskResponse {
  return {
    ...r,
    command: stripControl(r.command).trim(),
    explanation: stripControl(r.explanation).trim(),
    cause: stripControl(r.cause).trim(),
    risk_reason: stripControl(r.risk_reason).trim(),
    assumptions: r.assumptions.map((a) => stripControl(a, false).trim()),
  };
}

export class InvalidModelResponse extends Error {}

export function parseModelJson(raw: string): AskResponse {
  const fenced = /```(?:json)?\s*([\s\S]*?)```/.exec(raw);
  const body = (fenced ? fenced[1] : raw).trim();
  const start = body.indexOf("{");
  const end = body.lastIndexOf("}");
  if (start === -1 || end <= start) throw new InvalidModelResponse("no json");
  try {
    return cleanResponse(AskResponse.parse(JSON.parse(body.slice(start, end + 1))));
  } catch {
    throw new InvalidModelResponse("schema");
  }
}
