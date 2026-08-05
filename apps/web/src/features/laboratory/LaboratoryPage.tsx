import { CircleStop, LoaderCircle, Send, TriangleAlert } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type {
  LabMessage,
  LabScopeSelection,
  LabSession,
  LaboratoryAdapter,
  LaboratorySessionAdapter,
} from "../../data/contracts";
import { productionLaboratoryAdapter } from "../../data/adapters";
import { Button, IconButton, InlineNotice, Textarea, Tooltip } from "../../ui/primitives";
import { AuditActivity } from "./AuditActivity";
import { phaseLabels } from "./laboratoryModel";
import { useLaboratoryDemo } from "./useLaboratoryDemo";
import "./laboratory.css";

function isSessionAdapter(adapter: LaboratoryAdapter): adapter is LaboratorySessionAdapter {
  return "scopeOptions" in adapter && "selectScope" in adapter;
}

function formLabel(form: LabSession["form"]) {
  return { general: "Chat geral", project: "Project Room", focused: "Chat focado" }[form];
}

export function LaboratoryPage({ adapter }: { adapter?: LaboratoryAdapter }) {
  const laboratoryAdapter = useMemo(() => adapter ?? productionLaboratoryAdapter, [adapter]);
  const sessionAdapter = isSessionAdapter(laboratoryAdapter) ? laboratoryAdapter : null;
  const [options, setOptions] = useState<{ workspaces: Array<{ id: string; name: string }>; projects: Array<{ id: string; name: string }> }>({ workspaces: [], projects: [] });
  const [selection, setSelection] = useState<LabScopeSelection>({ workspaceId: "" });
  const [session, setSession] = useState<LabSession | null>(null);
  const [history, setHistory] = useState<LabMessage[]>([]);
  const [scopeError, setScopeError] = useState<string | null>(null);
  const [focusKind, setFocusKind] = useState("");
  const [focusId, setFocusId] = useState("");
  const [form, setForm] = useState<LabSession["form"]>("general");
  const hook = useLaboratoryDemo(laboratoryAdapter);

  useEffect(() => {
    if (!sessionAdapter) return;
    void sessionAdapter.scopeOptions().then((next) => {
      setOptions(next);
      if (next.workspaces.length === 1) setSelection((current) => ({ ...current, workspaceId: next.workspaces[0].id }));
    }).catch((error: unknown) => setScopeError(error instanceof Error ? error.message : "Não foi possível carregar os escopos."));
  }, [sessionAdapter]);

  async function activateScope(scope = selection) {
    if (!sessionAdapter || !scope.workspaceId) return;
    setScopeError(null);
    try {
      const next = await sessionAdapter.selectScope(scope);
      setSession(next);
      setHistory(await sessionAdapter.messages());
      hook.reset();
    } catch (error) {
      setScopeError(error instanceof Error ? error.message : "Não foi possível abrir a sessão.");
    }
  }

  function chooseForm(form: LabSession["form"]) {
    setForm(form);
    setSession(null);
    setHistory([]);
    setFocusKind("");
    setFocusId("");
    setSelection((current) => ({ workspaceId: current.workspaceId, ...(form !== "general" && current.projectId ? { projectId: current.projectId } : {}) }));
  }

  const selectedForm = form;
  const scopeReady = Boolean(session) && !hook.isRunning;

  return <section className="laboratory" data-state={hook.phase} aria-label="Laboratory">
    <div className="laboratory-state-announcer" role="status" aria-live="polite">{phaseLabels[hook.phase]}</div>
    <div className="laboratory-conversation-scroll"><div className="laboratory-conversation">
      <header className="laboratory-conversation-toolbar">
        <div><span className="laboratory-live-label">Corredor real</span><h1>Laboratory</h1></div>
        {session ? <span className="laboratory-session-form" data-form={session.form}>{formLabel(session.form)}</span> : null}
      </header>

      {sessionAdapter ? <section className="laboratory-scope" aria-label="Escopo da sessão">
        <h2>Abra uma sessão no escopo certo</h2>
        <p>Trocar de escopo cria ou retoma outra sessão. As mensagens da sessão aberta não são copiadas.</p>
        <div className="laboratory-scope-controls">
          <label>Workspace<select aria-label="Workspace" value={selection.workspaceId} onChange={(event) => { setSession(null); setHistory([]); setSelection({ workspaceId: event.target.value }); }}><option value="">Selecione</option>{options.workspaces.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.name}</option>)}</select></label>
          <label>Forma<select aria-label="Forma da sessão" value={selectedForm} onChange={(event) => chooseForm(event.target.value as LabSession["form"])}><option value="general">General</option><option value="project">Project</option><option value="focused">Focused</option></select></label>
          {selectedForm !== "general" ? <label>Project<select aria-label="Project" value={selection.projectId ?? ""} onChange={(event) => { setSession(null); setHistory([]); setSelection((current) => ({ ...current, projectId: event.target.value || undefined })); }}><option value="">Selecione</option>{options.projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label> : null}
          {selectedForm === "focused" ? <><label>Tipo do foco<input aria-label="Tipo do foco" value={focusKind} onChange={(event) => setFocusKind(event.target.value)} /></label><label>ID do foco<input aria-label="ID do foco" value={focusId} onChange={(event) => setFocusId(event.target.value)} /></label></> : null}
          <Button size="small" onClick={() => { const next = { workspaceId: selection.workspaceId, ...(selectedForm !== "general" && selection.projectId ? { projectId: selection.projectId } : {}), ...(selectedForm === "focused" && focusKind && focusId ? { focusKind, focusId } : {}) }; setSelection(next); void activateScope(next); }} disabled={!selection.workspaceId || (selectedForm !== "general" && !selection.projectId) || (selectedForm === "focused" && (!focusKind || !focusId))}>Criar ou retomar</Button>
        </div>
        {scopeError ? <InlineNotice tone="danger" title="Escopo indisponível">{scopeError}</InlineNotice> : null}
      </section> : null}

      {session ? <><div className="laboratory-session-note">Sessão ativa: <strong>{formLabel(session.form)}</strong>. {session.form === "general" ? "Leituras de Project exigem abrir uma Project chat." : "Project Room é a projeção desta Project chat; não é outro agente."}</div>
        {history.map((message) => <article className={`laboratory-message laboratory-${message.role}-message`} key={message.id}><header>{message.role === "human" ? "Você" : "Lab Agent"}</header><p>{message.content}</p></article>)}
        {hook.userMessage ? <article className="laboratory-message laboratory-user-message"><header>Você</header><p>{hook.userMessage}</p></article> : null}
        {(hook.userMessage || hook.tools.length > 0) ? <article className="laboratory-message laboratory-agent-message"><header>Lab Agent</header><AuditActivity statusLog={hook.statusLog} tools={hook.tools} phase={hook.phase} mode="live" />
          {hook.isRunning ? <div className="laboratory-live-activity"><LoaderCircle aria-hidden="true" size={15} /><span>{hook.statusLog.at(-1) ?? "Executando turno"}</span></div> : null}
          {hook.agentMessage ? <p className="laboratory-agent-draft">{hook.agentMessage}</p> : null}
          {hook.phase === "cancelled" ? <InlineNotice tone="warning" title="Turno cancelado">O trabalho parcial foi preservado como parcial; ele não é uma resposta completa.</InlineNotice> : null}
          {hook.phase === "failed" ? <InlineNotice tone="danger" title="Recusa ou falha do turno"><span>{hook.error}</span></InlineNotice> : null}
        </article> : null}</> : <div className="laboratory-fresh-state"><TriangleAlert aria-hidden="true" size={22} /><h1>Escolha o escopo da conversa</h1><p>O Lab Agent só inicia depois de uma sessão General, Project ou Focused explícita.</p></div>}
      {hook.phase === "unavailable" ? <div className="laboratory-unavailable"><h1>Laboratory indisponível</h1><p>O adapter informado não oferece uma integração executável.</p></div> : null}
    </div></div>
    {session && hook.phase !== "unavailable" ? <div className="laboratory-composer-position"><div className="laboratory-composer"><div className="laboratory-composer-main"><Textarea ref={hook.textareaRef} className="laboratory-composer-input" rows={1} value={hook.input} disabled={!scopeReady && !hook.isRunning} aria-label="Mensagem para o Laboratory" placeholder="Pergunte sobre este escopo..." onChange={(event) => hook.handleInput(event.target.value)} onInput={hook.resizeTextarea} onKeyDown={hook.handleKeyDown} /><Tooltip content={hook.isRunning ? "Cancelar turno" : "Enviar mensagem"}><IconButton variant={hook.isRunning ? "danger" : "primary"} aria-label={hook.isRunning ? "Cancelar turno" : "Enviar mensagem"} disabled={hook.phase === "stopping" || (!hook.isRunning && hook.input.trim().length === 0)} onClick={hook.isRunning ? hook.cancel : hook.submit}>{hook.phase === "stopping" ? <LoaderCircle className="laboratory-spin" aria-hidden="true" size={15} /> : hook.isRunning ? <CircleStop aria-hidden="true" size={16} /> : <Send aria-hidden="true" size={16} />}</IconButton></Tooltip></div></div></div> : null}
  </section>;
}
