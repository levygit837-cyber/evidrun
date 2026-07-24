import { useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  ArrowsOut,
  CaretDown,
  ChatCircle,
  Minus,
  PaperPlaneTilt,
  X,
} from "@phosphor-icons/react";
import { INITIAL_CHAT_MESSAGES } from "../../data/mockData.js";
import { IconButton } from "../primitives/Controls.jsx";

const SNAP_ORDER = ["compact", "half", "tall", "full"];
const SNAP_LABELS = {
  compact: "compacto",
  half: "meia altura",
  tall: "alto",
  full: "thread amplo",
};

export function AdaptiveChat({ open, onOpenChange, routeContext, scopeKey, scopeDescription }) {
  const reduceMotion = useReducedMotion();
  const [snap, setSnap] = useState("compact");
  const [collapsed, setCollapsed] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [highlighted, setHighlighted] = useState("compact");
  const [draft, setDraft] = useState("");
  const [threads, setThreads] = useState({});
  const holdTimer = useRef(null);
  const messages = threads[scopeKey] ?? INITIAL_CHAT_MESSAGES;

  const commitMessage = () => {
    const text = draft.trim();
    if (!text) return;
    setThreads((current) => ({
      ...current,
      [scopeKey]: [
        ...(current[scopeKey] ?? INITIAL_CHAT_MESSAGES),
        { id: `user-${Date.now()}`, role: "user", text },
        {
          id: `agent-${Date.now()}`,
          role: "agent",
          text: "Resposta ilustrativa: vou manter esta conversa como contexto lateral. Nenhum conteúdo foi enviado ao Subject Agent.",
        },
      ],
    }));
    setDraft("");
  };

  const startHold = (event) => {
    event.currentTarget.setPointerCapture?.(event.pointerId);
    clearTimeout(holdTimer.current);
    holdTimer.current = setTimeout(() => {
      setHighlighted(snap);
      setPreviewing(true);
    }, 350);
  };

  const moveHold = (event) => {
    if (!previewing) return;
    const y = event.clientY / window.innerHeight;
    const x = event.clientX / window.innerWidth;
    if (x < 0.55) setHighlighted("full");
    else if (y < 0.34) setHighlighted("tall");
    else if (y < 0.66) setHighlighted("half");
    else setHighlighted("compact");
  };

  const endHold = () => {
    clearTimeout(holdTimer.current);
    if (previewing) setSnap(highlighted);
    setPreviewing(false);
  };

  const onGripKeyDown = (event) => {
    const index = SNAP_ORDER.indexOf(snap);
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setSnap(SNAP_ORDER[Math.min(index + 1, SNAP_ORDER.length - 1)]);
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      setSnap(SNAP_ORDER[Math.max(index - 1, 0)]);
    } else if (event.key === "ArrowLeft" || event.key === "Home") {
      event.preventDefault();
      setSnap("compact");
    } else if (event.key === "ArrowRight" || event.key === "End") {
      event.preventDefault();
      setSnap("full");
    }
  };

  if (!open) {
    return (
      <button className="chat-dock" type="button" onClick={() => { onOpenChange(true); setCollapsed(false); }}>
        <ChatCircle size={20} aria-hidden="true" />
        <span>Chat</span>
      </button>
    );
  }

  return (
    <AnimatePresence>
      <motion.aside
        className={`adaptive-chat adaptive-chat--${snap} ${collapsed ? "is-collapsed" : ""}`}
        aria-label="Chat contextual"
        initial={reduceMotion ? false : { opacity: 0, x: 18 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 18 }}
        transition={{ duration: reduceMotion ? 0 : 0.2 }}
      >
        <header className="adaptive-chat__header">
          <div>
            <strong>Chat</strong>
            <span>{SNAP_LABELS[snap]}</span>
          </div>
          <div className="adaptive-chat__actions">
            <IconButton
              label={collapsed ? "Expandir thread" : "Colapsar thread"}
              icon={collapsed ? CaretDown : Minus}
              onClick={() => setCollapsed((value) => !value)}
            />
            <IconButton label="Usar thread amplo" icon={ArrowsOut} onClick={() => { setCollapsed(false); setSnap(snap === "full" ? "compact" : "full"); }} />
            <IconButton label="Fechar Chat" icon={X} onClick={() => onOpenChange(false)} />
          </div>
        </header>

        {!collapsed ? (
          <>
            <div
              className="chat-grip"
              role="slider"
              tabIndex={0}
              aria-label="Ajustar encaixe do Chat"
              aria-valuemin={0}
              aria-valuemax={3}
              aria-valuenow={SNAP_ORDER.indexOf(snap)}
              aria-valuetext={SNAP_LABELS[snap]}
              onPointerDown={startHold}
              onPointerMove={moveHold}
              onPointerUp={endHold}
              onPointerCancel={endHold}
              onKeyDown={onGripKeyDown}
            ><span /></div>

            <div className="adaptive-chat__context">
              <span>Contexto</span>
              <strong>{routeContext}</strong>
            </div>

            <div className="adaptive-chat__messages" aria-live="polite">
              {messages.map((message) => (
                <article key={message.id} className={`chat-message chat-message--${message.role}`}>
                  <strong>{message.role === "user" ? "Você" : "Lab Agent · Draft only"}</strong>
                  <p>{message.id === "context" ? scopeDescription : message.text}</p>
                </article>
              ))}
            </div>

            <div className="adaptive-chat__composer">
              <label htmlFor="chat-message">Mensagem para o Lab Agent</label>
              <div>
                <textarea
                  id="chat-message"
                  rows={2}
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      commitMessage();
                    }
                  }}
                  placeholder="Pergunte sobre o contexto atual"
                />
                <IconButton label="Enviar mensagem no Chat" icon={PaperPlaneTilt} disabled={!draft.trim()} onClick={commitMessage} />
              </div>
              <p>Demonstração local. Chat fora do SubjectEnvelope.</p>
            </div>
          </>
        ) : null}

        {previewing ? (
          <div className="snap-previews" role="status" aria-live="polite">
            {SNAP_ORDER.map((option) => (
              <div key={option} className={`snap-preview snap-preview--${option} ${highlighted === option ? "is-highlighted" : ""}`}>
                {SNAP_LABELS[option]}
              </div>
            ))}
          </div>
        ) : null}
      </motion.aside>
    </AnimatePresence>
  );
}
