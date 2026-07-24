import { useMemo, useRef, useState } from "react";
import {
  ArrowClockwise,
  CaretDown,
  Check,
  FileArrowDown,
  FileText,
  Fingerprint,
  FolderSimple,
  Info,
  PaperPlaneTilt,
  Pulse,
  TerminalWindow,
  Warning,
} from "@phosphor-icons/react";
import { ACTIVITY_SEQUENCE } from "../data/mockData.js";
import { useOperator } from "../context/OperatorContext.jsx";
import { Button, TechnicalId } from "./Primitives.jsx";

const presetOrder = ["idle", "running", "success", "failure"];
const presetLabels = {
  idle: "Pronto",
  running: "Em execução",
  success: "Sucesso",
  failure: "Falha",
};

export function EventInspector({ selectedStage = "tool-read" }) {
  const { state, dispatch } = useOperator();
  const cycleState = () => {
    const currentIndex = presetOrder.indexOf(state.agent.status);
    const next = presetOrder[(currentIndex + 1) % presetOrder.length];
    dispatch({ type: "AGENT_PRESET", preset: next });
  };

  return (
    <article className="event-inspector" aria-labelledby="selected-event-title">
      <div className="event-inspector__icon" aria-hidden="true">
        <TerminalWindow size={25} />
      </div>
      <div className="event-inspector__body">
        <p className="event-inspector__overline">Evento selecionado · Leitura da tool</p>
        <h2 id="selected-event-title">tool.completed: read_text</h2>
        <p>Input local autorizado para esta demonstração.</p>
        <dl className="event-inspector__metadata">
          <div>
            <dt>Job</dt>
            <dd>stub-local-23</dd>
          </div>
          <div>
            <dt>Tentativa</dt>
            <dd>01</dd>
          </div>
          <div>
            <dt>Run</dt>
            <dd><TechnicalId>run:stub-ri-0723-a</TechnicalId></dd>
          </div>
          <div>
            <dt>Seleção</dt>
            <dd>{selectedStage}</dd>
          </div>
        </dl>
      </div>
      <div className="event-inspector__actions">
        <Button
          variant="ghost"
          disabled
          aria-describedby="artifact-access-note"
          title="ArtifactRef sem grant de leitura"
        >
          <Fingerprint size={19} aria-hidden="true" />
          Abrir evidência
        </Button>
        <Button variant="ghost" onClick={cycleState}>
          <ArrowClockwise size={19} aria-hidden="true" />
          Alternar estado
        </Button>
        <p id="artifact-access-note">ArtifactRef identifica conteúdo, mas não concede acesso.</p>
      </div>
    </article>
  );
}

export function ConversationPreview() {
  const { state } = useOperator();
  const recentMessages = state.agent.messages.slice(-2);

  return (
    <section className="conversation-preview" aria-label="Preview da conversa do Lab">
      {recentMessages.map((message) => (
        <article key={message.id} className={`conversation-message conversation-message--${message.role}`}>
          <div className="conversation-message__label">
            <strong>{message.role === "user" ? "Usuário" : "Agente"}</strong>
            {message.role === "agent" ? <span>Draft do Lab Agent</span> : null}
          </div>
          <p>{message.body}</p>
        </article>
      ))}
      {state.agent.status === "running" && recentMessages.at(-1)?.role === "user" ? (
        <article className="conversation-message conversation-message--agent is-pending">
          <div className="conversation-message__label">
            <strong>Agente</strong>
            <span>Draft ainda não capturado</span>
          </div>
          <p>Aguardando o fim da sequência observável local.</p>
        </article>
      ) : null}
    </section>
  );
}

function ActivityIcon({ type }) {
  if (type === "tool-call") return <TerminalWindow size={20} aria-hidden="true" />;
  if (type === "tool-result") return <FileArrowDown size={20} aria-hidden="true" />;
  return <FileText size={20} aria-hidden="true" />;
}

export function ObservableActivity() {
  const { state } = useOperator();
  const items = ACTIVITY_SEQUENCE.slice(0, state.agent.activityCount);

  return (
    <details className="observable-activity" open>
      <summary>
        <CaretDown size={18} aria-hidden="true" />
        <span>Atividade observável</span>
        <span className="observable-activity__count">{items.length} eventos locais</span>
      </summary>
      <div className="observable-activity__body">
        <p className="observable-activity__boundary">
          Fatos públicos do stub. Sem chain-of-thought, hidden graders ou raciocínio privado.
        </p>
        <ol>
          {items.map((item) => (
            <li key={item.id} className={`activity-item activity-item--${item.type}`}>
              <span className="activity-item__icon"><ActivityIcon type={item.type} /></span>
              <div>
                <div className="activity-item__heading">
                  <strong>{item.label}</strong>
                  <time>{item.timestamp}</time>
                </div>
                <p>{item.summary}</p>
                {item.ref ? <TechnicalId>{item.ref}</TechnicalId> : null}
                {item.type !== "status" ? (
                  <span className="activity-item__kind">Demonstração local</span>
                ) : null}
              </div>
            </li>
          ))}
        </ol>
      </div>
    </details>
  );
}

export function ExecutionStatus() {
  const { state, dispatch } = useOperator();
  const status = state.agent.status;
  const StatusIcon = status === "success" ? Check : status === "failure" ? Warning : Pulse;

  return (
    <section className={`execution-status execution-status--${status}`} aria-label="Estado do Lab Agent">
      <div className="execution-status__primary" role="status" aria-live="polite" aria-atomic="true">
        {status === "running" ? (
          <span className="rhythm-spinner" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
        ) : (
          <StatusIcon size={19} weight="bold" aria-hidden="true" />
        )}
        <span>{state.agent.liveMessage}</span>
      </div>
      <div className="state-presets" aria-label="Presets de estado do Lab Agent">
        {presetOrder.map((preset) => (
          <button
            key={preset}
            type="button"
            aria-pressed={status === preset}
            onClick={() => dispatch({ type: "AGENT_PRESET", preset })}
          >
            {presetLabels[preset]}
          </button>
        ))}
      </div>
    </section>
  );
}

export function Composer() {
  const { state, dispatch } = useOperator();
  const [draft, setDraft] = useState("");
  const textareaRef = useRef(null);
  const running = state.agent.status === "running";
  const hasStudy = Boolean(state.study);
  const canSend = draft.trim().length > 0 && !running && hasStudy;
  const currentProject = useMemo(
    () => state.projects.find((project) => project.id === state.currentProjectId),
    [state.currentProjectId, state.projects],
  );

  const send = () => {
    if (!canSend) return;
    dispatch({ type: "AGENT_SEND", prompt: draft });
    setDraft("");
    requestAnimationFrame(() => textareaRef.current?.focus());
  };

  return (
    <form
      className={`composer ${running ? "is-busy" : ""}`}
      aria-busy={running}
      onSubmit={(event) => {
        event.preventDefault();
        send();
      }}
    >
      <label htmlFor="lab-composer">Novo draft para o Lab Agent</label>
      <textarea
        id="lab-composer"
        ref={textareaRef}
        rows={2}
        value={draft}
        disabled={!hasStudy}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            send();
          }
        }}
        placeholder={
          hasStudy
            ? "Pergunte sobre este Project ou descreva um novo draft"
            : "Vincule uma Study a este Project para criar drafts"
        }
      />
      <div className="composer__footer">
        <label className="composer__project">
          <FolderSimple size={19} aria-hidden="true" />
          <span className="sr-only">Project do draft</span>
          <select
            aria-label="Project do draft"
            value={state.currentProjectId}
            onChange={(event) =>
              dispatch({ type: "PROJECT_SELECT", projectId: event.target.value })
            }
          >
            {state.projects.map((project) => (
              <option key={project.id} value={project.id}>{project.name}</option>
            ))}
          </select>
          <CaretDown size={15} aria-hidden="true" />
        </label>
        <p>
          {!hasStudy
            ? "Bloqueado: este Project não possui Study vinculada."
            : running
              ? "Envio disponível após a resposta atual."
              : `Project: ${currentProject?.name}`}
        </p>
        <button type="submit" className="composer__send" disabled={!canSend} aria-label="Enviar draft">
          <PaperPlaneTilt size={21} weight="bold" aria-hidden="true" />
        </button>
      </div>
    </form>
  );
}

export function AgentBoundaryDisclosure() {
  return (
    <div className="agent-boundary-disclosure">
      <Info size={17} aria-hidden="true" />
      <span>O Chat do operador não entra no SubjectEnvelope. O Lab Agent produz somente drafts.</span>
    </div>
  );
}
