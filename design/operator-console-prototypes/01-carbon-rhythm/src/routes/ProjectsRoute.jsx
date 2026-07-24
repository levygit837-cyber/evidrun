import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  ArrowRight,
  FolderSimple,
  LinkSimple,
  Plus,
  Stack,
  X,
} from "@phosphor-icons/react";
import { PROJECT_STAGES } from "../data/mockData.js";
import { useOperator } from "../context/OperatorContext.jsx";
import { Button, IconButton, RouteHeading, TechnicalId } from "../components/Primitives.jsx";
import { RunTrace } from "../components/RunTrace.jsx";

function CreateProjectDialog({ open, onClose }) {
  const { dispatch } = useOperator();
  const [name, setName] = useState("");
  const [intent, setIntent] = useState("");
  const [errors, setErrors] = useState({});
  const nameRef = useRef(null);
  const dialogRef = useRef(null);
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (!open) return undefined;
    const timer = window.setTimeout(() => nameRef.current?.focus(), 0);
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !dialogRef.current) return;

      const focusable = Array.from(
        dialogRef.current.querySelectorAll(
          'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
        ),
      );
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      } else if (!dialogRef.current.contains(document.activeElement)) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose, open]);

  const submit = (event) => {
    event.preventDefault();
    const nextErrors = {};
    if (name.trim().length < 3) nextErrors.name = "Use pelo menos 3 caracteres.";
    if (intent.trim().length < 12) nextErrors.intent = "Descreva a intenção em pelo menos 12 caracteres.";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;
    dispatch({ type: "PROJECT_CREATE", name, intent });
    setName("");
    setIntent("");
    setErrors({});
    onClose();
  };

  return (
    <AnimatePresence>
      {open ? (
        <motion.div
          className="dialog-backdrop"
          initial={reduceMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
        >
          <motion.section
            ref={dialogRef}
            className="dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-project-title"
            initial={reduceMotion ? false : { opacity: 0, y: 12, scale: 0.99 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.99 }}
            transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
          >
            <header>
              <div>
                <p>Novo escopo local</p>
                <h2 id="create-project-title">Criar Project</h2>
              </div>
              <IconButton label="Fechar diálogo" onClick={onClose}><X size={19} /></IconButton>
            </header>
            <form onSubmit={submit} noValidate>
              <label htmlFor="project-name">Nome do Project</label>
              <input
                ref={nameRef}
                id="project-name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                aria-invalid={Boolean(errors.name)}
                aria-describedby={errors.name ? "project-name-error" : undefined}
              />
              {errors.name ? <p id="project-name-error" className="field-error">{errors.name}</p> : null}

              <label htmlFor="project-intent">Intenção</label>
              <textarea
                id="project-intent"
                rows={3}
                value={intent}
                onChange={(event) => setIntent(event.target.value)}
                aria-invalid={Boolean(errors.intent)}
                aria-describedby={errors.intent ? "project-intent-error" : "project-intent-help"}
              />
              <p id="project-intent-help" className="field-help">O Project delimita um escopo lógico. Não cria Workspace.</p>
              {errors.intent ? <p id="project-intent-error" className="field-error">{errors.intent}</p> : null}

              <footer>
                <Button variant="ghost" onClick={onClose}>Cancelar</Button>
                <Button type="submit" variant="primary"><Plus size={18} /> Criar Project</Button>
              </footer>
            </form>
          </motion.section>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}

export function ProjectsRoute() {
  const { state, dispatch } = useOperator();
  const [dialogOpen, setDialogOpen] = useState(false);
  const createButtonRef = useRef(null);
  const currentProject = state.projects.find((project) => project.id === state.currentProjectId);
  const selectedStage = PROJECT_STAGES.find((stage) => stage.id === state.selectedProjectStage);

  const closeDialog = () => {
    setDialogOpen(false);
    requestAnimationFrame(() => createButtonRef.current?.focus());
  };

  return (
    <div className="route route--projects">
      <RouteHeading
        eyebrow="Project context"
        title="Projects"
        description="Escopos lógicos para organizar Study, Admission, Run e evidência sem confundir integração local."
      >
        <Button ref={createButtonRef} variant="primary" onClick={() => setDialogOpen(true)}>
          <Plus size={18} aria-hidden="true" /> Criar Project
        </Button>
      </RouteHeading>

      <div className="projects-layout">
        <section className="project-index" aria-labelledby="project-index-title">
          <div className="section-heading-inline">
            <div>
              <p>Escopos disponíveis</p>
              <h2 id="project-index-title">Projects locais</h2>
            </div>
            <span>{state.projects.length}</span>
          </div>
          <div className="project-index__list">
            {state.projects.map((project) => {
              const selected = project.id === state.currentProjectId;
              return (
                <button
                  key={project.id}
                  type="button"
                  className={selected ? "is-selected" : ""}
                  aria-pressed={selected}
                  onClick={() => dispatch({ type: "PROJECT_SELECT", projectId: project.id })}
                >
                  <FolderSimple size={20} aria-hidden="true" />
                  <span><strong>{project.name}</strong><small>{project.study}</small></span>
                  <ArrowRight size={17} aria-hidden="true" />
                </button>
              );
            })}
          </div>

          <section className="workspace-boundary" aria-labelledby="workspace-boundary-title">
            <LinkSimple size={21} aria-hidden="true" />
            <div>
              <h3 id="workspace-boundary-title">Workspace</h3>
              <p>Integração local separada do Project.</p>
              <span>Integration pending</span>
            </div>
          </section>
        </section>

        <section className="project-inspector" aria-labelledby="project-inspector-title">
          <header>
            <div className="project-inspector__mark" aria-hidden="true"><Stack size={22} /></div>
            <div>
              <p>Project selecionado</p>
              <h2 id="project-inspector-title">{currentProject?.name}</h2>
              <TechnicalId>{currentProject?.id}</TechnicalId>
            </div>
          </header>
          <p className="project-inspector__intent">{currentProject?.intent}</p>

          <RunTrace
            stages={PROJECT_STAGES}
            currentStage="admission"
            selectedStage={state.selectedProjectStage}
            onSelect={(stageId) => dispatch({ type: "PROJECT_STAGE_SELECT", stageId })}
            label="Ritmo do Project"
            compact
          />

          <motion.article
            key={selectedStage?.id}
            className="stage-inspector"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18 }}
          >
            <p>Etapa selecionada</p>
            <h3>{selectedStage?.label}</h3>
            <span>{selectedStage?.description}</span>
            <TechnicalId>{selectedStage?.record}</TechnicalId>
          </motion.article>
        </section>
      </div>

      <CreateProjectDialog open={dialogOpen} onClose={closeDialog} />
    </div>
  );
}
