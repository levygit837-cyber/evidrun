import { ArrowLeft, LockSimple, Plugs } from "@phosphor-icons/react";
import { SurfaceHeader } from "./SurfaceHeader.jsx";

export function ProjectScopeLock({ project, surface, onNavigate }) {
  const titleId = `project-scope-lock-${surface.toLowerCase()}`;

  return (
    <div className="route-stack">
      <SurfaceHeader
        eyebrow={surface}
        title={project.name}
        description={`Estudo: ${project.study}`}
        action={
          <div className="workspace-disclosure">
            <Plugs aria-hidden="true" size={19} />
            <div>
              <span>Workspace</span>
              <strong>Integration pending</strong>
            </div>
          </div>
        }
      />

      <section
        className="project-scope-lock"
        aria-labelledby={titleId}
        data-project-scope="locked"
      >
        <LockSimple aria-hidden="true" size={34} />
        <div>
          <p className="micro-label">Fail closed</p>
          <h2 id={titleId}>{surface} indisponível para este Project</h2>
          <p>
            Este protótipo não possui StudyRevision, RunSpec, AdmissionRecord ou Run
            vinculados a este Project. Nenhum record de outro Project será reutilizado.
          </p>
        </div>
        <dl>
          <div>
            <dt>Project atual</dt>
            <dd>{project.name}</dd>
          </div>
          <div>
            <dt>Estudo declarado</dt>
            <dd>{project.study}</dd>
          </div>
          <div>
            <dt>Próxima ação</dt>
            <dd>{project.nextAction}</dd>
          </div>
        </dl>
        <button
          className="button button-secondary"
          type="button"
          onClick={() => onNavigate("/projects")}
        >
          <ArrowLeft aria-hidden="true" size={17} />
          Voltar para Projects
        </button>
      </section>
    </div>
  );
}
