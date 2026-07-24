import {
  Archive,
  FileLock,
  FileText,
  Notebook,
  Play,
  Shield,
} from "@phosphor-icons/react";
import { StatusMark } from "../primitives/StatusMark.jsx";

function RegionHeading({ index, title, icon: Icon, state, current }) {
  return (
    <header className="workflow-region-heading">
      <span className="stage-index" aria-hidden="true">
        {index}
      </span>
      <Icon aria-hidden="true" size={20} />
      <h3>{title}</h3>
      <span className="sr-only">{current ? "Etapa atual" : state}</span>
    </header>
  );
}

function CompiledRunSpecPreview({ revision }) {
  return (
    <section className="runspec-preview" aria-labelledby="runspec-preview-title">
      <div>
        <span className="micro-label">Prévia compilada</span>
        <h4 id="runspec-preview-title">RunSpec</h4>
      </div>
      <dl>
        <div>
          <dt>Revisão</dt>
          <dd className="mono">{revision.id}</dd>
        </div>
        <div>
          <dt>Variantes</dt>
          <dd>2</dd>
        </div>
        <div>
          <dt>Repetições</dt>
          <dd>1 por variante</dd>
        </div>
      </dl>
    </section>
  );
}

export function WorkflowBoard({
  activeRevision,
  onCorrectRevision,
  onNavigate,
}) {
  const admitted = activeRevision.admission === "admitted";

  return (
    <section className="workflow-board" aria-labelledby="workflow-title">
      <div className="workflow-intro">
        <div>
          <p className="micro-label">Posição atual</p>
          <h2 id="workflow-title">Da intenção à evidência</h2>
        </div>
        <p>
          A Admission verifica o RunSpec exato antes de existir qualquer Run.
        </p>
      </div>

      <ol className="workflow-grid">
        <li className="workflow-region stage-intent">
          <RegionHeading index="1" title="Intent" icon={FileText} state="Definido" />
          <p>Comparar cobertura de fontes entre duas variantes controladas.</p>
          <StatusMark tone="neutral" label="Definido" compact />
        </li>

        <li className="workflow-region stage-revision">
          <RegionHeading index="2" title="StudyRevision" icon={Notebook} state="Compilada" />
          <p>Draft versionado e selecionado para o preflight.</p>
          <button className="text-action mono" onClick={() => onNavigate("/study")}>
            {activeRevision.id}
          </button>
        </li>

        <li
          className="workflow-region stage-admission is-current"
          aria-current="step"
        >
          <RegionHeading
            index="3"
            title="Admission"
            icon={Shield}
            state={admitted ? "Admitted" : "Rejected"}
            current
          />
          <div className={`admission-surface${admitted ? " is-admitted" : ""}`}>
            <div className="admission-status-line">
              <StatusMark
                tone={admitted ? "success" : "danger"}
                label={admitted ? "Admitted" : "Rejected"}
              />
              <span className="mono">
                {admitted ? "capabilities compatible" : "required source coverage missing"}
              </span>
            </div>
            <p>
              {admitted
                ? "A cobertura solicitada está representada e suportada neste stub."
                : "A cobertura de fontes exigida não está presente nesta revisão."}
            </p>
            <CompiledRunSpecPreview revision={activeRevision} />
            <div className="admission-actions">
              {!admitted ? (
                <button className="button button-primary" onClick={onCorrectRevision}>
                  Criar revisão corrigida
                </button>
              ) : (
                <button className="button button-primary" onClick={() => onNavigate("/runs")}>
                  Ir para Runs
                </button>
              )}
              <button
                className="button button-secondary"
                disabled={!admitted}
                aria-describedby={!admitted ? "enqueue-help" : undefined}
                onClick={() => onNavigate("/runs")}
              >
                <Play aria-hidden="true" size={17} weight="fill" />
                Enfileirar
              </button>
            </div>
            {!admitted ? (
              <span id="enqueue-help" className="form-help">
                Indisponível enquanto este AdmissionRecord estiver rejected.
              </span>
            ) : null}
          </div>
        </li>

        <li className="workflow-region stage-run">
          <RegionHeading index="4" title="Run" icon={Play} state="Não criada" />
          <div className="empty-region">
            <StatusMark tone="pending" label="Aguardando Admission" compact />
            <strong>Nenhuma Run criada</strong>
            <p>Job e attempt só aparecem após enqueue válido.</p>
          </div>
        </li>

        <li className="workflow-region stage-evidence">
          <RegionHeading index="5" title="Evidence" icon={Archive} state="Vazio" />
          <div className="empty-region">
            <FileLock aria-hidden="true" size={24} />
            <strong>Nenhuma evidência desta Run</strong>
            <p>Sem ArtifactRef ilustrativo ou promessa de acesso.</p>
          </div>
        </li>
      </ol>
    </section>
  );
}
