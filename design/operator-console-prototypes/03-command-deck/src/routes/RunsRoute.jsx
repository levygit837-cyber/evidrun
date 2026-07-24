import { useEffect, useRef, useState } from "react";
import {
  Archive,
  ArrowsLeftRight,
  Check,
  Clock,
  FileLock,
  Fingerprint,
  Pause,
  PlayCircle,
  Pulse,
  ShieldCheck,
  XCircle,
} from "@phosphor-icons/react";
import { comparisonRows, evidenceRefs, runEventPhases } from "../data/mockData.js";
import {
  Definition,
  LocalDataFlag,
  PageIntro,
  SectionHeader,
  SegmentedControl,
  StatusLabel,
} from "../components/ui.jsx";

const terminalPhaseIndex = runEventPhases.length - 1;
const phaseForState = { loading: 2, failed: terminalPhaseIndex, completed: terminalPhaseIndex };

function phaseView(runState, phaseIndex, index, phase) {
  if (runState === "ready") {
    return { reached: false, current: false, eventId: phase.id, record: phase.record };
  }

  if (runState === "failed") {
    if (index === terminalPhaseIndex) {
      return {
        reached: true,
        current: true,
        eventId: "event-run-failed-001",
        record: "RunRecord terminal failed",
      };
    }
    if (index === terminalPhaseIndex - 1) {
      return { reached: false, current: false, eventId: phase.id, record: phase.record };
    }
    return { reached: index < terminalPhaseIndex - 1, current: false, eventId: phase.id, record: phase.record };
  }

  return {
    reached: index <= phaseIndex,
    current: index === phaseIndex,
    eventId: phase.id,
    record: phase.record,
  };
}

export function RunsRoute() {
  const [runState, setRunState] = useState("ready");
  const [phaseIndex, setPhaseIndex] = useState(-1);
  const [comparisonOpen, setComparisonOpen] = useState(false);
  const timersRef = useRef([]);

  const clearTimers = () => {
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
    timersRef.current = [];
  };

  useEffect(() => clearTimers, []);

  const setDemonstrationState = (state) => {
    clearTimers();
    setRunState(state);
    setPhaseIndex(phaseForState[state]);
  };

  const startRun = () => {
    clearTimers();
    setRunState("loading");
    setPhaseIndex(0);
    for (let index = 1; index < terminalPhaseIndex; index += 1) {
      timersRef.current.push(window.setTimeout(() => setPhaseIndex(index), index * 420));
    }
    timersRef.current.push(window.setTimeout(() => {
      setPhaseIndex(terminalPhaseIndex);
      setRunState("completed");
    }, terminalPhaseIndex * 420));
  };

  const terminal = runState === "failed" || runState === "completed";
  const startLabel = runState === "loading" ? "Stub Run em andamento" : terminal ? "Run encerrada" : "Start Stub Run";
  const currentStatus = runState === "completed"
    ? "Terminal completed"
    : runState === "failed"
      ? "Terminal failed"
      : runState === "ready"
        ? "Pronta para iniciar"
        : runEventPhases[phaseIndex]?.label ?? "Preparing";

  return (
    <div className="route-page">
      <PageIntro
        action={
          <button className="primary-button" disabled={runState !== "ready"} onClick={startRun} type="button">
            <PlayCircle aria-hidden="true" size={18} weight="fill" /> {startLabel}
          </button>
        }
        description="Acompanhe lifecycle, job, attempt, eventos e referências de evidência sem confundir suas identidades."
        icon={Pulse}
        kicker="23 July 2026, America/Asuncion"
        title="Runs"
      />

      <section aria-busy={runState === "loading"} className="run-overview">
        <header className="run-overview__header">
          <div>
            <span>Run selecionada</span>
            <h2>Diagnóstico de regressões após deploy</h2>
            <code>run-release-integrity-summary-001</code>
          </div>
          <SegmentedControl
            compact
            label="Estado demonstrativo da Run"
            onChange={setDemonstrationState}
            options={[
              { value: "loading", label: "Loading" },
              { value: "failed", label: "Failed" },
              { value: "completed", label: "Completed" },
            ]}
            value={runState}
          />
        </header>

        <div className="run-identities">
          <Definition label="Run" value="run-release-integrity-summary-001" mono />
          <Definition label="Job" value="job-local-queue-041" mono />
          <Definition label="Attempt" value="attempt-001" mono />
          <Definition label="AdmissionRecord" value="admission-summary-001" mono />
        </div>

        <div className="run-actions">
          <StatusLabel status={runState === "completed" ? "complete" : runState === "failed" ? "blocked" : runState === "ready" ? "pending" : "current"}>
            {currentStatus}
          </StatusLabel>
          <button className="secondary-button" disabled title="Pause/resume não está disponível no runtime ativo" type="button">
            <Pause aria-hidden="true" size={17} /> Pausar (não suportado)
          </button>
        </div>
      </section>

      <section className="event-progression">
        <SectionHeader
          action={<LocalDataFlag compact />}
          description="Eventos factuais aparecem apenas quando a fase correspondente foi alcançada."
          title="Fases e records canônicos"
        />
        <ol aria-label="Progressão de eventos da Run" className="event-track">
          {runEventPhases.map((phase, index) => {
            const view = phaseView(runState, phaseIndex, index, phase);
            const terminalFailed = runState === "failed" && index === runEventPhases.length - 1;
            return (
              <li data-reached={view.reached} data-current={view.current} key={phase.id}>
                <span className="event-track__mark" aria-hidden="true">
                  {view.reached ? (terminalFailed ? <XCircle size={17} weight="fill" /> : <Check size={14} weight="bold" />) : <Clock size={15} />}
                </span>
                <div>
                  <strong>{phase.label}</strong>
                  <span>{view.reached ? view.record : "Evento ainda não registrado"}</span>
                  <code>{view.reached ? view.eventId : "reserved until phase"}</code>
                </div>
              </li>
            );
          })}
        </ol>
      </section>

      {runState === "loading" ? (
        <section className="run-loading" aria-live="polite">
          <div className="run-loading__sweep" aria-hidden="true"><span /><span /><span /><span /></div>
          <div><strong>Executando stub determinístico</strong><p>O estado terminal ainda não foi registrado.</p></div>
        </section>
      ) : null}

      {runState === "failed" ? (
        <section className="run-failure" aria-live="polite">
          <XCircle aria-hidden="true" size={23} weight="duotone" />
          <div><strong>Attempt encerrou antes da avaliação</strong><p>A Run terminal é failed. Nenhum resultado parcial foi promovido a fato.</p></div>
        </section>
      ) : null}

      {runState === "completed" ? (
        <div className="evidence-layout">
          <section className="evidence-panel">
            <SectionHeader
              action={<StatusLabel status="complete">Terminal</StatusLabel>}
              description="Referências do bundle demonstrativo, sem locator ou blob embutido."
              title="Evidence"
            />
            <div className="digest-record">
              <Fingerprint aria-hidden="true" size={22} weight="duotone" />
              <div>
                <span>SubjectEnvelope digest registrado</span>
                <code>sha256:73b8f19a4d2c...7ea1</code>
                <small>O documento exato não é persistido ou exportável neste protótipo.</small>
              </div>
            </div>
            <div className="evidence-refs">
              {evidenceRefs.map((ref) => (
                <div key={ref.id}>
                  <FileLock aria-hidden="true" size={17} />
                  <span><strong>{ref.kind}</strong><code>{ref.id}</code></span>
                  <code>{ref.digest}</code>
                </div>
              ))}
            </div>
          </section>

          <aside className="bundle-panel">
            <Archive aria-hidden="true" size={24} weight="duotone" />
            <div>
              <span>Bundle v2, Stub local</span>
              <h2>Referências intencionais</h2>
            </div>
            <ul>
              <li><Check aria-hidden="true" size={14} /> Lifecycle e records terminais</li>
              <li><Check aria-hidden="true" size={14} /> Artifact entries declaradas</li>
              <li><XCircle aria-hidden="true" size={14} /> Não portátil</li>
              <li><XCircle aria-hidden="true" size={14} /> Não replayable</li>
            </ul>
            <p>Checksums e manifests não concedem acesso, restore ou estado privado recuperável.</p>
          </aside>
        </div>
      ) : null}

      <section className="comparison-section">
        <button
          aria-expanded={comparisonOpen}
          className="comparison-section__toggle"
          onClick={() => setComparisonOpen((open) => !open)}
          type="button"
        >
          <span><ArrowsLeftRight aria-hidden="true" size={20} /> Comparar variantes</span>
          <span>{comparisonOpen ? "Recolher" : "Inspecionar"}</span>
        </button>
        {comparisonOpen ? (
          <div className="comparison-grid">
            <header><span>Campo</span><strong className="mono">summary-first</strong><strong className="mono">evidence-first</strong></header>
            {comparisonRows.map((row) => (
              <div key={row.label}><span>{row.label}</span><span>{row.left}</span><span>{row.right}</span></div>
            ))}
            <p><ShieldCheck aria-hidden="true" size={16} /> A comparação mostra records. Ela não adjudica qual variante é melhor.</p>
          </div>
        ) : null}
      </section>
    </div>
  );
}
