from __future__ import annotations

import argparse
import json
from pathlib import Path

from pydantic import TypeAdapter

from evidrun.contracts import (
    AdmissionRecord,
    AgentInventoryRevision,
    ArtifactManifest,
    CheckpointPolicyRevision,
    CheckpointRecord,
    EvaluationPlanRevision,
    EvaluationRecord,
    EvaluatorEnvelope,
    ExecutionRevisionSet,
    ExecutionTrustProjection,
    ExecutionTrustRecord,
    GoalRevision,
    HumanAttestationRecord,
    InteractionProtocolRevision,
    ProgressArtifactContent,
    ProgressArtifactPolicyRevision,
    ProgressArtifactRecord,
    ReviewPackage,
    ReviewTarget,
    RevisionDecisionRecord,
    RunEventPayload,
    RunExecutionAttempt,
    RunExecutionJob,
    RunRecord,
    RunSpec,
    ScenarioRevision,
    StudyRevision,
    SubjectEnvelope,
    SubjectEnvelopeRecord,
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
    "progress-artifact-policy-revision-v1": ProgressArtifactPolicyRevision,
    "run-spec-v1": RunSpec,
    "admission-record-v1": AdmissionRecord,
    "subject-envelope-v1": SubjectEnvelope,
    "evaluation-record-v1": EvaluationRecord,
    "evaluator-envelope-v1": EvaluatorEnvelope,
    "execution-revision-set-v1": ExecutionRevisionSet,
    "execution-trust-projection-v1": ExecutionTrustProjection,
    "execution-trust-record-v1": ExecutionTrustRecord,
    "checkpoint-record-v1": CheckpointRecord,
    "revision-decision-record-v1": RevisionDecisionRecord,
    "review-target-v1": ReviewTarget,
    "review-package-v1": ReviewPackage,
    "human-attestation-record-v1": HumanAttestationRecord,
    "progress-artifact-content-v1": ProgressArtifactContent,
    "progress-artifact-record-v1": ProgressArtifactRecord,
    "artifact-manifest-v1": ArtifactManifest,
    "run-record-v1": RunRecord,
    "run-execution-job-v1": RunExecutionJob,
    "run-execution-attempt-v1": RunExecutionAttempt,
    "subject-envelope-record-v1": SubjectEnvelopeRecord,
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
    | ProgressArtifactPolicyRevision
    | RunSpec
    | AdmissionRecord
    | SubjectEnvelope
    | EvaluationRecord
    | EvaluatorEnvelope
    | ExecutionRevisionSet
    | ExecutionTrustProjection
    | ExecutionTrustRecord
    | CheckpointRecord
    | RevisionDecisionRecord
    | ReviewTarget
    | ReviewPackage
    | HumanAttestationRecord
    | ProgressArtifactContent
    | ProgressArtifactRecord
    | ArtifactManifest
    | RunRecord
    | RunExecutionJob
    | RunExecutionAttempt
    | SubjectEnvelopeRecord
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
