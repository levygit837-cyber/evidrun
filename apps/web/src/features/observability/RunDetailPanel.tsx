import { AlertTriangle, ArrowLeft, CircleSlash, FileWarning, Radio, RefreshCw } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import type { ObservabilityAdapter, RunStreamState } from "../../data/contracts";
import { auditTerm, productTerms } from "../../productLanguage";
import type { ExecutorState, RunDetail } from "../../types";
import { EvaluationPanel } from "./EvaluationPanel";
import { EvidencePanel } from "./EvidencePanel";
import { Fact, StatusMark } from "./ObservabilityParts";
import { TracePanel } from "./TracePanel";
import { type DetailData, formatDate, formatDuration } from "./observabilityModel";
import { runProgressIssue, issueTone, type RunProgressIssue } from "./runProgress";
import { executionTrustText, isolationText } from "./executionTrust";
import {
  attemptSummary,
  describeAttempts,
  goalStateLabels,
  isAnomaly,
  runMetrics,
  runOutcome,
} from "./runOutcome";

type DetailTab = "trace" | "evaluation" | "evidence" | "execution";

function GeneralFacts({
  data,
  adapter,
  onRetried,
}: {
  data: DetailData;
  adapter: ObservabilityAdapter;
  onRetried(runId: string): void;
}) {
  const { run } = data;
  const outcome = runOutcome(data.events);
  const metrics = runMetrics(data.events);
  const attempts = attemptSummary((run.execution?.attempts ?? []).map((attempt) => attempt.status));
  const trust = executionTrustText(run.execution_trust);
  return (
    <div className="obs-general-facts">
      {run.contract_mode === "legacy_v1" ? (
        <div className="obs-context-note obs-context-note-warning" role="status">
          <FileWarning aria-hidden="true" size={15} />
          <span>Run legacy. Contratos canônicos, job e attempts podem não existir.</span>
        </div>
      ) : null}
      {isAnomaly(outcome) ? (
        <AnomalyNote adapter={adapter} onRetried={onRetried} run={run} />
      ) : null}
      <dl>
        <Fact label={productTerms.run.label}>{run.id}</Fact>
        <Fact label="Status"><StatusMark status={run.status} /></Fact>
        <Fact label="Trust">{trust.label} — {trust.explanation}</Fact>
        <Fact label="Trust ID">
          {run.execution_trust.status === "recorded"
            ? run.execution_trust.trust_id
            : "Não registrado"}
        </Fact>
        <Fact label="Isolamento">{isolationText(run.isolation)}</Fact>
        {outcome.goalState ? (
          <Fact label="Resultado">{goalStateLabels[outcome.goalState]}</Fact>
        ) : null}
        {outcome.terminalCause ? <Fact label="Causa">{outcome.terminalCause}</Fact> : null}
        {metrics.inputTokens !== null || metrics.outputTokens !== null ? (
          <Fact label="Tokens">
            {`${metrics.inputTokens ?? "?"} entrada / ${metrics.outputTokens ?? "?"} saída`}
          </Fact>
        ) : null}
        {metrics.toolCalls !== null ? <Fact label="Tool calls">{metrics.toolCalls}</Fact> : null}
        <Fact label={auditTerm(productTerms.studyVersion)}>{run.experiment_revision_id}</Fact>
        <Fact label="Variant">{run.variant_id}</Fact>
        <Fact label={auditTerm(productTerms.runSpec)}>{run.run_spec_id ?? "Sem record"}</Fact>
        <Fact label={auditTerm(productTerms.admission)}>{run.admission_id ?? "Sem record"}</Fact>
        <Fact label={`${auditTerm(productTerms.subjectEnvelope)} digest`}>{run.subject_envelope_digest ?? "Não materializado"}</Fact>
        <Fact label="Runner">{run.runner}</Fact>
        <Fact label="Duração">{formatDuration(run)}</Fact>
        <Fact label="Rerun of">{run.record?.retry_of ?? "Não é rerun"}</Fact>
        <Fact label="Job">{run.execution?.job.job_id ?? "Não informado"}</Fact>
        <Fact label="Attempts">
          {run.execution ? describeAttempts(attempts) : "Não informado"}
        </Fact>
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
        <header>{productTerms.run.label}</header>
        <dl>
          <Fact label="Run ID">{run.id}</Fact>
          <Fact label="Lifecycle">{run.status}</Fact>
          <Fact label="Rerun of">{run.record?.retry_of ?? "Não é rerun"}</Fact>
          <Fact label={`${auditTerm(productTerms.runSpec)} digest`}>{run.record?.run_spec_digest ?? "Sem record"}</Fact>
          <Fact label={`${auditTerm(productTerms.admission)} digest`}>{run.record?.admission_digest ?? "Sem record"}</Fact>
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

/**
 * What `not_assessable` means, said plainly.
 *
 * The distinction is the point: this Run produced no gradable result, which is not the same as
 * the Subject getting it wrong. Reading one as the other would count infrastructure failures as
 * model failures.
 */
function AnomalyNote({
  adapter,
  run,
  onRetried,
}: {
  adapter: ObservabilityAdapter;
  run: RunDetail;
  onRetried(runId: string): void;
}) {
  const retry = useMutation({
    mutationFn: () => adapter.retryRun(run.id, run.run_spec_id!),
    onSuccess: (result) => onRetried(result.run_id),
  });
  return (
    <div className="obs-context-note obs-context-note-anomaly" role="status">
      <CircleSlash aria-hidden="true" size={15} />
      <div className="obs-anomaly-copy">
        <span>
          Ausência de resultado, não resultado negativo. A execução não chegou a produzir algo
          avaliável, então esta Run não afirma nada sobre o Subject.
        </span>
        {run.run_spec_id ? (
          <>
            <button
              className="obs-action-button"
              disabled={retry.isPending}
              onClick={() => retry.mutate()}
              type="button"
            >
              {retry.isPending ? "Refazendo…" : "Rerun"}
            </button>
            {/* Said plainly because the distinction is load-bearing: nothing here resumes the
                original Run, and a resumed conversation is not what happens. */}
            <span className="obs-anomaly-hint">
              Rerun usa o mesmo Execution Plan do zero e cria uma Run nova com proveniência
              declarada. Esta Run permanece como está.
            </span>
            {/* Its own `alert`, because the enclosing note is polite and a failed retry is not
                something to leave to the next announcement. */}
            {retry.isError ? (
              <span className="obs-anomaly-error" role="alert">
                {retry.error instanceof Error ? retry.error.message : "Falha ao criar a nova Run."}
              </span>
            ) : null}
          </>
        ) : (
          <span className="obs-anomaly-hint">
            Sem Execution Plan canônico, rerun não está disponível para esta Run.
          </span>
        )}
      </div>
    </div>
  );
}

/**
 * The progress note for a Run that is not moving.
 *
 * A reconnecting stream is transient and recovers on its own; a stalled executor blocks the Run
 * until someone acts. Both used to render as the same error line.
 */
function ProgressNote({ issue }: { issue: RunProgressIssue }) {
  const tone = issueTone(issue);
  return (
    <div
      className={`obs-progress-note obs-progress-note-${tone}`}
      role={tone === "danger" ? "alert" : "status"}
    >
      {issue.kind === "executor-down" ? (
        <AlertTriangle aria-hidden="true" size={15} />
      ) : (
        <RefreshCw aria-hidden="true" className="obs-spin" size={15} />
      )}
      <span>{issue.message}</span>
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
  executor,
  onBack,
  onRetried,
}: {
  data: DetailData;
  adapter: ObservabilityAdapter;
  streamState: RunStreamState;
  streamError: string | null;
  /**
   * Passed in rather than read from context, so the panel stays a plain view: a Run detail does
   * not need to know that a desktop shell exists. Absent outside one.
   */
  executor?: ExecutorState;
  onBack(): void;
  /** Called with the id of the Run a retry created, so the caller can follow it. */
  onRetried(runId: string): void;
}) {
  const [activeTab, setActiveTab] = useState<DetailTab>("trace");
  useEffect(() => setActiveTab("trace"), [data.run.id]);
  const issue = runProgressIssue({ run: data.run, streamState, streamError, executor });
  const trust = executionTrustText(data.run.execution_trust);
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
        <div className="obs-detail-identity">
          <div className="obs-detail-primary">
            <code title={data.run.id}>{data.run.id}</code>
            <StatusMark status={data.run.status} />
          </div>
          <div className="obs-detail-context">
            <span>Trust: {trust.label}</span>
            <span>Isolamento: {isolationText(data.run.isolation)}</span>
          </div>
        </div>
        <StreamState state={streamState} />
      </header>
      {issue ? <ProgressNote issue={issue} /> : null}
      <div className="obs-detail-scroll">
        <GeneralFacts adapter={adapter} data={data} onRetried={onRetried} />
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
