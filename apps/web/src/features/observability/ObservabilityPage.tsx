import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearch } from "@tanstack/react-router";
import {
  AlertTriangle,
  ArrowLeft,
  Box,
  Check,
  ChevronDown,
  Copy,
  Download,
  ExternalLink,
  FileWarning,
  LoaderCircle,
  Radio,
  RefreshCw,
  Search,
  TerminalSquare,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { observabilityAdapter } from "../../data/adapters";
import type {
  ObservabilityAdapter,
  RunStreamState,
} from "../../data/contracts";
import type {
  CheckpointRecordDto,
  EvaluationRecordDto,
  Run,
  RunDetail,
  RunEvent,
} from "../../types";
import {
  ACTIVE_RUN_STATUSES,
  ATTENTION_RUN_STATUSES,
  TERMINAL_RUN_STATUSES,
  cleanSearchState,
  correlateToolEvents,
  filterRuns,
  getForensicTurnWindow,
  mergeEvents,
  normalizePeriodFilter,
  normalizeStatusFilter,
  projectEvidenceReferences,
  sortEvents,
  summarizeRuns,
  type ObservabilitySearchState,
} from "./observabilityModel";
import "./observability.css";

type DetailTab = "trace" | "evaluation" | "evidence" | "execution";

interface DetailData {
  run: RunDetail;
  events: RunEvent[];
  evaluations: EvaluationRecordDto[];
  checkpoints: CheckpointRecordDto[];
}

interface ObservabilityWorkspaceProps {
  adapter?: ObservabilityAdapter;
  search: ObservabilitySearchState;
  onSearchChange(next: ObservabilitySearchState): void;
}

const statusLabels: Record<string, string> = {
  queued: "Queued",
  preparing: "Preparing",
  running: "Running",
  evaluating: "Evaluating",
  completed: "Completed",
  failed: "Failed",
  budget_exhausted: "Budget exhausted",
  cancelled: "Cancelled",
  guardrail_stopped: "Guardrail stopped",
};

function statusTone(status: string): string {
  if (status === "completed") return "success";
  if (ATTENTION_RUN_STATUSES.has(status)) return "danger";
  if (status === "running" || status === "evaluating") return "info";
  return "neutral";
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "Não registrado";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

function formatDuration(run: Run): string {
  if (!run.completed_at) return ACTIVE_RUN_STATUSES.has(run.status) ? "Em curso" : "Não registrado";
  const duration = Date.parse(run.completed_at) - Date.parse(run.created_at);
  if (!Number.isFinite(duration) || duration < 0) return "Não registrado";
  if (duration < 1_000) return `${duration} ms`;
  return `${(duration / 1_000).toFixed(1)} s`;
}

function shortId(value: string | null | undefined): string {
  if (!value) return "Não registrado";
  return value.length > 28 ? `${value.slice(0, 16)}…${value.slice(-8)}` : value;
}

function Fact({ label, children, mono = true }: { label: string; children: ReactNode; mono?: boolean }) {
  return (
    <div className="obs-fact">
      <dt>{label}</dt>
      <dd className={mono ? "mono" : undefined}>{children}</dd>
    </div>
  );
}

function StatusMark({ status }: { status: string }) {
  return (
    <span className={`obs-status obs-status-${statusTone(status)}`}>
      <span aria-hidden="true" />
      {statusLabels[status] ?? status}
    </span>
  );
}

function ListLoadingState() {
  return (
    <div className="obs-list-loading" aria-label="Carregando Runs" role="status">
      {Array.from({ length: 7 }, (_, index) => (
        <div className="obs-skeleton-row" key={index} aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
        </div>
      ))}
    </div>
  );
}

function PageState({
  icon,
  title,
  children,
  role,
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
  role?: "alert" | "status";
}) {
  return (
    <div className="obs-page-state" role={role}>
      {icon}
      <strong>{title}</strong>
      <span>{children}</span>
    </div>
  );
}

function RunList({
  runs,
  selectedRunId,
  onSelect,
}: {
  runs: Run[];
  selectedRunId?: string;
  onSelect(runId: string): void;
}) {
  return (
    <div className="obs-run-list" role="group" aria-label="Lista de Runs">
      <div className="obs-list-head" aria-hidden="true">
        <span>Run</span>
        <span>Study revision / variant</span>
        <span>Runner</span>
        <span>Status</span>
        <span>Detalhe</span>
        <span>Duração</span>
        <span>Horário</span>
      </div>
      {runs.map((run) => (
        <button
          className="obs-run-row"
          data-selected={selectedRunId === run.id || undefined}
          key={run.id}
          onClick={() => onSelect(run.id)}
          type="button"
        >
          <span className="obs-run-primary mono" title={run.id}>
            {shortId(run.id)}
            {run.contract_mode === "legacy_v1" ? <small>Legacy</small> : null}
          </span>
          <span className="obs-run-study">
            <strong title={run.experiment_revision_id}>{shortId(run.experiment_revision_id)}</strong>
            <small className="mono" title={run.variant_id}>{run.variant_id}</small>
          </span>
          <span className="obs-run-provider">
            <strong className="mono" title={run.runner}>{shortId(run.runner)}</strong>
          </span>
          <span><StatusMark status={run.status} /></span>
          <span className="mono">{run.contract_mode === "legacy_v1" ? "Legacy" : "Ver detalhe"}</span>
          <span className="mono">{formatDuration(run)}</span>
          <span className="mono">{formatDate(run.created_at)}</span>
        </button>
      ))}
    </div>
  );
}

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

function TracePanel({ events }: { events: RunEvent[] }) {
  const ordered = useMemo(() => sortEvents(events), [events]);
  const toolCorrelations = useMemo(() => correlateToolEvents(ordered), [ordered]);
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const selectedEvent = ordered.find((event) => event.event_id === expandedEventId) ?? null;
  const forensicWindow = selectedEvent
    ? getForensicTurnWindow(ordered, selectedEvent.event_id)
    : null;

  useEffect(() => {
    setExpandedEventId(null);
    setCopied(false);
  }, [events[0]?.run_id]);

  async function copyWindow() {
    if (!forensicWindow) return;
    await navigator.clipboard.writeText(JSON.stringify(forensicWindow, null, 2));
    setCopied(true);
  }

  if (!ordered.length) {
    return (
      <PageState icon={<TerminalSquare size={20} />} title="Sem eventos" role="status">
        O ledger ainda não possui records para esta Run.
      </PageState>
    );
  }

  return (
    <div className="obs-trace">
      <ol aria-label="Eventos ordenados por sequence">
        {ordered.map((event) => {
          const expanded = expandedEventId === event.event_id;
          const toolState = toolCorrelations.get(event.event_id);
          return (
            <li key={`${event.sequence}:${event.event_id}`} data-event-type={event.type}>
              <button
                aria-expanded={expanded}
                className="obs-event-row"
                onClick={() => {
                  setCopied(false);
                  setExpandedEventId(expanded ? null : event.event_id);
                }}
                type="button"
              >
                <span className="obs-event-sequence mono">{String(event.sequence).padStart(3, "0")}</span>
                <span className="obs-event-type mono">
                  {toolState === "complete" ? <Box aria-hidden="true" size={13} /> : null}
                  {event.type}
                </span>
                <span className="obs-event-actor">{event.actor_type}</span>
                <time className="mono" dateTime={event.occurred_at_utc}>{formatDate(event.occurred_at_utc)}</time>
                <ChevronDown aria-hidden="true" size={14} />
              </button>
              {expanded ? (
                <div className="obs-event-expanded">
                  {toolState === "complete" ? (
                    <div className="obs-tool-state">Tool activity correlacionada por call_id.</div>
                  ) : null}
                  {toolState === "orphan-terminal" ? (
                    <div className="obs-tool-state obs-tool-state-incomplete">Evento factual incompleto: tool.called correlacionado não foi carregado.</div>
                  ) : null}
                  <dl>
                    <Fact label="Sequence">{event.sequence}</Fact>
                    <Fact label="Timestamp">{formatDate(event.occurred_at_utc)}</Fact>
                    <Fact label="Classification">{event.classification || "Não informado"}</Fact>
                    <Fact label="Correlation ID">{event.correlation_id ?? "Não informado"}</Fact>
                    <Fact label="Causation ID">{event.causation_id ?? "Não informado"}</Fact>
                    <Fact label="Event ID">{event.event_id}</Fact>
                    <Fact label="Event hash">{event.event_hash}</Fact>
                    <Fact label="Prev hash">{event.prev_event_hash ?? "Primeiro evento"}</Fact>
                    <Fact label="Actor">{`${event.actor_type}:${event.actor_id}`}</Fact>
                  </dl>
                  <label>
                    Payload factual
                    <pre tabIndex={0}>{JSON.stringify(event.payload, null, 2)}</pre>
                  </label>
                  <section className="obs-forensic-window" aria-label="Janela forense read-only">
                    <div>
                      <strong>Janela forense read-only</strong>
                      <span>{forensicWindow ? "1 turno disponível" : "Nenhum turno completo neste ponto"}</span>
                    </div>
                    {forensicWindow ? (
                      <>
                        <button className="obs-text-button" onClick={() => void copyWindow()} type="button">
                          {copied ? <Check aria-hidden="true" size={13} /> : <Copy aria-hidden="true" size={13} />}
                          {copied ? "Copiado" : "Copiar 1 turno"}
                        </button>
                        <pre tabIndex={0}>{JSON.stringify(forensicWindow, null, 2)}</pre>
                      </>
                    ) : null}
                  </section>
                </div>
              ) : null}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function EvaluationPanel({ evaluations }: { evaluations: EvaluationRecordDto[] }) {
  if (!evaluations.length) {
    return (
      <PageState icon={<FileWarning size={20} />} title="Sem EvaluationRecords" role="status">
        Nenhum record canônico foi preservado para esta Run.
      </PageState>
    );
  }
  return (
    <div className="obs-evaluations">
      {evaluations.map((evaluation) => (
        <article key={evaluation.record_id}>
          <header>
            <div>
              <strong className="mono">{evaluation.record_id}</strong>
              <span>{evaluation.stage_id} / {evaluation.source_type}</span>
            </div>
            <span className={`obs-gate obs-gate-${evaluation.gate_status}`}>
              Gate {evaluation.gate_status}
            </span>
          </header>
          <dl className="obs-evaluation-meta">
            <Fact label="Status">{evaluation.status}</Fact>
            <Fact label="Digest">{evaluation.digest}</Fact>
            <Fact label="Boundary sequence">{evaluation.boundary.up_to_event_sequence ?? "Não informada"}</Fact>
          </dl>
          <div className="obs-dimensions">
            {evaluation.dimension_values.map((dimension) => (
              <section key={dimension.dimension_id}>
                <div className="obs-dimension-heading">
                  <strong>{dimension.dimension_id}</strong>
                  <code>{String(dimension.value)}</code>
                </div>
                <dl>
                  <Fact label="Rationale" mono={false}>{dimension.rationale}</Fact>
                  <Fact label="Confidence">{dimension.confidence ?? "Não informada"}</Fact>
                  <Fact label="Evidence">
                    {dimension.evidence_refs.map((item) => item.ref).join(", ")}
                  </Fact>
                </dl>
              </section>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}

function EvidencePanel({
  data,
  adapter,
}: {
  data: DetailData;
  adapter: ObservabilityAdapter;
}) {
  const refs = useMemo(
    () => projectEvidenceReferences(data.events, data.evaluations, data.checkpoints),
    [data.checkpoints, data.evaluations, data.events],
  );
  const groupedRefs = useMemo(() => ({
    event: refs.filter((item) => item.origin === "event"),
    evaluation: refs.filter((item) => item.origin === "evaluation"),
    checkpoint: refs.filter((item) => item.origin === "checkpoint"),
  }), [refs]);
  const [exportedPath, setExportedPath] = useState<string | null>(null);
  const [revealError, setRevealError] = useState<string | null>(null);
  const exportBundle = useMutation({
    mutationFn: () => adapter.exportRunBundle(data.run.id),
    onSuccess: (result) => setExportedPath(result.path),
  });
  const terminal = TERMINAL_RUN_STATUSES.has(data.run.status);

  useEffect(() => {
    setExportedPath(null);
    setRevealError(null);
  }, [data.run.id]);

  async function reveal() {
    if (!exportedPath || !window.evidrunDesktop) return;
    setRevealError(null);
    const shown = await window.evidrunDesktop.showItemInFolder(exportedPath);
    if (!shown) setRevealError("O desktop não conseguiu revelar o arquivo exportado.");
  }

  return (
    <div className="obs-evidence">
      <div className="obs-context-note">
        <Box aria-hidden="true" size={15} />
        <span>Bundle v3 usa references_only. portable=false e replayable=false.</span>
      </div>
      <div className="obs-bundle-actions">
        <button
          className="obs-action-button"
          disabled={!terminal || exportBundle.isPending}
          onClick={() => exportBundle.mutate()}
          type="button"
        >
          {exportBundle.isPending ? <LoaderCircle className="obs-spin" size={14} /> : <Download size={14} />}
          Exportar Bundle v3
        </button>
        {!terminal ? <span>Disponível após estado terminal.</span> : null}
        {exportedPath ? (
          <button
            className="obs-text-button"
            disabled={!window.evidrunDesktop}
            onClick={() => void reveal()}
            type="button"
          >
            <ExternalLink aria-hidden="true" size={13} />
            Revelar arquivo
          </button>
        ) : null}
      </div>
      {exportBundle.isError ? (
        <div className="obs-inline-error" role="alert">Falha ao exportar o Bundle v3.</div>
      ) : null}
      {exportedPath ? <code className="obs-export-path">{exportedPath}</code> : null}
      {revealError ? <div className="obs-inline-error" role="alert">{revealError}</div> : null}
      <section className="obs-reference-list">
        <header>
          <strong>Referências preservadas</strong>
          <span>{refs.length}</span>
        </header>
        {refs.length ? (
          <div className="obs-evidence-groups">
            {(["event", "evaluation", "checkpoint"] as const).map((origin) => groupedRefs[origin].length ? (
              <section key={origin}>
                <h3>{origin === "event" ? "Run events" : origin === "evaluation" ? "Evaluation records" : "Checkpoint records"}</h3>
                <ul>
                  {groupedRefs[origin].map((item, index) => (
                    <li key={`${item.sourceId}:${item.ref}:${index}`}>
                      <code>{item.ref}</code>
                      <dl>
                        <Fact label="Origem">{item.origin}</Fact>
                        <Fact label="Papel">{item.role || "Não informado"}</Fact>
                        <Fact label="Record">{item.sourceId || "Não informado"}</Fact>
                        <Fact label="Digest">{item.digest ?? "Não informado"}</Fact>
                        <Fact label="Media type">{item.mediaType ?? "Não informado"}</Fact>
                        <Fact label="Sequence">{item.sequence ?? "Não informado"}</Fact>
                        <Fact label="Timestamp">{item.timestamp ? formatDate(item.timestamp) : "Não informado"}</Fact>
                        <Fact label="Classification">{item.classification ?? "Não informado"}</Fact>
                        <Fact label="Gate">{item.gateStatus ?? "Não informado"}</Fact>
                      </dl>
                      <span>Referência preservada; conteúdo indisponível</span>
                    </li>
                  ))}
                </ul>
              </section>
            ) : null)}
          </div>
        ) : (
          <PageState icon={<FileWarning size={20} />} title="Sem referências" role="status">
            Nenhuma ref run:, event: ou artifact: aparece nos records carregados.
          </PageState>
        )}
      </section>
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

function RunDetailPanel({
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

export function ObservabilityWorkspace({
  adapter = observabilityAdapter,
  search,
  onSearchChange,
}: ObservabilityWorkspaceProps) {
  const queryClient = useQueryClient();
  const runsQuery = useQuery({ queryKey: ["observability", "runs"], queryFn: adapter.listRuns });
  const selectedRunId = search.run;
  const detailQuery = useQuery({
    queryKey: ["observability", "run", selectedRunId],
    enabled: Boolean(selectedRunId),
    queryFn: async (): Promise<DetailData> => {
      const runId = selectedRunId!;
      const [run, events, evaluations, checkpoints] = await Promise.all([
        adapter.getRun(runId),
        adapter.getEvents(runId),
        adapter.getEvaluations(runId),
        adapter.getCheckpoints(runId),
      ]);
      return { run, events: mergeEvents(run.events, events), evaluations, checkpoints };
    },
  });
  const [streamState, setStreamState] = useState<RunStreamState>("closed");
  const [streamError, setStreamError] = useState<string | null>(null);
  const [moreFiltersOpen, setMoreFiltersOpen] = useState(false);
  const moreFiltersRef = useRef<HTMLDivElement>(null);
  const moreFiltersButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!moreFiltersOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      setMoreFiltersOpen(false);
      moreFiltersButtonRef.current?.focus();
    };
    const closeOnOutsidePointer = (event: PointerEvent) => {
      if (event.target instanceof Node && !moreFiltersRef.current?.contains(event.target)) {
        setMoreFiltersOpen(false);
      }
    };
    document.addEventListener("keydown", closeOnEscape);
    document.addEventListener("pointerdown", closeOnOutsidePointer);
    return () => {
      document.removeEventListener("keydown", closeOnEscape);
      document.removeEventListener("pointerdown", closeOnOutsidePointer);
    };
  }, [moreFiltersOpen]);

  useEffect(() => {
    if (!selectedRunId) {
      setStreamState("closed");
      setStreamError(null);
      return;
    }
    setStreamError(null);
    return adapter.stream.subscribe(selectedRunId, {
      onEvent(event) {
        queryClient.setQueryData<DetailData>(
          ["observability", "run", selectedRunId],
          (current) => current ? { ...current, events: mergeEvents(current.events, [event]) } : current,
        );
        if (TERMINAL_RUN_STATUSES.has(event.type.replace("run.", ""))) {
          void queryClient.invalidateQueries({ queryKey: ["observability", "runs"] });
          void queryClient.invalidateQueries({ queryKey: ["observability", "run", selectedRunId] });
        }
      },
      onState: setStreamState,
      onError(error) {
        setStreamError(`Stream interrompido: ${error.message}. A reconexão permanece ativa.`);
      },
    });
  }, [adapter, queryClient, selectedRunId]);

  const runs = runsQuery.data ?? [];
  const filteredRuns = useMemo(() => filterRuns(runs, search), [runs, search]);
  const summary = useMemo(() => summarizeRuns(runs), [runs]);
  const status = normalizeStatusFilter(search.status);
  const period = normalizePeriodFilter(search.period);
  const filtersActive = Boolean(search.q || search.status || search.period);
  const connectionLabel = runsQuery.isError
    ? (runsQuery.error instanceof TypeError ? "Backend desconectado" : "Falha no endpoint")
    : runsQuery.isPending
      ? "Conectando"
      : runsQuery.isFetching || streamState === "reconnecting"
      ? "Reconectando"
      : "Conectado";
  const selectedMissing = Boolean(selectedRunId && runsQuery.isSuccess && !runs.some((run) => run.id === selectedRunId));

  function updateSearch(patch: Partial<ObservabilitySearchState>) {
    onSearchChange(cleanSearchState({ ...search, ...patch }));
  }

  function clearFilters() {
    onSearchChange(cleanSearchState({ run: search.run }));
  }

  return (
    <section className="obs-root" aria-label="Observability">
      <form className="obs-command-bar" onSubmit={(event) => event.preventDefault()}>
        <label className="obs-search-control">
          <Search aria-hidden="true" size={15} />
          <span className="obs-sr-only">Buscar Runs</span>
          <input
            aria-label="Buscar Runs"
            onChange={(event) => updateSearch({ q: event.target.value || undefined })}
            placeholder="Run ID, Study, variant ou runner"
            type="search"
            value={search.q ?? ""}
          />
        </label>
        <label>
          <span className="obs-sr-only">Status</span>
          <select
            aria-label="Status"
            onChange={(event) => updateSearch({ status: event.target.value === "all" ? undefined : event.target.value })}
            value={status}
          >
            <option value="all">Todos os status</option>
            <option value="active">Ativas</option>
            <option value="completed">Completed</option>
            <option value="attention">Atenção</option>
          </select>
        </label>
        <label>
          <span className="obs-sr-only">Período</span>
          <select
            aria-label="Período"
            onChange={(event) => updateSearch({ period: event.target.value === "all" ? undefined : event.target.value })}
            value={period}
          >
            <option value="all">Todo o período</option>
            <option value="24h">Últimas 24 h</option>
            <option value="7d">Últimos 7 dias</option>
            <option value="30d">Últimos 30 dias</option>
          </select>
        </label>
        <div className="obs-more-filters" ref={moreFiltersRef}>
          <button aria-controls="obs-more-filters-popover" aria-expanded={moreFiltersOpen} className="obs-clear-button" onClick={() => setMoreFiltersOpen((value) => !value)} ref={moreFiltersButtonRef} type="button">Mais filtros</button>
          {moreFiltersOpen ? (
            <div className="obs-filter-popover" id="obs-more-filters-popover" role="dialog" aria-label="Mais filtros">
              <label>
                Status exato
                <select aria-label="Status exato" onChange={(event) => updateSearch({ status: event.target.value === "all" ? undefined : event.target.value })} value={status}>
                  <option value="all">Qualquer status</option>
                  <option value="active">Ativas (grupo)</option>
                  <option value="attention">Atenção (grupo)</option>
                  <option value="queued">Queued</option>
                  <option value="preparing">Preparing</option>
                  <option value="running">Running</option>
                  <option value="evaluating">Evaluating</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                  <option value="budget_exhausted">Budget exhausted</option>
                </select>
              </label>
              <p>Provider e trust não são atribuídos por Run pelo endpoint de lista. Runner pode ser pesquisado em q.</p>
            </div>
          ) : null}
        </div>
        {filtersActive ? <button className="obs-clear-button" onClick={clearFilters} type="button">Limpar filtros</button> : null}
        <span className={`obs-command-connection ${runsQuery.isError ? "is-error" : connectionLabel === "Reconectando" ? "is-reconnecting" : ""}`} role="status">
          {connectionLabel === "Reconectando" ? <RefreshCw className="obs-spin" size={12} /> : <Radio size={12} />}
          {connectionLabel}
        </span>
      </form>

      <nav className="obs-status-strip" aria-label="Agrupar Runs por estado">
        <span className="obs-strip-label">Runs</span>
        {([
          ["all", "Todas", summary.all],
          ["active", "Ativas", summary.active],
          ["completed", "Concluídas", summary.completed],
          ["attention", "Atenção", summary.attention],
        ] as const).map(([value, label, count]) => (
          <button
            aria-current={status === value ? "page" : undefined}
            key={value}
            onClick={() => updateSearch({ status: value === "all" ? undefined : value })}
            type="button"
          >
            <span>{label}</span>
            <strong className="mono">{count}</strong>
          </button>
        ))}
      </nav>

      <div className={`obs-workspace${selectedRunId ? " has-selection" : ""}`} data-layout={selectedRunId ? "master-detail" : "list"}>
        <div className="obs-list-pane">
          {runsQuery.isPending ? <ListLoadingState /> : null}
          {runsQuery.isError ? (
            <div className="obs-error-state" role="alert">
              <AlertTriangle size={20} />
              <div>
                <strong>{runsQuery.error instanceof TypeError ? "Backend desconectado" : "Falha no endpoint de Runs"}</strong>
                <span>{runsQuery.error instanceof TypeError ? "Não foi possível alcançar o backend local." : "O backend respondeu, mas a lista de Runs falhou."}</span>
              </div>
              <button className="obs-action-button" onClick={() => void runsQuery.refetch()} type="button">Tentar novamente</button>
            </div>
          ) : null}
          {runsQuery.isSuccess && !runs.length ? (
            <PageState icon={<FileWarning size={20} />} title="Nenhuma Run registrada" role="status">
              A lista live está vazia. Nenhuma fixture foi criada pela interface.
            </PageState>
          ) : null}
          {runsQuery.isSuccess && runs.length && !filteredRuns.length ? (
            <PageState icon={<Search size={20} />} title="Nenhuma Run encontrada" role="status">
              Ajuste q, status ou período. Os filtros atuais não retornaram records.
            </PageState>
          ) : null}
          {filteredRuns.length ? (
            <RunList
              onSelect={(runId) => updateSearch({ run: runId })}
              runs={filteredRuns}
              selectedRunId={selectedRunId}
            />
          ) : null}
        </div>
        {selectedRunId ? <div className="obs-split-divider" aria-hidden="true" /> : null}
        <aside className="obs-detail-pane" aria-label="Detalhe da Run selecionada">
          {selectedRunId && detailQuery.isPending ? (
            <PageState icon={<LoaderCircle className="obs-spin" size={20} />} title="Carregando detalhe" role="status">
              Buscando records, eventos, evaluations e execution.
            </PageState>
          ) : null}
          {selectedRunId && (detailQuery.isError || selectedMissing) ? (
            <PageState icon={<AlertTriangle size={20} />} title="Run indisponível" role="alert">
              O parâmetro run não corresponde a um detalhe carregável.
              <button className="obs-text-button" onClick={() => updateSearch({ run: undefined })} type="button">
                Voltar às Runs
              </button>
            </PageState>
          ) : null}
          {detailQuery.data ? (
            <RunDetailPanel
              adapter={adapter}
              data={detailQuery.data}
              onBack={() => updateSearch({ run: undefined })}
              streamError={streamError}
              streamState={streamState}
            />
          ) : null}
        </aside>
      </div>
    </section>
  );
}

export function ObservabilityPage() {
  const search = useSearch({ from: "/observability" }) as ObservabilitySearchState;
  const navigate = useNavigate({ from: "/observability" });
  return (
    <ObservabilityWorkspace
      search={search}
      onSearchChange={(next) => {
        void navigate({ search: next, replace: true });
      }}
    />
  );
}
