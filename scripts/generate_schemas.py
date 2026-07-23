from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import TypeAdapter

from evidrun.contracts import (
    AdmissionRecord,
    AgentInventoryRevision,
    CheckpointPolicyRevision,
    CheckpointRecord,
    EvaluationPlanRevision,
    EvaluationRecord,
    EvaluatorEnvelope,
    GoalRevision,
    InteractionProtocolRevision,
    RevisionDecisionRecord,
    RunEventPayload,
    RunRecord,
    RunSpec,
    ScenarioRevision,
    StudyRevision,
    SubjectEnvelope,
    WorkspaceTemplateRevision,
)
from evidrun.entrypoints.api.app import create_app
from evidrun.experiments import ExperimentManifest

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "schemas" / "generated"
CONTRACT_OUTPUT = OUTPUT / "contracts"

CONTRACT_MODELS = {
    "study-revision-v1": StudyRevision,
    "goal-revision-v1": GoalRevision,
    "scenario-revision-v1": ScenarioRevision,
    "agent-inventory-revision-v1": AgentInventoryRevision,
    "workspace-template-revision-v1": WorkspaceTemplateRevision,
    "interaction-protocol-revision-v1": InteractionProtocolRevision,
    "evaluation-plan-revision-v1": EvaluationPlanRevision,
    "checkpoint-policy-revision-v1": CheckpointPolicyRevision,
    "run-spec-v1": RunSpec,
    "admission-record-v1": AdmissionRecord,
    "subject-envelope-v1": SubjectEnvelope,
    "evaluation-record-v1": EvaluationRecord,
    "evaluator-envelope-v1": EvaluatorEnvelope,
    "checkpoint-record-v1": CheckpointRecord,
    "revision-decision-record-v1": RevisionDecisionRecord,
    "run-record-v1": RunRecord,
}

ContractCatalog = (
    StudyRevision
    | GoalRevision
    | ScenarioRevision
    | AgentInventoryRevision
    | WorkspaceTemplateRevision
    | InteractionProtocolRevision
    | EvaluationPlanRevision
    | CheckpointPolicyRevision
    | RunSpec
    | AdmissionRecord
    | SubjectEnvelope
    | EvaluationRecord
    | EvaluatorEnvelope
    | CheckpointRecord
    | RevisionDecisionRecord
    | RunRecord
    | RunEventPayload
)


def render_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def emit(path: Path, content: str, *, check: bool) -> bool:
    if check:
        return path.exists() and path.read_text() == content
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    outputs: dict[Path, str] = {
        OUTPUT / "experiment-manifest-v1.json": render_json(
            ExperimentManifest.model_json_schema()
        ),
        CONTRACT_OUTPUT / "catalog-v1.json": render_json(
            TypeAdapter(ContractCatalog).json_schema()
        ),
        CONTRACT_OUTPUT / "run-event-payload-catalog-v1.json": render_json(
            TypeAdapter(RunEventPayload).json_schema()
        ),
    }
    for name, model in CONTRACT_MODELS.items():
        outputs[CONTRACT_OUTPUT / f"{name}.json"] = render_json(model.model_json_schema())

    app = create_app(data_dir=ROOT / ".schema-build")
    outputs[OUTPUT / "openapi-v1.json"] = render_json(app.openapi())

    mismatches = [
        str(path.relative_to(ROOT))
        for path, content in outputs.items()
        if not emit(path, content, check=args.check)
    ]
    if mismatches:
        rendered = "\n".join(f"- {path}" for path in mismatches)
        raise SystemExit(f"Generated schemas are stale:\n{rendered}")


if __name__ == "__main__":
    main()
