import {
  FileMagnifyingGlass,
  FolderOpen,
  PaperPlaneTilt,
  Paperclip,
} from "@phosphor-icons/react";
import { useRef } from "react";

export function EvidenceComposer({
  disabled,
  onSubmit,
  projectName,
  value,
  onValueChange,
  sourceSelected,
  onSourceSelectedChange,
}) {
  const inputRef = useRef(null);
  const canSubmit = value.trim().length > 0 && !disabled;

  function submit() {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    onValueChange("");
    queueMicrotask(() => inputRef.current?.focus({ preventScroll: true }));
  }

  return (
    <div className="composer-wrap">
      <div className="evidence-composer">
        <button
          className="composer-project"
          type="button"
          aria-label={`Project atual: ${projectName}`}
        >
          <FolderOpen aria-hidden="true" size={20} />
          <span>{projectName}</span>
        </button>
        <textarea
          ref={inputRef}
          rows="1"
          value={value}
          aria-label="Mensagem para o Lab Agent"
          placeholder="Pergunte sobre a evidência ou descreva um draft"
          onChange={(event) => onValueChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              submit();
            }
          }}
        />
        <button
          className="icon-button"
          type="button"
          aria-label="Anexar referência local"
          title="Anexar referência local"
        >
          <Paperclip aria-hidden="true" size={22} />
        </button>
        <button
          className={`icon-button${sourceSelected ? " is-selected" : ""}`}
          type="button"
          aria-label="Selecionar fonte autorizada"
          aria-pressed={sourceSelected}
          title="Selecionar fonte autorizada"
          onClick={() => onSourceSelectedChange(!sourceSelected)}
        >
          <FileMagnifyingGlass aria-hidden="true" size={22} />
        </button>
        <button
          className="composer-send"
          type="button"
          aria-label="Enviar mensagem"
          disabled={!canSubmit}
          onClick={submit}
        >
          <PaperPlaneTilt aria-hidden="true" size={21} weight="fill" />
        </button>
      </div>
      <p className="composer-boundary">
        O Lab Agent cria apenas drafts. Chat não integra o SubjectEnvelope.
      </p>
    </div>
  );
}
