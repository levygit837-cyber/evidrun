import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check, ExternalLink, LockKeyhole, Pencil, RotateCcw } from "lucide-react";
import { useMemo, useRef, useState, type FormEvent } from "react";
import { creationAdapter } from "../../data/adapters";
import type { CreationAdapter } from "../../data/contracts";
import type { BootstrapDemoResult } from "../../types";
import {
  Button,
  InlineNotice,
  Input,
  Spinner,
  StatusIndicator,
  Textarea,
} from "../../ui/primitives";
import "./CreatePage.css";

type Step = 1 | 2 | 3 | 4;
type AdmissionState = "admitted" | "rejected" | "failed" | "unavailable" | "stale";
type DownstreamState = "empty" | "fresh" | "stale";
type EvaluationDisclosure = "none" | "pre_run";

interface StudyDraft {
  name: string;
  objective: string;
  hypothesis: string;
  evaluationDisclosure: EvaluationDisclosure;
}

interface CompiledStudy extends StudyDraft {
  revision: number;
}

interface CreatePageProps {
  adapter?: CreationAdapter;
}

const initialStudy: StudyDraft = {
  name: "Recuperação fundamentada por tool",
  objective: "Comparar a recuperação de contexto entre baseline e candidate.",
  hypothesis: "A variante candidate preserva evidência suficiente para responder com fundamento.",
  evaluationDisclosure: "none",
};

const admissionCopy: Record<AdmissionState, { label: string; tone: "success" | "danger" | "warning" | "neutral" }> = {
  admitted: { label: "admitted", tone: "success" },
  rejected: { label: "rejected", tone: "danger" },
  failed: { label: "failed", tone: "danger" },
  unavailable: { label: "unavailable", tone: "neutral" },
  stale: { label: "stale", tone: "warning" },
};

const steps: Array<{ id: Step; label: string }> = [
  { id: 1, label: "Study" },
  { id: 2, label: "RunSpecs" },
  { id: 3, label: "Admission" },
  { id: 4, label: "Runs" },
];

function resultLink(runId: string): string {
  return `#/observability?run=${encodeURIComponent(runId)}`;
}

function classifyFailure(error: unknown): AdmissionState {
  const message = error instanceof Error ? error.message.toLowerCase() : "";
  if (message.includes("rejected") || message.includes("rejeitad")) return "rejected";
  if (message.includes("unavailable") || message.includes("indispon")) return "unavailable";
  if (message.includes("stale")) return "stale";
  return "failed";
}

function AdmissionBadge({ state }: { state: AdmissionState }) {
  const copy = admissionCopy[state];
  return <StatusIndicator tone={copy.tone} label={copy.label} />;
}

export function CreatePage({ adapter = creationAdapter }: CreatePageProps) {
  const queryClient = useQueryClient();
  const [activeStep, setActiveStep] = useState<Step>(1);
  const [study, setStudy] = useState<StudyDraft>(initialStudy);
  const [compiledStudy, setCompiledStudy] = useState<CompiledStudy | null>(null);
  const [downstreamState, setDownstreamState] = useState<DownstreamState>("empty");
  const [result, setResult] = useState<BootstrapDemoResult | null>(null);
  const submissionInFlight = useRef(false);

  const bootstrap = useMutation({
    mutationFn: () => adapter.bootstrapCanonicalDemo(),
    onSuccess: async (nextResult) => {
      setResult(nextResult);
      setDownstreamState("fresh");
      setActiveStep(4);
      await queryClient.invalidateQueries();
    },
    onSettled: () => {
      submissionInFlight.current = false;
    },
  });

  const admissionState = useMemo<AdmissionState>(() => {
    if (downstreamState === "stale") return "stale";
    if (bootstrap.error) return classifyFailure(bootstrap.error);
    if (result) return "admitted";
    if (compiledStudy?.evaluationDisclosure === "pre_run") return "rejected";
    return "unavailable";
  }, [bootstrap.error, compiledStudy?.evaluationDisclosure, downstreamState, result]);

  const markDownstreamStale = () => {
    if (compiledStudy) setDownstreamState("stale");
    setResult(null);
    bootstrap.reset();
  };

  const updateStudy = <Key extends keyof StudyDraft>(key: Key, value: StudyDraft[Key]) => {
    setStudy((current) => ({ ...current, [key]: value }));
    markDownstreamStale();
  };

  const editStudy = () => {
    markDownstreamStale();
    setActiveStep(1);
  };

  const compileRunSpecs = (event: FormEvent) => {
    event.preventDefault();
    setCompiledStudy({ ...study, revision: (compiledStudy?.revision ?? 0) + 1 });
    setDownstreamState("fresh");
    setResult(null);
    bootstrap.reset();
    setActiveStep(2);
  };

  const runBootstrap = () => {
    if (submissionInFlight.current || bootstrap.isPending) return;
    submissionInFlight.current = true;
    bootstrap.mutate();
  };

  const primaryAction = (() => {
    if (activeStep === 1) {
      return (
        <Button variant="primary" type="submit" form="create-study-form">
          Compilar RunSpecs
          <ArrowRight aria-hidden="true" size={15} />
        </Button>
      );
    }
    if (activeStep === 2) {
      return (
        <Button variant="primary" onClick={() => setActiveStep(3)}>
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
          {bootstrap.isPending ? <Spinner label="Executando fixture no backend" /> : <RotateCcw aria-hidden="true" size={14} />}
          {bootstrap.isPending ? "Executando fixture no backend" : bootstrap.error ? "Tentar fixture novamente" : "Executar fixture canônica"}
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
          <span className="create-eyebrow">Novo experimento</span>
          <h1 id="create-title">Study até Runs, sem esconder as fronteiras</h1>
          <p>Configure localmente e execute a fixture canônica no backend quando a revisão estiver pronta.</p>
        </div>
        <span className="create-local-label">Draft local</span>
      </header>

      <ol className="create-stepper" aria-label="Etapas de criação">
        {steps.map((step) => {
          const isActive = activeStep === step.id;
          const isPast = step.id < activeStep;
          const isStale = downstreamState === "stale" && step.id > 1;
          return (
            <li key={step.id} data-active={isActive || undefined} data-stale={isStale || undefined}>
              <span className="create-step-number" aria-hidden="true">
                {isPast && !isStale ? <Check size={12} /> : step.id}
              </span>
              <span>{step.label}</span>
              {isStale ? <small>stale</small> : null}
            </li>
          );
        })}
      </ol>

      <div className="create-scroll-region">
        <div className="create-stages">
          <article className="create-stage" data-expanded={activeStep === 1 || undefined}>
            <header className="create-stage-header">
              <div>
                <span className="create-stage-index">1</span>
                <div>
                  <h2>Study</h2>
                  {activeStep !== 1 ? <p>{study.name} · revisão local {compiledStudy?.revision ?? 1}</p> : <p>Definição editável mantida apenas nesta tela.</p>}
                </div>
              </div>
              {activeStep !== 1 ? (
                <Button variant="quiet" size="small" disabled={bootstrap.isPending} onClick={editStudy}>
                  <Pencil aria-hidden="true" size={13} />
                  Editar Study
                </Button>
              ) : null}
            </header>

            {activeStep === 1 ? (
              <form id="create-study-form" className="create-study-form" onSubmit={compileRunSpecs}>
                {downstreamState === "stale" ? (
                  <InlineNotice tone="warning" title="Downstream stale">
                    A revisão anterior de RunSpecs, Admission e Runs não representa mais este Study. Compile uma nova revisão.
                  </InlineNotice>
                ) : null}

                <label>
                  <span>Nome do Study</span>
                  <Input required value={study.name} onChange={(event) => updateStudy("name", event.target.value)} />
                </label>
                <label>
                  <span>Objetivo</span>
                  <Textarea required value={study.objective} onChange={(event) => updateStudy("objective", event.target.value)} />
                </label>
                <label>
                  <span>Hipótese</span>
                  <Textarea required value={study.hypothesis} onChange={(event) => updateStudy("hypothesis", event.target.value)} />
                </label>
                <label>
                  <span>Disclosure da avaliação ao Subject</span>
                  <select
                    className="create-select"
                    value={study.evaluationDisclosure}
                    onChange={(event) => updateStudy("evaluationDisclosure", event.target.value as EvaluationDisclosure)}
                  >
                    <option value="none">none · avaliação não entra no SubjectEnvelope</option>
                    <option value="pre_run">pre_run · compilável, runtime indisponível</option>
                  </select>
                </label>
                <InlineNotice title="Fronteira de disclosure">
                  O Subject recebe apenas objective e context. <code>pre_run</code> pode ser compilado, mas a admissão do runner atual deve rejeitá-lo.
                </InlineNotice>
              </form>
            ) : null}
          </article>

          <article className="create-stage" data-expanded={activeStep === 2 || undefined} data-stale={downstreamState === "stale" || undefined}>
            <header className="create-stage-header">
              <div>
                <span className="create-stage-index">2</span>
                <div>
                  <h2>RunSpecs</h2>
                  <p>{compiledStudy ? `2 snapshots imutáveis · revisão local ${compiledStudy.revision}` : "Aguardando Study"}</p>
                </div>
              </div>
              {compiledStudy ? <StatusIndicator tone={downstreamState === "stale" ? "warning" : "success"} label={downstreamState === "stale" ? "stale" : "imutáveis"} /> : null}
            </header>

            {activeStep === 2 && compiledStudy ? (
              <div className="create-stage-body">
                <InlineNotice title="Snapshots locais, ainda sem record canônico">
                  O backend atribui IDs e digests durante o bootstrap. Esta tela não inventa um RunSpec persistido.
                </InlineNotice>
                <div className="create-spec-grid">
                  <section>
                    <span className="create-spec-kicker">baseline</span>
                    <h3>Full context</h3>
                    <dl>
                      <div><dt>interaction</dt><dd>single_turn</dd></div>
                      <div><dt>max_wall_seconds</dt><dd>budget suportado</dd></div>
                      <div><dt>disclosure</dt><dd>{compiledStudy.evaluationDisclosure}</dd></div>
                    </dl>
                  </section>
                  <section>
                    <span className="create-spec-kicker">candidate</span>
                    <h3>Tool-guided context</h3>
                    <dl>
                      <div><dt>interaction</dt><dd>single_turn</dd></div>
                      <div><dt>capability</dt><dd>read_text</dd></div>
                      <div><dt>disclosure</dt><dd>{compiledStudy.evaluationDisclosure}</dd></div>
                    </dl>
                  </section>
                </div>
                <p className="create-immutable-note"><LockKeyhole aria-hidden="true" size={13} /> Alterações exigem editar o Study e compilar uma nova revisão.</p>
              </div>
            ) : null}
          </article>

          <article className="create-stage" data-expanded={activeStep === 3 || undefined} data-stale={downstreamState === "stale" || undefined}>
            <header className="create-stage-header">
              <div>
                <span className="create-stage-index">3</span>
                <div>
                  <h2>Admission</h2>
                  <p>Capability real e decisão factual permanecem distintas.</p>
                </div>
              </div>
              {compiledStudy ? <AdmissionBadge state={admissionState} /> : null}
            </header>

            {activeStep === 3 && compiledStudy ? (
              <div className="create-stage-body">
                {bootstrap.isPending ? (
                  <InlineNotice title="Executando fixture no backend">
                    Este é o único estado factual exposto enquanto a chamada está pendente.
                  </InlineNotice>
                ) : bootstrap.error ? (
                  <InlineNotice tone="danger" title={`Admission ${admissionState}`}>
                    {bootstrap.error instanceof Error ? bootstrap.error.message : "O backend não concluiu a fixture canônica."}
                  </InlineNotice>
                ) : admissionState === "rejected" ? (
                  <InlineNotice tone="danger" title="Admission rejected">
                    Disclosure <code>pre_run</code> é compilável, mas indisponível no runner atual, que recebe somente objective e context.
                  </InlineNotice>
                ) : (
                  <InlineNotice title="Admission unavailable até o bootstrap">
                    Nenhum AdmissionRecord foi afirmado. A fixture solicitará a admissão do RunSpec exato no backend.
                  </InlineNotice>
                )}

                <div className="create-admission-table" aria-label="Estados de integração">
                  <div><span>Autoria do Study</span><strong>Integração pendente</strong><small>Nenhum ator humano foi inferido.</small></div>
                  <div><span>Authority humana</span><strong>Integração pendente</strong><small>Exige HumanAttestationRecord verificável.</small></div>
                  <div><span>Acesso a Artifact</span><strong>Integração pendente</strong><small>ArtifactRef identifica conteúdo, mas não concede acesso.</small></div>
                </div>

                <details className="create-status-key">
                  <summary>Estados de Admission distinguidos pela interface</summary>
                  <div>
                    {(["admitted", "rejected", "failed", "unavailable", "stale"] as AdmissionState[]).map((state) => (
                      <AdmissionBadge state={state} key={state} />
                    ))}
                  </div>
                </details>
              </div>
            ) : null}
          </article>

          <article className="create-stage" data-expanded={activeStep === 4 || undefined} data-stale={downstreamState === "stale" || undefined}>
            <header className="create-stage-header">
              <div>
                <span className="create-stage-index">4</span>
                <div>
                  <h2>Runs</h2>
                  <p>{result ? "Baseline e candidate retornados pelo backend" : "Nenhuma Run criada nesta tela"}</p>
                </div>
              </div>
              {result ? <StatusIndicator tone="success" label="resultado real" /> : null}
            </header>

            {activeStep === 4 && result ? (
              <div className="create-stage-body">
                <InlineNotice tone="success" title="Fixture concluída no backend">
                  Comparison <code>{result.comparison_id}</code> · validade <code>{result.validity}</code>. Os fatos abaixo apontam para Runs reais.
                </InlineNotice>
                <div className="create-result-grid">
                  <a href={resultLink(result.baseline_run_id)}>
                    <span>baseline</span>
                    <code>{result.baseline_run_id}</code>
                    <small>Inspecionar na Observability <ExternalLink aria-hidden="true" size={12} /></small>
                  </a>
                  <a href={resultLink(result.candidate_run_id)}>
                    <span>candidate</span>
                    <code>{result.candidate_run_id}</code>
                    <small>Inspecionar na Observability <ExternalLink aria-hidden="true" size={12} /></small>
                  </a>
                </div>
                <div className="create-integration-ending">
                  <strong>Integração pendente</strong>
                  <span>Autoria humana, authority verificável e materialização de Artifact continuam ausentes deste fluxo.</span>
                </div>
              </div>
            ) : null}
          </article>
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
