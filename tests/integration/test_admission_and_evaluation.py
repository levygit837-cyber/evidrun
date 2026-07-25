from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from evidrun.contracts import (
    ArtifactRef,
    ContractRef,
    ContractType,
    EvaluationRecord,
    EvidenceRef,
)
from evidrun.contracts.authoring import (
    CapabilityRequirement,
    EvaluationDimension,
    EvaluationPlanSpec,
    EvaluationStage,
    EvaluationTrigger,
)
from evidrun.contracts.compiler import (
    AdmissionService,
    CapabilityCatalogEntry,
)
from evidrun.contracts.legacy import capability_ref
from evidrun.contracts.runtime import DimensionValue, EvaluationBoundary
from evidrun.infrastructure.database import Repository
from evidrun.runs import EvidrunService
from evidrun.shared.types import sha256_bytes, utc_now

ROOT = Path(__file__).resolve().parents[2]


def test_rejected_admission_cannot_create_a_run(repository: Repository) -> None:
    result = EvidrunService(repository).bootstrap_demo(ROOT / "benchmarks")
    source_run = repository.read_model.get_run(result["baseline_run_id"])
    assert source_run.run_spec_id is not None
    spec = repository.read_model.get_run_spec(source_run.run_spec_id)
    rejected = AdmissionService(runners=()).admit(spec)
    assert rejected.decision == "rejected"
    spec_row = repository.catalog.save_run_spec(spec)
    admission_row = repository.catalog.save_admission_record(spec_row.id, rejected)
    run_count = repository.read_model.latest_dashboard()["summary"]["runs"]

    with pytest.raises(ValueError, match="requires an admitted record"):
        repository.catalog.create_run(
            experiment_revision_id=source_run.experiment_revision_id,
            variant_id=spec.variant_id,
            runner=spec.agent_inventory.subject_id,
            objective=spec.goal.instruction,
            run_spec_id=spec_row.id,
            admission_id=admission_row.id,
        )

    assert repository.read_model.latest_dashboard()["summary"]["runs"] == run_count


def test_run_identity_and_lifecycle_are_enforced_by_canonical_contracts(
    repository: Repository,
) -> None:
    result = EvidrunService(repository).bootstrap_demo(ROOT / "benchmarks")
    source_run = repository.read_model.get_run(result["baseline_run_id"])
    assert source_run.run_spec_id is not None
    assert source_run.admission_id is not None
    spec = repository.read_model.get_run_spec(source_run.run_spec_id)
    admission = repository.read_model.get_admission_record(source_run.admission_id)

    with pytest.raises(ValueError, match="new Runs require"):
        repository.catalog.create_run(
            experiment_revision_id=source_run.experiment_revision_id,
            variant_id=spec.variant_id,
            runner=spec.agent_inventory.runner_ref.name,
            objective=spec.goal.instruction,
        )
    with pytest.raises(ValueError, match="identity must match"):
        repository.catalog.create_run(
            experiment_revision_id=source_run.experiment_revision_id,
            variant_id="forged-variant",
            runner=spec.agent_inventory.runner_ref.name,
            objective=spec.goal.instruction,
            run_spec_id=source_run.run_spec_id,
            admission_id=source_run.admission_id,
        )

    run = repository.catalog.create_run(
        experiment_revision_id=source_run.experiment_revision_id,
        variant_id=spec.variant_id,
        runner=spec.agent_inventory.runner_ref.name,
        objective=spec.goal.instruction,
        repetition=spec.repetition_index,
        run_spec_id=source_run.run_spec_id,
        admission_id=source_run.admission_id,
    )
    with pytest.raises(ValueError, match=r"run\.queued must be the first"):
        repository.ledger.append_event(
            run_id=run.id,
            event_type="run.preparing",
            payload={"scenario_ref": spec.scenario_ref.model_dump(mode="json")},
        )
    repository.ledger.append_event(
        run_id=run.id,
        event_type="run.queued",
        payload={
            "run_id": run.id,
            "variant_id": spec.variant_id,
            "run_spec_digest": spec.digest,
            "admission_digest": admission.digest,
        },
    )
    with pytest.raises(ValueError, match="not valid while the Run is queued"):
        repository.ledger.append_event(
            run_id=run.id,
            event_type="evaluation.completed",
            payload={
                "evaluation_record_id": "eval_missing",
                "evaluation_record_digest": "f" * 64,
                "gate_status": "passed",
            },
        )
    with pytest.raises(
        ValueError,
        match=r"invalid Run lifecycle transition|completed Run requires",
    ):
        repository.ledger.append_event(
            run_id=run.id,
            event_type="run.completed",
            payload={
                "status": "completed",
                "goal_result": {
                    "goal_mode": "goal_state",
                    "state": "not_assessable",
                },
                "terminal_cause": "forged direct completion",
            },
        )
    assert repository.read_model.get_run(run.id).status == "queued"

    repository.ledger.append_event(
        run_id=run.id,
        event_type="run.preparing",
        payload={"scenario_ref": spec.scenario_ref.model_dump(mode="json")},
    )
    repository.ledger.append_event(
        run_id=run.id,
        event_type="run.running",
        payload={"from_status": "preparing", "reason": "Test runtime is ready."},
    )
    with pytest.raises(ValueError, match="before a Subject response"):
        repository.ledger.append_event(
            run_id=run.id,
            event_type="run.evaluating",
            payload={"from_status": "running", "reason": "Forged empty evaluation."},
        )
    assert repository.read_model.get_run(run.id).status == "running"


def test_ledger_rejects_unverified_human_progress_and_capture_bypass(
    repository: Repository,
) -> None:
    result = EvidrunService(repository).bootstrap_demo(ROOT / "benchmarks")
    terminal_run = repository.read_model.get_run(result["baseline_run_id"])
    assert terminal_run.run_spec_id is not None
    assert terminal_run.admission_id is not None
    spec = repository.read_model.get_run_spec(terminal_run.run_spec_id)
    admission = repository.read_model.get_admission_record(terminal_run.admission_id)
    valid_response_payload: dict[str, object] = {
        "output_digest": "a" * 64,
        "capture_mode": spec.capture_policy.default_mode,
    }
    if spec.capture_policy.default_mode == "redacted":
        valid_response_payload["output"] = "[REDACTED]"

    with pytest.raises(ValueError, match="cannot claim human authority"):
        repository.ledger.append_event(
            run_id=terminal_run.id,
            event_type="subject.responded",
            payload=valid_response_payload,
            actor_type="human",
            actor_id="agent-self-asserted",
        )
    with pytest.raises(ValueError, match="event type is reserved"):
        repository.ledger.append_event(
            run_id=terminal_run.id,
            event_type="progress.artifact_created",
            payload={},
        )
    with pytest.raises(ValueError, match="after a terminal lifecycle event"):
        repository.ledger.append_event(
            run_id=terminal_run.id,
            event_type="subject.responded",
            payload=valid_response_payload,
        )

    run = repository.catalog.create_run(
        experiment_revision_id=terminal_run.experiment_revision_id,
        variant_id=spec.variant_id,
        runner=spec.agent_inventory.runner_ref.name,
        objective=spec.goal.instruction,
        repetition=spec.repetition_index,
        run_spec_id=terminal_run.run_spec_id,
        admission_id=terminal_run.admission_id,
    )
    repository.ledger.append_event(
        run_id=run.id,
        event_type="run.queued",
        payload={
            "run_id": run.id,
            "variant_id": spec.variant_id,
            "run_spec_digest": spec.digest,
            "admission_digest": admission.digest,
        },
    )
    repository.ledger.append_event(
        run_id=run.id,
        event_type="run.preparing",
        payload={"scenario_ref": spec.scenario_ref.model_dump(mode="json")},
    )
    repository.ledger.append_event(
        run_id=run.id,
        event_type="run.running",
        payload={"from_status": "preparing", "reason": "Test runtime is ready."},
    )
    canonical_envelope = repository.read_model.get_subject_envelope(terminal_run.id).envelope
    repository.catalog.save_subject_envelope(run.id, canonical_envelope)
    repository.ledger.append_event(
        run_id=run.id,
        event_type="subject.invoked",
        payload={
            "runner": spec.agent_inventory.runner_ref.name,
            "network": "disabled",
            "subject_envelope_digest": canonical_envelope.digest,
        },
    )
    mismatched_mode = (
        "disabled"
        if spec.capture_policy.default_mode != "disabled"
        else "metadata"
    )
    with pytest.raises(ValueError, match="does not match the RunSpec policy"):
        repository.ledger.append_event(
            run_id=run.id,
            event_type="subject.responded",
            payload={
                "output_digest": "b" * 64,
                "capture_mode": mismatched_mode,
            },
        )
    response_event = repository.ledger.append_event(
        run_id=run.id,
        event_type="subject.responded",
        payload=valid_response_payload,
    )
    repository.ledger.append_event(
        run_id=run.id,
        event_type="run.evaluating",
        payload={"from_status": "running", "reason": "The Subject turn is complete."},
    )
    with pytest.raises(ValueError, match="requires a Subject response and evaluation records"):
        repository.ledger.append_event(
            run_id=run.id,
            event_type="run.completed",
            payload={
                "status": "completed",
                "goal_result": {"goal_mode": "goal_state", "state": "achieved"},
                "terminal_cause": "Forged achievement without an evaluation record.",
            },
        )
    stage = spec.evaluation_plan.stages[0]
    evaluation = EvaluationRecord(
        record_id="eval_terminal_exact_set",
        run_id=run.id,
        plan_ref=spec.evaluation_plan_ref,
        stage_id=stage.id,
        source_type="deterministic_grader",
        evaluator_ref=stage.evaluator_ref,
        boundary=EvaluationBoundary(
            up_to_event_sequence=response_event.sequence,
            event_hash=response_event.event_hash,
        ),
        dimension_values=(
            DimensionValue(
                dimension_id=stage.output_dimensions[0],
                value=True,
                rationale="The exact terminal reference set is under test.",
                evidence_refs=(EvidenceRef(ref=f"event:{response_event.id}"),),
            ),
        ),
        gate_status="passed",
        status="final",
        created_at_utc=utc_now(),
    )
    repository.evaluation.save_evaluation_record(evaluation)
    repository.ledger.append_event(
        run_id=run.id,
        event_type="evaluation.completed",
        payload={
            "evaluation_record_id": evaluation.record_id,
            "evaluation_record_digest": evaluation.digest,
            "gate_status": evaluation.gate_status,
        },
    )
    with pytest.raises(ValueError, match="every persisted EvaluationRecord exactly"):
        repository.ledger.append_event(
            run_id=run.id,
            event_type="run.failed",
            payload={
                "status": "failed",
                "goal_result": {
                    "goal_mode": "goal_state",
                    "state": "not_assessable",
                },
                "terminal_cause": "Forged omission of a persisted evaluation.",
            },
        )
    assert repository.read_model.get_run(run.id).status == "evaluating"


def test_admission_persistence_rejects_extra_subject_capability_context(
    repository: Repository,
) -> None:
    result = EvidrunService(repository).bootstrap_demo(ROOT / "benchmarks")
    source_run = repository.read_model.get_run(result["baseline_run_id"])
    assert source_run.run_spec_id is not None
    base_spec = repository.read_model.get_run_spec(source_run.run_spec_id)
    tool_ref = capability_ref("example.tool", "review-context-boundary")
    declared_instruction = ArtifactRef(
        artifact_id="declared-instruction",
        digest=sha256_bytes(b"declared"),
        media_type="text/markdown",
    )
    injected_instruction = ArtifactRef(
        artifact_id="injected-instruction",
        digest=sha256_bytes(b"injected"),
        media_type="text/markdown",
    )
    requirement = CapabilityRequirement(
        kind="tool",
        capability_ref=tool_ref,
        minimum_interface_version="1",
        exposure="instructions",
        instruction_refs=(declared_instruction,),
    )
    spec = base_spec.model_copy(
        update={
            "variant_id": "admission-context-boundary",
            "agent_inventory": base_spec.agent_inventory.model_copy(
                update={"capability_requirements": (requirement,)}
            ),
        }
    )
    spec_row = repository.catalog.save_run_spec(spec)
    admission = AdmissionService(
        runners=(spec.agent_inventory.runner_ref,),
        capabilities=(
            CapabilityCatalogEntry(
                ref=tool_ref,
                adapter="review-context-adapter@1",
                allowed_permissions=frozenset(),
                compatible_interface_versions=frozenset({"1"}),
            ),
        ),
    ).admit(spec)
    assert admission.decision == "admitted"
    repository.catalog.save_admission_record(spec_row.id, admission)
    assert admission.resolved_inventory.capabilities[0].context_refs == (
        declared_instruction,
    )
    resolved = admission.resolved_inventory.capabilities[0].model_copy(
        update={
            "context_refs": (
                *admission.resolved_inventory.capabilities[0].context_refs,
                injected_instruction,
            ),
        }
    )
    tampered = admission.model_copy(
        update={
            "resolved_inventory": admission.resolved_inventory.model_copy(
                update={"capabilities": (resolved,)}
            )
        }
    )

    with pytest.raises(ValueError, match="does not satisfy its interface or authority"):
        repository.catalog.save_admission_record(spec_row.id, tampered)


def test_unsupported_hard_gate_pipeline_is_rejected_before_run(
    repository: Repository,
) -> None:
    result = EvidrunService(repository).bootstrap_demo(ROOT / "benchmarks")
    source_run = repository.read_model.get_run(result["baseline_run_id"])
    assert source_run.run_spec_id is not None
    base_spec = repository.read_model.get_run_spec(source_run.run_spec_id)
    plan_ref = ContractRef(
        contract_type=ContractType.EVALUATION_PLAN,
        logical_id="hard-gate-plan",
        revision=1,
        digest="f" * 64,
    )
    integrity_ref = capability_ref("evidrun.evaluator", "integrity")
    judge_ref = capability_ref("evidrun.evaluator", "judge")
    plan = EvaluationPlanSpec(
        dimensions=(
            EvaluationDimension(
                id="integrity",
                description="The evidence boundary is structurally valid.",
                value_type="boolean",
            ),
            EvaluationDimension(
                id="quality",
                description="The answer quality on a bounded scale.",
                value_type="number",
                minimum=0,
                maximum=4,
            ),
        ),
        stages=(
            EvaluationStage(
                id="integrity",
                kind="integrity",
                evaluator_ref=integrity_ref,
                trigger=EvaluationTrigger(kind="event", reference="run.queued"),
                output_dimensions=("integrity",),
                hard_gate=True,
            ),
            EvaluationStage(
                id="judge",
                kind="model_judge",
                evaluator_ref=judge_ref,
                trigger=EvaluationTrigger(kind="event", reference="run.queued"),
                output_dimensions=("quality",),
            ),
        ),
    )
    spec = base_spec.model_copy(
        update={
            "variant_id": "hard-gate-test",
            "evaluation_plan_ref": plan_ref,
            "evaluation_plan": plan,
        }
    )
    spec_row = repository.catalog.save_run_spec(spec)
    admission = EvidrunService(repository).admission_service.admit(spec)
    admission_row = repository.catalog.save_admission_record(spec_row.id, admission)
    assert admission.decision == "rejected"
    assert "runtime:evaluation_pipeline" in admission.missing_requirements
    with pytest.raises(ValueError, match="requires an admitted record"):
        repository.catalog.create_run(
            experiment_revision_id=source_run.experiment_revision_id,
            variant_id="hard-gate-test",
            runner=spec.agent_inventory.subject_id,
            objective=spec.goal.instruction,
            run_spec_id=spec_row.id,
            admission_id=admission_row.id,
        )


def test_wall_time_exhaustion_writes_a_terminal_event(
    repository: Repository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = EvidrunService(repository).bootstrap_demo(ROOT / "benchmarks")
    source_run = repository.read_model.get_run(result["baseline_run_id"])
    assert source_run.run_spec_id is not None
    spec = repository.read_model.get_run_spec(source_run.run_spec_id)
    service = EvidrunService(repository)

    async def timeout_runner(_objective: str, _context: str) -> None:
        raise TimeoutError

    monkeypatch.setattr(service.runner, "execute", timeout_runner)
    run_ids_before = {
        item["id"] for item in repository.read_model.latest_dashboard()["runs"]
    }
    source = (
        ROOT / "benchmarks/scenarios/crl-ctx-002/fixtures/long.log"
    ).read_text()
    with pytest.raises(TimeoutError):
        asyncio.run(
            service._execute_spec(
                source_run.experiment_revision_id,
                spec,
                source,
            )
        )
    new_runs = [
        item
        for item in repository.read_model.latest_dashboard()["runs"]
        if item["id"] not in run_ids_before
    ]
    assert len(new_runs) == 1
    timed_out_run = repository.read_model.get_run(new_runs[0]["id"])
    assert timed_out_run.status == "budget_exhausted"
    assert repository.read_model.get_run_events(timed_out_run.id)[-1]["type"] == (
        "run.budget_exhausted"
    )


def test_runner_failure_writes_a_terminal_event_without_leaking_error(
    repository: Repository,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = EvidrunService(repository).bootstrap_demo(ROOT / "benchmarks")
    source_run = repository.read_model.get_run(result["baseline_run_id"])
    assert source_run.run_spec_id is not None
    spec = repository.read_model.get_run_spec(source_run.run_spec_id)
    service = EvidrunService(repository)

    async def failing_runner(_objective: str, _context: str) -> None:
        raise RuntimeError("sensitive provider response must not reach the ledger")

    monkeypatch.setattr(service.runner, "execute", failing_runner)
    run_ids_before = {item["id"] for item in repository.read_model.latest_dashboard()["runs"]}
    source = (
        ROOT / "benchmarks/scenarios/crl-ctx-002/fixtures/long.log"
    ).read_text()

    with pytest.raises(RuntimeError, match="Subject runner execution failed"):
        asyncio.run(
            service._execute_spec(
                source_run.experiment_revision_id,
                spec,
                source,
            )
        )

    new_runs = [
        item
        for item in repository.read_model.latest_dashboard()["runs"]
        if item["id"] not in run_ids_before
    ]
    assert len(new_runs) == 1
    failed_run = repository.read_model.get_run(new_runs[0]["id"])
    assert failed_run.status == "failed"
    terminal_event = repository.read_model.get_run_events(failed_run.id)[-1]
    assert terminal_event["type"] == "run.failed"
    assert terminal_event["payload"]["terminal_cause"] == (
        "Subject runner execution failed"
    )
    assert "sensitive provider response" not in str(terminal_event)
