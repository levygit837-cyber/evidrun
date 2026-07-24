import { motion, useReducedMotion } from "motion/react";
import {
  Archive,
  Check,
  Circle,
  FileLock,
  Fingerprint,
  LinkBreak,
  Play,
  Pulse,
  TerminalWindow,
  Warning,
  X,
} from "@phosphor-icons/react";
import { RUN_PHASES, RUN_VARIANTS } from "../data/mockData.js";
import { useOperator } from "../context/OperatorContext.jsx";
import { Button, BoundaryNote, RouteHeading, TechnicalId } from "../components/Primitives.jsx";

function RunPhaseTrace({ phaseIndex, status }) {
  return (
    <ol className="run-phase-trace" aria-label="Fases da Run stub">
      {RUN_PHASES.map((phase, index) => {
        const failedHere = status === "failed" && index === phaseIndex;
        const stepStatus = failedHere
          ? "failed"
          : index < phaseIndex
            ? "completed"
            : index === phaseIndex
              ? "current"
              : "future";
        const Icon = failedHere ? X : stepStatus === "completed" ? Check : stepStatus === "current" ? Pulse : Circle;
        return (
          <li key={phase.id} className={`run-phase-trace__step run-phase-trace__step--${stepStatus}`}>
            <span aria-hidden="true"><Icon size={18} weight={stepStatus === "future" ? "regular" : "bold"} /></span>
            <div>
              <strong>{phase.label}</strong>
              <TechnicalId>{phase.event}</TechnicalId>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

function RunEventTrace({ events, phaseIndex }) {
  const visibleEvents = [...events];
  if (phaseIndex >= 2 && !visibleEvents.some((event) => event.type === "tool.call")) {
    visibleEvents.splice(Math.min(2, visibleEvents.length), 0, {
      id: "event:stub-run-ri-0723-a:tool-call-illustrative",
      type: "tool.call",
      label: "read_text, demonstração local",
      illustrative: true,
    });
  }

  return (
    <section className="run-event-trace" aria-labelledby="run-event-trace-title">
      <header className="section-heading-inline">
        <div>
          <p>Traço staged</p>
          <h2 id="run-event-trace-title">Eventos observáveis</h2>
        </div>
        <span>{visibleEvents.length} refs</span>
      </header>
      {visibleEvents.length ? (
        <ol>
          {visibleEvents.map((event, index) => (
            <li key={event.id}>
              <span className="run-event-trace__index">{String(index + 1).padStart(2, "0")}</span>
              <span className="run-event-trace__icon" aria-hidden="true">
                {event.illustrative ? <TerminalWindow size={19} /> : <Fingerprint size={19} />}
              </span>
              <div>
                <strong>{event.type}</strong>
                <span>{event.label}</span>
                <TechnicalId>{event.id}</TechnicalId>
              </div>
              {event.illustrative ? <small>Ilustrativo</small> : null}
            </li>
          ))}
        </ol>
      ) : (
        <p className="run-event-trace__empty">Inicie a Run stub para materializar o primeiro evento local.</p>
      )}
    </section>
  );
}

export function RunsRoute() {
  const { state, dispatch } = useOperator();
  const reduceMotion = useReducedMotion();
  const run = state.run;
  const sourceRevision = state.study?.revisions.find(
    (revision) => revision.id === run?.sourceRevisionId,
  );
  const admittedInventory = Boolean(
    sourceRevision?.runSpecs.length &&
      sourceRevision.runSpecs.every((runSpec) => runSpec.admission === "admitted"),
  );

  if (!state.study || !run || !admittedInventory) {
    const withoutStudy = !state.study;
    return (
      <div className="route route--runs">
        <RouteHeading
          eyebrow="Run execution stub"
          title="Runs"
          description="O inventário desta rota pertence somente ao Project selecionado e exige enqueue de RunSpecs admitidos."
        />

        <section className="scope-empty-state" aria-labelledby="runs-empty-title">
          <div className="scope-empty-state__icon" aria-hidden="true"><LinkBreak size={25} /></div>
          <div>
            <p>{state.currentProject?.name}</p>
            <h2 id="runs-empty-title">Nenhuma Run disponível</h2>
            <span>
              {withoutStudy
                ? "Este Project não possui Study vinculada; enqueue, start e presets permanecem indisponíveis."
                : "A revisão selecionada ainda não foi admitida e enfileirada; start e presets permanecem indisponíveis."}
            </span>
          </div>
        </section>

        <BoundaryNote tone="warning">
          Fail-closed: uma Run nova só aparece depois do AdmissionRecord admitted para a revisão exata e do enqueue explícito.
        </BoundaryNote>
      </div>
    );
  }

  const inProgress = run.auto;
  const statusIcon = run.status === "failed" ? Warning : run.status === "terminal" ? Check : Pulse;
  const StatusIcon = statusIcon;

  return (
    <div className="route route--runs">
      <RouteHeading
        eyebrow="Run execution stub"
        title="Runs"
        description="Acompanhe Run, job, attempt, eventos e referências sem prometer replay ou materialização de artifacts."
      >
        <Button variant="primary" disabled={inProgress} onClick={() => dispatch({ type: "RUN_START" })}>
          <Play size={18} weight="fill" aria-hidden="true" />
          {run.status === "idle" || run.status === "queued" ? "Iniciar Run stub" : "Reiniciar Run stub"}
        </Button>
      </RouteHeading>

      <BoundaryNote>
        Demonstração local: nenhuma Run canônica ocorreu e nenhuma capability externa foi chamada.
      </BoundaryNote>

      <section className={`run-overview run-overview--${run.status}`} aria-labelledby="run-overview-title">
        <header>
          <div className="run-overview__status" role="status" aria-live="polite">
            <StatusIcon size={21} weight="bold" aria-hidden="true" />
            <div>
              <p>Estado do stub</p>
              <h2 id="run-overview-title">{run.status === "idle" ? "Ociosa" : run.status}</h2>
            </div>
          </div>
          <div className="run-presets" aria-label="Presets de estado da Run">
            <button type="button" onClick={() => dispatch({ type: "RUN_PRESET", preset: "loading" })}>Loading</button>
            <button type="button" onClick={() => dispatch({ type: "RUN_PRESET", preset: "failed" })}>Failed</button>
            <button type="button" onClick={() => dispatch({ type: "RUN_PRESET", preset: "completed" })}>Completed</button>
          </div>
        </header>

        <dl className="run-identity">
          <div><dt>Run</dt><dd><TechnicalId>run:stub-ri-0723-a</TechnicalId></dd></div>
          <div><dt>Job</dt><dd><TechnicalId>job:stub-ri-0723-01</TechnicalId></dd></div>
          <div><dt>Attempt</dt><dd><TechnicalId>attempt:stub-ri-0723-01</TechnicalId></dd></div>
          <div><dt>Origem</dt><dd><TechnicalId>{run.sourceRevisionId ?? "study-revision-stub-04"}</TechnicalId></dd></div>
        </dl>

        <RunPhaseTrace phaseIndex={run.phaseIndex} status={run.status} />
        <p className="run-overview__live">{run.liveMessage}</p>
      </section>

      <div className="runs-detail-grid">
        <RunEventTrace events={run.events} phaseIndex={run.phaseIndex} />

        <section className="evidence-boundaries" aria-labelledby="evidence-boundaries-title">
          <header className="section-heading-inline">
            <div>
              <p>Limites de disclosure</p>
              <h2 id="evidence-boundaries-title">Envelope e Bundle</h2>
            </div>
            <FileLock size={22} aria-hidden="true" />
          </header>

          <article>
            <div className="evidence-boundaries__icon" aria-hidden="true"><Fingerprint size={21} /></div>
            <div>
              <h3>SubjectEnvelope digest</h3>
              <TechnicalId>sha256:stub-7b19c6d2</TechnicalId>
              <p>Registrado no evento ilustrativo, mas o documento exato não é persistido nem automaticamente exportável.</p>
            </div>
          </article>

          <article>
            <div className="evidence-boundaries__icon" aria-hidden="true"><Archive size={21} /></div>
            <div>
              <h3>Bundle de referências</h3>
              <TechnicalId>artifact:stub-bundle-ref-01</TechnicalId>
              <p>References-only, não portátil e não replayable. Sem blobs, grants, restore ou estado privado recuperável.</p>
            </div>
          </article>
        </section>
      </div>

      <section className="run-comparison" aria-labelledby="run-comparison-title">
        <header>
          <p>Comparison draft</p>
          <h2 id="run-comparison-title">Variantes em justaposição</h2>
          <span>Sem veredito automático</span>
        </header>
        <div className="run-comparison__columns">
          {RUN_VARIANTS.map((variant, index) => (
            <motion.article
              key={variant.id}
              initial={reduceMotion ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: reduceMotion ? 0 : index * 0.05 }}
            >
              <TechnicalId>{variant.title}</TechnicalId>
              <h3>{variant.disposition}</h3>
              <p>{variant.detail}</p>
            </motion.article>
          ))}
        </div>
      </section>
    </div>
  );
}
