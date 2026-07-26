import type { Run } from "../../types";
import { StatusMark } from "./ObservabilityParts";
import { formatDate, formatDuration, shortId } from "./observabilityModel";

export function RunList({
  runs,
  selectedRunId,
  onSelect,
}: {
  runs: Run[];
  selectedRunId?: string;
  onSelect(runId: string): void;
}) {
  return (
    <div className="obs-run-list" role="group" aria-label="Lista de Runs">
      <div className="obs-list-head" aria-hidden="true">
        <span>Run</span>
        <span>Study revision / variant</span>
        <span>Runner</span>
        <span>Status</span>
        <span>Detalhe</span>
        <span>Duração</span>
        <span>Horário</span>
      </div>
      {runs.map((run) => (
        <button
          className="obs-run-row"
          data-selected={selectedRunId === run.id || undefined}
          key={run.id}
          onClick={() => onSelect(run.id)}
          type="button"
        >
          <span className="obs-run-primary mono" title={run.id}>
            {shortId(run.id)}
            {run.contract_mode === "legacy_v1" ? <small>Legacy</small> : null}
          </span>
          <span className="obs-run-study">
            <strong title={run.experiment_revision_id}>{shortId(run.experiment_revision_id)}</strong>
            <small className="mono" title={run.variant_id}>{run.variant_id}</small>
          </span>
          <span className="obs-run-provider">
            <strong className="mono" title={run.runner}>{shortId(run.runner)}</strong>
          </span>
          <span><StatusMark status={run.status} /></span>
          <span className="mono">{run.contract_mode === "legacy_v1" ? "Legacy" : "Ver detalhe"}</span>
          <span className="mono">{formatDuration(run)}</span>
          <span className="mono">{formatDate(run.created_at)}</span>
        </button>
      ))}
    </div>
  );
}
