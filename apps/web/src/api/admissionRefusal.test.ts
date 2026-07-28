import { describe, expect, it } from "vitest";
import { ApiError, admissionRefusal } from "./client";

/**
 * A refused admission answers 4xx with the decision in the body, so the error a caller catches
 * carries a serialized contract document. These pin the translation, because the untranslated
 * path put that whole JSON blob on screen.
 */
describe("admission refusal", () => {
  it("reads the typed message out of the rejection body", () => {
    const error = new ApiError(
      422,
      JSON.stringify({
        decision: "rejected",
        missing_requirements: [],
        error: { code: "ADMIT_CAPABILITY_UNAVAILABLE", message: "capability is unavailable" },
      }),
    );
    const message = admissionRefusal(error);
    expect(message).toContain("capability is unavailable");
    expect(message).not.toContain("ADMIT_CAPABILITY_UNAVAILABLE");
    expect(message).not.toContain("{");
  });

  it("names the missing requirements when the body lists them", () => {
    const error = new ApiError(
      422,
      JSON.stringify({
        decision: "rejected",
        missing_requirements: ["capability:read-artifact-text-v1"],
        error: { message: "runtime does not provide the capability" },
      }),
    );
    expect(admissionRefusal(error)).toContain("capability:read-artifact-text-v1");
  });

  it("falls back to the decision when no typed error is present", () => {
    expect(admissionRefusal(new ApiError(422, JSON.stringify({ decision: "rejected" })))).toContain(
      "rejected",
    );
  });

  it("stays readable when the body is not JSON at all", () => {
    const message = admissionRefusal(new ApiError(500, "Internal Server Error"));
    expect(message).toContain("500");
    expect(message).not.toContain("Internal Server Error");
  });
});
