import { ExternalLink, LockKeyhole, Pencil } from "lucide-react";
import { Button, InlineNotice, Input, StatusIndicator, Textarea } from "../../ui/primitives";
import { productTerms, studyPipelineSteps } from "../../productLanguage";
import { StudyCollectionEditor } from "./StudyCollectionEditor";
import {
  type AdmissionState,
  type EvaluationDisclosure,
  admissionCopy,
  resultLink,
} from "./createModel";
import type { StudyDraftState } from "./useStudyDraft";

function AdmissionBadge({ state }: { state: AdmissionState }) {
  const copy = admissionCopy[state];
  return <StatusIndicator tone={copy.tone} label={copy.label} />;
}

export function StudyStage({ draft }: { draft: StudyDraftState }) {
  const {
    activeStep,
    bootstrap,
    compiledStudy,
    downstreamState,
    study,
    addStudyItem,
    compileRunSpecs,
    editStudy,
    removeStudyItem,
    updateStudy,
    updateStudyItem,
  } = draft;

  return (
    <article className="create-stage" data-expanded={activeStep === 1 || undefined}>
      <header className="create-stage-header">
        <div>
          <span className="create-stage-index">1</span>
          <div>
            <h2>{studyPipelineSteps[0].label}</h2>
            {activeStep !== 1 ? <p>{study.name} · versão local {compiledStudy?.revision ?? 1}</p> : <p>Defina propósito, tarefa, cenários, variações e avaliação.</p>}
          </div>
        </div>
        <span className="create-stage-mode">{productTerms.study.technicalName} · Demo</span>
        {activeStep !== 1 ? (
          <Button variant="quiet" size="small" disabled={bootstrap.isPending} onClick={editStudy}>
            <Pencil aria-hidden="true" size={13} />
            Edit Study Design
          </Button>
        ) : null}
      </header>

      {activeStep === 1 ? (
        <form id="create-study-form" className="create-study-form" onSubmit={compileRunSpecs}>
          {downstreamState === "stale" ? (
            <InlineNotice tone="warning" title="Downstream steps are outdated">
              Os Execution Plans, o Readiness Check e as Runs anteriores não representam mais este Study. Gere novos planos.
            </InlineNotice>
          ) : null}

          <label>
            <span>Study name</span>
            <Input autoComplete="off" name="study-name" required value={study.name} onChange={(event) => updateStudy("name", event.target.value)} />
          </label>
          <label>
            <span>Agent task</span>
            <Textarea autoComplete="off" name="agent-task" required value={study.objective} onChange={(event) => updateStudy("objective", event.target.value)} />
          </label>
          <label>
            <span>Study hypothesis</span>
            <Textarea autoComplete="off" name="study-hypothesis" required value={study.hypothesis} onChange={(event) => updateStudy("hypothesis", event.target.value)} />
          </label>
          <label>
            <span>Evaluation disclosure</span>
            <select
              className="create-select"
              name="evaluation-disclosure"
              value={study.evaluationDisclosure}
              onChange={(event) => updateStudy("evaluationDisclosure", event.target.value as EvaluationDisclosure)}
            >
              <option value="none">None · evaluation stays hidden from the Subject</option>
              <option value="pre_run">Pre-run · runtime unavailable</option>
            </select>
          </label>
          <InlineNotice title="Disclosure boundary">
            O agente avaliado recebe apenas sua tarefa e o contexto permitido. O modo <code>pre_run</code> pode ser planejado, mas a verificação atual deve bloqueá-lo.
          </InlineNotice>

          <StudyCollectionEditor
            title="Scenarios"
            collection="scenarios"
            items={study.scenarios}
            defaultOpen
            addLabel="Add Scenario"
            placeholder="New scenario"
            onAdd={addStudyItem}
            onChange={updateStudyItem}
            onRemove={removeStudyItem}
          />
          <StudyCollectionEditor
            title="Variants"
            collection="variants"
            items={study.variants}
            addLabel="Add Variant"
            placeholder="New variant"
            onAdd={addStudyItem}
            onChange={updateStudyItem}
            onRemove={removeStudyItem}
          />
          <StudyCollectionEditor
            title="Evaluation criteria"
            collection="evaluationModules"
            items={study.evaluationModules}
            addLabel="Add Evaluation Criterion"
            placeholder="New evaluation criterion"
            onAdd={addStudyItem}
            onChange={updateStudyItem}
            onRemove={removeStudyItem}
          />
        </form>
      ) : null}
    </article>
  );
}

export function RunSpecsStage({ draft }: { draft: StudyDraftState }) {
  const { activeStep, compiledStudy, downstreamState } = draft;

  return (
    <article className="create-stage" data-expanded={activeStep === 2 || undefined} data-stale={downstreamState === "stale" || undefined}>
      <header className="create-stage-header">
        <div>
          <span className="create-stage-index">2</span>
          <div>
            <h2>{studyPipelineSteps[1].label}</h2>
            <p>{compiledStudy ? `Planos imutáveis · versão local ${compiledStudy.revision}` : "Aguardando o desenho do estudo"}</p>
          </div>
        </div>
        <span className="create-stage-mode">{productTerms.runSpec.technicalName} · Demo</span>
        {compiledStudy ? <StatusIndicator tone={downstreamState === "stale" ? "warning" : "success"} label={downstreamState === "stale" ? "Outdated" : "Plans generated"} /> : null}
      </header>

      {activeStep === 2 && compiledStudy ? (
        <div className="create-stage-body">
          <InlineNotice title="Local Execution Plans">
            Estes planos ilustram a configuração exata de cada execução. Eles ainda não são enviados nem usados pelo bootstrap CRL-CTX-002.
          </InlineNotice>
          <div className="create-spec-grid">
            <section>
              <span className="create-spec-kicker">baseline</span>
              <h3>Full context</h3>
              <dl>
                <div><dt>interaction</dt><dd>single_turn</dd></div>
                <div><dt>time limit</dt><dd>supported budget</dd></div>
                <div><dt>evaluation disclosure</dt><dd>{compiledStudy.evaluationDisclosure}</dd></div>
                <div><dt>scenarios</dt><dd>{compiledStudy.scenarios.length}</dd></div>
              </dl>
            </section>
            <section>
              <span className="create-spec-kicker">candidate</span>
              <h3>Tool-guided context</h3>
              <dl>
                <div><dt>interaction</dt><dd>single_turn</dd></div>
                <div><dt>capability</dt><dd>read_text</dd></div>
                <div><dt>evaluation disclosure</dt><dd>{compiledStudy.evaluationDisclosure}</dd></div>
                <div><dt>evaluation criteria</dt><dd>{compiledStudy.evaluationModules.length}</dd></div>
              </dl>
            </section>
          </div>
          <p className="create-immutable-note"><LockKeyhole aria-hidden="true" size={13} /> Para alterar um plano, edite o estudo e gere uma nova versão.</p>
        </div>
      ) : null}
    </article>
  );
}

export function AdmissionStage({ draft }: { draft: StudyDraftState }) {
  const { activeStep, admissionState, bootstrap, compiledStudy, downstreamState } = draft;

  return (
    <article className="create-stage" data-expanded={activeStep === 3 || undefined} data-stale={downstreamState === "stale" || undefined}>
      <header className="create-stage-header">
        <div>
          <span className="create-stage-index">3</span>
          <div>
            <h2>{studyPipelineSteps[2].label}</h2>
            <p>Confirma se cada plano pode ser executado com os recursos disponíveis.</p>
          </div>
        </div>
        <span className="create-stage-mode">{productTerms.admission.technicalName} · Demo</span>
        {compiledStudy ? <AdmissionBadge state={admissionState} /> : null}
      </header>

      {activeStep === 3 && compiledStudy ? (
        <div className="create-stage-body">
          {bootstrap.isPending ? (
            <InlineNotice title="Executando CRL-CTX-002 no backend">
              Esta fixture não humana é independente do rascunho local.
            </InlineNotice>
          ) : bootstrap.error ? (
            <InlineNotice tone="danger" title={`Readiness Check: ${admissionCopy[admissionState].label}`}>
              {bootstrap.error instanceof Error ? bootstrap.error.message : "O backend não concluiu a fixture canônica."}
            </InlineNotice>
          ) : admissionState === "rejected" ? (
            <InlineNotice tone="danger" title="Run Blocked">
              Mostrar a avaliação antes da execução é planejável, mas o executor atual ainda não entrega essa informação ao agente avaliado.
            </InlineNotice>
          ) : (
            <InlineNotice tone="warning" title="O rascunho não será enviado">
              A ação executa a fixture não humana <code>CRL-CTX-002</code>. O estudo, seus cenários, variações, critérios e planos desta tela ainda não alimentam o bootstrap.
            </InlineNotice>
          )}

          <div className="create-admission-table" aria-label="Estados de integração">
            <div><span>Study authorship</span><strong>Integração pendente</strong><small>Nenhum ator humano foi inferido.</small></div>
            <div><span>Human authority</span><strong>Integração pendente</strong><small>Exige uma atestação humana verificável.</small></div>
            <div><span>Artifact access</span><strong>Integração pendente</strong><small>A referência identifica conteúdo, mas não concede acesso.</small></div>
          </div>

          <details className="create-status-key">
            <summary>Readiness Check States</summary>
            <div>
              {(["admitted", "rejected", "failed", "unavailable", "stale"] as AdmissionState[]).map((state) => (
                <span key={state}><AdmissionBadge state={state} /><code translate="no">{state}</code></span>
              ))}
            </div>
          </details>
        </div>
      ) : null}
    </article>
  );
}

export function RunsStage({ draft }: { draft: StudyDraftState }) {
  const { activeStep, downstreamState, result } = draft;

  return (
    <article className="create-stage" data-expanded={activeStep === 4 || undefined} data-stale={downstreamState === "stale" || undefined}>
      <header className="create-stage-header">
        <div>
          <span className="create-stage-index">4</span>
          <div>
            <h2>{studyPipelineSteps[3].label}</h2>
            <p>{result ? "CRL-CTX-002 retornou execuções de referência e candidata reais" : "A demonstração local não criou nenhuma execução"}</p>
          </div>
        </div>
        <span className="create-stage-mode">{productTerms.run.technicalName} · Demo</span>
        {result ? <StatusIndicator tone="success" label="Real runs · CRL-CTX-002" /> : null}
      </header>

      {activeStep === 4 && result ? (
        <div className="create-stage-body">
          <InlineNotice tone="success" title="CRL-CTX-002 concluída no backend">
            A fixture não humana retornou a comparação <code>{result.comparison_id}</code> · validade <code>{result.validity}</code>. O rascunho local não foi enviado.
          </InlineNotice>
          <div className="create-result-grid">
            <a href={resultLink(result.baseline_run_id)}>
              <span>baseline</span>
              <code>{result.baseline_run_id}</code>
              <small>Inspect in Runs <ExternalLink aria-hidden="true" size={12} /></small>
            </a>
            <a href={resultLink(result.candidate_run_id)}>
              <span>candidate</span>
              <code>{result.candidate_run_id}</code>
              <small>Inspect in Runs <ExternalLink aria-hidden="true" size={12} /></small>
            </a>
          </div>
          <div className="create-integration-ending">
            <strong>Integração pendente</strong>
            <span>Autoria humana, autoridade verificável e materialização do artefato continuam ausentes deste fluxo.</span>
          </div>
        </div>
      ) : null}
    </article>
  );
}
