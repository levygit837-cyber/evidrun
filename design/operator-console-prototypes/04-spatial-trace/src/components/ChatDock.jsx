import {
  ArrowsIn,
  ArrowsOut,
  BracketsCurly,
  ChatCircleDots,
  CheckCircle,
  DotsSixVertical,
  FileText,
  PaperPlaneTilt,
  Robot,
  UserCircle,
  WarningCircle,
  Wrench,
  X,
} from "@phosphor-icons/react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { authorizedExcerpt } from "../data/stubData.js";

const snapLabels = {
  compact: "Compacto",
  half: "Meio",
  tall: "Alto",
  full: "Thread completo",
};

const initialMessages = [
  {
    id: "welcome",
    type: "agent",
    text: "Posso preparar um draft local e explicar o próximo gate. Nada será executado fora desta demonstração.",
  },
];

function ResolverSpinner() {
  return (
    <div className="resolver-spinner" role="status" aria-label="Agente resolvendo o traço">
      <span className="resolver-spinner__track" aria-hidden="true">
        <i />
        <i />
        <i />
        <i />
      </span>
      <span>Resolvendo o traço local</span>
    </div>
  );
}

function MessageBlock({ message }) {
  if (message.type === "user" || message.type === "agent") {
    const Icon = message.type === "user" ? UserCircle : Robot;
    return (
      <article className={`chat-message chat-message--${message.type}`}>
        <header>
          <Icon size={17} weight="fill" aria-hidden="true" />
          <span>{message.type === "user" ? "Você" : "Agent"}</span>
        </header>
        <p>{message.text}</p>
      </article>
    );
  }

  if (message.type === "thinking") {
    return (
      <article className="activity-block">
        <header>
          <BracketsCurly size={17} aria-hidden="true" />
          <span>Atividade observável</span>
        </header>
        <ol>
          <li>Pedido recebido no composer local</li>
          <li>Escopo do Project confirmado</li>
          <li>Leitura autorizada selecionada</li>
        </ol>
      </article>
    );
  }

  if (message.type === "tool") {
    return (
      <article className="tool-block">
        <header>
          <Wrench size={17} aria-hidden="true" />
          <span>Tool Call</span>
          <em>Demonstração stub</em>
        </header>
        <code>read_text({"{ scope: 'authorized-local-excerpt' }"})</code>
      </article>
    );
  }

  return (
    <article className="tool-block tool-block--result">
      <header>
        <FileText size={17} aria-hidden="true" />
        <span>Tool Result</span>
        <em>Demonstração stub</em>
      </header>
      <p>{authorizedExcerpt}</p>
    </article>
  );
}

function SnapPreviews({ selected }) {
  return (
    <div className="snap-previews" aria-hidden="true">
      {Object.keys(snapLabels).map((snap) => (
        <div key={snap} className={`snap-preview snap-preview--${snap} ${selected === snap ? "is-selected" : ""}`}>
          <span>{snapLabels[snap]}</span>
        </div>
      ))}
    </div>
  );
}

export function ChatDock() {
  const [visible, setVisible] = useState(true);
  const [open, setOpen] = useState(false);
  const [geometry, setGeometry] = useState("compact");
  const [selectedSnap, setSelectedSnap] = useState("compact");
  const [snapPreview, setSnapPreview] = useState(false);
  const [messages, setMessages] = useState(initialMessages);
  const [draft, setDraft] = useState("");
  const [activity, setActivity] = useState("idle");
  const holdTimer = useRef(null);
  const taskTimers = useRef([]);
  const snapActive = useRef(false);
  const composerRef = useRef(null);
  const reduceMotion = useReducedMotion();

  useEffect(
    () => () => {
      window.clearTimeout(holdTimer.current);
      taskTimers.current.forEach((timer) => window.clearTimeout(timer));
    },
    [],
  );

  const appendLater = (delay, message, callback) => {
    taskTimers.current.push(
      window.setTimeout(() => {
        setMessages((current) => [...current, message]);
        callback?.();
      }, delay),
    );
  };

  const send = () => {
    const text = draft.trim();
    if (!text || activity === "running") return;
    taskTimers.current.forEach((timer) => window.clearTimeout(timer));
    taskTimers.current = [];
    const willFail = /falhar|erro/i.test(text);
    const stamp = Date.now();
    setOpen(true);
    setActivity("running");
    setDraft("");
    setMessages((current) => [...current, { id: `user-${stamp}`, type: "user", text }]);
    appendLater(180, { id: `thinking-${stamp}`, type: "thinking" });
    appendLater(420, { id: `tool-${stamp}`, type: "tool" });
    appendLater(650, { id: `result-${stamp}`, type: "result" });
    appendLater(
      900,
      {
        id: `agent-${stamp}`,
        type: "agent",
        text: willFail
          ? "A sequência stub terminou em falha controlada. Nenhum recurso real foi alterado ou executado."
          : "Draft local preparado. A próxima ação continua sujeita ao AdmissionRecord e à decisão humana verificável quando aplicável.",
      },
      () => setActivity(willFail ? "failure" : "success"),
    );
    composerRef.current?.focus({ preventScroll: true });
  };

  const onComposerKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send();
    }
  };

  const chooseSnapFromPointer = (event) => {
    if (!snapActive.current) return;
    const xRatio = event.clientX / window.innerWidth;
    const yRatio = event.clientY / window.innerHeight;
    if (xRatio < 0.45) setSelectedSnap("full");
    else if (yRatio < 0.35) setSelectedSnap("tall");
    else if (yRatio < 0.68) setSelectedSnap("half");
    else setSelectedSnap("compact");
  };

  const onGripDown = (event) => {
    event.currentTarget.setPointerCapture?.(event.pointerId);
    window.clearTimeout(holdTimer.current);
    holdTimer.current = window.setTimeout(() => {
      snapActive.current = true;
      setSelectedSnap(geometry);
      setSnapPreview(true);
    }, 350);
  };

  const finishGrip = () => {
    window.clearTimeout(holdTimer.current);
    if (snapActive.current) {
      setGeometry(selectedSnap);
      setOpen(true);
    }
    snapActive.current = false;
    setSnapPreview(false);
  };

  const activityLabel = {
    idle: "Agent ocioso",
    running: "Agent em atividade",
    success: "Atividade concluída",
    failure: "Atividade falhou de forma controlada",
  }[activity];

  if (!visible) {
    return (
      <button
        type="button"
        className="chat-reopen"
        aria-label="Reabrir Chat"
        onClick={() => {
          setVisible(true);
          setOpen(false);
        }}
      >
        <ChatCircleDots size={22} weight="fill" aria-hidden="true" />
      </button>
    );
  }

  return (
    <>
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {activityLabel}
      </div>
      <AnimatePresence>{snapPreview ? <SnapPreviews selected={selectedSnap} /> : null}</AnimatePresence>
      <motion.aside
        className={`chat-dock chat-dock--${geometry} ${open ? "is-open" : "is-collapsed"}`}
        aria-label="Chat lateral do Lab Agent"
        layout={!reduceMotion}
        transition={{ duration: reduceMotion ? 0 : 0.22, ease: [0.16, 1, 0.3, 1] }}
      >
        {!open ? (
          <button type="button" className="chat-strip" onClick={() => setOpen(true)}>
            <ChatCircleDots size={22} weight="fill" aria-hidden="true" />
            <span>
              <strong>Chat</strong>
              <small>{activityLabel}</small>
            </span>
            <ArrowsOut size={17} aria-hidden="true" />
          </button>
        ) : (
          <>
            <header className="chat-header">
              <div className="chat-header__identity">
                <span className={`agent-state agent-state--${activity}`} aria-hidden="true">
                  {activity === "failure" ? (
                    <WarningCircle size={18} weight="fill" />
                  ) : activity === "success" ? (
                    <CheckCircle size={18} weight="fill" />
                  ) : (
                    <Robot size={18} weight="fill" />
                  )}
                </span>
                <span>
                  <strong>Lab Agent</strong>
                  <small>{activityLabel}</small>
                </span>
              </div>
              <div className="chat-header__actions">
                <button
                  type="button"
                  className="icon-button"
                  aria-label="Recolher Chat"
                  onClick={() => setOpen(false)}
                >
                  <ArrowsIn size={17} aria-hidden="true" />
                </button>
                <button
                  type="button"
                  className="icon-button"
                  aria-label="Fechar Chat"
                  onClick={() => setVisible(false)}
                >
                  <X size={17} aria-hidden="true" />
                </button>
              </div>
            </header>

            <div className="snap-controls" aria-label="Tamanho do Chat">
              {Object.entries(snapLabels).map(([snap, label]) => (
                <button
                  key={snap}
                  type="button"
                  className={geometry === snap ? "is-active" : ""}
                  aria-pressed={geometry === snap}
                  onClick={() => setGeometry(snap)}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="chat-thread" aria-label="Thread local de demonstração">
              {messages.map((message) => (
                <MessageBlock key={message.id} message={message} />
              ))}
            </div>

            <div className="chat-composer-wrap">
              {activity === "running" ? <ResolverSpinner /> : null}
              <label className="sr-only" htmlFor="lab-agent-composer">
                Mensagem para o Lab Agent
              </label>
              <div className="chat-composer">
                <textarea
                  ref={composerRef}
                  id="lab-agent-composer"
                  value={draft}
                  rows={2}
                  placeholder="Peça um draft local..."
                  onChange={(event) => setDraft(event.target.value)}
                  onKeyDown={onComposerKeyDown}
                  readOnly={activity === "running"}
                  aria-busy={activity === "running"}
                />
                <button
                  type="button"
                  aria-label="Enviar mensagem"
                  onClick={send}
                  disabled={!draft.trim() || activity === "running"}
                >
                  <PaperPlaneTilt size={19} weight="fill" aria-hidden="true" />
                </button>
              </div>
              <p>Enter envia. Shift+Enter cria uma nova linha.</p>
            </div>

            <button
              type="button"
              className="chat-grip"
              aria-label="Segure para escolher o encaixe do Chat"
              onPointerDown={onGripDown}
              onPointerMove={chooseSnapFromPointer}
              onPointerUp={finishGrip}
              onPointerCancel={finishGrip}
            >
              <DotsSixVertical size={17} weight="bold" aria-hidden="true" />
            </button>
          </>
        )}
      </motion.aside>
    </>
  );
}
