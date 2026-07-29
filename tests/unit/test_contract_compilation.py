"""Study compilation: envelopes, disclosure, progress artifacts and payload shape."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from evidrun.contracts import (
    EvaluationPlanRevision,
    EvidenceRef,
    ProgressArtifactContent,
    ProgressArtifactPolicyRevision,
    ProgressArtifactPolicySpec,
    StudyRevision,
    normalize_event_payload,
)
from evidrun.contracts.authoring.evaluation import (
    EvaluationTrigger,
    SubjectEvaluationDisclosure,
)
from evidrun.contracts.authoring.progress import (
    ProgressArtifactDefinition,
    SubjectTurnIntervalProgressTrigger,
)
from evidrun.contracts.authoring.run import StopCondition
from evidrun.contracts.compiler import (
    EvaluatorEnvelopeCompiler,
    StudyCompiler,
    SubjectEnvelopeCompiler,
)
from evidrun.contracts.legacy import (
    capability_ref,
)
from evidrun.contracts.runtime.records import (
    ProgressStatement,
)
from tests.support.admission_specs import scripted_admission_service as scripted_service
from tests.support.contract_fixtures import (
    ROOT,
    accept,
    baseline_specs,
    materialized_subject_inputs,
)
from tests.support.execution_trust import unpersisted_unverified_trust


def test_legacy_study_compiles_two_specs_and_hides_laboratory_data() -> None:
    manifest, _, _, specs = baseline_specs()
    assert {spec.variant_id for spec in specs} == {"head-truncation", "tail-preservation"}
    assert all(spec.repetition_index == 1 for spec in specs)

    admission_service = scripted_service(
        capability_ref("evidrun.runner", "scripted-log-investigator-v1")
    )
    baseline = next(spec for spec in specs if spec.variant_id == manifest.baseline_variant)
    admission = admission_service.admit(baseline, unpersisted_unverified_trust(baseline))
    envelope = SubjectEnvelopeCompiler.compile(
        baseline,
        admission,
        materialized_inputs=materialized_subject_inputs(baseline),
    )
    with pytest.raises(ValueError, match="must match visible scenario inputs"):
        SubjectEnvelopeCompiler.compile(
            baseline,
            admission,
            materialized_inputs=(),
        )
    serialized = envelope.model_dump_json()

    assert admission.decision == "admitted"
    assert manifest.hypothesis not in serialized
    assert manifest.graders[0].expected not in serialized
    assert "evaluation_plan" not in serialized
    assert "provider_profile_id" not in serialized
    assert str(ROOT / "benchmarks/scenarios/crl-ctx-002/fixtures/long.log") not in serialized
    assert "context-snapshot:incident-log" in serialized
    evaluator = EvaluatorEnvelopeCompiler.compile(baseline, baseline.evaluation_plan.stages[0].id)
    evaluator_serialized = evaluator.model_dump_json()
    assert manifest.graders[0].expected in evaluator_serialized
    assert manifest.hypothesis not in evaluator_serialized
    assert str(ROOT / "benchmarks/scenarios/crl-ctx-002/fixtures/long.log") not in (
        evaluator_serialized
    )


def test_progress_artifact_policy_compiles_but_fails_admission_without_observer() -> None:
    _, package, registry, _ = baseline_specs()
    base_study = package.study
    policy = ProgressArtifactPolicyRevision(
        logical_id="subject-progress-summaries",
        revision=1,
        project_id=base_study.project_id,
        title="Periodic human-readable Subject progress",
        payload=ProgressArtifactPolicySpec(
            definitions=(
                ProgressArtifactDefinition(
                    id="every-five-subject-turns",
                    label="Every five completed Subject responses",
                    trigger=SubjectTurnIntervalProgressTrigger(every_n_turns=5),
                    summarizer_ref=capability_ref("evidrun.observer", "progress-summarizer"),
                ),
            ),
            limitations=("The summary is provisional and does not replace the Run ledger.",),
        ),
    )
    accept(registry, policy)
    study = StudyRevision(
        logical_id=base_study.logical_id,
        revision=2,
        project_id=base_study.project_id,
        title=base_study.title,
        payload=base_study.payload.model_copy(
            update={
                "run_blueprint": base_study.payload.run_blueprint.model_copy(
                    update={"progress_artifact_policy_ref": policy.ref}
                )
            }
        ),
    )
    accept(registry, study)

    specs = StudyCompiler(registry).compile(study)
    assert len(specs) == 2
    assert all(spec.progress_artifact_policy_ref == policy.ref for spec in specs)
    assert all(
        spec.progress_artifact_policy.definitions[0].trigger.kind == "subject_turn_interval"
        for spec in specs
        if spec.progress_artifact_policy is not None
    )
    definition = specs[0].progress_artifact_policy.definitions[0]
    assert definition.trigger.kind == "subject_turn_interval"
    assert definition.trigger.counted_event_type == "subject.responded"
    assert definition.input_scope == "complete_run_ledger_prefix"
    with pytest.raises(ValidationError):
        ProgressArtifactDefinition(
            id="unsafe-observer",
            label="Observer without isolation",
            trigger=SubjectTurnIntervalProgressTrigger(every_n_turns=1),
            summarizer_ref=capability_ref("evidrun.observer", "unsafe"),
            authority_constraints=(),
        )
    admission = scripted_service(specs[0].agent_inventory.runner_ref).admit(
        specs[0], unpersisted_unverified_trust(specs[0])
    )
    assert admission.decision == "rejected"
    assert "runtime:background_progress_observer" in admission.missing_requirements
    observer_issue = next(
        item for item in admission.issues if item.subject_ref == "background_progress_observer"
    )
    assert observer_issue.blocking is True
    with pytest.raises(ValueError, match="rejected admission"):
        SubjectEnvelopeCompiler.compile(
            specs[0],
            admission,
            materialized_inputs=materialized_subject_inputs(specs[0]),
        )


def test_progress_summary_is_provisional_evidence_cited_and_not_a_score() -> None:
    with pytest.raises(ValidationError, match="require evidence refs"):
        ProgressArtifactContent(
            run_id="run-progress",
            up_to_event_sequence=12,
            event_hash="a" * 64,
            title="Progress through Subject turn five",
            overview="The Subject inspected the authorized packet.",
            statements=(
                ProgressStatement(
                    id="inspection",
                    kind="observation",
                    text="The Subject inspected the packet.",
                ),
            ),
            limitations=("This is a lossy summary of the ledger prefix.",),
        )

    content = ProgressArtifactContent(
        run_id="run-progress",
        up_to_event_sequence=12,
        event_hash="a" * 64,
        title="Progress through Subject turn five",
        overview="The Subject inspected the authorized packet.",
        statements=(
            ProgressStatement(
                id="inspection",
                kind="observation",
                text="The Subject inspected the packet.",
                evidence_refs=(EvidenceRef(ref="event:evt_subject_response_5"),),
            ),
            ProgressStatement(
                id="unknown-cause",
                kind="uncertainty",
                text="No supported root cause has been established yet.",
            ),
        ),
        limitations=("This is a lossy summary of the ledger prefix.",),
    )
    document = content.model_dump(mode="json")
    assert content.status == "provisional"
    assert document["up_to_event_sequence"] == 12
    assert "score" not in document
    assert "goal_state" not in document
    assert "files_read" not in document
    assert "files_edited" not in document


def test_pre_run_evaluation_disclosure_is_minimal_and_explicit() -> None:
    manifest, package, registry, _ = baseline_specs()
    base_study = package.study
    base_plan = next(
        revision for revision in package.revisions if isinstance(revision, EvaluationPlanRevision)
    )
    public_dimension = base_plan.payload.dimensions[0]
    disclosed_plan = EvaluationPlanRevision(
        logical_id=base_plan.logical_id,
        revision=2,
        project_id=base_plan.project_id,
        title=base_plan.title,
        payload=base_plan.payload.model_copy(
            update={
                "disclosure": base_plan.payload.disclosure.model_copy(
                    update={
                        "subject": SubjectEvaluationDisclosure(
                            mode="pre_run",
                            dimension_ids=(public_dimension.id,),
                            include_scale=False,
                            include_anchors=False,
                        )
                    }
                )
            }
        ),
    )
    accept(registry, disclosed_plan)
    study = StudyRevision(
        logical_id=base_study.logical_id,
        revision=2,
        project_id=base_study.project_id,
        title=base_study.title,
        payload=base_study.payload.model_copy(
            update={
                "run_blueprint": base_study.payload.run_blueprint.model_copy(
                    update={"evaluation_plan_ref": disclosed_plan.ref}
                )
            }
        ),
    )
    accept(registry, study)
    spec = StudyCompiler(registry).compile(study)[0]
    service = scripted_service(spec.agent_inventory.runner_ref)
    admission = service.admit(spec, unpersisted_unverified_trust(spec))
    assert admission.decision == "rejected"
    missing = admission.missing_requirements
    assert "runtime:subject_evaluation_guidance_delivery" in missing
    base_spec = StudyCompiler(registry).compile(base_study)[0]
    base_admission = service.admit(base_spec, unpersisted_unverified_trust(base_spec))
    assert base_admission.decision == "admitted"
    # Exercise the pure envelope compiler as a future compatible runtime would.
    compatible_admission = base_admission.model_copy(
        update={
            "run_spec_ref": f"run-spec:{spec.digest}",
            "run_spec_digest": spec.digest,
        }
    )
    envelope = SubjectEnvelopeCompiler.compile(
        spec,
        compatible_admission,
        materialized_inputs=materialized_subject_inputs(spec),
    )
    assert envelope.evaluation_guidance is not None
    assert [item.id for item in envelope.evaluation_guidance.dimensions] == [public_dimension.id]
    guidance_json = envelope.evaluation_guidance.model_dump_json()
    assert "stages" not in guidance_json
    assert "evaluator_ref" not in guidance_json
    assert "parameters" not in guidance_json
    assert "hidden_input_refs" not in guidance_json
    assert manifest.graders[0].expected not in envelope.model_dump_json()


def test_terminal_payload_separates_goal_state_from_bounded_exploration() -> None:
    goal_state = normalize_event_payload(
        "run.completed",
        {
            "status": "completed",
            "goal_result": {"goal_mode": "goal_state", "state": "achieved"},
            "terminal_cause": "The declared observable outcome was produced.",
        },
    )
    assert goal_state["goal_result"] == {
        "goal_mode": "goal_state",
        "state": "achieved",
    }
    exploration = normalize_event_payload(
        "run.completed",
        {
            "status": "completed",
            "goal_result": {
                "goal_mode": "bounded_exploration",
                "disposition": "concluded",
                "stop_reason": "evidence_saturation",
                "stop_condition_kind": "bounded_exploration_complete",
                "evidence_refs": [{"ref": "event:evt_terminal"}],
            },
            "terminal_cause": "The bounded evidence search reached its stop policy.",
        },
    )
    assert exploration["goal_result"]["goal_mode"] == "bounded_exploration"
    assert "state" not in exploration["goal_result"]
    with pytest.raises(ValidationError):
        normalize_event_payload(
            "run.completed",
            {
                "status": "completed",
                "goal_result": {
                    "goal_mode": "bounded_exploration",
                    "state": "achieved",
                },
                "terminal_cause": "An exploration cannot claim Goal achievement.",
            },
        )


def test_trigger_and_stop_condition_references_are_not_ambiguous() -> None:
    with pytest.raises(ValidationError, match="event evaluation trigger requires"):
        EvaluationTrigger(kind="event")
    with pytest.raises(ValidationError, match="checkpoint evaluation trigger requires"):
        EvaluationTrigger(kind="checkpoint")
    with pytest.raises(ValidationError, match="cannot declare a reference"):
        EvaluationTrigger(kind="run_terminal", reference="subject.responded")

    predicate_ref = capability_ref("evidrun.predicate", "bounded-stop")
    with pytest.raises(ValidationError, match="requires a predicate_ref"):
        StopCondition(kind="predicate")
    with pytest.raises(ValidationError, match="only valid for predicate"):
        StopCondition(kind="goal_complete", predicate_ref=predicate_ref)

    assert EvaluationTrigger(kind="event", reference="subject.responded").reference == (
        "subject.responded"
    )
    assert StopCondition(kind="predicate", predicate_ref=predicate_ref).predicate_ref == (
        predicate_ref
    )
