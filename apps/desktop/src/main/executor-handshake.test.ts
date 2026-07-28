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

  it("rejects the backend envelope", () => {
    // Both processes announce on stdout; accepting the wrong banner would report a ready
    // executor for a process that never claims a job.
    expect(() =>
      parseExecutorReadiness(
        JSON.stringify({
          protocol: "evidrun-desktop-v1",
          port: 43121,
          backend_instance_id: "backend-1",
          schema_version: "1",
          pid: 123,
          health_nonce: "nonce",
        }),
      ),
    ).toThrow();
  });

  it("rejects a missing worker id", () => {
    expect(() => parseExecutorReadiness(JSON.stringify({ ...valid, worker_id: "" }))).toThrow();
  });

  it("rejects a non-positive pid", () => {
    expect(() => parseExecutorReadiness(JSON.stringify({ ...valid, pid: 0 }))).toThrow();
  });
});
