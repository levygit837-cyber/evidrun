import { useEffect, useRef, useState } from "react";
import {
  ArrowSquareOut,
  CaretDown,
  CaretRight,
  ChatCenteredDots,
  Check,
  DotsSixVertical,
  FileText,
  PaperPlaneRight,
  TerminalWindow,
  Wrench,
  X,
  XCircle,
} from "@phosphor-icons/react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { authorizedExcerpt, labSequence } from "../data/mockData.js";
import { useLabStub } from "../hooks/useLabStub.js";
import { LocalDataFlag, SegmentedControl } from "./ui.jsx";

const snapLayouts = ["compact", "half", "tall", "full"];
const snapLabels = {
  compact: "Compacta",
  half: "Meia altura",
  tall: "Alta",
  full: "Thread completa",
};

function SignalSweep() {
  return (
    <div className="signal-sweep" role="status" aria-label="Execução do stub em andamento">
      <span className="signal-sweep__rails" aria-hidden="true">
        {[0, 1, 2, 3, 4].map((rail) => (
          <span key={rail} style={{ "--rail-index": rail }} />
        ))}
      </span>
      <span>Stub em execução</span>
    </div>
  );
}

function ObservableActivity({ state, onToggle }) {
  const visibleSteps = labSequence.slice(0, state.stageIndex + 1);
  const hasResult = state.execution !== "idle" && state.execution !== "active";
  return (
    <section className="activity-block" aria-label="Atividade observável">
      <button
        aria-expanded={state.thinkingOpen}
        className="activity-block__toggle"
        disabled={!hasResult}
        onClick={onToggle}
        type="button"
      >
        <span>
          {state.thinkingOpen ? <CaretDown aria-hidden="true" size={15} /> : <CaretRight aria-hidden="true" size={15} />}
          Atividade observável
        </span>
        <span className="activity-block__summary">
          {state.execution === "active" ? `${visibleSteps.length}/${labSequence.length}` : "Capturada"}
        </span>
      </button>

      <AnimatePresence initial={false}>
        {state.thinkingOpen ? (
          <motion.ol
            animate={{ opacity: 1, y: 0 }}
            className="activity-block__steps"
            exit={{ opacity: 0, y: -4 }}
            initial={{ opacity: 0, y: -4 }}
          >
            {labSequence.map((step, index) => (
              <li data-reached={index <= state.stageIndex} key={step}>
                <span aria-hidden="true">{index <= state.stageIndex ? <Check size={12} weight="bold" /> : null}</span>
                {step}
              </li>
            ))}
          </motion.ol>
        ) : null}
      </AnimatePresence>
    </section>
  );
}

function ToolTrace({ state }) {
  if (state.execution === "idle") return null;
  const toolReached = state.stageIndex >= 2;
  const resultReached = state.stageIndex >= 3;
  if (!toolReached) return null;

  return (
    <div className="tool-trace">
      <section className="tool-block" aria-label="Tool Call read_text">
        <header>
          <Wrench aria-hidden="true" size={16} />
          <strong>Tool Call</strong>
          <code>read_text</code>
        </header>
        <p>Input autorizado: <span className="mono">deployment-log-trace</span></p>
      </section>

      {resultReached ? (
        <section className="tool-block tool-block--result" aria-label="Tool Result local">
          <header>
            <FileText aria-hidden="true" size={16} />
            <strong>Tool Result</strong>
            <LocalDataFlag compact />
          </header>
          {state.demoMode === "success" ? (
            <pre>{authorizedExcerpt.join("\n")}</pre>
          ) : null}
          {state.demoMode === "empty" ? <p>Nenhum trecho autorizado encontrado no Stub local.</p> : null}
          {state.demoMode === "failure" ? (
            <p className="tool-block__failure"><XCircle aria-hidden="true" size={15} /> read_text falhou no Stub local.</p>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}

export function AdaptiveChat() {
  const reduceMotion = useReducedMotion();
  const { state, send, setDemoMode, toggleThinking } = useLabStub();
  const [view, setView] = useState("dock");
  const [layout, setLayout] = useState("compact");
  const [highlightedLayout, setHighlightedLayout] = useState("compact");
  const [snapOpen, setSnapOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const holdTimerRef = useRef(null);
  const snapOpenRef = useRef(false);
  const textareaRef = useRef(null);

  useEffect(() => {
    snapOpenRef.current = snapOpen;
  }, [snapOpen]);

  useEffect(
    () => () => {
      window.clearTimeout(holdTimerRef.current);
    },
    [],
  );

  const openThread = () => {
    setView("thread");
    setLayout("compact");
    window.setTimeout(() => textareaRef.current?.focus(), 0);
  };

  useEffect(() => {
    const handleOpenRequest = () => openThread();
    window.addEventListener("commanddeck:open-chat", handleOpenRequest);
    return () => window.removeEventListener("commanddeck:open-chat", handleOpenRequest);
  }, []);

  const setSnap = (nextLayout) => {
    setLayout(nextLayout);
    setHighlightedLayout(nextLayout);
    if (nextLayout === "full") setView("wide");
  };

  const handleGripDown = (event) => {
    window.clearTimeout(holdTimerRef.current);
    event.currentTarget.setPointerCapture?.(event.pointerId);
    holdTimerRef.current = window.setTimeout(() => {
      setSnapOpen(true);
      setHighlightedLayout(layout);
    }, 350);
  };

  const handleGripMove = (event) => {
    if (!snapOpenRef.current) return;
    const ratio = event.clientY / Math.max(window.innerHeight, 1);
    if (ratio < 0.24) setHighlightedLayout("full");
    else if (ratio < 0.5) setHighlightedLayout("tall");
    else if (ratio < 0.74) setHighlightedLayout("half");
    else setHighlightedLayout("compact");
  };

  const handleGripUp = () => {
    window.clearTimeout(holdTimerRef.current);
    if (snapOpenRef.current) setSnap(highlightedLayout);
    setSnapOpen(false);
  };

  const handleGripKey = (event) => {
    const currentIndex = snapLayouts.indexOf(layout);
    let next = null;
    if (event.key === "ArrowUp") next = snapLayouts[Math.min(currentIndex + 1, snapLayouts.length - 1)];
    if (event.key === "ArrowDown") next = snapLayouts[Math.max(currentIndex - 1, 0)];
    if (event.key === "Home") next = "compact";
    if (event.key === "End") next = "full";
    if (["1", "2", "3", "4"].includes(event.key)) next = snapLayouts[Number(event.key) - 1];
    if (next) {
      event.preventDefault();
      setSnap(next);
    }
  };

  const submit = () => {
    if (!send(draft)) return;
    setDraft("");
    textareaRef.current?.focus();
  };

  if (view === "dock") {
    return (
      <motion.aside
        animate={{ opacity: 1, x: 0 }}
        className="chat-dock"
        initial={reduceMotion ? false : { opacity: 0, x: 12 }}
        transition={{ duration: reduceMotion ? 0 : 0.2 }}
      >
        <button aria-label="Abrir Chat" onClick={openThread} type="button">
          <span className="chat-dock__icon"><ChatCenteredDots aria-hidden="true" size={21} weight="fill" /></span>
          <span>
            <strong>Lab Agent</strong>
            <small>Contexto autorizado</small>
          </span>
          <ArrowSquareOut aria-hidden="true" size={16} />
        </button>
      </motion.aside>
    );
  }

  return (
    <motion.aside
      animate={{ opacity: 1, scale: 1 }}
      aria-label="Chat adaptativo do Lab Agent"
      className={`adaptive-chat adaptive-chat--${view} adaptive-chat--${layout}`}
      data-layout={layout}
      initial={reduceMotion ? false : { opacity: 0, scale: 0.98 }}
      transition={{ duration: reduceMotion ? 0 : 0.2 }}
    >
      <header className="adaptive-chat__header">
        <button
          aria-label="Ajustar encaixe do Chat. Use setas, Home, End ou teclas 1 a 4."
          className="chat-grip"
          data-testid="chat-grip"
          onKeyDown={handleGripKey}
          onPointerDown={handleGripDown}
          onPointerMove={handleGripMove}
          onPointerUp={handleGripUp}
          type="button"
        >
          <DotsSixVertical aria-hidden="true" size={17} weight="bold" />
        </button>
        <div className="adaptive-chat__title">
          <strong>Lab Agent</strong>
          <span>Somente SubjectEnvelope autorizado</span>
        </div>
        <div className="adaptive-chat__header-actions">
          <button
            aria-label={view === "wide" ? "Reduzir Chat" : "Expandir Chat para inspeção"}
            onClick={() => setView(view === "wide" ? "thread" : "wide")}
            type="button"
          >
            <ArrowSquareOut aria-hidden="true" size={16} />
          </button>
          <button aria-label="Recolher Chat" onClick={() => setView("dock")} type="button">
            <X aria-hidden="true" size={17} />
          </button>
        </div>
      </header>

      <div className="adaptive-chat__controls">
        <SegmentedControl
          compact
          label="Estado demonstrativo"
          onChange={setDemoMode}
          options={[
            { value: "success", label: "Sucesso" },
            { value: "empty", label: "Vazio" },
            { value: "failure", label: "Falha" },
          ]}
          value={state.demoMode}
        />
        <div className="height-controls" aria-label="Altura do Chat" role="group">
          {snapLayouts.slice(0, 3).map((item) => (
            <button
              aria-label={`Altura ${snapLabels[item].toLowerCase()}`}
              data-selected={layout === item}
              key={item}
              onClick={() => setSnap(item)}
              type="button"
            >
              {snapLabels[item]}
            </button>
          ))}
        </div>
      </div>

      <div className="adaptive-chat__thread" aria-live="polite">
        {!state.userMessage ? (
          <div className="thread-empty">
            <TerminalWindow aria-hidden="true" size={26} weight="duotone" />
            <strong>Teste o envelope autorizado</strong>
            <p>Peça um diagnóstico do trecho local. Chats e conteúdo oculto nunca entram no SubjectEnvelope.</p>
          </div>
        ) : (
          <>
            <article className="message-block message-block--user">
              <span>Você</span>
              <p>{state.userMessage}</p>
            </article>

            <ObservableActivity onToggle={toggleThinking} state={state} />
            <ToolTrace state={state} />

            {state.agentMessage ? (
              <article className={`message-block message-block--agent message-block--${state.execution}`}>
                <span>Lab Agent</span>
                <p>{state.agentMessage}</p>
              </article>
            ) : null}
          </>
        )}
      </div>

      <div className="adaptive-chat__composer-wrap">
        {state.execution === "active" ? <SignalSweep /> : null}
        <div className="composer">
          <label className="sr-only" htmlFor="lab-composer">Mensagem para o Lab Agent</label>
          <textarea
            id="lab-composer"
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                submit();
              }
            }}
            placeholder="Diagnostique o trecho autorizado..."
            ref={textareaRef}
            rows={2}
            value={draft}
          />
          <button
            aria-label="Enviar mensagem"
            className="composer__send"
            disabled={!draft.trim() || state.execution === "active"}
            onClick={submit}
            type="button"
          >
            <PaperPlaneRight aria-hidden="true" size={18} weight="fill" />
          </button>
        </div>
        <p className="composer__hint">Enter envia. Shift+Enter cria uma linha.</p>
      </div>

      <AnimatePresence>
        {snapOpen ? (
          <motion.div
            animate={{ opacity: 1 }}
            className="snap-preview"
            data-testid="snap-preview"
            exit={{ opacity: 0 }}
            initial={{ opacity: 0 }}
            onPointerUp={handleGripUp}
          >
            <div className="snap-preview__map">
              {snapLayouts.map((item) => (
                <button
                  data-highlighted={highlightedLayout === item}
                  key={item}
                  onClick={() => {
                    setSnap(item);
                    setSnapOpen(false);
                  }}
                  onPointerEnter={() => setHighlightedLayout(item)}
                  type="button"
                >
                  <span aria-hidden="true" />
                  {snapLabels[item]}
                </button>
              ))}
            </div>
            <p>Solte para encaixar. Teclado: 1-4, setas, Home ou End.</p>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </motion.aside>
  );
}
