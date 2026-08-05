import { api, LabStreamError, runEventStream } from "../api/client";
import type {
  CreationAdapter,
  LabSession,
  LabUiEvent,
  LaboratoryAdapter,
  ObservabilityAdapter,
} from "./contracts";

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

export class LiveLaboratoryAdapter implements LaboratoryAdapter {
  readonly mode = "live" as const;
  private session: Promise<LabSession> | null = null;

  private resolveSession(): Promise<LabSession> {
    if (this.session) return this.session;
    this.session = (async () => {
      const dashboard = await api.dashboard();
      const workspace = dashboard.workspaces[0];
      if (!workspace) throw new Error("Nenhum Workspace está disponível para o Laboratory.");
      return api.createLabSession({
        workspace_id: workspace.id,
        title: "Laboratory",
      });
    })();
    this.session.catch(() => {
      // Uma falha transitória não deve inutilizar o adapter por todo o restante da sessão da UI.
      this.session = null;
    });
    return this.session;
  }

  async *send(input: string, signal: AbortSignal): AsyncGenerator<LabUiEvent> {
    let sawDone = false;
    try {
      const session = await this.resolveSession();
      if (signal.aborted) return;
      for await (const event of api.streamLabTurn(
        session.id,
        session.workspace_id,
        input,
        signal,
      )) {
        yield event;
        if (event.type === "done") sawDone = true;
      }
      if (!signal.aborted && !sawDone) {
        yield {
          type: "error",
          source: "live",
          message: "O turno foi interrompido antes de confirmar sua conclusão.",
        };
      }
    } catch (error) {
      if (signal.aborted) return;
      if (error instanceof LabStreamError && error.labError) {
        yield {
          type: "error",
          source: "live",
          message: error.labError.message,
          code: error.labError.code,
          remediation: error.labError.remediation,
        };
        return;
      }
      yield {
        type: "error",
        source: "live",
        message: error instanceof Error ? error.message : "Falha ao executar o turno do Laboratory.",
      };
    }
  }
}

export const productionLaboratoryAdapter: LaboratoryAdapter = new LiveLaboratoryAdapter();
