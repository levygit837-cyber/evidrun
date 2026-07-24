import {
  ArrowRight,
  BoundingBox,
  Check,
  FolderOpen,
  Plus,
  X,
} from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import { SurfaceHeader } from "../components/primitives/SurfaceHeader.jsx";
import { workflowStages } from "../data/mockData.js";

function CreateProjectDialog({ open, onClose, onCreate }) {
  const [name, setName] = useState("");
  const [intent, setIntent] = useState("");
  const [error, setError] = useState("");
  const [errorField, setErrorField] = useState("");
  const dialogRef = useRef(null);
  const nameRef = useRef(null);
  const intentRef = useRef(null);

  useEffect(() => {
    if (open) {
      setError("");
      setErrorField("");
      window.setTimeout(() => nameRef.current?.focus(), 0);
    }
  }, [open]);

  if (!open) return null;

  function submit(event) {
    event.preventDefault();
    if (name.trim().length < 3) {
      setError("Informe um nome com pelo menos 3 caracteres.");
      setErrorField("name");
      nameRef.current?.focus();
      return;
    }
    if (intent.trim().length < 12) {
      setError("Descreva o limite do Project em pelo menos 12 caracteres.");
      setErrorField("intent");
      intentRef.current?.focus();
      return;
    }
    onCreate({ name: name.trim(), intent: intent.trim() });
    setName("");
    setIntent("");
    setError("");
    setErrorField("");
  }

  function handleDialogKeyDown(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      onClose();
      return;
    }
    if (event.key !== "Tab") return;

    const focusable = Array.from(
      dialogRef.current?.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ) ?? [],
    );
    const first = focusable[0];
    const last = focusable.at(-1);
    if (!first || !last) return;

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        ref={dialogRef}
        className="project-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-project-title"
        onMouseDown={(event) => event.stopPropagation()}
        onKeyDown={handleDialogKeyDown}
      >
        <header>
          <div>
            <p className="micro-label">Somente estado local</p>
            <h2 id="create-project-title">Criar Project</h2>
          </div>
          <button className="icon-button" type="button" aria-label="Fechar diálogo" onClick={onClose}>
            <X aria-hidden="true" size={20} />
          </button>
        </header>
        <form onSubmit={submit}>
          <div className="field-block">
            <label htmlFor="project-name">Nome do Project</label>
            <input
              id="project-name"
              ref={nameRef}
              value={name}
              onChange={(event) => {
                setName(event.target.value);
                if (errorField === "name") {
                  setError("");
                  setErrorField("");
                }
              }}
              aria-describedby={`project-name-help${error ? " create-project-error" : ""}`}
              aria-invalid={errorField === "name" ? "true" : undefined}
            />
            <span id="project-name-help" className="form-help">
              Um limite lógico de trabalho, não uma pasta.
            </span>
          </div>
          <div className="field-block">
            <label htmlFor="project-intent">Intent</label>
            <textarea
              id="project-intent"
              ref={intentRef}
              rows="3"
              value={intent}
              onChange={(event) => {
                setIntent(event.target.value);
                if (errorField === "intent") {
                  setError("");
                  setErrorField("");
                }
              }}
              aria-describedby={error ? "create-project-error" : undefined}
              aria-invalid={errorField === "intent" ? "true" : undefined}
            />
          </div>
          {error ? (
            <p className="form-error" id="create-project-error" role="alert">
              {error}
            </p>
          ) : null}
          <div className="dialog-actions">
            <button className="button button-secondary" type="button" onClick={onClose}>
              Cancelar
            </button>
            <button className="button button-primary" type="submit">
              Criar Project
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

export function ProjectsRoute({
  projects,
  currentProjectId,
  onSelectProject,
  onCreateProject,
}) {
  const [selectedStage, setSelectedStage] = useState("admission");
  const [dialogOpen, setDialogOpen] = useState(false);
  const newProjectTriggerRef = useRef(null);
  const selected = workflowStages.find((stage) => stage.id === selectedStage);

  function closeDialog() {
    setDialogOpen(false);
    window.queueMicrotask(() => newProjectTriggerRef.current?.focus());
  }

  return (
    <div className="route-stack">
      <div
        className="route-stack"
        inert={dialogOpen || undefined}
        aria-hidden={dialogOpen ? "true" : undefined}
      >
        <SurfaceHeader
          eyebrow="Projects"
          title="Escopo antes da execução"
          description="Cada Project delimita intenção, Study e posição no workflow sem se tornar uma pasta."
          action={
            <button
              ref={newProjectTriggerRef}
              className="button button-primary"
              onClick={() => setDialogOpen(true)}
            >
              <Plus aria-hidden="true" size={18} weight="bold" />
              Novo Project
            </button>
          }
        />

        <div className="projects-layout">
          <section className="project-lanes" aria-label="Projects locais">
            {projects.map((project) => (
              <article
                className={`project-lane${
                  project.id === currentProjectId ? " is-current" : ""
                }`}
                key={project.id}
              >
                <button
                  className="project-select"
                  type="button"
                  onClick={() => onSelectProject(project.id)}
                  aria-pressed={project.id === currentProjectId}
                >
                  <BoundingBox aria-hidden="true" size={23} />
                  <span>
                    <strong>{project.name}</strong>
                    <small>{project.intent}</small>
                  </span>
                  {project.id === currentProjectId ? (
                    <Check aria-hidden="true" size={18} weight="bold" />
                  ) : (
                    <ArrowRight aria-hidden="true" size={18} />
                  )}
                </button>
                <div className="project-stage-strip" aria-label={`Workflow de ${project.name}`}>
                  {workflowStages.map((stage) => {
                    const current = project.stage === stage.id;
                    return (
                      <button
                        type="button"
                        key={stage.id}
                        className={selectedStage === stage.id ? "is-selected" : undefined}
                        aria-current={current ? "step" : undefined}
                        onClick={() => setSelectedStage(stage.id)}
                      >
                        <span>{stage.label}</span>
                        {current ? <small>Atual</small> : null}
                      </button>
                    );
                  })}
                </div>
                <footer>
                  <FolderOpen aria-hidden="true" size={17} />
                  <span>Estudo: {project.study}</span>
                  <strong>Próxima ação: {project.nextAction}</strong>
                </footer>
              </article>
            ))}
          </section>

          <aside className="stage-inspector" aria-live="polite">
            <p className="micro-label">Inspector da etapa</p>
            <h2>{selected?.label}</h2>
            <p>{selected?.description}</p>
            <dl>
              <div>
                <dt>Project atual</dt>
                <dd>{projects.find((project) => project.id === currentProjectId)?.name}</dd>
              </div>
              <div>
                <dt>Workspace</dt>
                <dd>Integration pending</dd>
              </div>
            </dl>
          </aside>
        </div>
      </div>

      <CreateProjectDialog
        open={dialogOpen}
        onClose={closeDialog}
        onCreate={(project) => {
          onCreateProject(project);
          closeDialog();
        }}
      />
    </div>
  );
}
