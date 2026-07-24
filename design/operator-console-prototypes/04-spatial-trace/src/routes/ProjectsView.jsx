import { BoundingBox, LinkBreak, Plus, Warning, X } from "@phosphor-icons/react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { TracePath } from "../components/TracePath.jsx";

function CreateProjectDialog({ onClose, onCreate }) {
  const [name, setName] = useState("");
  const [purpose, setPurpose] = useState("");
  const [error, setError] = useState("");
  const panelRef = useRef(null);

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = panelRef.current.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), [href]',
      );
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const submit = (event) => {
    event.preventDefault();
    if (!name.trim()) {
      setError("Informe um nome para o Project.");
      return;
    }
    if (purpose.trim().length < 12) {
      setError("Descreva o objetivo em pelo menos 12 caracteres.");
      return;
    }
    onCreate({ name: name.trim(), purpose: purpose.trim() });
  };

  return (
    <div className="dialog-layer" role="presentation">
      <motion.div
        ref={panelRef}
        className="dialog-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-project-title"
        initial={{ opacity: 0, scale: 0.98, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.98, y: 5 }}
        transition={{ duration: 0.2 }}
      >
        <header>
          <div>
            <span className="section-label">Draft local</span>
            <h2 id="create-project-title">Criar Project</h2>
          </div>
          <button type="button" className="icon-button" aria-label="Fechar diálogo" onClick={onClose}>
            <X size={18} aria-hidden="true" />
          </button>
        </header>
        <form onSubmit={submit} noValidate>
          <div className="field">
            <label htmlFor="project-name">Nome do Project</label>
            <input
              id="project-name"
              value={name}
              onChange={(event) => {
                setName(event.target.value);
                setError("");
              }}
              autoFocus
              aria-describedby="project-name-help"
            />
            <small id="project-name-help">Um escopo lógico, nunca uma pasta.</small>
          </div>
          <div className="field">
            <label htmlFor="project-purpose">Objetivo local</label>
            <textarea
              id="project-purpose"
              rows={3}
              value={purpose}
              onChange={(event) => {
                setPurpose(event.target.value);
                setError("");
              }}
            />
          </div>
          {error ? (
            <p className="form-error" role="alert">
              <Warning size={17} weight="fill" aria-hidden="true" />
              {error}
            </p>
          ) : null}
          <footer>
            <button type="button" className="secondary-button" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="primary-button">
              Criar draft
            </button>
          </footer>
        </form>
      </motion.div>
    </div>
  );
}

export function ProjectsView({ projects, selectedProject, onSelectProject, onCreateProject, linkProps }) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [traceStage, setTraceStage] = useState(selectedProject.currentStage);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    setTraceStage(selectedProject.currentStage);
  }, [selectedProject.currentStage, selectedProject.id]);

  const selectProject = (project) => {
    onSelectProject(project.id);
    setTraceStage(project.currentStage);
  };

  return (
    <div className="route route--projects">
      <header className="page-intro">
        <div>
          <span className="section-label">Projects</span>
          <h1>Escopos com limites visíveis.</h1>
          <p>Selecione um Project para reposicionar o traço sem recarregar a aplicação.</p>
        </div>
        <button type="button" className="primary-button" onClick={() => setDialogOpen(true)}>
          <Plus size={17} weight="bold" aria-hidden="true" />
          Criar Project
        </button>
      </header>

      <section className="project-map" aria-label="Mapa de Projects">
        <div className="project-map__regions">
          {projects.map((project, index) => {
            const selected = project.id === selectedProject.id;
            return (
              <motion.button
                layout
                type="button"
                key={project.id}
                className={`project-region project-region--${project.tone} ${selected ? "is-selected" : ""}`}
                aria-pressed={selected}
                onClick={() => selectProject(project)}
                initial={reduceMotion ? false : { opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, delay: reduceMotion ? 0 : index * 0.04 }}
              >
                <span className="project-region__body">
                  <span className="project-region__icon" aria-hidden="true">
                    <BoundingBox size={22} weight={selected ? "fill" : "regular"} />
                  </span>
                  <strong>{project.name}</strong>
                  <small>{project.description}</small>
                </span>
                <span className="project-region__stage">
                  <small>Posição atual</small>
                  <strong>{project.currentStage}</strong>
                </span>
              </motion.button>
            );
          })}
        </div>

        <div className="project-map__trace">
          <header>
            <div>
              <span>Traço selecionado</span>
              <h2>{selectedProject.name}</h2>
            </div>
            <p>{selectedProject.nextAction}</p>
          </header>
          <TracePath
            activeStage={traceStage}
            linkProps={linkProps}
            onSelect={setTraceStage}
          />
        </div>
      </section>

      <section className="workspace-boundary" aria-label="Integração de Workspace indisponível">
        <LinkBreak size={23} weight="duotone" aria-hidden="true" />
        <div>
          <h2>Vínculo com Workspace indisponível</h2>
          <p>
            Integração externa não existe neste protótipo. Project continua separado de Workspace e filesystem.
          </p>
        </div>
        <span>Integração futura</span>
      </section>

      <AnimatePresence>
        {dialogOpen ? (
          <CreateProjectDialog
            onClose={() => setDialogOpen(false)}
            onCreate={(draft) => {
              onCreateProject(draft);
              setDialogOpen(false);
            }}
          />
        ) : null}
      </AnimatePresence>
    </div>
  );
}
