import {
  Archive,
  Check,
  FileMagnifyingGlass,
  Fingerprint,
  Play,
  Pulse,
  Queue,
  WarningCircle,
} from "@phosphor-icons/react";
import { useEffect, useReducer } from "react";
import { StatusMark } from "../components/primitives/StatusMark.jsx";
import { SurfaceHeader } from "../components/primitives/SurfaceHeader.jsx";
import { runPhases, studyContext } from "../data/mockData.js";
import {
  initialRunState,
  runReducer,
  runSequenceLength,
} from "../state/runReducer.js";

const phaseIcons = {
  queued: Queue,
  preparing: Fingerprint,
  running: Pulse,
  evaluating: FileMagnifyingGlass,
  terminal: Check,
};

function runTime(cursor) {
  return `11:32:${String(10 + cursor * 3).padStart(2, "0")}`;
}

export function RunsRoute({ canStart, activeRevision }) {
  const [state, dispatch] = useReducer(runReducer, initialRunState);

  useEffect(() => {
    if (!canStart || state.status !== "running" || !state.autoAdvance) return undefined;
    const next = state.cursor + 1;
    if (next >= runSequenceLength) {
      const timer = window.setTimeout(() => dispatch({ type: "complete" }), 280);
      return () => window.clearTimeout(timer);
    }
    const timer = window.setTimeout(
      () => dispatch({ type: "advance", cursor: next, time: runTime(next) }),
      280,
    );
    return () => window.clearTimeout(timer);
  }, [canStart, state]);

  useEffect(() => {
    if (!canStart && state.status !== "idle") {
      dispatch({ type: "reset" });
    }
  }, [canStart, state.status]);

  const statusTone =
    state.status === "completed"
      ? "success"
      : state.status === "failed"
        ? "danger"
        : state.status === "running"
          ? "pending"
          : "neutral";

  return (
    <div className="route-stack">
      <SurfaceHeader
        eyebrow="Runs"
        title="Execução determinística"
        description="Job, attempt, lifecycle e evidência permanecem entidades separadas no stub."
        action={
          <button
            className="button button-primary"
            disabled={!canStart || state.status === "running"}
            aria-describedby={!canStart ? "start-run-help" : undefined}
            onClick={() => dispatch({ type: "start" })}
          >
            <Play aria-hidden="true" size={18} weight="fill" />
            Start Stub Run
          </button>
        }
      />
      {!canStart ? (
        <p id="start-run-help" className="route-alert">
          A revisão ativa precisa de um AdmissionRecord admitted para o RunSpec exato.
        </p>
      ) : null}

      <div className="run-presets" aria-label="Presets de Run">
        <span>Presets locais</span>
        <button
          type="button"
          disabled={!canStart}
          aria-describedby={!canStart ? "run-presets-help" : undefined}
          onClick={() => canStart && dispatch({ type: "preset-running" })}
        >
          Loading
        </button>
        <button
          type="button"
          disabled={!canStart}
          aria-describedby={!canStart ? "run-presets-help" : undefined}
          onClick={() => canStart && dispatch({ type: "preset-failed" })}
        >
          Failed
        </button>
        <button
          type="button"
          disabled={!canStart}
          aria-describedby={!canStart ? "run-presets-help" : undefined}
          onClick={() => canStart && dispatch({ type: "preset-completed" })}
        >
          Completed
        </button>
        <button
          type="button"
          disabled={!canStart}
          aria-describedby={!canStart ? "run-presets-help" : undefined}
          onClick={() => canStart && dispatch({ type: "reset" })}
        >
          Idle
        </button>
      </div>
      {!canStart ? (
        <p id="run-presets-help" className="preset-boundary">
          Presets não criam uma Run sem AdmissionRecord admitted.
        </p>
      ) : null}

      <div className="runs-layout">
        <section className="run-lifecycle" aria-labelledby="run-lifecycle-title">
          <header>
            <div>
              <p className="micro-label">Trace espacial</p>
              <h2 id="run-lifecycle-title">Lifecycle da Run</h2>
            </div>
            <StatusMark
              tone={statusTone}
              label={
                state.status === "idle"
                  ? "Idle"
                  : state.status === "running"
                    ? "Em execução"
                    : state.status === "completed"
                      ? "Completed"
                      : "Failed"
              }
            />
          </header>

          <div className="run-identities">
            <div>
              <span>Job</span>
              <strong className="mono">{state.jobId ?? "Ainda não criado"}</strong>
            </div>
            <div>
              <span>Attempt</span>
              <strong className="mono">{state.attemptId ?? "Ainda não criado"}</strong>
            </div>
          </div>

          <ol className="run-trace">
            {runPhases.map((phase, index) => {
              const event = state.events.find((candidate) => candidate.id === phase.id);
              const Icon = phaseIcons[phase.id];
              const active = state.status === "running" && state.cursor === index;
              return (
                <li
                  className={`${event ? "is-reached" : ""}${active ? " is-active" : ""}`}
                  key={phase.id}
                >
                  <span className="trace-marker">
                    <Icon aria-hidden="true" size={20} />
                  </span>
                  <div>
                    <strong>{phase.label}</strong>
                    <p>{event?.detail ?? phase.detail}</p>
                  </div>
                  <time>{event?.time ?? "Pendente"}</time>
                </li>
              );
            })}
          </ol>

          {state.events.some((event) => event.id === "running") ? (
            <div className="stub-tool-event">
              <FileMagnifyingGlass aria-hidden="true" size={20} />
              <div>
                <strong>Tool event ilustrativo</strong>
                <span>
                  <span className="mono">read_text</span> executado apenas no stub local.
                </span>
              </div>
            </div>
          ) : null}
        </section>

        <aside className="run-boundaries" aria-label="Limites de evidência">
          <section>
            <Fingerprint aria-hidden="true" size={25} />
            <div>
              <h2>SubjectEnvelope digest</h2>
              <p>
                O documento exato não é persistido nem exportado. O digest alegado não o torna
                recomputável.
              </p>
            </div>
          </section>
          <section>
            <Archive aria-hidden="true" size={25} />
            <div>
              <h2>Bundle v2</h2>
              <p>
                Referências intencionais apenas. Não portátil, não replayable e sem promessa de
                blob, grant ou restore.
              </p>
            </div>
          </section>
          {state.status === "failed" ? (
            <section className="is-danger">
              <WarningCircle aria-hidden="true" size={25} />
              <div>
                <h2>Falha terminal</h2>
                <p>O stub encerrou a Run sem convertê-la em completed.</p>
              </div>
            </section>
          ) : null}
        </aside>
      </div>

      <section className="comparison-section" aria-labelledby="comparison-title">
        <header>
          <p className="micro-label">Justaposição</p>
          <h2 id="comparison-title">Comparison</h2>
          <p>Exemplo visual local, sem score, ranking ou achievement inventado.</p>
        </header>
        <div className="comparison-pair">
          {studyContext.variants.map((variant) => (
            <article key={variant}>
              <strong className="mono">{variant}</strong>
              <span>1 repetição</span>
              <p>
                {state.status === "completed"
                  ? "Resposta disponível para leitura lado a lado no stub."
                  : "Aguardando uma Run terminal para esta revisão."}
              </p>
            </article>
          ))}
        </div>
        <p className="comparison-revision mono">StudyRevision {activeRevision.id}</p>
      </section>
    </div>
  );
}
