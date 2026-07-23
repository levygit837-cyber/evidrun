from __future__ import annotations

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
from evidrun.shared.types import new_id, sha256_bytes, utc_now

ROOT = Path(__file__).resolve().parents[2]


def test_rejected_admission_cannot_create_a_run(repository: Repository) -> None:
    result = EvidrunService(repository).bootstrap_demo(ROOT / "benchmarks")
    source_run = repository.get_run(result["baseline_run_id"])
    assert source_run.run_spec_id is not None
    spec = repository.get_run_spec(source_run.run_spec_id)
    rejected = AdmissionService(runners=()).admit(spec)
    assert rejected.decision == "rejected"
    spec_row = repository.save_run_spec(spec)
    admission_row = repository.save_admission_record(spec_row.id, rejected)
    run_count = repository.latest_dashboard()["summary"]["runs"]

    with pytest.raises(ValueError, match="requires an admitted record"):
        repository.create_run(
            experiment_revision_id=source_run.experiment_revision_id,
            variant_id=spec.variant_id,
            runner=spec.agent_inventory.subject_id,
            objective=spec.goal.instruction,
            run_spec_id=spec_row.id,
            admission_id=admission_row.id,
        )

    assert repository.latest_dashboard()["summary"]["runs"] == run_count


def test_run_identity_and_lifecycle_are_enforced_by_canonical_contracts(
    repository: Repository,
) -> None:
    result = EvidrunService(repository).bootstrap_demo(ROOT / "benchmarks")
    source_run = repository.get_run(result["baseline_run_id"])
    assert source_run.run_spec_id is not None
    assert source_run.admission_id is not None
    spec = repository.get_run_spec(source_run.run_spec_id)
    admission = repository.get_admission_record(source_run.admission_id)

    with pytest.raises(ValueError, match="new Runs require"):
        repository.create_run(
            experiment_revision_id=source_run.experiment_revision_id,
            variant_id=spec.variant_id,
            runner=spec.agent_inventory.runner_ref.name,
            objective=spec.goal.instruction,
        )
    with pytest.raises(ValueError, match="identity must match"):
        repository.create_run(
            experiment_revision_id=source_run.experiment_revision_id,
            variant_id="forged-variant",
            runner=spec.agent_inventory.runner_ref.name,
            objective=spec.goal.instruction,
            run_spec_id=source_run.run_spec_id,
            admission_id=source_run.admission_id,
        )

    run = repository.create_run(
        experiment_revision_id=source_run.experiment_revision_id,
        variant_id=spec.variant_id,
        runner=spec.agent_inventory.runner_ref.name,
        objective=spec.goal.instruction,
        repetition=spec.repetition_index,
        run_spec_id=source_run.run_spec_id,
        admission_id=source_run.admission_id,
    )
    with pytest.raises(ValueError, match=r"run\.queued must be the first"):
        repository.append_event(
            run_id=run.id,
            event_type="run.preparing",
            payload={"scenario_ref": spec.scenario_ref.model_dump(mode="json")},
        )
    repository.append_event(
        run_id=run.id,
        event_type="run.queued",
        payload={
            "run_id": run.id,
            "variant_id": spec.variant_id,
            "run_spec_digest": spec.digest,
            "admission_digest": admission.digest,
        },
    )
    with pytest.raises(ValueError, match="invalid Run lifecycle transition"):
        repository.append_event(
            run_id=run.id,
            event_type="run.completed",
            payload={
                "status": "completed",
                "goal_state": "not_assessable",
                "terminal_cause": "forged direct completion",
            },
        )
    assert repository.get_run(run.id).status == "queued"


def test_admission_persistence_rejects_extra_subject_capability_context(
    repository: Repository,
) -> None:
    result = EvidrunService(repository).bootstrap_demo(ROOT / "benchmarks")
    source_run = repository.get_run(result["baseline_run_id"])
    assert source_run.run_spec_id is not None
    base_spec = repository.get_run_spec(source_run.run_spec_id)
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
    spec_row = repository.save_run_spec(spec)
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
    resolved = admission.resolved_inventory.capabilities[0].model_copy(
        update={
            "context_refs": (declared_instruction, injected_instruction),
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
        repository.save_admission_record(spec_row.id, tampered)


def test_failed_hard_gate_blocks_later_evaluation_stage(repository: Repository) -> None:
    result = EvidrunService(repository).bootstrap_demo(ROOT / "benchmarks")
    source_run = repository.get_run(result["baseline_run_id"])
    assert source_run.run_spec_id is not None
    base_spec = repository.get_run_spec(source_run.run_spec_id)
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
    spec_row = repository.save_run_spec(spec)
    admission = EvidrunService(repository).admission_service.admit(spec)
    admission_row = repository.save_admission_record(spec_row.id, admission)
    run = repository.create_run(
        experiment_revision_id=source_run.experiment_revision_id,
        variant_id="hard-gate-test",
        runner=spec.agent_inventory.subject_id,
        objective=spec.goal.instruction,
        run_spec_id=spec_row.id,
        admission_id=admission_row.id,
    )
    boundary = repository.append_event(
        run_id=run.id,
        event_type="run.queued",
        payload={
            "run_id": run.id,
            "variant_id": run.variant_id,
            "run_spec_digest": spec.digest,
            "admission_digest": admission.digest,
        },
    )
    evaluation_boundary = EvaluationBoundary(
        up_to_event_sequence=boundary.sequence,
        event_hash=boundary.event_hash,
    )
    integrity = EvaluationRecord(
        record_id=new_id("eval"),
        run_id=run.id,
        plan_ref=plan_ref,
        stage_id="integrity",
        source_type="deterministic_grader",
        evaluator_ref=integrity_ref,
        boundary=evaluation_boundary,
        dimension_values=(
            DimensionValue(
                dimension_id="integrity",
                value=False,
                rationale="The integrity check failed.",
                evidence_refs=(EvidenceRef(ref=f"event:{boundary.id}"),),
            ),
        ),
        gate_status="failed",
        status="final",
        created_at_utc=utc_now(),
    )
    fake_evidence = integrity.model_copy(
        update={
            "record_id": new_id("eval"),
            "dimension_values": (
                integrity.dimension_values[0].model_copy(
                    update={"evidence_refs": (EvidenceRef(ref="event:fake"),)}
                ),
            ),
        }
    )
    with pytest.raises(ValueError, match="authorized boundary"):
        repository.save_evaluation_record(fake_evidence)
    repository.save_evaluation_record(integrity)
    judge = EvaluationRecord(
        record_id=new_id("eval"),
        run_id=run.id,
        plan_ref=plan_ref,
        stage_id="judge",
        source_type="model_judge",
        evaluator_ref=judge_ref,
        provider_profile_id="test-judge-provider",
        provider_model="test-judge-model",
        boundary=evaluation_boundary,
        dimension_values=(
            DimensionValue(
                dimension_id="quality",
                value=3,
                rationale="This stage must not be accepted after the failed gate.",
                evidence_refs=(EvidenceRef(ref=f"event:{boundary.id}"),),
            ),
        ),
        gate_status="not_applicable",
        status="provisional",
        created_at_utc=utc_now(),
    )

    with pytest.raises(ValueError, match="blocked by a failed hard gate"):
        repository.save_evaluation_record(judge)
