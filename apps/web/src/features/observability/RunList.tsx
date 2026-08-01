import { productTerms } from "../../productLanguage";
import type { Run } from "../../types";
import { StatusMark } from "./ObservabilityParts";
import { formatDate, formatDuration, shortId } from "./observabilityModel";
import { executionTrustText, isolationText } from "./executionTrust";

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
        <span>{productTerms.studyVersion.label} / Variant</span>
        <span>Runner</span>
        <span>Status</span>
        <span>Trust / isolamento</span>
        <span>Duração</span>
        <span>Horário</span>
      </div>
      {runs.map((run) => {
        const trust = executionTrustText(run.execution_trust);
        return (
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
            <span className="obs-run-trust">
              <strong>Trust: {trust.label}</strong>
              <small>Isolamento: {isolationText(run.isolation)}</small>
            </span>
            <span className="mono">{formatDuration(run)}</span>
            <span className="mono">{formatDate(run.created_at)}</span>
          </button>
        );
      })}
    </div>
  );
}
