import { describe, expect, it } from "vitest";
import { parseReadiness } from "../main/desktop-handshake.js";
import { parseExecutorReadiness } from "../main/executor-handshake.js";
import {
  BridgeError,
  bridgeErrorCodeOf,
  bridgeErrorCodes,
} from "./desktop-contract.js";

/**
 * The bridge's refusals are observable, so they carry codes rather than only text.
 *
 * Main throws across an IPC boundary and the renderer receives a serialized string, so a
 * reworded message would otherwise be an observable change. These pin the code as the
 * stable part and the message as free text.
 */
describe("bridge error codes", () => {
  it("declares one code per refusal, all namespaced", () => {
    const codes: string[] = Object.values(bridgeErrorCodes);
    expect(new Set(codes).size).toBe(codes.length);
    expect(codes.every((code) => code.startsWith("bridge."))).toBe(true);
  });

  it("keeps the code readable after the message crosses IPC as a string", () => {
    const error = new BridgeError(bridgeErrorCodes.untrustedSender, "Untrusted IPC sender");

    // Electron serializes an Error over IPC, so only the message survives. The code has to
    // be recoverable from that text alone.
    expect(bridgeErrorCodeOf(error.message)).toBe(bridgeErrorCodes.untrustedSender);
    expect(bridgeErrorCodeOf(error)).toBe(bridgeErrorCodes.untrustedSender);
    expect(error.message).toContain("Untrusted IPC sender");
  });

  it("returns null for anything carrying no known code", () => {
    expect(bridgeErrorCodeOf(new Error("some unrelated failure"))).toBeNull();
    expect(bridgeErrorCodeOf("bridge.not_a_real_code")).toBeNull();
    expect(bridgeErrorCodeOf(undefined)).toBeNull();
    expect(bridgeErrorCodeOf(null)).toBeNull();
    expect(bridgeErrorCodeOf(42)).toBeNull();
  });

  it("names a malformed backend handshake", () => {
    const invalid = JSON.stringify({ protocol: "evidrun-desktop-v1", schema_version: "1" });

    expect(() => parseReadiness(invalid)).toThrow(BridgeError);
    try {
      parseReadiness(invalid);
    } catch (error) {
      expect(bridgeErrorCodeOf(error)).toBe(bridgeErrorCodes.invalidBackendHandshake);
    }
  });

  it("names a malformed executor handshake distinctly from the backend one", () => {
    const invalid = JSON.stringify({ protocol: "evidrun-worker-v1", schema_version: "1" });

    try {
      parseExecutorReadiness(invalid);
      throw new Error("expected a refusal");
    } catch (error) {
      // Two processes announce different things; one code for both would erase which
      // plane failed.
      expect(bridgeErrorCodeOf(error)).toBe(bridgeErrorCodes.invalidExecutorHandshake);
      expect(bridgeErrorCodeOf(error)).not.toBe(bridgeErrorCodes.invalidBackendHandshake);
    }
  });

  it("still accepts a valid handshake on both planes", () => {
    const backend = parseReadiness(
      JSON.stringify({
        protocol: "evidrun-desktop-v1",
        schema_version: "1",
        port: 8765,
        backend_instance_id: "instance-1",
        pid: 4242,
        health_nonce: "nonce-1",
      }),
    );
    expect(backend.port).toBe(8765);

    const executor = parseExecutorReadiness(
      JSON.stringify({
        protocol: "evidrun-worker-v1",
        schema_version: "1",
        pid: 4243,
        worker_id: "worker-1",
      }),
    );
    expect(executor.worker_id).toBe("worker-1");
  });
});
