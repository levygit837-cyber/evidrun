import { useMemo, useRef, useState } from "react";
import {
  ArrowDown,
  ArrowRight,
  ChartBar,
  ChatsCircle,
  CheckCircle,
  FileCode,
  FileText,
  FolderOpen,
  HardDrives,
  MagnifyingGlass,
  Plus,
  ShieldCheck,
} from "@phosphor-icons/react";
import { WORKFLOW_NODES } from "../data/mockData.js";
import { Button, Field, Notice, StatusBadge, TechnicalRef } from "../components/primitives/Controls.jsx";
import { Modal } from "../components/primitives/Modal.jsx";

const NODE_ICONS = {
  StudyRevision: FileText,
  RunSpec: FileCode,
  AdmissionRecord: ShieldCheck,
  Run: ArrowRight,
  EvaluationRecord: CheckCircle,
  Comparison: ChartBar,
};

function WorkflowNode({ node, selected, onSelect }) {
  const Icon = NODE_ICONS[node.type] ?? FileText;
  return (
    <button
      type="button"
      className={`workflow-node ${selected ? "is-selected" : ""}`}
      aria-pressed={selected}
      onClick={() => onSelect(node.id)}
    >
      <span className="workflow-node__icon"><Icon size={18} aria-hidden="true" /></span>
      <span className="workflow-node__copy"><small>{node.type}</small><strong>{node.label}</strong><code>{node.secondary}</code></span>
      <StatusBadge tone={node.status === "admitted" || node.status === "completed" || node.status === "accepted" ? "success" : "neutral"}>{node.status}</StatusBadge>
    </button>
  );
}

export function ProjectsRoute({ projects, project, onProjectChange, onAddProject, navigate, onOpenChat }) {
  const [selectedNode, setSelectedNode] = useState("revision");
  const [query, setQuery] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [errors, setErrors] = useState({});
  const nameRef = useRef(null);
  const descriptionRef = useRef(null);

  const currentProject = projects.find((item) => item.id === project) ?? projects[0];
  const node = WORKFLOW_NODES.find((item) => item.id === selectedNode) ?? WORKFLOW_NODES[0];
  const filteredProjects = useMemo(() => projects.filter((item) => item.name.toLowerCase().includes(query.toLowerCase())), [projects, query]);

  const submitProject = (event) => {
    event.preventDefault();
    const nextErrors = {};
    if (name.trim().length < 3) nextErrors.name = "Use pelo menos 3 caracteres.";
    if (description.trim().length < 12) nextErrors.description = "Descreva o escopo em pelo menos 12 caracteres.";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      const firstInvalid = nextErrors.name ? nameRef : descriptionRef;
      queueMicrotask(() => firstInvalid.current?.focus());
      return;
    }
    onAddProject({ name: name.trim(), description: description.trim() });
    setName("");
    setDescription("");
    setErrors({});
    setDialogOpen(false);
  };

  return (
    <div className="route route--projects">
      <header className="route-header route-header--actions">
        <div><span className="route-kicker">Projects</span><h1>Escopos e proveniência</h1><p>Leia a relação entre revisão, admissão, execução, avaliação e comparação sem confundir Project com Workspace.</p></div>
        <div className="route-header__actions">
          <Button icon={ChatsCircle} onClick={onOpenChat}>Abrir Chat</Button>
          <Button variant="primary" icon={Plus} onClick={() => setDialogOpen(true)}>Criar Project</Button>
        </div>
      </header>

      <div className="project-toolbar">
        <label className="search-field">
          <span className="sr-only">Buscar Projects</span>
          <MagnifyingGlass size={18} aria-hidden="true" />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar Projects" />
        </label>
        <label className="project-select">
          <span className="sr-only">Selecionar Project</span>
          <FolderOpen size={18} aria-hidden="true" />
          <select value={project} onChange={(event) => onProjectChange(event.target.value)}>
            {filteredProjects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </label>
      </div>

      <section className="project-summary">
        <div className="project-summary__icon"><FolderOpen size={26} aria-hidden="true" /></div>
        <div><h2>{currentProject.name}</h2><p>{currentProject.description}</p></div>
        <StatusBadge tone="info">{currentProject.status}</StatusBadge>
        <Button size="sm" onClick={() => navigate("/study")}>Abrir Study</Button>
      </section>

      {currentProject.id === "crl" ? (
        <div className="workflow-layout">
          <section className="workflow-canvas" aria-labelledby="workflow-title">
            <header><div><h2 id="workflow-title">Fluxo registrado</h2><p>Uma revisão se ramifica em dois RunSpecs e converge em uma Comparison.</p></div><StatusBadge tone="neutral">fixture capturada</StatusBadge></header>
            <div className="workflow-sequence">
              <div className="workflow-stage workflow-stage--revision">
                <span>Revisão</span>
                <WorkflowNode node={WORKFLOW_NODES[0]} selected={selectedNode === "revision"} onSelect={setSelectedNode} />
              </div>
              <ArrowDown className="workflow-flow-arrow" size={19} aria-hidden="true" />
              <div className="workflow-branches">
                <span className="workflow-branches__label">Duas variantes</span>
                {["head", "tail"].map((variant) => {
                  const ids = variant === "head" ? ["spec-head", "admission-head", "run-head", "eval-head"] : ["spec-tail", "admission-tail", "run-tail", "eval-tail"];
                  return (
                    <div className="workflow-branch" key={variant}>
                      <strong className="workflow-branch__label">{variant === "head" ? "head-truncation" : "tail-preservation"}</strong>
                      {ids.map((id, index) => {
                        const item = WORKFLOW_NODES.find((candidate) => candidate.id === id);
                        return (
                          <div className="workflow-branch__step" key={id}>
                            {index > 0 ? <ArrowDown className="workflow-arrow" size={16} aria-hidden="true" /> : null}
                            <WorkflowNode node={item} selected={selectedNode === id} onSelect={setSelectedNode} />
                          </div>
                        );
                      })}
                    </div>
                  );
                })}
              </div>
              <ArrowDown className="workflow-flow-arrow" size={19} aria-hidden="true" />
              <div className="workflow-stage workflow-stage--comparison">
                <span>Convergência</span>
                <WorkflowNode node={WORKFLOW_NODES.at(-1)} selected={selectedNode === "comparison"} onSelect={setSelectedNode} />
              </div>
            </div>
          </section>

          <aside className="workflow-inspector" aria-live="polite">
            <span className="inspector-label">Inspector</span>
            <div className="workflow-inspector__title">
              {(() => { const Icon = NODE_ICONS[node.type] ?? FileText; return <Icon size={23} aria-hidden="true" />; })()}
              <div><small>{node.type}</small><h2>{node.label}</h2></div>
            </div>
            <p>{node.detail}</p>
            <dl>
              <div><dt>Status</dt><dd>{node.status}</dd></div>
              <div><dt>Reference</dt><dd><TechnicalRef>{node.ref}</TechnicalRef></dd></div>
              <div><dt>Persistência</dt><dd>fixture capturada</dd></div>
            </dl>
            <Notice compact title="Leitura operacional">IDs técnicos ficam secundários ao objeto e ao seu estado.</Notice>
          </aside>
        </div>
      ) : (
        <Notice title="Project sem workflow registrado">Este Project é um stub navegável. Nenhuma Run ou Admission foi criada.</Notice>
      )}

      <section className="workspace-boundary">
        <div className="workspace-boundary__icon"><HardDrives size={25} aria-hidden="true" /></div>
        <div><h2>Workspace local separado</h2><p>Fronteira de dados local distinta do escopo lógico do Project.</p></div>
        <StatusBadge tone="warning">Integração pendente</StatusBadge>
        <Button disabled>Vincular pasta</Button>
      </section>

      <Modal
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        title="Criar Project local"
        description="Cria somente estado React neste protótipo. Nenhum record será persistido."
        footer={<><Button onClick={() => setDialogOpen(false)}>Cancelar</Button><Button variant="primary" form="create-project-form" type="submit">Criar Project</Button></>}
      >
        <form id="create-project-form" onSubmit={submitProject} noValidate>
          <Field label="Nome do Project" hint="Use um nome de escopo reconhecível." error={errors.name}>
            <input ref={nameRef} value={name} onChange={(event) => setName(event.target.value)} aria-invalid={Boolean(errors.name)} />
          </Field>
          <Field label="Descrição" hint="Explique o que será avaliado." error={errors.description}>
            <textarea ref={descriptionRef} rows={4} value={description} onChange={(event) => setDescription(event.target.value)} aria-invalid={Boolean(errors.description)} />
          </Field>
        </form>
      </Modal>
    </div>
  );
}
