import { CheckCircle, Info, Warning, XCircle } from "@phosphor-icons/react";
import { cloneElement, useId } from "react";

export function Button({ variant = "secondary", size = "md", icon: Icon, children, className = "", ...props }) {
  return (
    <button className={`button button--${variant} button--${size} ${className}`} {...props}>
      {Icon ? <Icon aria-hidden="true" size={18} weight="regular" /> : null}
      <span>{children}</span>
    </button>
  );
}

export function IconButton({ label, icon: Icon, className = "", ...props }) {
  return (
    <button className={`icon-button ${className}`} aria-label={label} title={label} {...props}>
      <Icon aria-hidden="true" size={19} weight="regular" />
    </button>
  );
}

export function StatusBadge({ tone = "neutral", children }) {
  return <span className={`status-badge status-badge--${tone}`}>{children}</span>;
}

export function Notice({ tone = "info", title, children, compact = false }) {
  const Icon = tone === "danger" ? XCircle : tone === "warning" ? Warning : tone === "success" ? CheckCircle : Info;
  return (
    <div className={`notice notice--${tone} ${compact ? "notice--compact" : ""}`} role={tone === "danger" ? "alert" : "status"}>
      <Icon size={20} weight="regular" aria-hidden="true" />
      <div>
        {title ? <strong>{title}</strong> : null}
        {children ? <div className="notice__body">{children}</div> : null}
      </div>
    </div>
  );
}

export function SegmentedControl({ label, value, options, onChange, compact = false }) {
  return (
    <fieldset className={`segmented ${compact ? "segmented--compact" : ""}`}>
      <legend className="sr-only">{label}</legend>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          className={value === option.value ? "is-selected" : ""}
          aria-pressed={value === option.value}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </fieldset>
  );
}

export function Field({ label, hint, error, children }) {
  const inputId = useId();
  const descriptionId = useId();
  return (
    <div className="field">
      <label className="field__label" htmlFor={inputId}>{label}</label>
      {cloneElement(children, { id: inputId, "aria-describedby": hint || error ? descriptionId : undefined })}
      {hint && !error ? <span id={descriptionId} className="field__hint">{hint}</span> : null}
      {error ? <span id={descriptionId} className="field__error" role="alert">{error}</span> : null}
    </div>
  );
}

export function TechnicalRef({ children }) {
  return <code className="technical-ref">{children}</code>;
}
