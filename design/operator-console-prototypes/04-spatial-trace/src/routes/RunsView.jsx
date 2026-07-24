import {
  Archive,
  ArrowClockwise,
  Check,
  Clock,
  Database,
  FileLock,
  Fingerprint,
  Play,
  Pulse,
  Warning,
} from "@phosphor-icons/react";
import { motion, useReducedMotion } from "motion/react";
import { comparisonStub, runPhaseLabels, runPhaseOrder } from "../data/stubData.js";
import { useRunMachine } from "../hooks/useRunMachine.js";

const previewStates = [
  { phase: "preparing", label: "Carregando" },
  { phase: "failed", label: "Falhou" },
  { phase: "completed", label: "Concluído" },
];

function EventTrace({ events }) {
  if (!events.length) {
    return (
      <div className="run-empty">
        <Pulse size={28} weight="duotone" aria-hidden="true" />
        <p>Inicie a Run admitida ou selecione um estado de demonstração.</p>
      </div>
    );
  }

  return (
    <ol className="event-trace" aria-label="Eventos da Run stub">
      {events.map((event, index) => (
        <motion.li
          key={event.type}
          className={`event-trace__event event-trace__event--${event.kind}`}
          initial={{ opacity: 0, x: -6 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.18, delay: index * 0.025 }}
        >
          <span className="event-trace__node" aria-hidden="true">
            {index === events.length - 1 ? <Check size={13} weight="bold" /> : null}
          </span>
          <div>
            <code>{event.type}</code>
            <p>{event.label}</p>
          </div>
          <span>stub</span>
        </motion.li>
      ))}
    </ol>
  );
}

function RunChildren({ sequence }) {
  return (
    <div className="run-children" aria-label="Filhos operacionais da Run">
      <div>
        <Database size={19} aria-hidden="true" />
        <span>
          <small>job operacional</small>
          <code>stub-job-{String(sequence || 1).padStart(2, "0")}</code>
        </span>
      </div>
      <div>
        <Fingerprint size={19} aria-hidden="true" />
        <span>
          <small>attempt operacional</small>
          <code>stub-attempt-{String(sequence || 1).padStart(2, "0")}</code>
        </span>
      </div>
    </div>
  );
}

function RunsScopeGate({ project, linkProps }) {
  return (
    <div className="route route--runs route--scope-gated">
      <header className="page-intro">
        <div>
          <span className="section-label">Runs</span>
          <h1>Execução permanece presa ao Project.</h1>
          <p>
            O escopo ativo é {project.name}. A tela não projeta Runs, Admissions ou evidência de outro Project.
          </p>
        </div>
      </header>

      <section className="scope-gate" aria-labelledby="runs-scope-gate-title">
        <span className="scope-gate__icon" aria-hidden="true">
          <Archive size={26} weight="duotone" />
        </span>
        <div className="scope-gate__copy">
          <span className="section-label">Project scoped</span>
          <h2 id="runs-scope-gate-title">Nenhuma Run representada para este Project.</h2>
          <p>
            Sem RunSpec exato e AdmissionRecord admitido vinculados a este Project, nenhuma Run nova existe e nenhum bundle é mostrado.
          </p>
          <dl className="scope-gate__facts">
            <div>
              <dt>Project</dt>
              <dd className="mono">{project.id}</dd>
            </div>
            <div>
              <dt>Posição declarada</dt>
              <dd>{project.currentStage}</dd>
            </div>
            <div>
              <dt>Próxima ação</dt>
              <dd>{project.nextAction}</dd>
            </div>
          </dl>
          <a {...linkProps("/projects")} className="secondary-button">
            Revisar Project
          </a>
        </div>
        <span className="scope-gate__status">Execução bloqueada</span>
      </section>

      <section className="unsupported-controls" aria-label="Limite de execução">
        <FileLock size={20} aria-hidden="true" />
        <p>O bloqueio é explícito e não materializa records ausentes por conveniência da interface.</p>
      </section>
    </div>
  );
}

function BoundRunsView({ project, study }) {
  const { state, start, preview } = useRunMachine();
  const reduceMotion = useReducedMotion();
  const terminal = state.phase === "completed" || state.phase === "failed";

  return (
    <div className="route route--runs">
      <header className="page-intro">
        <div>
          <span className="section-label">Runs</span>
          <h1>Execução como traço, não como tabela.</h1>
          <p>Job e attempt permanecem filhos operacionais de uma Run admitida.</p>
        </div>
        <button
          type="button"
          className="primary-button"
          onClick={start}
          disabled={["queued", "preparing", "running", "evaluating"].includes(state.phase)}
        >
          <Play size={17} weight="fill" aria-hidden="true" />
          {state.phase === "idle" || terminal ? "Iniciar Stub Run" : runPhaseLabels[state.phase]}
        </button>
      </header>

      <section className="run-workbench" aria-labelledby="run-trace-title">
        <header className="run-workbench__header">
          <div>
            <span className={`run-state run-state--${state.phase}`}>
              {state.phase === "failed" ? <Warning size={16} weight="fill" /> : <Pulse size={16} weight="fill" />}
              {runPhaseLabels[state.phase]}
            </span>
            <h2 id="run-trace-title">{study.run.id}</h2>
            <p>
              Project {project.name}, variant {study.run.variant}, uma repetição, 23 jul 2026 em America/Asuncion.
            </p>
          </div>
          <div className="state-switches" aria-label="Estados de demonstração">
            {previewStates.map(({ phase, label }) => (
              <button
                key={phase}
                type="button"
                aria-pressed={state.phase === phase}
                className={state.phase === phase ? "is-active" : ""}
                onClick={() => preview(phase)}
              >
                {label}
              </button>
            ))}
          </div>
        </header>

        <div className="run-phase-line" aria-label={`Fase atual: ${runPhaseLabels[state.phase]}`}>
          {runPhaseOrder.map((phase, index) => {
            const currentIndex = runPhaseOrder.indexOf(state.phase);
            const active = phase === state.phase;
            const reached = state.phase === "failed" ? index <= 2 : currentIndex >= index;
            return (
              <span key={phase} className={`${active ? "is-active" : ""} ${reached ? "is-reached" : ""}`}>
                <i aria-hidden="true" />
                {runPhaseLabels[phase]}
              </span>
            );
          })}
        </div>

        <RunChildren sequence={state.sequence} />

        <div className="run-trace-layout">
          <section className="event-surface" aria-label="Traço de eventos">
            <motion.div
              key={state.phase}
              initial={reduceMotion ? false : { opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: reduceMotion ? 0 : 0.18 }}
            >
              <EventTrace events={state.events} />
            </motion.div>
          </section>

          <aside className="evidence-inspector" aria-labelledby="evidence-title">
            <header>
              <Archive size={22} weight="duotone" aria-hidden="true" />
              <div>
                <small>Evidence inspector</small>
                <h2 id="evidence-title">Bundle v2 stub</h2>
              </div>
            </header>
            <dl>
              <div>
                <dt>artifact_content</dt>
                <dd>references_only</dd>
              </div>
              <div>
                <dt>portable</dt>
                <dd>false</dd>
              </div>
              <div>
                <dt>replayable</dt>
                <dd>false</dd>
              </div>
            </dl>
            <div className="digest-limit">
              <FileLock size={19} aria-hidden="true" />
              <p>
                O documento exato do SubjectEnvelope não é persistido nem exportado. O digest alegado não o torna recomputável.
              </p>
            </div>
            <p className="manifest-limit">
              <strong>artifact-manifest.json</strong> enumera somente referências intencionais do bundle, não todos os arquivos observados.
            </p>
          </aside>
        </div>
      </section>

      <section className="comparison" aria-labelledby="comparison-title">
        <header>
          <div>
            <span className="section-label">Comparação stub</span>
            <h2 id="comparison-title">Duas variantes, disposições distintas.</h2>
          </div>
          <Clock size={21} aria-hidden="true" />
        </header>
        <div className="comparison__field">
          {comparisonStub.map((item) => (
            <article key={item.variant} className={`comparison-side comparison-side--${item.geometry}`}>
              <span className="comparison-side__geometry" aria-hidden="true">
                {item.geometry === "filled" ? <Check size={18} weight="bold" /> : null}
              </span>
              <div>
                <h3>{item.variant}</h3>
                <strong>{item.disposition}</strong>
                <p>{item.observation}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="unsupported-controls" aria-label="Controles não suportados">
        <ArrowClockwise size={20} aria-hidden="true" />
        <p>Pausa e retomada não são suportadas pelo runner ativo e não aparecem como controles.</p>
      </section>
    </div>
  );
}

export function RunsView({ project, study, linkProps }) {
  if (!study) return <RunsScopeGate project={project} linkProps={linkProps} />;
  return <BoundRunsView project={project} study={study} />;
}
