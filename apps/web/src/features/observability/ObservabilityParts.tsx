import { type ReactNode } from "react";
import { statusLabel, statusTone } from "./observabilityModel";

export function Fact({ label, children, mono = true }: { label: string; children: ReactNode; mono?: boolean }) {
  return (
    <div className="obs-fact">
      <dt>{label}</dt>
      <dd className={mono ? "mono" : undefined}>{children}</dd>
    </div>
  );
}

export function StatusMark({ status }: { status: string }) {
  return (
    <span className={`obs-status obs-status-${statusTone(status)}`}>
      <span aria-hidden="true" />
      {statusLabel(status)}
    </span>
  );
}

export function ListLoadingState() {
  return (
    <div className="obs-list-loading" aria-label="Carregando Runs" role="status">
      {Array.from({ length: 7 }, (_, index) => (
        <div className="obs-skeleton-row" key={index} aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
        </div>
      ))}
    </div>
  );
}

export function PageState({
  icon,
  title,
  children,
  role,
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
  role?: "alert" | "status";
}) {
  return (
    <div className="obs-page-state" role={role}>
      {icon}
      <strong>{title}</strong>
      <span>{children}</span>
    </div>
  );
}
