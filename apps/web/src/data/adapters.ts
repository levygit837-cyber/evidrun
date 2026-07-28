import { api, runEventStream } from "../api/client";
import type { CreationAdapter, LaboratoryAdapter, ObservabilityAdapter } from "./contracts";

export const creationAdapter: CreationAdapter = {
  bootstrapCanonicalDemo: api.bootstrapDemo,
};

export const observabilityAdapter: ObservabilityAdapter = {
  listRuns: api.runs,
  getRun: api.runDetail,
  getEvents: api.runEvents,
  getEvaluations: api.runEvaluations,
  getCheckpoints: api.runCheckpoints,
  getProvider: api.defaultProvider,
  exportRunBundle: api.exportRunBundle,
  async retryRun(runId, runSpecId) {
    // Admit first: a retry requires an AdmissionRecord created after the source Run went
    // terminal, and reusing the original one is refused by contract.
    const admission = await api.admitRunSpec(runSpecId);
    // The idempotency key is derived from the source Run, not from the clock. A wall-clock key
    // differs on every click, and the queue dedupes on that key alone — so a double click used
    // to enqueue two Runs nobody asked for. Retrying the same Run twice on purpose is still
    // possible; it just needs the first retry to have finished and produced a new source.
    return api.retryRun(runId, admission.id, `retry-of-${runId}`);
  },
  stream: runEventStream,
};

export const productionLaboratoryAdapter: LaboratoryAdapter = {
  mode: "integration_pending",
  async *send() {
    yield {
      type: "error",
      source: "integration_pending",
      message: "O backend ainda não fornece send/stream/cancel para o Lab Agent.",
    };
  },
};
