"""Persist the Subject response and the deterministic evaluation that follows it.

Capture policy decides what may be retained, and it is the only thing that decides
it: `raw_encrypted` stores a recoverable artifact, `redacted` keeps a placeholder,
`metadata` and `disabled` keep nothing. A Run captured without a recoverable
artifact cannot be evaluated after a crash, and that is the designed trade.
"""

from __future__ import annotations

from typing import Any

from evidrun.contracts import (
    ArtifactRef,
    RunExecutionAttempt,
    RunExecutionJob,
    RunSpec,
)
from evidrun.runs.adapters import EvaluationOutcome
from evidrun.runs.coordinator.context import ExecutionContext
from evidrun.runs.coordinator.lease import assert_held, lease_of
from evidrun.shared.ports import SubjectResult
from evidrun.shared.types import Classification, canonical_json, sha256_bytes


def persist_response(
    context: ExecutionContext,
    job: RunExecutionJob,
    attempt: RunExecutionAttempt,
    spec: RunSpec,
    result: SubjectResult,
) -> Any:
    """Write `subject.responded`, storing the raw output only when authorized."""

    run_id = job.run_id
    capture_mode = spec.capture_policy.default_mode
    captured_output = "[REDACTED]" if capture_mode == "redacted" else None
    captured_metadata = _captured_metadata(result, capture_mode)
    output_ref: ArtifactRef | None = None
    captured_evidence: list[str] = []
    if capture_mode == "raw_encrypted":
        output_ref = context.artifact_store.put_ref(
            canonical_json(
                {
                    "output": result.output,
                    "evidence": list(result.evidence),
                    "metadata": captured_metadata,
                }
            ).encode("utf-8"),
            project_id=context.project_id(run_id),
            media_type="application/json",
            classification=Classification.SENSITIVE,
            raw_authorized=True,
            ttl_days=spec.capture_policy.sensitive_ttl_days,
        )
        captured_evidence = [f"artifact:{output_ref.artifact_id}"]
    return context.repository.ledger.save_subject_response(
        run_id=run_id,
        spec=spec,
        response_payload={
            "output": captured_output,
            "output_ref": (
                output_ref.model_dump(mode="json") if output_ref is not None else None
            ),
            "output_digest": sha256_bytes(result.output.encode("utf-8")),
            "capture_mode": capture_mode,
            "evidence": captured_evidence,
            "metadata": captured_metadata,
        },
        captured_output=captured_output,
        lease=lease_of(job, attempt),
    )


def persist_evaluation(
    context: ExecutionContext,
    job: RunExecutionJob,
    attempt: RunExecutionAttempt,
    outcome: EvaluationOutcome,
) -> None:
    assert_held(context.repository, job, attempt)
    context.repository.evaluation.save_deterministic_evaluation(
        record=outcome.record,
        score=outcome.score,
        passed=outcome.passed,
        rationale=outcome.rationale,
        evidence=outcome.evidence,
        lease=lease_of(job, attempt),
    )


def _captured_metadata(
    result: SubjectResult, capture_mode: str
) -> list[dict[str, object]]:
    """Only scalar metadata is retained, and `disabled` retains none."""

    if capture_mode == "disabled":
        return []
    return [
        {"key": str(key), "value": value}
        for key, value in result.metadata.items()
        if isinstance(value, str | int | float | bool)
    ]
