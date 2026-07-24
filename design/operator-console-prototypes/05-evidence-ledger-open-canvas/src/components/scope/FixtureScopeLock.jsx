import { ArrowLeft, FolderOpen, LockKeyOpen } from "@phosphor-icons/react";
import { Button, Notice, StatusBadge } from "../primitives/Controls.jsx";

export function FixtureScopeLock({ entity, project, onBack, onOpenFixture }) {
  const isStudy = entity === "Study";
  return (
    <div className="route route--scope-lock">
      <header className="route-header">
        <div>
          <span className="route-kicker">{isStudy ? "Study & Admission" : "Runs & Evidence"}</span>
          <h1>Nenhuma {entity} vinculada</h1>
          <p>O Project selecionado não possui {isStudy ? "StudyRevision, RunSpec ou AdmissionRecord" : "Run, eventos ou Evidence Bundle"} registrados.</p>
        </div>
      </header>

      <section className="scope-lock" aria-labelledby="scope-lock-title">
        <div className="scope-lock__identity">
          <span className="scope-lock__icon"><FolderOpen size={26} aria-hidden="true" /></span>
          <div>
            <span>Project selecionado</span>
            <h2 id="scope-lock-title">{project.name}</h2>
            <p>{project.description}</p>
          </div>
          <StatusBadge tone="warning">sem {isStudy ? "Study" : "Runs"}</StatusBadge>
        </div>

        <Notice title="Fronteira de fixture preservada">
          CRL-CTX-002 permanece uma fixture separada de Context Reliability Lab. Nenhum record dessa fixture pertence a {project.name}.
        </Notice>

        <div className="scope-lock__actions">
          <Button icon={ArrowLeft} onClick={onBack}>Voltar para Projects</Button>
          <Button variant="primary" icon={LockKeyOpen} onClick={onOpenFixture}>Abrir fixture CRL-CTX-002</Button>
        </div>
      </section>
    </div>
  );
}
