import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  Check,
  ExternalLink,
  LockKeyhole,
  Pencil,
  Plus,
  RotateCcw,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
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
  scenarios: StudyItem[];
  variants: StudyItem[];
  evaluationModules: StudyItem[];
}

interface StudyItem {
  id: string;
  name: string;
}

type StudyCollection = "scenarios" | "variants" | "evaluationModules";

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
  scenarios: [{ id: "scenario-1", name: "tool-result pressure" }],
  variants: [
    { id: "variant-1", name: "Full context" },
    { id: "variant-2", name: "Tool-guided context" },
  ],
  evaluationModules: [{ id: "evaluation-1", name: "grounded retrieval" }],
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

interface StudyCollectionEditorProps {
  title: string;
  collection: StudyCollection;
  items: StudyItem[];
  addLabel: string;
  placeholder: string;
  defaultOpen?: boolean;
  onAdd(collection: StudyCollection, name: string): void;
  onChange(collection: StudyCollection, id: string, name: string): void;
  onRemove(collection: StudyCollection, id: string): void;
}

function StudyCollectionEditor({
  title,
  collection,
  items,
  addLabel,
  placeholder,
  defaultOpen = false,
  onAdd,
  onChange,
  onRemove,
}: StudyCollectionEditorProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <details
      className="create-collection"
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
    >
      <summary>
        <span>{title}</span>
        <small>{items.length}</small>
      </summary>
      <div className="create-collection-body">
        {items.length ? (
          items.map((item, index) => (
            <div className="create-collection-row" key={item.id}>
              <Input
                aria-label={`${title} ${index + 1}`}
                value={item.name}
                onChange={(event) => onChange(collection, item.id, event.target.value)}
              />
              <Button
                variant="quiet"
                size="small"
                aria-label={`Remover ${title} ${index + 1}`}
                onClick={() => onRemove(collection, item.id)}
              >
                <Trash2 aria-hidden="true" size={13} />
              </Button>
            </div>
          ))
        ) : (
          <p className="create-collection-empty">Nenhum item nesta seção local.</p>
        )}
        <Button variant="quiet" size="small" onClick={() => onAdd(collection, placeholder)}>
          <Plus aria-hidden="true" size={13} />
          {addLabel}
        </Button>
      </div>
    </details>
  );
}

export function CreatePage({ adapter = creationAdapter }: CreatePageProps) {
  const queryClient = useQueryClient();
  const [activeStep, setActiveStep] = useState<Step>(1);
  const [maxReachedStep, setMaxReachedStep] = useState<Step>(1);
  const [study, setStudy] = useState<StudyDraft>(initialStudy);
  const [compiledStudy, setCompiledStudy] = useState<CompiledStudy | null>(null);
  const [downstreamState, setDownstreamState] = useState<DownstreamState>("empty");
  const [result, setResult] = useState<BootstrapDemoResult | null>(null);
  const [showPendingSpinner, setShowPendingSpinner] = useState(false);
  const submissionInFlight = useRef(false);
  const nextItemId = useRef(2);

  const bootstrap = useMutation({
    mutationFn: () => adapter.bootstrapCanonicalDemo(),
    onSuccess: async (nextResult) => {
      setResult(nextResult);
      setDownstreamState("fresh");
      setActiveStep(4);
      setMaxReachedStep(4);
      await queryClient.invalidateQueries();
    },
    onSettled: () => {
      submissionInFlight.current = false;
    },
  });

  useEffect(() => {
    if (!bootstrap.isPending) {
      setShowPendingSpinner(false);
      return;
    }
    const timer = window.setTimeout(() => setShowPendingSpinner(true), 150);
    return () => window.clearTimeout(timer);
  }, [bootstrap.isPending]);

  const admissionState = useMemo<AdmissionState>(() => {
    if (downstreamState === "stale") return "stale";
    if (bootstrap.error) return classifyFailure(bootstrap.error);
    if (result) return "admitted";
    if (compiledStudy?.evaluationDisclosure === "pre_run") return "rejected";
    return "unavailable";
  }, [bootstrap.error, compiledStudy?.evaluationDisclosure, downstreamState, result]);

  const markDownstreamStale = () => {
    if (compiledStudy) {
      setDownstreamState("stale");
      setMaxReachedStep(1);
    }
    setResult(null);
    bootstrap.reset();
  };

  const updateStudy = <Key extends keyof StudyDraft>(key: Key, value: StudyDraft[Key]) => {
    setStudy((current) => ({ ...current, [key]: value }));
    markDownstreamStale();
  };

  const updateStudyItem = (collection: StudyCollection, id: string, name: string) => {
    setStudy((current) => ({
      ...current,
      [collection]: current[collection].map((item) => (item.id === id ? { ...item, name } : item)),
    }));
    markDownstreamStale();
  };

  const addStudyItem = (collection: StudyCollection, name: string) => {
    const id = `${collection}-${nextItemId.current++}`;
    setStudy((current) => ({ ...current, [collection]: [...current[collection], { id, name }] }));
    markDownstreamStale();
  };

  const removeStudyItem = (collection: StudyCollection, id: string) => {
    setStudy((current) => ({
      ...current,
      [collection]: current[collection].filter((item) => item.id !== id),
    }));
    markDownstreamStale();
  };

  const editStudy = () => {
    setActiveStep(1);
  };

  const compileRunSpecs = (event: FormEvent) => {
    event.preventDefault();
    setCompiledStudy({
      ...study,
      scenarios: study.scenarios.map((item) => ({ ...item })),
      variants: study.variants.map((item) => ({ ...item })),
      evaluationModules: study.evaluationModules.map((item) => ({ ...item })),
      revision: (compiledStudy?.revision ?? 0) + 1,
    });
    setDownstreamState("fresh");
    setResult(null);
    bootstrap.reset();
    setActiveStep(2);
    setMaxReachedStep(2);
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
          <article className="create-stage" data-expanded={activeStep === 1 || undefined}>
            <header className="create-stage-header">
              <div>
                <span className="create-stage-index">1</span>
                <div>
                  <h2>Study</h2>
                  {activeStep !== 1 ? <p>{study.name} · preview Demo local {compiledStudy?.revision ?? 1}</p> : <p>Demo / integration_pending · não alimenta o bootstrap.</p>}
                </div>
              </div>
              <span className="create-stage-mode">Demo · integration_pending</span>
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

                <StudyCollectionEditor
                  title="Scenarios"
                  collection="scenarios"
                  items={study.scenarios}
                  defaultOpen
                  addLabel="Adicionar Scenario"
                  placeholder="Novo Scenario"
                  onAdd={addStudyItem}
                  onChange={updateStudyItem}
                  onRemove={removeStudyItem}
                />
                <StudyCollectionEditor
                  title="Variants"
                  collection="variants"
                  items={study.variants}
                  addLabel="Adicionar Variant"
                  placeholder="Nova Variant"
                  onAdd={addStudyItem}
                  onChange={updateStudyItem}
                  onRemove={removeStudyItem}
                />
                <StudyCollectionEditor
                  title="Evaluation modules"
                  collection="evaluationModules"
                  items={study.evaluationModules}
                  addLabel="Adicionar Evaluation module"
                  placeholder="Novo Evaluation module"
                  onAdd={addStudyItem}
                  onChange={updateStudyItem}
                  onRemove={removeStudyItem}
                />
              </form>
            ) : null}
          </article>

          <article className="create-stage" data-expanded={activeStep === 2 || undefined} data-stale={downstreamState === "stale" || undefined}>
            <header className="create-stage-header">
              <div>
                <span className="create-stage-index">2</span>
                <div>
                  <h2>RunSpecs</h2>
                  <p>{compiledStudy ? `Preview Demo imutável · revisão local ${compiledStudy.revision}` : "Aguardando preview Demo local"}</p>
                </div>
              </div>
              <span className="create-stage-mode">Demo · integration_pending</span>
              {compiledStudy ? <StatusIndicator tone={downstreamState === "stale" ? "warning" : "success"} label={downstreamState === "stale" ? "stale" : "imutáveis"} /> : null}
            </header>

            {activeStep === 2 && compiledStudy ? (
              <div className="create-stage-body">
                <InlineNotice title="Preview Demo · integration_pending">
                  Estes RunSpecs são somente uma compilação local ilustrativa. Não são enviados nem usados pelo bootstrap CRL-CTX-002.
                </InlineNotice>
                <div className="create-spec-grid">
                  <section>
                    <span className="create-spec-kicker">baseline</span>
                    <h3>Full context</h3>
                    <dl>
                      <div><dt>interaction</dt><dd>single_turn</dd></div>
                      <div><dt>max_wall_seconds</dt><dd>budget suportado</dd></div>
                      <div><dt>disclosure</dt><dd>{compiledStudy.evaluationDisclosure}</dd></div>
                      <div><dt>scenarios</dt><dd>{compiledStudy.scenarios.length}</dd></div>
                    </dl>
                  </section>
                  <section>
                    <span className="create-spec-kicker">candidate</span>
                    <h3>Tool-guided context</h3>
                    <dl>
                      <div><dt>interaction</dt><dd>single_turn</dd></div>
                      <div><dt>capability</dt><dd>read_text</dd></div>
                      <div><dt>disclosure</dt><dd>{compiledStudy.evaluationDisclosure}</dd></div>
                      <div><dt>evaluations</dt><dd>{compiledStudy.evaluationModules.length}</dd></div>
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
                  <p>Demo local não alimenta a repository_fixture CRL-CTX-002.</p>
                </div>
              </div>
              <span className="create-stage-mode">Demo · integration_pending</span>
              {compiledStudy ? <AdmissionBadge state={admissionState} /> : null}
            </header>

            {activeStep === 3 && compiledStudy ? (
              <div className="create-stage-body">
                {bootstrap.isPending ? (
                  <InlineNotice title="Executando CRL-CTX-002 no backend">
                    Esta repository_fixture não humana é independente do draft local.
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
                  <InlineNotice tone="warning" title="O draft não será enviado">
                    A ação executa a repository_fixture não humana <code>CRL-CTX-002</code>. Study, Scenarios, Variants, Evaluation modules e RunSpecs desta tela não alimentam o bootstrap.
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
                  <p>{result ? "CRL-CTX-002 retornou baseline e candidate reais" : "Demo local não criou nenhuma Run"}</p>
                </div>
              </div>
              <span className="create-stage-mode">Demo · integration_pending</span>
              {result ? <StatusIndicator tone="success" label="resultado real · CRL-CTX-002" /> : null}
            </header>

            {activeStep === 4 && result ? (
              <div className="create-stage-body">
                <InlineNotice tone="success" title="CRL-CTX-002 concluída no backend">
                  A repository_fixture não humana retornou Comparison <code>{result.comparison_id}</code> · validade <code>{result.validity}</code>. O draft local não foi enviado.
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
