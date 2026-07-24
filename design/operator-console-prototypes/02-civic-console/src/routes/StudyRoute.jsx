import {
  Check,
  FileMagnifyingGlass,
  Notebook,
  Play,
  Plus,
  Shield,
  X,
} from "@phosphor-icons/react";
import { StatusMark } from "../components/primitives/StatusMark.jsx";
import { SurfaceHeader } from "../components/primitives/SurfaceHeader.jsx";
import { studyContext } from "../data/mockData.js";

function AdmissionPreflight({ variant, decision, supported, onEnqueue }) {
  const admitted = decision === "admitted";
  const pending = decision === "pending";
  return (
    <article className={`preflight-row is-${decision}`}>
      <div className="preflight-variant">
        <Shield aria-hidden="true" size={21} />
        <div>
          <strong className="mono">{variant}</strong>
          <span>Um AdmissionRecord por RunSpec</span>
        </div>
      </div>
      <dl className="coverage-values">
        <div>
          <dt>Solicitado</dt>
          <dd className="mono">source_coverage=required</dd>
        </div>
        <div>
          <dt>Suportado</dt>
          <dd className="mono">{supported ? "required" : "optional"}</dd>
        </div>
      </dl>
      <div className="preflight-decision">
        <StatusMark
          tone={pending ? "pending" : admitted ? "success" : "danger"}
          label={pending ? "Pending" : admitted ? "Admitted" : "Rejected"}
        />
        <button
          className="button button-secondary"
          disabled={!admitted}
          aria-describedby={!admitted ? `preflight-help-${variant}` : undefined}
          onClick={onEnqueue}
        >
          <Play aria-hidden="true" size={16} weight="fill" />
          Enfileirar
        </button>
        {!admitted ? (
          <span className="form-help" id={`preflight-help-${variant}`}>
            {pending ? "Compile a revisão primeiro." : "Valores incompatíveis."}
          </span>
        ) : null}
      </div>
    </article>
  );
}

export function StudyRoute({
  revisions,
  activeRevision,
  onSelectRevision,
  onUpdateRevision,
  onCreateRevision,
  onCompile,
  onNavigate,
}) {
  const decision = activeRevision.compiled ? activeRevision.admission : "pending";
  const evidenceDecision = activeRevision.compiled ? "admitted" : "pending";

  return (
    <div className="route-stack">
      <SurfaceHeader
        eyebrow="Study"
        title={studyContext.name}
        description="Edite uma StudyRevision local, compile os RunSpecs e confira cada Admission antes do enqueue."
        action={
          <button className="button button-secondary" onClick={onCreateRevision}>
            <Plus aria-hidden="true" size={17} weight="bold" />
            Nova revisão local
          </button>
        }
      />

      <div className="study-layout">
        <section className="revision-editor" aria-labelledby="revision-editor-title">
          <header>
            <div>
              <p className="micro-label">Draft versionado</p>
              <h2 id="revision-editor-title">StudyRevision</h2>
            </div>
            <div className="revision-tabs" role="tablist" aria-label="Revisões">
              {revisions.map((revision) => (
                <button
                  type="button"
                  role="tab"
                  aria-selected={revision.id === activeRevision.id}
                  key={revision.id}
                  onClick={() => onSelectRevision(revision.id)}
                >
                  {revision.label}
                  {revision.isLocal ? <span>Local</span> : null}
                </button>
              ))}
            </div>
          </header>

          <label className="field-block">
            Objetivo
            <textarea
              rows="4"
              value={activeRevision.objective}
              onChange={(event) =>
                onUpdateRevision({ objective: event.target.value, compiled: false, admission: "pending" })
              }
            />
          </label>

          <label className="coverage-check">
            <input
              type="checkbox"
              checked={activeRevision.sourceCoverage}
              onChange={(event) =>
                onUpdateRevision({
                  sourceCoverage: event.target.checked,
                  compiled: false,
                  admission: "pending",
                })
              }
            />
            <FileMagnifyingGlass aria-hidden="true" size={22} />
            <span>
              <strong>Cobertura de fontes autorizadas</strong>
              <small>
                Requisito explícito para a variante <span className="mono">direct-answer</span>.
              </small>
            </span>
          </label>

          <div className="revision-actions">
            <button className="button button-primary" onClick={onCompile}>
              <Notebook aria-hidden="true" size={18} />
              Compilar e validar
            </button>
            <span className="form-help">
              O Lab Agent não cria autoridade humana. Esta ação gera somente um draft local.
            </span>
          </div>
        </section>

        <aside className="compile-preview" aria-labelledby="compile-preview-title">
          <p className="micro-label">Prévia de compilação</p>
          <h2 id="compile-preview-title">scenario × variants × repetitions</h2>
          <div className="scenario-map">
            <div className="scenario-node">
              <span>Cenário</span>
              <strong className="mono">{studyContext.scenario}</strong>
            </div>
            <div className="variant-lanes">
              {studyContext.variants.map((variant) => (
                <div key={variant}>
                  <span className="mono">{variant}</span>
                  <strong>1 repetição</strong>
                </div>
              ))}
            </div>
          </div>
          <div className="compile-summary">
            <div>
              <span>RunSpecs</span>
              <strong>2</strong>
            </div>
            <div>
              <span>Runs</span>
              <strong>0 antes do enqueue</strong>
            </div>
          </div>
        </aside>
      </div>

      <section className="preflight-section" aria-labelledby="preflight-title">
        <header>
          <div>
            <p className="micro-label">Fail closed</p>
            <h2 id="preflight-title">Admission preflight</h2>
          </div>
          <StatusMark
            tone={decision === "admitted" ? "success" : decision === "rejected" ? "danger" : "pending"}
            label={
              decision === "admitted"
                ? "Revisão compatível"
                : decision === "rejected"
                  ? "Correção necessária"
                  : "Aguardando compilação"
            }
          />
        </header>
        <div className="preflight-list">
          <AdmissionPreflight
            variant="direct-answer"
            decision={decision}
            supported={activeRevision.sourceCoverage}
            onEnqueue={() => onNavigate("/runs")}
          />
          <AdmissionPreflight
            variant="evidence-first"
            decision={evidenceDecision}
            supported
            onEnqueue={() => onNavigate("/runs")}
          />
        </div>
        {decision === "rejected" ? (
          <div className="admission-explanation">
            <X aria-hidden="true" size={20} weight="bold" />
            <p>
              Solicitado <span className="mono">required</span>, suportado{" "}
              <span className="mono">optional</span>. Crie uma revisão local e marque a cobertura
              antes de recompilar.
            </p>
          </div>
        ) : decision === "admitted" ? (
          <div className="admission-explanation is-success">
            <Check aria-hidden="true" size={20} weight="bold" />
            <p>Os dois RunSpecs possuem AdmissionRecord admitted neste stub local.</p>
          </div>
        ) : null}
      </section>
    </div>
  );
}
