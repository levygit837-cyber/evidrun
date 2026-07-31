import { describe, expect, it, vi } from "vitest";
import { emitSecureLog } from "./secure-logging.js";

describe("desktop secure logging", () => {
  it("keeps stable diagnostics without exception or classified payload text", () => {
    const sink = vi.fn();
    const secret = "fixture-secret-must-never-be-logged";

    emitSecureLog(
      "desktop.sidecar.failed",
      {
        correlationId: "backend_instance_01",
        errorCode: "desktop.sidecar_error",
        error: new Error(`Authorization: Bearer ${secret}`),
        fields: {
          process: "backend",
          exit_code: 1,
          authorization: `Bearer ${secret}`,
          cookie: `session=${secret}`,
          environment: { EVIDRUN_PROVIDER_API_KEY: secret },
          prompt: secret,
          subject_envelope: { input: secret },
          actor: "claimed-human",
        },
      },
      sink,
    );

    expect(sink).toHaveBeenCalledWith(JSON.stringify({
      correlation_id: "backend_instance_01",
      error_code: "desktop.sidecar_error",
      error_type: "Error",
      event_code: "desktop.sidecar.failed",
      exit_code: 1,
      process: "backend",
    }));
    expect(sink.mock.calls[0]?.[0]).not.toContain(secret);
    expect(sink.mock.calls[0]?.[0]).not.toContain("claimed-human");
  });
});
