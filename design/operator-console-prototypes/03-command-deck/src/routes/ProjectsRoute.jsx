import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  BoundingBox,
  CheckCircle,
  Folder,
  FolderPlus,
  PlugsConnected,
  Plus,
  X,
} from "@phosphor-icons/react";
import { workflowStages } from "../data/mockData.js";
import { Definition, LocalDataFlag, PageIntro, SectionHeader, StatusLabel } from "../components/ui.jsx";

function CreateProjectDialog({ open, onClose, onCreate }) {
  const [name, setName] = useState("");
  const [summary, setSummary] = useState("");
  const [workspace, setWorkspace] = useState("workspace-local-evidrun");
  const [errors, setErrors] = useState({});
  const dialogRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    inputRef.current?.focus();
    const containFocus = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = Array.from(dialogRef.current?.querySelectorAll(
        'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
      ) ?? []);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;

      if (event.shiftKey && (active === first || !dialogRef.current?.contains(active))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", containFocus);
    return () => window.removeEventListener("keydown", containFocus);
  }, [onClose, open]);

  if (!open) return null;

  const submit = (event) => {
    event.preventDefault();
    const nextErrors = {};
    if (name.trim().length < 3) nextErrors.name = "Use ao menos 3 caracteres.";
    if (summary.trim().length < 12) nextErrors.summary = "Descreva o limite lógico em ao menos 12 caracteres.";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;

    onCreate({
      id: `project-local-${name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "")}`,
      name: name.trim(),
      summary: summary.trim(),
      workspace,
      currentStage: "scope",
    });
    setName("");
    setSummary("");
    setErrors({});
    onClose();
  };

  return (
    <div className="dialog-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section aria-labelledby="create-project-title" aria-modal="true" className="dialog" ref={dialogRef} role="dialog">
        <header className="dialog__header">
          <div>
            <FolderPlus aria-hidden="true" size={21} weight="duotone" />
            <h2 id="create-project-title">Criar Project local</h2>
          </div>
          <button aria-label="Fechar diálogo" onClick={onClose} type="button"><X aria-hidden="true" size={18} /></button>
        </header>
        <form onSubmit={submit} noValidate>
          <div className="field">
            <label htmlFor="project-name">Nome do Project</label>
            <input
              aria-describedby={errors.name ? "project-name-error" : "project-name-help"}
              aria-invalid={Boolean(errors.name)}
              id="project-name"
              onChange={(event) => setName(event.target.value)}
              ref={inputRef}
              value={name}
            />
            <p className="field__help" id="project-name-help">Um limite lógico legível, não um diretório.</p>
            {errors.name ? <p className="field__error" id="project-name-error">{errors.name}</p> : null}
          </div>

          <div className="field">
            <label htmlFor="project-summary">Limite de escopo</label>
            <textarea
              aria-describedby={errors.summary ? "project-summary-error" : "project-summary-help"}
              aria-invalid={Boolean(errors.summary)}
              id="project-summary"
              onChange={(event) => setSummary(event.target.value)}
              rows={3}
              value={summary}
            />
            <p className="field__help" id="project-summary-help">Explique o que pertence a este Project.</p>
            {errors.summary ? <p className="field__error" id="project-summary-error">{errors.summary}</p> : null}
          </div>

          <div className="field">
            <label htmlFor="project-workspace">Workspace de integração</label>
            <select id="project-workspace" onChange={(event) => setWorkspace(event.target.value)} value={workspace}>
              <option value="workspace-local-evidrun">workspace-local-evidrun</option>
              <option value="workspace-local-audit">workspace-local-audit</option>
            </select>
            <p className="field__help">Workspace conecta recursos locais. Não define o escopo lógico.</p>
          </div>

          <footer className="dialog__actions">
            <button className="secondary-button" onClick={onClose} type="button">Cancelar</button>
            <button className="primary-button" type="submit"><Plus aria-hidden="true" size={17} /> Criar Project</button>
          </footer>
        </form>
      </section>
    </div>
  );
}

export function ProjectsRoute({ projects, selectedProjectId, onProjectChange, onCreateProject }) {
  const selectedProject = projects.find((project) => project.id === selectedProjectId) ?? projects[0];
  const [selectedStageId, setSelectedStageId] = useState(selectedProject.currentStage);
  const [dialogOpen, setDialogOpen] = useState(false);
  const newProjectButtonRef = useRef(null);

  const closeDialog = useCallback(() => {
    setDialogOpen(false);
    window.setTimeout(() => newProjectButtonRef.current?.focus(), 0);
  }, []);

  useEffect(() => setSelectedStageId(selectedProject.currentStage), [selectedProject.currentStage, selectedProject.id]);
  const selectedStage = workflowStages.find((stage) => stage.id === selectedStageId) ?? workflowStages[0];
  const currentStageIndex = workflowStages.findIndex((stage) => stage.id === selectedProject.currentStage);
  const selectedStageIndex = workflowStages.findIndex((stage) => stage.id === selectedStage.id);
  const selectedStageStatus = selectedStageIndex < currentStageIndex
    ? "complete"
    : selectedStageIndex === currentStageIndex
      ? "current"
      : "pending";
  const evidenceInInspection = selectedStage.id === "evidence" && selectedProject.currentStage === "evidence";
  const selectedStageCopy = selectedStageStatus === "pending"
    ? {
        happened: "Nenhum record canônico desta etapa foi criado para este Project.",
        blocked: "A etapa anterior ainda precisa ser concluída.",
        next: "Concluir a etapa anterior e registrar esta transição.",
      }
    : selectedStage.id === "scope"
      ? {
          happened: `Project ${selectedProject.name} foi associado ao workspace local.`,
          blocked: selectedStage.blocked,
          next: selectedStage.next,
        }
      : evidenceInInspection
        ? {
            happened: "As referências intencionais do bundle estão sob inspeção local.",
            blocked: "Portabilidade e replay permanecem fora do escopo demonstrado.",
            next: "Concluir a leitura sem promover o bundle a um artefato portátil.",
          }
        : selectedStage;

  return (
    <div className="route-page">
      <PageIntro
        action={
          <button className="primary-button" onClick={() => setDialogOpen(true)} ref={newProjectButtonRef} type="button">
            <FolderPlus aria-hidden="true" size={18} /> Novo Project
          </button>
        }
        description="Mantenha o limite lógico do Project separado do Workspace que fornece integrações locais."
        icon={Folder}
        kicker="Logical scope"
        title="Projects"
      />

      <section className="project-context">
        <div className="project-context__scope">
          <div className="project-context__icon" aria-hidden="true"><BoundingBox size={24} weight="duotone" /></div>
          <div>
            <span>Project selecionado</span>
            <h2>{selectedProject.name}</h2>
            <p>{selectedProject.summary}</p>
          </div>
          <select
            aria-label="Selecionar Project"
            onChange={(event) => onProjectChange(event.target.value)}
            value={selectedProject.id}
          >
            {projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
          </select>
        </div>
        <div className="project-context__connector" aria-hidden="true"><ArrowRight size={18} /></div>
        <div className="project-context__workspace">
          <PlugsConnected aria-hidden="true" size={21} weight="duotone" />
          <div>
            <span>Workspace local</span>
            <strong className="mono">{selectedProject.workspace}</strong>
            <small>Integração, não autoridade de Project</small>
          </div>
        </div>
      </section>

      <section className="workflow-section">
        <SectionHeader
          action={<LocalDataFlag compact />}
          description="Selecione uma etapa para ver o registro atual, o bloqueio e a próxima ação."
          title="Workflow do Project"
        />

        <div className="workflow-layout">
          <div className="workflow-map" aria-label="Etapas do workflow">
            {workflowStages.map((stage, index) => {
              const effectiveStatus = index < currentStageIndex ? "complete" : index === currentStageIndex ? "current" : "pending";
              const effectiveShort = effectiveStatus === "current"
                ? "Posição atual"
                : effectiveStatus === "complete"
                  ? "Registrado"
                  : stage.id === "queue"
                    ? "Ainda não criada"
                    : stage.id === "evidence"
                      ? "Após terminal"
                      : "Pendente";
              return (
                <button
                  aria-pressed={selectedStage.id === stage.id}
                  className="workflow-node"
                  data-selected={selectedStage.id === stage.id}
                  data-status={effectiveStatus}
                  key={stage.id}
                  onClick={() => setSelectedStageId(stage.id)}
                  type="button"
                >
                  <span className="workflow-node__index" aria-hidden="true">
                    {effectiveStatus === "complete" ? <CheckCircle size={16} weight="fill" /> : index + 1}
                  </span>
                  <span>
                    <strong>{stage.label}</strong>
                    <small>{effectiveShort}</small>
                  </span>
                  {stage.id === "admission" ? (
                    <span className="workflow-branch" aria-label="Admission pode admitir ou rejeitar">
                      <span>Admit</span><span>Reject</span>
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>

          <aside className="stage-inspector" aria-live="polite">
            <header>
              <div>
                <span>Inspector</span>
                <h3>{selectedStage.label}</h3>
              </div>
              <StatusLabel status={selectedStageStatus}>{selectedStageStatus === "current" ? "Posição atual" : selectedStageStatus === "complete" ? "Registrado" : "Pendente"}</StatusLabel>
            </header>
            <dl>
              <Definition label="O que aconteceu" value={selectedStageCopy.happened} />
              <Definition label="O que bloqueia" value={selectedStageCopy.blocked} />
              <Definition label="O que vem depois" value={selectedStageCopy.next} />
            </dl>
          </aside>
        </div>
      </section>

      <CreateProjectDialog
        onClose={closeDialog}
        onCreate={onCreateProject}
        open={dialogOpen}
      />
    </div>
  );
}
