import { describe, expect, it } from "vitest";
import { AskRequest, InvalidModelResponse, parseModelJson } from "@/lib/schema";

describe("parseModelJson", () => {
  it("accepte du JSON dans des fences ou entouré de prose", () => {
    expect(parseModelJson('```json\n{"command":"ls","risk":"low"}\n```').command).toBe("ls");
    expect(parseModelJson('Voici : {"command":"pwd"} ok').command).toBe("pwd");
  });
  it.each(["pas de json", '{"risk":"extreme"}', '{"confidence":5}', "{cassé"])("rejette %s", (raw) => {
    expect(() => parseModelJson(raw)).toThrow(InvalidModelResponse);
  });
  it("retire ANSI et caractères de contrôle", () => {
    const r = parseModelJson(JSON.stringify({ command: "ls\u001b[2J", explanation: "\u001b[31mHack\u001b[0m\u0007" }));
    expect(r.command).toBe("ls");
    expect(r.explanation).toBe("Hack");
  });
});

describe("AskRequest", () => {
  it("borne les tailles", () => {
    expect(AskRequest.safeParse({ mode: "translate", query: "x".repeat(2001) }).success).toBe(false);
    expect(AskRequest.safeParse({ mode: "nope" }).success).toBe(false);
    expect(AskRequest.safeParse({ mode: "translate", query: "ok" }).success).toBe(true);
  });
});
