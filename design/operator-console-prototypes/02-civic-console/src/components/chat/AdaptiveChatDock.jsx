import {
  ArrowSquareOut,
  ArrowsIn,
  ArrowsOut,
  ArrowsVertical,
  CaretLeft,
  ChatCircleDots,
  DotsSixVertical,
  SidebarSimple,
  X,
} from "@phosphor-icons/react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useRef, useState } from "react";

const snapOptions = [
  { id: "compact", label: "Compacto" },
  { id: "half", label: "Metade" },
  { id: "tall", label: "Alto" },
  { id: "full", label: "Conversa completa" },
];

function nextHeight(state) {
  if (state === "compact") return "half";
  if (state === "half") return "tall";
  return "compact";
}

export function AdaptiveChatDock({ state, onStateChange, messages, projectName }) {
  const reduceMotion = useReducedMotion();
  const [showSnaps, setShowSnaps] = useState(false);
  const [snapCandidate, setSnapCandidate] = useState("half");
  const holdTimer = useRef(null);
  const holding = useRef(false);

  const lastMessage = [...messages].reverse().find((message) => message.text);

  function clearHoldTimer() {
    if (holdTimer.current) {
      window.clearTimeout(holdTimer.current);
      holdTimer.current = null;
    }
  }

  function commitCandidate() {
    onStateChange(snapCandidate);
    setShowSnaps(false);
    holding.current = false;
  }

  function handlePointerDown(event) {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    holding.current = true;
    setSnapCandidate(state === "dock" || state === "closed" ? "half" : state);
    event.currentTarget.setPointerCapture?.(event.pointerId);
    holdTimer.current = window.setTimeout(() => {
      setShowSnaps(true);
      holdTimer.current = null;
    }, 360);
  }

  function handlePointerMove(event) {
    if (!holding.current || !showSnaps) return;
    const widthRatio = event.clientX / Math.max(window.innerWidth, 1);
    const heightRatio = event.clientY / Math.max(window.innerHeight, 1);
    if (widthRatio < 0.68) setSnapCandidate("full");
    else if (heightRatio < 0.28) setSnapCandidate("tall");
    else if (heightRatio > 0.7) setSnapCandidate("compact");
    else setSnapCandidate("half");
  }

  function handlePointerUp() {
    const previewWasOpen = showSnaps;
    clearHoldTimer();
    holding.current = false;
    if (previewWasOpen) commitCandidate();
  }

  function handleGripKeyDown(event) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (showSnaps) commitCandidate();
      else setShowSnaps(true);
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setShowSnaps(true);
      setSnapCandidate("tall");
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      setShowSnaps(true);
      setSnapCandidate("full");
    }
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      setShowSnaps(true);
      setSnapCandidate("half");
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setShowSnaps(true);
      setSnapCandidate("compact");
    }
    if (event.key === "Escape") {
      setShowSnaps(false);
    }
  }

  if (state === "closed") {
    return (
      <button
        className="chat-reopen"
        type="button"
        aria-label="Reabrir Chat"
        onClick={() => onStateChange("dock")}
      >
        <ChatCircleDots aria-hidden="true" size={23} />
      </button>
    );
  }

  if (state === "dock") {
    return (
      <motion.aside
        className="chat-dock"
        aria-label="Chat recolhido"
        initial={reduceMotion ? false : { opacity: 0, x: 12 }}
        animate={{ opacity: 1, x: 0 }}
      >
        <button type="button" aria-label="Abrir Chat" onClick={() => onStateChange("compact")}>
          <ChatCircleDots aria-hidden="true" size={24} />
          <span>Chat</span>
          <strong>{messages.length}</strong>
        </button>
        <p>{lastMessage?.text ?? "Sem mensagens"}</p>
      </motion.aside>
    );
  }

  return (
    <>
      <AnimatePresence>
        {showSnaps ? (
          <motion.div
            className="chat-snap-preview"
            role="listbox"
            aria-label="Encaixes do Chat"
            initial={reduceMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            {snapOptions.map((option) => (
              <button
                type="button"
                role="option"
                aria-selected={snapCandidate === option.id}
                className={snapCandidate === option.id ? "is-selected" : undefined}
                key={option.id}
                onClick={() => {
                  setSnapCandidate(option.id);
                  onStateChange(option.id);
                  setShowSnaps(false);
                }}
              >
                <span className={`snap-shape snap-${option.id}`} aria-hidden="true" />
                {option.label}
              </button>
            ))}
          </motion.div>
        ) : null}
      </AnimatePresence>

      <motion.aside
        className={`chat-panel chat-${state}`}
        data-chat-state={state}
        aria-label="Chat"
        initial={reduceMotion ? false : { opacity: 0, x: 16 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.2 }}
      >
        <button
          className="chat-grip"
          type="button"
          aria-label="Segure para visualizar encaixes do Chat"
          aria-expanded={showSnaps}
          title="Segure por 350 ms ou use as setas para escolher um encaixe"
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={() => {
            clearHoldTimer();
            holding.current = false;
          }}
          onKeyDown={handleGripKeyDown}
        >
          <DotsSixVertical aria-hidden="true" size={20} weight="bold" />
        </button>

        <header className="chat-header">
          <div>
            <h2>Chat</h2>
            <span>
              {messages.length} mensagens · {projectName}
            </span>
          </div>
          <div className="chat-controls">
            <button
              type="button"
              aria-label={state === "full" ? "Reduzir largura do Chat" : "Expandir largura do Chat"}
              title={state === "full" ? "Reduzir largura" : "Expandir largura"}
              onClick={() => onStateChange(state === "full" ? "half" : "full")}
            >
              {state === "full" ? (
                <ArrowsIn aria-hidden="true" size={19} />
              ) : (
                <ArrowsOut aria-hidden="true" size={19} />
              )}
            </button>
            <button
              type="button"
              aria-label="Alterar altura do Chat"
              title="Alterar altura"
              onClick={() => onStateChange(nextHeight(state))}
            >
              <ArrowsVertical aria-hidden="true" size={19} />
            </button>
            <button
              type="button"
              aria-label="Mostrar encaixes do Chat"
              aria-expanded={showSnaps}
              title="Mostrar encaixes"
              onClick={() => setShowSnaps((current) => !current)}
            >
              <SidebarSimple aria-hidden="true" size={19} />
            </button>
            <button
              type="button"
              aria-label="Recolher Chat"
              title="Recolher"
              onClick={() => onStateChange("dock")}
            >
              <CaretLeft aria-hidden="true" size={19} />
            </button>
            <button
              type="button"
              aria-label="Fechar Chat"
              title="Fechar"
              onClick={() => onStateChange("closed")}
            >
              <X aria-hidden="true" size={19} />
            </button>
          </div>
        </header>

        <div className="chat-thread" aria-live="polite">
          {messages.length === 0 ? (
            <p className="chat-empty">Nenhuma conversa neste Project.</p>
          ) : (
            messages.slice(-5).map((message) => (
              <article
                className={message.author === "Lab Agent" ? "chat-message is-agent" : "chat-message"}
                key={`chat-${message.id}`}
              >
                <header>
                  <strong>{message.author}</strong>
                  <time>{message.time}</time>
                </header>
                <p>{message.text}</p>
              </article>
            ))
          )}
        </div>

        <footer className="chat-footer">
          <button type="button" onClick={() => onStateChange("full")}>
            Abrir conversa completa
            <ArrowSquareOut aria-hidden="true" size={18} />
          </button>
        </footer>
      </motion.aside>
    </>
  );
}
