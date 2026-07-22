import { describe, expect, it } from "vitest";
import { isApprovedExternalUrl, isTrustedRendererUrl } from "./external-links.js";

describe("Electron boundaries", () => {
  it("rejects executable and lookalike external URLs", () => {
    expect(isApprovedExternalUrl("file:///tmp/payload")).toBe(false);
    expect(isApprovedExternalUrl("https://openai.com.attacker.example")).toBe(false);
    expect(isApprovedExternalUrl("https://developers.openai.com/api/docs")).toBe(true);
  });

  it("accepts only the packaged origin or configured dev origin", () => {
    expect(isTrustedRendererUrl("evidrun://app/")).toBe(true);
    expect(isTrustedRendererUrl("https://attacker.example", "http://127.0.0.1:5173")).toBe(false);
    expect(isTrustedRendererUrl("http://127.0.0.1:5173/", "http://127.0.0.1:5173")).toBe(true);
  });
});

