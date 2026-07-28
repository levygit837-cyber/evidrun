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
    if (admission.decision !== "admitted") {
      throw new Error(`A admissão recusou este RunSpec: ${admission.decision}`);
    }
    return api.retryRun(runId, admission.id, `retry-${runId}-${Date.now()}`);
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
