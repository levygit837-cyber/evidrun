import { api, LabStreamError, runEventStream } from "../api/client";
import type {
  CreationAdapter,
  LabSession,
  LabUiEvent,
  LaboratoryAdapter,
  LaboratorySessionAdapter,
  LabScopeSelection,
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

export class LiveLaboratoryAdapter implements LaboratorySessionAdapter {
  readonly mode = "live" as const;
  private session: LabSession | null = null;

  async scopeOptions() {
    const dashboard = await api.dashboard();
    return { workspaces: dashboard.workspaces, projects: dashboard.projects };
  }

  activeSession() {
    return this.session;
  }

  async selectScope(selection: LabScopeSelection): Promise<LabSession> {
    const sessions = await api.labSessions(selection.workspaceId);
    const session = sessions.find(
      (candidate) =>
        candidate.project_id === (selection.projectId ?? null) &&
        candidate.focus_kind === (selection.focusKind ?? null) &&
        candidate.focus_id === (selection.focusId ?? null),
    );
    this.session =
      session ??
      (await api.createLabSession({
        workspace_id: selection.workspaceId,
        title: "Laboratory",
        ...(selection.projectId ? { project_id: selection.projectId } : {}),
        ...(selection.focusKind ? { focus_kind: selection.focusKind } : {}),
        ...(selection.focusId ? { focus_id: selection.focusId } : {}),
      }));
    return this.session;
  }

  async messages() {
    if (!this.session) return [];
    return api.labMessages(this.session.id, this.session.workspace_id);
  }

  async *send(input: string, signal: AbortSignal): AsyncGenerator<LabUiEvent> {
    let sawDone = false;
    try {
      const session = this.session;
      if (!session) throw new Error("Escolha um escopo antes de enviar uma mensagem.");
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
