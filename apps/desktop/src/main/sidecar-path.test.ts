import { describe, expect, it } from "vitest";
import { sidecarPath } from "./sidecar-path.js";

describe("sidecar path", () => {
  it("points inside the per-sidecar directory a onedir build produces", () => {
    expect(sidecarPath("evidrun-backend", "/res")).toContain("backend/evidrun-backend/");
  });

  it("resolves each plane to its own executable", () => {
    expect(sidecarPath("evidrun-worker", "/res")).not.toBe(
      sidecarPath("evidrun-backend", "/res"),
    );
  });
});
