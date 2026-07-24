import { useEffect, useRef, useState } from "react";
import {
  ArrowsOutSimple,
  Browsers,
  ChatCircle,
  DotsSixVertical,
  PaperPlaneTilt,
  Rows,
  SidebarSimple,
  X,
} from "@phosphor-icons/react";
import { useOperator } from "../context/OperatorContext.jsx";
import { Button, IconButton } from "./Primitives.jsx";

const snapOptions = [
  { id: "compact", label: "Compacto", detail: "Dock lateral curto", Icon: SidebarSimple },
  { id: "half", label: "Meia altura", detail: "Thread com contexto", Icon: Rows },
  { id: "tall", label: "Alto", detail: "Thread lateral completa", Icon: ArrowsOutSimple },
  { id: "full", label: "Thread ampla", detail: "Leitura lado a lado", Icon: Browsers },
];

function SnapPreview({ target }) {
  if (!target) return null;
  return (
    <div className="snap-preview" aria-hidden="true">
      {snapOptions.map((option) => (
        <div
          key={option.id}
          className={`snap-preview__zone snap-preview__zone--${option.id} ${
            target === option.id ? "is-target" : ""
          }`}
        >
          <span>{option.label}</span>
        </div>
      ))}
    </div>
  );
}

export function AdaptiveChat() {
  const { state, dispatch } = useOperator();
  const [draft, setDraft] = useState("");
  const messages = state.chat.threadsByProjectId[state.currentProjectId] ?? [];
  const holdTimerRef = useRef(null);
  const previewActiveRef = useRef(false);
  const previewTargetRef = useRef("compact");
  const launcherRef = useRef(null);
  const previousModeRef = useRef(state.chat.mode);
  const gripRef = useRef(null);

  useEffect(() => {
    if (state.chat.mode === "closed" && previousModeRef.current !== "closed") {
      requestAnimationFrame(() => launcherRef.current?.focus());
    }
    previousModeRef.current = state.chat.mode;
  }, [state.chat.mode]);

  useEffect(() => {
    setDraft("");
  }, [state.currentProjectId]);

  useEffect(
    () => () => {
      if (holdTimerRef.current) window.clearTimeout(holdTimerRef.current);
    },
    [],
  );

  const commitMode = (mode) => {
    dispatch({ type: "CHAT_SET_MODE", mode });
  };

  const openPreview = () => {
    previewActiveRef.current = true;
    previewTargetRef.current = state.chat.mode === "closed" ? "compact" : state.chat.mode;
    dispatch({ type: "CHAT_PREVIEW", target: previewTargetRef.current });
  };

  const cancelPointer = () => {
    if (holdTimerRef.current) window.clearTimeout(holdTimerRef.current);
    holdTimerRef.current = null;
    previewActiveRef.current = false;
    dispatch({ type: "CHAT_PREVIEW", target: null });
  };

  const handlePointerDown = (event) => {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    holdTimerRef.current = window.setTimeout(openPreview, 350);
  };

  const handlePointerMove = (event) => {
    if (!previewActiveRef.current) return;
    const width = window.innerWidth;
    const height = window.innerHeight;
    let nextTarget = "half";
    if (event.clientX < width * 0.55) nextTarget = "full";
    else if (event.clientY < height * 0.32) nextTarget = "compact";
    else if (event.clientY > height * 0.7) nextTarget = "tall";
    if (nextTarget !== previewTargetRef.current) {
      previewTargetRef.current = nextTarget;
      dispatch({ type: "CHAT_PREVIEW", target: nextTarget });
    }
  };

  const handlePointerUp = () => {
    if (holdTimerRef.current) window.clearTimeout(holdTimerRef.current);
    holdTimerRef.current = null;
    if (previewActiveRef.current) {
      const target = previewTargetRef.current;
      previewActiveRef.current = false;
      commitMode(target);
      return;
    }
    dispatch({ type: "CHAT_TOGGLE_MENU" });
  };

  const handleGripKeyDown = (event) => {
    const menuOpen = state.chat.snapMenuOpen;
    if (event.key === "Escape") {
      event.preventDefault();
      dispatch({ type: "CHAT_MENU_CLOSE" });
      return;
    }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const direction = event.key === "ArrowDown" ? 1 : -1;
      const nextIndex = (state.chat.snapIndex + direction + snapOptions.length) % snapOptions.length;
      dispatch({ type: "CHAT_MENU_INDEX", index: nextIndex });
      if (!menuOpen) dispatch({ type: "CHAT_TOGGLE_MENU" });
      return;
    }
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (menuOpen) commitMode(snapOptions[state.chat.snapIndex].id);
      else dispatch({ type: "CHAT_TOGGLE_MENU" });
    }
  };

  const submitMessage = (event) => {
    event.preventDefault();
    const body = draft.trim();
    if (!body) return;
    dispatch({ type: "CHAT_ADD_MESSAGE", body });
    setDraft("");
  };

  if (state.chat.mode === "closed") {
    return (
      <button
        ref={launcherRef}
        type="button"
        className="chat-launcher"
        onClick={() => dispatch({ type: "CHAT_OPEN" })}
      >
        <ChatCircle size={22} weight="bold" aria-hidden="true" />
        <span>Chat</span>
      </button>
    );
  }

  return (
    <>
      <SnapPreview target={state.chat.previewTarget} />
      <aside className={`adaptive-chat adaptive-chat--${state.chat.mode}`} aria-label="Chat do operador">
        <button
          ref={gripRef}
          type="button"
          className="chat-grip"
          aria-label="Escolher posição e tamanho do Chat"
          aria-haspopup="menu"
          aria-expanded={state.chat.snapMenuOpen}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          onPointerCancel={cancelPointer}
          onLostPointerCapture={() => {
            if (!previewActiveRef.current) return;
            cancelPointer();
          }}
          onKeyDown={handleGripKeyDown}
        >
          <DotsSixVertical size={22} weight="bold" aria-hidden="true" />
        </button>

        {state.chat.snapMenuOpen ? (
          <div className="snap-menu" role="menu" aria-label="Posições do Chat">
            {snapOptions.map((option, index) => (
              <button
                key={option.id}
                type="button"
                role="menuitem"
                className={index === state.chat.snapIndex ? "is-keyboard-target" : ""}
                onMouseEnter={() => dispatch({ type: "CHAT_MENU_INDEX", index })}
                onClick={() => commitMode(option.id)}
              >
                <option.Icon size={19} aria-hidden="true" />
                <span><strong>{option.label}</strong><small>{option.detail}</small></span>
              </button>
            ))}
          </div>
        ) : null}

        <header className="adaptive-chat__header">
          <div>
            <h2>Chat do operador</h2>
            <p>Fora do SubjectEnvelope</p>
          </div>
          <div className="adaptive-chat__controls">
            <IconButton label="Compactar Chat" onClick={() => commitMode("compact")}>
              <SidebarSimple size={19} aria-hidden="true" />
            </IconButton>
            <IconButton label="Expandir para thread ampla" onClick={() => commitMode("full")}>
              <ArrowsOutSimple size={19} aria-hidden="true" />
            </IconButton>
            <IconButton label="Fechar Chat" onClick={() => dispatch({ type: "CHAT_CLOSE" })}>
              <X size={19} aria-hidden="true" />
            </IconButton>
          </div>
        </header>

        <div className="adaptive-chat__thread" aria-live="polite">
          <p className="adaptive-chat__scope">
            Project: <strong>{state.currentProject?.name}</strong> · thread isolado
          </p>
          {messages.map((message) => (
            <article key={message.id} className="operator-message">
              <div><strong>Operador</strong><time>{message.time}</time></div>
              <p>{message.body}</p>
            </article>
          ))}
          {!messages.length ? (
            <p className="adaptive-chat__empty-thread">Nenhuma nota neste Project.</p>
          ) : null}
          <p className="adaptive-chat__empty-space">
            Este thread permanece separado da execução e atravessa mudanças de rota.
          </p>
        </div>

        <form className="adaptive-chat__composer" onSubmit={submitMessage}>
          <label htmlFor="operator-chat-draft" className="sr-only">Mensagem do Chat do operador</label>
          <input
            id="operator-chat-draft"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Nota do operador"
          />
          <IconButton label="Adicionar nota ao Chat" type="submit" disabled={!draft.trim()}>
            <PaperPlaneTilt size={18} weight="bold" aria-hidden="true" />
          </IconButton>
        </form>

        <footer className="adaptive-chat__footer">
          <DotsSixVertical size={20} aria-hidden="true" />
          <span>Pressione e segure o grip por 350 ms para ver posições. Clique ou use as setas para escolher.</span>
        </footer>
      </aside>
    </>
  );
}
