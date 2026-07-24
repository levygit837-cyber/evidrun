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
