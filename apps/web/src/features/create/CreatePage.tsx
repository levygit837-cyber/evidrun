import { ArrowRight, Check, ExternalLink, Pencil, RotateCcw } from "lucide-react";
import { creationAdapter } from "../../data/adapters";
import type { CreationAdapter } from "../../data/contracts";
import { Button, Spinner } from "../../ui/primitives";
import {
  AdmissionStage,
  RunSpecsStage,
  RunsStage,
  StudyStage,
} from "./CreateStages";
import { resultLink, steps } from "./createModel";
import { useStudyDraft } from "./useStudyDraft";
import "./CreatePage.css";

interface CreatePageProps {
  adapter?: CreationAdapter;
}

export function CreatePage({ adapter = creationAdapter }: CreatePageProps) {
  const draft = useStudyDraft(adapter);
  const {
    activeStep,
    admissionState,
    bootstrap,
    downstreamState,
    maxReachedStep,
    result,
    showPendingSpinner,
    editStudy,
    runBootstrap,
    setActiveStep,
    setMaxReachedStep,
  } = draft;

  const primaryAction = (() => {
    if (activeStep === 1) {
      return (
        <Button variant="primary" type="submit" form="create-study-form">
          Compilar preview Demo
          <ArrowRight aria-hidden="true" size={15} />
        </Button>
      );
    }
    if (activeStep === 2) {
      return (
        <Button
          variant="primary"
          onClick={() => {
            setActiveStep(3);
            setMaxReachedStep(3);
          }}
        >
          Revisar Admission
          <ArrowRight aria-hidden="true" size={15} />
        </Button>
      );
    }
    if (activeStep === 3 && admissionState === "rejected") {
      return (
        <Button variant="primary" onClick={editStudy}>
          Corrigir Study
          <Pencil aria-hidden="true" size={14} />
        </Button>
      );
    }
    if (activeStep === 3) {
      return (
        <Button variant="primary" disabled={bootstrap.isPending} onClick={runBootstrap}>
          {showPendingSpinner ? <Spinner label="Executando CRL-CTX-002 no backend" /> : null}
          {!bootstrap.isPending ? <RotateCcw aria-hidden="true" size={14} /> : null}
          {bootstrap.isPending
            ? "Executando CRL-CTX-002 no backend"
            : bootstrap.error
              ? "Tentar CRL-CTX-002 novamente"
              : "Executar CRL-CTX-002"}
        </Button>
      );
    }
    if (result) {
      return (
        <a className="ui-button ui-button-primary ui-button-medium create-primary-link" href={resultLink(result.baseline_run_id)}>
          Abrir baseline na Observability
          <ExternalLink aria-hidden="true" size={14} />
        </a>
      );
    }
    return null;
  })();

  return (
    <section className="create-flow" aria-labelledby="create-title">
      <header className="create-heading">
        <div>
          <span className="create-eyebrow">Create · Demo / integration_pending</span>
          <h1 id="create-title">Study local e fixture canônica</h1>
          <p>O draft local serve apenas como preview: ele não alimenta o bootstrap CRL-CTX-002.</p>
        </div>
        <span className="create-local-label">Draft local</span>
      </header>

      <ol className="create-stepper" aria-label="Etapas de criação">
        {steps.map((step) => {
          const isActive = activeStep === step.id;
          const isPast = step.id < maxReachedStep && step.id !== activeStep;
          const isLocked = step.id > maxReachedStep;
          const isStale = downstreamState === "stale" && step.id > 1;
          return (
            <li key={step.id} data-active={isActive || undefined} data-stale={isStale || undefined}>
              <button
                type="button"
                aria-current={isActive ? "step" : undefined}
                disabled={isLocked || (bootstrap.isPending && !isActive)}
                onClick={() => setActiveStep(step.id)}
              >
                <span className="create-step-number" aria-hidden="true">
                  {isPast && !isStale ? <Check size={12} /> : step.id}
                </span>
                <span>{step.label}</span>
                {isStale ? <small>stale</small> : isLocked ? <small>bloqueado</small> : null}
              </button>
            </li>
          );
        })}
      </ol>

      <div className="create-scroll-region">
        <div className="create-stages">
          <StudyStage draft={draft} />
          <RunSpecsStage draft={draft} />
          <AdmissionStage draft={draft} />
          <RunsStage draft={draft} />
        </div>
      </div>

      <footer className="create-action-bar">
        <div>
          <span>Etapa {activeStep} de 4</span>
          <strong>{steps[activeStep - 1].label}</strong>
        </div>
        {primaryAction}
      </footer>
    </section>
  );
}
