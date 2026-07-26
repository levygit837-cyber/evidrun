import { AlertTriangle, ArrowLeft, FileWarning, Radio, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import type { ObservabilityAdapter, RunStreamState } from "../../data/contracts";
import type { RunDetail } from "../../types";
import { EvaluationPanel } from "./EvaluationPanel";
import { EvidencePanel } from "./EvidencePanel";
import { Fact, StatusMark } from "./ObservabilityParts";
import { TracePanel } from "./TracePanel";
import { type DetailData, formatDate, formatDuration } from "./observabilityModel";

type DetailTab = "trace" | "evaluation" | "evidence" | "execution";

function GeneralFacts({ data }: { data: DetailData }) {
  const { run } = data;
  return (
    <div className="obs-general-facts">
      {run.contract_mode === "legacy_v1" ? (
        <div className="obs-context-note obs-context-note-warning" role="status">
          <FileWarning aria-hidden="true" size={15} />
          <span>Run legacy. Contratos canônicos, job e attempts podem não existir.</span>
        </div>
      ) : null}
      <dl>
        <Fact label="Run">{run.id}</Fact>
        <Fact label="Status"><StatusMark status={run.status} /></Fact>
        <Fact label="Study revision">{run.experiment_revision_id}</Fact>
        <Fact label="Variant">{run.variant_id}</Fact>
        <Fact label="RunSpec">{run.run_spec_id ?? "Sem record"}</Fact>
        <Fact label="AdmissionRecord">{run.admission_id ?? "Sem record"}</Fact>
        <Fact label="SubjectEnvelope digest">{run.subject_envelope_digest ?? "Não materializado"}</Fact>
        <Fact label="Runner">{run.runner}</Fact>
        <Fact label="Duração">{formatDuration(run)}</Fact>
        <Fact label="Retry of">{run.record?.retry_of ?? "Não é retry"}</Fact>
        <Fact label="Job">{run.execution?.job.job_id ?? "Não informado"}</Fact>
        <Fact label="Attempts">{run.execution?.attempts.length ?? "Não informado"}</Fact>
        <Fact label="Criada em">{formatDate(run.created_at)}</Fact>
        <Fact label="Terminal em">{formatDate(run.completed_at)}</Fact>
      </dl>
    </div>
  );
}

function ExecutionPanel({ run }: { run: RunDetail }) {
  return (
    <div className="obs-execution">
      <section>
        <header>Run</header>
        <dl>
          <Fact label="Run ID">{run.id}</Fact>
          <Fact label="Lifecycle">{run.status}</Fact>
          <Fact label="Retry of">{run.record?.retry_of ?? "Não é retry"}</Fact>
          <Fact label="RunSpec digest">{run.record?.run_spec_digest ?? "Sem record"}</Fact>
          <Fact label="Admission digest">{run.record?.admission_digest ?? "Sem record"}</Fact>
        </dl>
      </section>
      <section>
        <header>Job</header>
        {run.execution ? (
          <dl>
            <Fact label="Job ID">{run.execution.job.job_id}</Fact>
            <Fact label="Status">{run.execution.job.status}</Fact>
            <Fact label="Active attempt">{run.execution.job.active_attempt_id ?? "Nenhum"}</Fact>
            <Fact label="Lease generation">{run.execution.job.lease_generation}</Fact>
            <Fact label="Disponível em">{formatDate(run.execution.job.available_at_utc)}</Fact>
            <Fact label="Finalizado em">{formatDate(run.execution.job.finished_at_utc)}</Fact>
            <Fact label="Digest">{run.execution.job.digest}</Fact>
          </dl>
        ) : (
          <p>Sem RunExecutionJob.</p>
        )}
      </section>
      <section>
        <header>Attempts</header>
        {run.execution?.attempts.length ? (
          <ol>
            {run.execution.attempts.map((attempt) => (
              <li key={attempt.attempt_id}>
                <strong className="mono">{attempt.attempt_id}</strong>
                <dl>
                  <Fact label="Ordinal">{attempt.ordinal}</Fact>
                  <Fact label="Status">{attempt.status}</Fact>
                  <Fact label="Worker">{attempt.worker_id}</Fact>
                  <Fact label="Lease generation">{attempt.lease_generation}</Fact>
                  <Fact label="Heartbeat">{formatDate(attempt.last_heartbeat_at_utc)}</Fact>
                  <Fact label="Lease expira">{formatDate(attempt.lease_expires_at_utc)}</Fact>
                  <Fact label="Reason code">{attempt.reason_code ?? "Não informado"}</Fact>
                </dl>
              </li>
            ))}
          </ol>
        ) : (
          <p>Sem RunExecutionAttempts.</p>
        )}
      </section>
    </div>
  );
}

function StreamState({ state }: { state: RunStreamState }) {
  const labels: Record<RunStreamState, string> = {
    connecting: "Conectando stream",
    open: "Stream aberto",
    reconnecting: "Reconectando stream",
    closed: "Stream fechado",
  };
  return (
    <span className={`obs-stream-state obs-stream-${state}`} role="status">
      {state === "reconnecting" ? <RefreshCw className="obs-spin" size={12} /> : <Radio size={12} />}
      {labels[state]}
    </span>
  );
}

export function RunDetailPanel({
  data,
  adapter,
  streamState,
  streamError,
  onBack,
}: {
  data: DetailData;
  adapter: ObservabilityAdapter;
  streamState: RunStreamState;
  streamError: string | null;
  onBack(): void;
}) {
  const [activeTab, setActiveTab] = useState<DetailTab>("trace");
  useEffect(() => setActiveTab("trace"), [data.run.id]);
  const tabs: Array<{ id: DetailTab; label: string }> = [
    { id: "trace", label: "Trace" },
    { id: "evaluation", label: "Evaluation" },
    { id: "evidence", label: "Evidence" },
    { id: "execution", label: "Execution" },
  ];

  function moveTab(current: DetailTab, key: string) {
    const currentIndex = tabs.findIndex((tab) => tab.id === current);
    let nextIndex = currentIndex;
    if (key === "ArrowRight") nextIndex = (currentIndex + 1) % tabs.length;
    else if (key === "ArrowLeft") nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
    else if (key === "Home") nextIndex = 0;
    else if (key === "End") nextIndex = tabs.length - 1;
    else return;
    const next = tabs[nextIndex]!;
    setActiveTab(next.id);
    requestAnimationFrame(() => document.getElementById(`obs-tab-${next.id}`)?.focus());
  }

  return (
    <div className="obs-detail-panel">
      <header className="obs-detail-header">
        <button className="obs-back-button" onClick={onBack} type="button">
          <ArrowLeft aria-hidden="true" size={15} />
          Voltar às Runs
        </button>
        <div>
          <code title={data.run.id}>{data.run.id}</code>
          <StatusMark status={data.run.status} />
        </div>
        <StreamState state={streamState} />
      </header>
      {streamError ? (
        <div className="obs-stream-error" role="status">
          <AlertTriangle aria-hidden="true" size={14} />
          {streamError}
        </div>
      ) : null}
      <div className="obs-detail-scroll">
        <GeneralFacts data={data} />
        <nav className="obs-tabs" aria-label="Detalhes da Run" role="tablist">
          {tabs.map((tab) => (
            <button
              aria-controls={`obs-panel-${tab.id}`}
              aria-selected={activeTab === tab.id}
              id={`obs-tab-${tab.id}`}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              onKeyDown={(event) => moveTab(tab.id, event.key)}
              role="tab"
              tabIndex={activeTab === tab.id ? 0 : -1}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </nav>
        <div aria-labelledby="obs-tab-trace" className="obs-tab-panel" hidden={activeTab !== "trace"} id="obs-panel-trace" role="tabpanel"><TracePanel events={data.events} /></div>
        <div aria-labelledby="obs-tab-evaluation" className="obs-tab-panel" hidden={activeTab !== "evaluation"} id="obs-panel-evaluation" role="tabpanel"><EvaluationPanel evaluations={data.evaluations} /></div>
        <div aria-labelledby="obs-tab-evidence" className="obs-tab-panel" hidden={activeTab !== "evidence"} id="obs-panel-evidence" role="tabpanel"><EvidencePanel adapter={adapter} data={data} /></div>
        <div aria-labelledby="obs-tab-execution" className="obs-tab-panel" hidden={activeTab !== "execution"} id="obs-panel-execution" role="tabpanel"><ExecutionPanel run={data.run} /></div>
      </div>
    </div>
  );
}
