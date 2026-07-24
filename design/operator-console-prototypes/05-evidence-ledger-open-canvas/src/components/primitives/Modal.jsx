import { useEffect, useRef } from "react";
import { X } from "@phosphor-icons/react";
import { IconButton } from "./Controls.jsx";

export function Modal({ title, description, open, onClose, children, footer }) {
  const panelRef = useRef(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return undefined;
    const previous = document.activeElement;
    const focusableSelector = [
      "button:not([disabled])",
      "input:not([disabled])",
      "textarea:not([disabled])",
      "select:not([disabled])",
      "a[href]",
      "[tabindex]:not([tabindex='-1'])",
    ].join(",");
    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = Array.from(panelRef.current?.querySelectorAll(focusableSelector) ?? []);
      if (!focusable.length) {
        event.preventDefault();
        panelRef.current?.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable.at(-1);
      if (event.shiftKey && (document.activeElement === first || document.activeElement === panelRef.current)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    const frame = requestAnimationFrame(() => panelRef.current?.focus());
    return () => {
      cancelAnimationFrame(frame);
      document.removeEventListener("keydown", onKeyDown);
      previous?.focus?.();
    };
  }, [open]);

  if (!open) return null;

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section
        className="modal-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        aria-describedby={description ? "modal-description" : undefined}
        tabIndex={-1}
        ref={panelRef}
      >
        <header className="modal-panel__header">
          <div>
            <h2 id="modal-title">{title}</h2>
            {description ? <p id="modal-description">{description}</p> : null}
          </div>
          <IconButton label="Fechar diálogo" icon={X} onClick={onClose} />
        </header>
        <div className="modal-panel__body">{children}</div>
        {footer ? <footer className="modal-panel__footer">{footer}</footer> : null}
      </section>
    </div>
  );
}
