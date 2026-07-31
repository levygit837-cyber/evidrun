import { describe, expect, it } from "vitest";
import { RefusalError, triageErrorOf } from "../../api/client";
import type { TriageError, TriageErrorCode } from "../../generated/contracts";
import { ADMISSION_STATE_BY_CODE, classifyFailure } from "./createModel";

/**
 * The displayed state derives from the refusal code, never from message text.
 *
 * Before this, the console searched for substrings in two languages — `"rejected"`/`"rejeitad"`,
 * `"unavailable"`/`"indispon"` — so translating a message silently broke the classification with
 * nothing failing. These pin the code as the only input.
 */
function refusal(code: string, message = "texto livre para o humano"): RefusalError {
  const triage = { code, phase: code.split(".")[0], message } as unknown as TriageError;
  return new RefusalError(message, triage, 422);
}

describe("admission state classification", () => {
  it("derives every mapped state from its code", () => {
    for (const [code, expected] of Object.entries(ADMISSION_STATE_BY_CODE)) {
      expect(classifyFailure(refusal(code))).toBe(expected);
    }
  });

  it("falls into the declared safe state for a code it does not know", () => {
    // A code the backend may add later must not land in an optimistic state by omission.
    expect(classifyFailure(refusal("parse.schema_invalid"))).toBe("failed");
    expect(classifyFailure(refusal("enqueue.retry_legacy_run"))).toBe("failed");
  });

  it("ignores message text entirely", () => {
    // The message says "rejected" while the code says unavailable: the code must win.
    const misleading = refusal("register.storage_unavailable", "rejected e rejeitado");
    expect(classifyFailure(misleading)).toBe("unavailable");

    // And the reverse: an admit rejection whose text mentions neither word.
    expect(classifyFailure(refusal("admit.rejected", "sem palavras-chave"))).toBe("rejected");
  });

  it("treats an untyped failure as failed", () => {
    expect(classifyFailure(new Error("A admissão recusou este RunSpec: rejected."))).toBe("failed");
    expect(classifyFailure(new RefusalError("no body", null, 500))).toBe("failed");
    expect(classifyFailure("not an error")).toBe("failed");
  });

  it("maps only codes the backend actually declares", () => {
    // Guards against a typo silently becoming dead configuration: every key must be a real code.
    const declared: TriageErrorCode[] = [
      "admit.inventory_not_persistible",
      "admit.rejected",
      "admit.run_spec_not_found",
      "compile.dependency_not_accepted",
      "compile.revision_not_found",
      "decide.human_authority_unavailable",
      "enqueue.admission_not_admitted",
      "register.storage_unavailable",
    ];
    expect(Object.keys(ADMISSION_STATE_BY_CODE).sort()).toEqual(declared);
  });
});

describe("triage error extraction", () => {
  it("reads a refusal from a bare body and from a FastAPI detail envelope", () => {
    const bare = JSON.stringify({ phase: "admit", code: "admit.rejected", message: "recusado" });
    expect(triageErrorOf(bare)?.code).toBe("admit.rejected");

    const wrapped = JSON.stringify({
      detail: { phase: "enqueue", code: "enqueue.idempotency_conflict", message: "conflito" },
    });
    expect(triageErrorOf(wrapped)?.code).toBe("enqueue.idempotency_conflict");
  });

  it("reads the nested error an admission rejection carries", () => {
    const admission = JSON.stringify({
      decision: "rejected",
      error: { phase: "admit", code: "admit.rejected", message: "recusado" },
    });
    expect(triageErrorOf(admission)?.code).toBe("admit.rejected");
  });

  it("returns null when the body carries no named refusal", () => {
    expect(triageErrorOf("Internal Server Error")).toBeNull();
    expect(triageErrorOf(JSON.stringify({ decision: "rejected" }))).toBeNull();
    expect(triageErrorOf(JSON.stringify({ detail: "plain text" }))).toBeNull();
    expect(triageErrorOf("null")).toBeNull();
  });
});
