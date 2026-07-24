import { forwardRef } from "react";
import {
  Check,
  Info,
  Warning,
  X,
} from "@phosphor-icons/react";

export const Button = forwardRef(function Button({
  children,
  variant = "secondary",
  size = "default",
  className = "",
  type = "button",
  ...props
}, ref) {
  return (
    <button
      {...props}
      ref={ref}
      type={type}
      className={`button button--${variant} button--${size} ${className}`.trim()}
    >
      {children}
    </button>
  );
});

export const IconButton = forwardRef(function IconButton({
  label,
  children,
  className = "",
  type = "button",
  ...props
}, ref) {
  return (
    <button
      {...props}
      ref={ref}
      type={type}
      className={`icon-button ${className}`.trim()}
      aria-label={label}
      title={label}
    >
      {children}
    </button>
  );
});

export function TechnicalId({ children, className = "" }) {
  return <code className={`technical-id ${className}`.trim()}>{children}</code>;
}

export function BoundaryNote({ children, tone = "neutral", className = "" }) {
  const Icon = tone === "warning" ? Warning : tone === "positive" ? Check : Info;
  return (
    <p className={`boundary-note boundary-note--${tone} ${className}`.trim()}>
      <Icon aria-hidden="true" size={17} weight="bold" />
      <span>{children}</span>
    </p>
  );
}

export function RouteHeading({ eyebrow, title, description, children }) {
  return (
    <header className="route-heading">
      <div>
        {eyebrow ? <p className="route-heading__eyebrow">{eyebrow}</p> : null}
        <h1>{title}</h1>
        {description ? <p className="route-heading__description">{description}</p> : null}
      </div>
      {children ? <div className="route-heading__actions">{children}</div> : null}
    </header>
  );
}

export function StatusMark({ status, label }) {
  const Icon = status === "rejected" || status === "failure" || status === "failed" ? X : Check;
  return (
    <span className={`status-mark status-mark--${status}`}>
      <Icon aria-hidden="true" size={14} weight="bold" />
      {label}
    </span>
  );
}

export function ScreenReaderLiveRegion({ children }) {
  return (
    <div className="sr-only" aria-live="polite" aria-atomic="true">
      {children}
    </div>
  );
}
