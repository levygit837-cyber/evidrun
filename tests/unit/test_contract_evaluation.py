"""Evaluation plans, validators, checkpoints, adjudication and the event payload catalog."""

from __future__ import annotations

from datetime import timedelta

import pytest
from pydantic import ValidationError

from evidrun.contracts import (
    AdjudicatesEvaluationRelation,
    ArtifactRef,
    CheckpointRecord,
    ContractRef,
    ContractType,
    EvaluationPlanRevision,
    EvaluationPlanSpec,
    EvaluationRecord,
    EvaluationValidator,
    EvidenceRef,
    ExtensionRef,
    GoalRevision,
    GoalSpec,
    HumanAttestationRecord,
    RunBlueprint,
    StudyIntent,
    StudyRevision,
    StudySpec,
    normalize_event_payload,
    semantic_model_dump,
)
from evidrun.contracts.authoring.evaluation import (
    EvaluationDimension,
    EvaluationDisclosure,
    EvaluationStage,
    EvaluationTrigger,
    HumanAdjudicationPolicy,
)
from evidrun.contracts.compiler import (
    ExtensionSchemaRegistry,
    StudyCompiler,
    SubjectEnvelopeCompiler,
)
from evidrun.contracts.legacy import (
    capability_ref,
)
from evidrun.contracts.runtime.records import (
    CheckpointValidation,
    DimensionValue,
    EvaluationBoundary,
)
from evidrun.shared.types import (
    EvidenceMode,
    sha256_bytes,
    utc_now,
)
from tests.support.contract_fixtures import (
    accept,
    baseline_specs,
    materialized_subject_inputs,
    scripted_service,
)


def test_exploratory_study_has_default_variant_and_no_aggregate_score() -> None:
    _, package, registry, _ = baseline_specs()
    base_study = package.study
    goal = GoalRevision(
        logical_id="qualitative-incident-goal",
        revision=1,
        project_id=base_study.project_id,
        title="Qualitative incident exploration",
        payload=GoalSpec(
            mode="bounded_exploration",
            instruction="Investigate the authorized incident packet without claiming causality.",
            learning_targets=("Separate observations, hypotheses, and unknowns.",),
        ),
    )
    hidden_ref = ArtifactRef(
        artifact_id="hidden-calibration",
        digest=sha256_bytes(b"hidden calibration"),
        media_type="application/json",
    )
    evaluation = EvaluationPlanRevision(
        logical_id="qualitative-incident-eval",
        revision=1,
        project_id=base_study.project_id,
        title="Qualitative vector evaluation",
        payload=EvaluationPlanSpec(
            dimensions=(
                EvaluationDimension(
                    id="grounding",
                    description="Claims remain grounded in authorized evidence.",
                    value_type="number",
                    minimum=0,
                    maximum=4,
                ),
            ),
            stages=(
                EvaluationStage(
                    id="qualitative-judge",
                    kind="model_judge",
                    evaluator_ref=capability_ref("evidrun.evaluator", "qualitative-judge"),
                    trigger=EvaluationTrigger(kind="run_terminal"),
                    output_dimensions=("grounding",),
                ),
            ),
            disclosure=EvaluationDisclosure(hidden_input_refs=(hidden_ref,)),
            aggregation=None,
            human_adjudication_policy=HumanAdjudicationPolicy(
                required=True,
                adjudicator_ref=capability_ref(
                    "evidrun.human", "qualitative-adjudicator"
                ),
                adjudicable_stage_ids=("qualitative-judge",),
                attestation_verifier_ref=capability_ref(
                    "evidrun.authority", "webauthn-verifier"
                ),
            ),
        ),
    )
    accept(registry, goal)
    accept(registry, evaluation)
    blueprint = base_study.payload.run_blueprint.model_copy(
        update={"evaluation_plan_ref": evaluation.ref}
    )
    study = StudyRevision(
        logical_id="qualitative-incident-study",
        revision=1,
        project_id=base_study.project_id,
        title="Qualitative incident Study",
        payload=StudySpec(
            intent=StudyIntent(purpose="Evaluate investigation quality under uncertainty."),
            evidence_mode=EvidenceMode.EXPLORATORY,
            goal_ref=goal.ref,
            scenario_refs=base_study.payload.scenario_refs,
            run_blueprint=RunBlueprint.model_validate(blueprint),
        ),
    )
    accept(registry, study)

    specs = StudyCompiler(registry).compile(study)
    assert len(specs) == 1
    assert specs[0].variant_id == "default"
    assert specs[0].evaluation_plan.aggregation is None
    admission = scripted_service(specs[0].agent_inventory.runner_ref).admit(specs[0])
    assert admission.decision == "rejected"
    assert "runtime:bounded_exploration_terminal" in admission.missing_requirements
    assert "runtime:evaluation_pipeline" in admission.missing_requirements
    assert "runtime:verified_human_adjudication" in admission.missing_requirements
    with pytest.raises(ValueError, match="rejected admission"):
        SubjectEnvelopeCompiler.compile(
            specs[0],
            admission,
            materialized_inputs=materialized_subject_inputs(specs[0]),
        )
    assert "hidden-calibration" not in specs[0].goal.model_dump_json()


def test_unknown_required_extension_is_rejected_by_compiler() -> None:
    _, package, registry, _ = baseline_specs()
    study = package.study
    schema = ArtifactRef(
        artifact_id="schema",
        digest=sha256_bytes(b"{}"),
        media_type="application/schema+json",
    )
    payload = ArtifactRef(
        artifact_id="payload",
        digest=sha256_bytes(b"{}"),
        media_type="application/json",
    )
    extension = ExtensionRef(
        namespace="example.unregistered",
        slot="analysis",
        schema_ref=schema,
        schema_version="1",
        payload_ref=payload,
        digest=payload.digest,
        classification=payload.classification,
    )
    changed = StudyRevision(
        logical_id=study.logical_id,
        revision=2,
        project_id=study.project_id,
        title=study.title,
        payload=study.payload.model_copy(
            update={
                "run_blueprint": study.payload.run_blueprint.model_copy(
                    update={"extensions": (extension,)}
                )
            }
        ),
    )
    accept(registry, changed)
    with pytest.raises(ValueError, match="unregistered required extension"):
        StudyCompiler(registry, ExtensionSchemaRegistry()).compile(changed)


def test_evaluation_validator_enforces_types_scales_and_hard_gates() -> None:
    plan = EvaluationPlanSpec(
        dimensions=(
            EvaluationDimension(
                id="integrity",
                description="Structural integrity",
                value_type="boolean",
            ),
            EvaluationDimension(
                id="quality",
                description="Qualitative score",
                value_type="number",
                minimum=0,
                maximum=4,
            ),
        ),
        stages=(
            EvaluationStage(
                id="integrity",
                kind="integrity",
                evaluator_ref=capability_ref("evidrun.evaluator", "integrity"),
                trigger=EvaluationTrigger(kind="run_terminal"),
                output_dimensions=("integrity",),
                hard_gate=True,
            ),
            EvaluationStage(
                id="judge",
                kind="model_judge",
                evaluator_ref=capability_ref("evidrun.evaluator", "judge"),
                trigger=EvaluationTrigger(kind="run_terminal"),
                output_dimensions=("quality",),
            ),
        ),
    )
    assert EvaluationValidator.stages_visible_after_gates(plan, {"integrity": "failed"}) == (
        "integrity",
    )
    assert EvaluationValidator.stages_visible_after_gates(plan, {}) == ("integrity",)

    _, _, _, specs = baseline_specs()
    base = specs[0]
    record = EvaluationRecord(
        record_id="eval_test",
        run_id="run_test",
        plan_ref=base.evaluation_plan_ref,
        stage_id="integrity",
        source_type="deterministic_grader",
        evaluator_ref=plan.stages[0].evaluator_ref,
        boundary=EvaluationBoundary(
            up_to_event_sequence=1,
            event_hash="a" * 64,
        ),
        dimension_values=(
            DimensionValue(
                dimension_id="integrity",
                value=True,
                rationale="Structure is valid.",
                evidence_refs=(EvidenceRef(ref="event:evt_test"),),
            ),
        ),
        gate_status="passed",
        status="final",
        created_at_utc=utc_now(),
    )
    EvaluationValidator.validate(plan, record)
    invalid = record.model_copy(
        update={
            "dimension_values": (
                record.dimension_values[0].model_copy(update={"value": "yes"}),
            )
        }
    )
    with pytest.raises(ValueError, match="boolean"):
        EvaluationValidator.validate(plan, invalid)
    substituted_evaluator = record.model_copy(
        update={"evaluator_ref": capability_ref("evidrun.evaluator", "substituted")}
    )
    with pytest.raises(ValueError, match="substituted"):
        EvaluationValidator.validate(plan, substituted_evaluator)
    with pytest.raises(ValidationError, match="only model judge"):
        EvaluationRecord.model_validate(
            {
                **semantic_model_dump(record),
                "provider_profile_id": "fabricated-provider",
                "provider_model": "fabricated-model",
            }
        )

    failed_primary = record.model_copy(update={"gate_status": "failed"})
    passing_adjudication = failed_primary.model_copy(
        update={
            "record_id": "eval-integrity-adjudicated",
            "source_type": "human_adjudicator",
            "gate_status": "passed",
        }
    )
    assert EvaluationValidator.gate_results(
        plan, [failed_primary, passing_adjudication]
    ) == {"integrity": "passed"}
    assert EvaluationValidator.gate_results(
        plan, [passing_adjudication, failed_primary]
    ) == {"integrity": "passed"}
    future_primary = failed_primary.model_copy(
        update={
            "record_id": "eval-integrity-future",
            "boundary": failed_primary.boundary.model_copy(
                update={"up_to_event_sequence": 3}
            ),
        }
    )
    bounded_adjudication = passing_adjudication.model_copy(
        update={
            "boundary": passing_adjudication.boundary.model_copy(
                update={"up_to_event_sequence": 2}
            )
        }
    )
    with pytest.raises(ValueError, match="outside its boundary"):
        EvaluationValidator.validate_human_relation_boundary(
            bounded_adjudication,
            boundary_sequence=2,
            related_records=[(future_primary, 3)],
        )


def test_checkpoint_and_human_adjudication_are_append_only_records() -> None:
    validator = capability_ref("evidrun.checkpoint", "integrity")
    checkpoint = CheckpointRecord(
        checkpoint_id="checkpoint_test",
        run_id="run_test",
        policy_ref=ContractRef(
            contract_type=ContractType.CHECKPOINT_POLICY,
            logical_id="policy",
            revision=1,
            digest="b" * 64,
        ),
        definition_id="requirements-frozen",
        definition_digest="d" * 64,
        up_to_event_sequence=4,
        event_hash="c" * 64,
        validations=(
            CheckpointValidation(
                validator_ref=validator,
                passed=True,
                rationale="All required references are frozen.",
                evidence_refs=(EvidenceRef(ref="event:evt_four"),),
            ),
        ),
        replayability="partial",
        replayability_limitations=("Private model state is not captured.",),
        created_at_utc=utc_now(),
    )
    assert len(checkpoint.checkpoint_hash) == 64
    with pytest.raises(ValidationError, match="successful validations"):
        CheckpointRecord.model_validate(
            checkpoint.model_copy(
                update={
                    "validations": (
                        checkpoint.validations[0].model_copy(update={"passed": False}),
                    )
                }
            ).model_dump(mode="json", exclude={"checkpoint_hash"})
        )


def test_human_evaluation_timestamp_is_bound_to_verified_attestation() -> None:
    _, _, _, specs = baseline_specs()
    spec = specs[0]
    created_at = utc_now()
    relation = AdjudicatesEvaluationRelation(target_record_refs=("eval-source",))
    dimension_values = (
        DimensionValue(
            dimension_id=spec.evaluation_plan.dimensions[0].id,
            value=True,
            rationale="The human resolved the declared disagreement.",
            evidence_refs=(EvidenceRef(ref="event:evt-reviewed"),),
        ),
    )
    evaluator_ref = capability_ref("evidrun.human", "test-adjudicator")
    draft = EvaluationRecord.model_construct(
        schema_version="1",
        record_id="eval-human",
        run_id="run-human",
        plan_ref=spec.evaluation_plan_ref,
        stage_id=spec.evaluation_plan.stages[0].id,
        source_type="human_adjudicator",
        evaluator_ref=evaluator_ref,
        provider_profile_id=None,
        provider_model=None,
        boundary=EvaluationBoundary(
            up_to_event_sequence=1,
            event_hash="a" * 64,
        ),
        dimension_values=dimension_values,
        gate_status="passed",
        status="final",
        relation=relation,
        human_attestation=None,
        created_at_utc=created_at,
    )
    attestation = HumanAttestationRecord(
        attestation_id="attestation-human-eval",
        principal_id="human-reviewer",
        credential_id="credential-human-reviewer",
        action="evaluation.adjudicated",
        target_digest=spec.evaluation_plan_ref.digest,
        subject_digest=draft.human_subject_digest(),
        challenge_digest="b" * 64,
        assertion_ref=ArtifactRef(
            artifact_id="webauthn-human-eval",
            digest="c" * 64,
            media_type="application/webauthn+json",
        ),
        relying_party_id="evidrun.local",
        origin="https://evidrun.local",
        verifier_ref=capability_ref("evidrun.authority", "webauthn"),
        verified_at_utc=created_at,
    )
    record = EvaluationRecord(
        record_id="eval-human",
        run_id="run-human",
        plan_ref=spec.evaluation_plan_ref,
        stage_id=spec.evaluation_plan.stages[0].id,
        source_type="human_adjudicator",
        evaluator_ref=evaluator_ref,
        boundary=draft.boundary,
        dimension_values=dimension_values,
        gate_status="passed",
        status="final",
        relation=relation,
        human_attestation=attestation,
        created_at_utc=created_at,
    )
    assert record.created_at_utc == attestation.verified_at_utc
    with pytest.raises(ValidationError, match="verified attestation timestamp"):
        EvaluationRecord.model_validate(
            {
                **semantic_model_dump(record),
                "created_at_utc": (created_at + timedelta(seconds=1)).isoformat(),
            }
        )


def test_run_event_payload_catalog_rejects_unknown_types_and_extra_fields() -> None:
    normalized = normalize_event_payload(
        "run.running",
        {"from_status": "preparing", "reason": "The workspace is ready."},
    )
    assert normalized["from_status"] == "preparing"
    with pytest.raises(ValueError, match="unregistered Run Event"):
        normalize_event_payload("custom.unregistered", {})
    with pytest.raises(ValidationError, match="Extra inputs"):
        normalize_event_payload(
            "run.running",
            {
                "from_status": "preparing",
                "reason": "The workspace is ready.",
                "arbitrary": True,
            },
        )
    with pytest.raises(ValidationError, match="metadata Subject capture"):
        normalize_event_payload(
            "subject.responded",
            {
                "output": "SECRET_SHOULD_NOT_BE_CAPTURED",
                "output_digest": "a" * 64,
                "capture_mode": "metadata",
                "evidence": ["raw evidence"],
            },
        )
    with pytest.raises(ValidationError, match="raw encrypted Subject capture"):
        normalize_event_payload(
            "subject.responded",
            {
                "output_digest": "a" * 64,
                "capture_mode": "raw_encrypted",
                "evidence": ["plaintext evidence"],
            },
        )
    with pytest.raises(ValidationError, match="must be unique"):
        normalize_event_payload(
            "run.completed",
            {
                "status": "completed",
                "goal_result": {
                    "goal_mode": "goal_state",
                    "state": "achieved",
                },
                "terminal_cause": "Duplicate refs are not valid evidence coverage.",
                "evaluation_record_refs": ["eval-one", "eval-one"],
            },
        )
