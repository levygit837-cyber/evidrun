import { ExternalLink, LockKeyhole, Pencil } from "lucide-react";
import { Button, InlineNotice, Input, StatusIndicator, Textarea } from "../../ui/primitives";
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
  );
}
