import { FileWarning } from "lucide-react";
import type { EvaluationRecordDto } from "../../types";
import { Fact, PageState } from "./ObservabilityParts";

export function EvaluationPanel({ evaluations }: { evaluations: EvaluationRecordDto[] }) {
  if (!evaluations.length) {
    return (
      <PageState icon={<FileWarning size={20} />} title="No Recorded Evaluations" role="status">
        Nenhum EvaluationRecord canônico foi preservado para esta Run.
      </PageState>
    );
  }
  return (
    <div className="obs-evaluations">
      {evaluations.map((evaluation) => (
        <article key={evaluation.record_id}>
          <header>
            <div>
              <strong className="mono">{evaluation.record_id}</strong>
              <span>{evaluation.stage_id} / {evaluation.source_type}</span>
            </div>
            <span className={`obs-gate obs-gate-${evaluation.gate_status}`}>
              Gate {evaluation.gate_status}
            </span>
          </header>
          <dl className="obs-evaluation-meta">
            <Fact label="Status">{evaluation.status}</Fact>
            <Fact label="Digest">{evaluation.digest}</Fact>
            <Fact label="Boundary sequence">{evaluation.boundary.up_to_event_sequence ?? "Não informada"}</Fact>
          </dl>
          <div className="obs-dimensions">
            {evaluation.dimension_values.map((dimension) => (
              <section key={dimension.dimension_id}>
                <div className="obs-dimension-heading">
                  <strong>{dimension.dimension_id}</strong>
                  <code>{String(dimension.value)}</code>
                </div>
                <dl>
                  <Fact label="Rationale" mono={false}>{dimension.rationale}</Fact>
                  <Fact label="Confidence">{dimension.confidence ?? "Não informada"}</Fact>
                  <Fact label="Evidence">
                    {dimension.evidence_refs.map((item) => item.ref).join(", ")}
                  </Fact>
                </dl>
              </section>
            ))}
          </div>
        </article>
      ))}
    </div>
  );
}
