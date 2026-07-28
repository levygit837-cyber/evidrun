import { describe, expect, it } from "vitest";
import { parseExecutorReadiness } from "./executor-handshake.js";

const valid = {
  protocol: "evidrun-worker-v1",
  schema_version: "1",
  pid: 4321,
  worker_id: "host:4321:worker_01",
};

describe("executor handshake", () => {
  it("accepts the readiness envelope", () => {
    expect(parseExecutorReadiness(JSON.stringify(valid)).worker_id).toBe("host:4321:worker_01");
  });

  it("rejects the backend protocol even when every other field is valid", () => {
    // Both processes announce on stdout, so the protocol tag is what separates them.
    // Rejecting the raw backend banner would prove nothing — it lacks `worker_id` anyway.
    expect(() =>
      parseExecutorReadiness(JSON.stringify({ ...valid, protocol: "evidrun-desktop-v1" })),
    ).toThrow();
  });

  it("rejects a missing worker id", () => {
    expect(() => parseExecutorReadiness(JSON.stringify({ ...valid, worker_id: "" }))).toThrow();
  });

  it("rejects a non-positive pid", () => {
    expect(() => parseExecutorReadiness(JSON.stringify({ ...valid, pid: 0 }))).toThrow();
  });
});
