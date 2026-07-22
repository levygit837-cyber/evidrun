import { describe, expect, it } from "vitest";
import { parseReadiness } from "./desktop-handshake.js";

describe("desktop handshake", () => {
  it("validates the readiness envelope", () => {
    const message = parseReadiness(JSON.stringify({
      protocol: "evidrun-desktop-v1",
      port: 43121,
      backend_instance_id: "backend-1",
      schema_version: "1",
      pid: 123,
      health_nonce: "nonce",
    }));
    expect(message.port).toBe(43121);
  });

  it("rejects invalid ports", () => {
    expect(() => parseReadiness(JSON.stringify({
      protocol: "evidrun-desktop-v1",
      port: 0,
      backend_instance_id: "backend-1",
      schema_version: "1",
      pid: 123,
      health_nonce: "nonce",
    }))).toThrow();
  });
});
