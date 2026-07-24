import {
  Archive,
  Check,
  CheckCircle,
  Circle,
  Clock,
  XCircle,
} from "@phosphor-icons/react";

export function LocalDataFlag({ compact = false }) {
  return (
    <span className="local-flag">
      <Archive aria-hidden="true" size={14} weight="duotone" />
      {compact ? "Stub local" : "Demonstração local"}
    </span>
  );
}

const statusIcon = {
  complete: CheckCircle,
  current: Clock,
  pending: Circle,
  blocked: XCircle,
  admitted: CheckCircle,
  rejected: XCircle,
};

export function StatusLabel({ status, children }) {
  const Icon = statusIcon[status] ?? Circle;
  return (
    <span className={`status-label status-label--${status}`}>
      <Icon aria-hidden="true" size={14} weight={status === "pending" ? "regular" : "fill"} />
      {children}
    </span>
  );
}

export function SegmentedControl({ label, options, value, onChange, compact = false }) {
  return (
    <div className={`segmented ${compact ? "segmented--compact" : ""}`} aria-label={label} role="group">
      {options.map((option) => (
        <button
          className="segmented__button"
          data-selected={value === option.value}
          key={option.value}
          onClick={() => onChange(option.value)}
          type="button"
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function PageIntro({ icon: Icon, title, description, action, kicker }) {
  return (
    <header className="page-intro">
      <div className="page-intro__mark" aria-hidden="true">
        <Icon size={22} weight="duotone" />
      </div>
      <div className="page-intro__copy">
        {kicker ? <p className="page-intro__kicker">{kicker}</p> : null}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action ? <div className="page-intro__action">{action}</div> : null}
    </header>
  );
}

export function SectionHeader({ title, description, action }) {
  return (
    <header className="section-header">
      <div>
        <h2>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
      {action ? <div className="section-header__action">{action}</div> : null}
    </header>
  );
}

export function Definition({ label, value, mono = false }) {
  return (
    <div className="definition">
      <dt>{label}</dt>
      <dd className={mono ? "mono" : undefined}>{value}</dd>
    </div>
  );
}

export function ChecklistItem({ children, checked = true }) {
  return (
    <li className="checklist-item">
      <span className="checklist-item__icon" aria-hidden="true">
        {checked ? <Check size={13} weight="bold" /> : <Circle size={11} />}
      </span>
      <span>{children}</span>
    </li>
  );
}
