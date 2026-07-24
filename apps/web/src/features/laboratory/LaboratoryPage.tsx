import {
  Braces,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleStop,
  FileText,
  FlaskConical,
  LoaderCircle,
  Plus,
  RefreshCw,
  RotateCcw,
  Search,
  Send,
  ShieldCheck,
  Trash2,
  TriangleAlert,
  X,
  XCircle,
} from "lucide-react";
import {
  type KeyboardEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { LabUiEvent, LaboratoryAdapter } from "../../data/contracts";
import { Button, IconButton, InlineNotice, Textarea, Tooltip } from "../../ui/primitives";
import { DemoLaboratoryAdapter } from "./DemoLaboratoryAdapter";
import "./laboratory.css";

export type LaboratoryPhase =
  | "empty"
  | "ready"
  | "submitting"
  | "active"
  | "stopping"
  | "completed"
  | "cancelled"
  | "failed"
  | "unavailable";

type ToolEvent = Extract<LabUiEvent, { type: "tool" }>;
type MenuOption = { value: string; label: string };
type ContextItem = { id: string; label: string; kind: "run" | "artifact" };

const phaseLabels: Record<LaboratoryPhase, string> = {
  empty: "Aguardando pergunta",
  ready: "Pronto para enviar",
  submitting: "Enviando para o adapter Demo",
  active: "Demonstração em andamento",
  stopping: "Cancelando demonstração",
  completed: "Demonstração concluída",
  cancelled: "Demonstração cancelada",
  failed: "Demonstração com falha",
  unavailable: "Laboratory indisponível",
};

const samplePrompts = [
  "Resuma o contexto desta investigação.",
  "Use ferramentas para inspecionar o Run Demo.",
  "Simule uma falha e permita uma nova tentativa.",
];

function ComposerMenu({
  label,
  value,
  options,
  icon,
  onChange,
  compact = false,
}: {
  label: string;
  value: string;
  options: MenuOption[];
  icon?: ReactNode;
  onChange(value: string): void;
  compact?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const selected = options.find((option) => option.value === value) ?? options[0];

  useEffect(() => {
    if (!open) return;

    function closeOnOutsideClick(event: MouseEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }

    function closeOnEscape(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }

    document.addEventListener("mousedown", closeOnOutsideClick);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutsideClick);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  return (
    <div className="laboratory-menu" ref={rootRef}>
      <button
        type="button"
        className={compact ? "laboratory-menu-trigger compact" : "laboratory-menu-trigger"}
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        {icon}
        <span>{selected?.label}</span>
        <ChevronDown aria-hidden="true" size={12} />
      </button>
      {open ? (
        <div className="laboratory-menu-popover" role="menu" aria-label={label}>
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              role="menuitemradio"
              aria-checked={option.value === value}
              onClick={() => {
                onChange(option.value);
                setOpen(false);
              }}
            >
              <span>{option.label}</span>
              {option.value === value ? <Check aria-hidden="true" size={14} /> : null}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ToolIcon({ name }: { name: string }) {
  if (name === "search_repository") return <Search aria-hidden="true" size={15} />;
  if (name === "compile_subject") return <Braces aria-hidden="true" size={15} />;
  return <FileText aria-hidden="true" size={15} />;
}

function ToolStatus({ tool }: { tool: ToolEvent }) {
  if (tool.status === "running") {
    return (
      <span className="laboratory-tool-status is-running">
        <LoaderCircle aria-hidden="true" size={12} /> em execução
      </span>
    );
  }
  if (tool.status === "failed") {
    return (
      <span className="laboratory-tool-status is-failed">
        <XCircle aria-hidden="true" size={12} /> falhou
      </span>
    );
  }
  return (
    <span className="laboratory-tool-status is-completed">
      <CheckCircle2 aria-hidden="true" size={12} /> concluída
    </span>
  );
}

function AuditActivity({
  statusLog,
  tools,
  phase,
}: {
  statusLog: string[];
  tools: ToolEvent[];
  phase: LaboratoryPhase;
}) {
  const running = phase === "submitting" || phase === "active" || phase === "stopping";

  return (
    <details className="laboratory-audit" open>
      <summary>
        <ChevronRight className="laboratory-disclosure-chevron" aria-hidden="true" size={15} />
        <span>Atividade auditável</span>
        <span className="laboratory-demo-label">Demo</span>
        <span className="laboratory-audit-summary-state">
          {running ? "em andamento" : phaseLabels[phase].toLocaleLowerCase("pt-BR")}
        </span>
      </summary>
      <div className="laboratory-audit-body">
        <p>
          Eventos expostos pelo adapter Demo. Esta área não mostra raciocínio oculto e não representa
          execução do backend.
        </p>
        {statusLog.length > 0 ? (
          <ol className="laboratory-status-log" aria-label="Cronologia Demo">
            {statusLog.map((status, index) => (
              <li key={`${status}-${index}`}>{status}</li>
            ))}
          </ol>
        ) : null}

        {tools.length > 0 ? (
          <div className="laboratory-tool-group" aria-label="Tool calls Demo">
            {tools.map((tool) => (
              <details className="laboratory-tool" key={tool.id}>
                <summary>
                  <span className="laboratory-tool-icon">
                    <ToolIcon name={tool.name} />
                  </span>
                  <span className="laboratory-tool-name">{tool.name}</span>
                  <ToolStatus tool={tool} />
                  {tool.durationMs !== undefined ? (
                    <span className="laboratory-tool-duration">{tool.durationMs} ms</span>
                  ) : null}
                  <ChevronRight
                    className="laboratory-tool-chevron"
                    aria-hidden="true"
                    size={14}
                  />
                </summary>
                <div className="laboratory-tool-detail">
                  <dl>
                    <div>
                      <dt>Parâmetros</dt>
                      <dd>{tool.argumentsSummary ?? "Sem parâmetros demonstrativos."}</dd>
                    </div>
                    <div>
                      <dt>Resultado</dt>
                      <dd>{tool.resultSummary ?? "Aguardando resultado Demo."}</dd>
                    </div>
                    <div>
                      <dt>Fonte</dt>
                      <dd>Demo local determinística</dd>
                    </div>
                  </dl>
                </div>
              </details>
            ))}
          </div>
        ) : null}
      </div>
    </details>
  );
}

export function LaboratoryPage({ adapter }: { adapter?: LaboratoryAdapter }) {
  const laboratoryAdapter = useMemo(() => adapter ?? new DemoLaboratoryAdapter(), [adapter]);
  const initiallyUnavailable = laboratoryAdapter.mode !== "demo";
  const [phase, setPhase] = useState<LaboratoryPhase>(
    initiallyUnavailable ? "unavailable" : "empty",
  );
  const [input, setInput] = useState("");
  const [userMessage, setUserMessage] = useState<string | null>(null);
  const [agentMessage, setAgentMessage] = useState<string | null>(null);
  const [statusLog, setStatusLog] = useState<string[]>([]);
  const [tools, setTools] = useState<ToolEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [approval, setApproval] = useState("ask");
  const [model, setModel] = useState("deepseek-v4-flash");
  const [reasoning, setReasoning] = useState("max");
  const [contextItems, setContextItems] = useState<ContextItem[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastSubmittedInputRef = useRef<string | null>(null);
  const isRunning = phase === "submitting" || phase === "active" || phase === "stopping";
  const conversationStarted = userMessage !== null;

  const resizeTextarea = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(Math.max(textarea.scrollHeight, 40), 160)}px`;
  }, []);

  useEffect(() => {
    resizeTextarea();
  }, [input, resizeTextarea]);

  useEffect(
    () => () => {
      abortControllerRef.current?.abort();
    },
    [],
  );

  const runDemo = useCallback(
    async (exactInput: string) => {
      const controller = new AbortController();
      abortControllerRef.current = controller;
      lastSubmittedInputRef.current = exactInput;
      setUserMessage(exactInput);
      setAgentMessage(null);
      setStatusLog([]);
      setTools([]);
      setError(null);
      setInput("");
      setPhase("submitting");

      let terminalEventSeen = false;
      try {
        for await (const event of laboratoryAdapter.send(exactInput, controller.signal)) {
          if (event.source !== laboratoryAdapter.mode) {
            setError("O adapter retornou uma fonte incompatível com o modo declarado.");
            setPhase("failed");
            return;
          }

          if (event.type === "status") {
            setPhase("active");
            setStatusLog((current) => [...current, event.label]);
          } else if (event.type === "tool") {
            setPhase("active");
            setTools((current) => {
              const existingIndex = current.findIndex((tool) => tool.id === event.id);
              if (existingIndex === -1) return [...current, event];
              return current.map((tool, index) => (index === existingIndex ? event : tool));
            });
          } else if (event.type === "message") {
            setPhase("active");
            setAgentMessage(event.content);
          } else if (event.type === "error") {
            terminalEventSeen = true;
            setError(event.message);
            setPhase(event.source === "demo" ? "failed" : "unavailable");
          } else if (event.type === "done") {
            terminalEventSeen = true;
            setPhase("completed");
          }
        }

        if (!terminalEventSeen && !controller.signal.aborted) {
          setError("O adapter encerrou sem um evento terminal.");
          setPhase("failed");
        }
      } catch (caught) {
        if (controller.signal.aborted || (caught instanceof DOMException && caught.name === "AbortError")) {
          setPhase("cancelled");
        } else {
          setError(caught instanceof Error ? caught.message : "Falha inesperada na demonstração.");
          setPhase("failed");
        }
      } finally {
        if (abortControllerRef.current === controller) abortControllerRef.current = null;
      }
    },
    [laboratoryAdapter],
  );

  function submit() {
    if (isRunning || phase === "unavailable" || input.trim().length === 0) return;
    void runDemo(input);
  }

  function cancel() {
    if (!abortControllerRef.current || !isRunning) return;
    setPhase("stopping");
    abortControllerRef.current.abort();
  }

  function reset() {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    lastSubmittedInputRef.current = null;
    setInput("");
    setUserMessage(null);
    setAgentMessage(null);
    setStatusLog([]);
    setTools([]);
    setError(null);
    setPhase(initiallyUnavailable ? "unavailable" : "empty");
    textareaRef.current?.focus();
  }

  function retry() {
    const lastInput = lastSubmittedInputRef.current;
    if (lastInput) void runDemo(lastInput);
  }

  function handleInput(nextInput: string) {
    setInput(nextInput);
    if (!conversationStarted && phase !== "unavailable") {
      setPhase(nextInput.trim().length > 0 ? "ready" : "empty");
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (isRunning) cancel();
      else submit();
    }
  }

  function addContext(item: ContextItem) {
    setContextItems((current) =>
      current.some((currentItem) => currentItem.id === item.id) ? current : [...current, item],
    );
  }

  return (
    <section className="laboratory" data-state={phase} aria-label="Laboratory Demo">
      <div className="laboratory-state-announcer" role="status" aria-live="polite">
        {phaseLabels[phase]}
      </div>

      {conversationStarted ? (
        <div className="laboratory-conversation-scroll">
          <div className="laboratory-conversation">
            <div className="laboratory-conversation-toolbar">
              <span className="laboratory-demo-label">Demo</span>
              <Button variant="quiet" size="small" onClick={reset}>
                <RotateCcw aria-hidden="true" size={14} /> Nova demonstração
              </Button>
            </div>

            <article className="laboratory-message laboratory-user-message">
              <header>Você</header>
              <p>{userMessage}</p>
            </article>

            <article className="laboratory-message laboratory-agent-message">
              <header>
                <span>Lab Agent</span>
                <span className="laboratory-demo-label">Demo</span>
              </header>
              <AuditActivity statusLog={statusLog} tools={tools} phase={phase} />

              {isRunning ? (
                <div className="laboratory-live-activity">
                  <LoaderCircle aria-hidden="true" size={15} />
                  <span>{statusLog.at(-1) ?? "Preparando sequência Demo"}</span>
                </div>
              ) : null}

              {agentMessage ? <p className="laboratory-agent-draft">{agentMessage}</p> : null}

              {phase === "cancelled" ? (
                <InlineNotice tone="warning" title="Demonstração cancelada">
                  A sequência local foi interrompida. Nenhuma ação externa foi executada.
                </InlineNotice>
              ) : null}

              {phase === "failed" ? (
                <InlineNotice tone="danger" title="Falha Demo">
                  <span>{error}</span>
                  <Button variant="secondary" size="small" onClick={retry}>
                    <RefreshCw aria-hidden="true" size={13} /> Tentar novamente
                  </Button>
                </InlineNotice>
              ) : null}
            </article>
          </div>
        </div>
      ) : (
        <div className="laboratory-fresh-state" aria-hidden={phase === "unavailable"}>
          <span className="laboratory-demo-label">Laboratory Demo</span>
          <h1>O que você quer investigar?</h1>
          <p>Sequência local determinística. Nenhuma Run real ou backend é consultado.</p>
          <div className="laboratory-samples" aria-label="Perguntas de demonstração">
            {samplePrompts.map((prompt) => (
              <button key={prompt} type="button" onClick={() => handleInput(prompt)}>
                <span>{prompt}</span>
                <ChevronRight aria-hidden="true" size={14} />
              </button>
            ))}
          </div>
        </div>
      )}

      {phase === "unavailable" ? (
        <div className="laboratory-unavailable">
          <TriangleAlert aria-hidden="true" size={24} />
          <h1>Laboratory indisponível</h1>
          <p>O adapter informado não oferece uma integração executável para esta tela.</p>
          <span>Nenhuma mensagem foi enviada.</span>
        </div>
      ) : null}

      <div className="laboratory-composer-position">
        {contextItems.length > 0 ? (
          <div className="laboratory-context" aria-label="Contexto Demo selecionado">
            <span>Contexto Demo</span>
            <div>
              {contextItems.map((item) => (
                <span className="laboratory-context-item" key={item.id}>
                  {item.label}
                  <button
                    type="button"
                    onClick={() =>
                      setContextItems((current) =>
                        current.filter((currentItem) => currentItem.id !== item.id),
                      )
                    }
                    aria-label={`Remover ${item.label}`}
                  >
                    <X aria-hidden="true" size={12} />
                  </button>
                </span>
              ))}
            </div>
          </div>
        ) : null}

        <div className="laboratory-composer">
          <div className="laboratory-composer-main">
            <ComposerMenu
              compact
              label="Adicionar contexto Demo"
              value="add"
              icon={<Plus aria-hidden="true" size={17} />}
              options={[
                { value: "run", label: "Run Demo 018" },
                { value: "artifact", label: "ArtifactRef Demo" },
              ]}
              onChange={(value) =>
                addContext(
                  value === "run"
                    ? { id: "run-demo-018", label: "Run Demo 018", kind: "run" }
                    : { id: "artifact-demo", label: "ArtifactRef Demo", kind: "artifact" },
                )
              }
            />
            <Textarea
              ref={textareaRef}
              className="laboratory-composer-input"
              rows={1}
              value={input}
              disabled={phase === "unavailable" || phase === "stopping"}
              aria-label="Mensagem para a demonstração do Laboratory"
              placeholder="Pergunte sobre o contexto desta demonstração..."
              onChange={(event) => handleInput(event.target.value)}
              onInput={resizeTextarea}
              onKeyDown={handleKeyDown}
            />
            <Tooltip content={isRunning ? "Cancelar demonstração" : "Enviar mensagem"}>
              <IconButton
                variant={isRunning ? "danger" : "primary"}
                className="laboratory-send-button"
                aria-label={isRunning ? "Cancelar demonstração" : "Enviar mensagem"}
                disabled={
                  phase === "unavailable" ||
                  phase === "stopping" ||
                  (!isRunning && input.trim().length === 0)
                }
                onClick={isRunning ? cancel : submit}
              >
                {phase === "stopping" ? (
                  <LoaderCircle className="laboratory-spin" aria-hidden="true" size={15} />
                ) : isRunning ? (
                  <CircleStop aria-hidden="true" size={16} />
                ) : (
                  <Send aria-hidden="true" size={16} />
                )}
              </IconButton>
            </Tooltip>
          </div>

          <div className="laboratory-composer-toolbar" aria-label="Configurações da demonstração">
            <ComposerMenu
              label="Selecionar modo de aprovação Demo"
              value={approval}
              icon={<ShieldCheck aria-hidden="true" size={13} />}
              options={[
                { value: "ask", label: "Ask before actions" },
                { value: "read-only", label: "Read-only" },
                { value: "admitted", label: "Allow admitted tools" },
              ]}
              onChange={setApproval}
            />
            <div className="laboratory-composer-settings">
              <ComposerMenu
                compact
                label="Selecionar modelo Demo"
                value={model}
                options={[{ value: "deepseek-v4-flash", label: "deepseek-v4-flash" }]}
                onChange={setModel}
              />
              <ComposerMenu
                compact
                label="Selecionar reasoning Demo"
                value={reasoning}
                options={[
                  { value: "low", label: "reasoning: low" },
                  { value: "medium", label: "reasoning: medium" },
                  { value: "high", label: "reasoning: high" },
                  { value: "max", label: "reasoning: max" },
                ]}
                onChange={setReasoning}
              />
            </div>
          </div>
        </div>
        <div className="laboratory-provider-note">
          <FlaskConical aria-hidden="true" size={12} />
          <span>Demo local</span>
          <span aria-hidden="true">/</span>
          <code>cliproxyapi-local</code>
          {conversationStarted ? (
            <Tooltip content="Descartar a conversa Demo atual">
              <button type="button" onClick={reset} aria-label="Descartar demonstração atual">
                <Trash2 aria-hidden="true" size={12} />
              </button>
            </Tooltip>
          ) : null}
        </div>
      </div>
    </section>
  );
}
