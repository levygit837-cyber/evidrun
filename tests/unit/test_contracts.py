from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from evidrun.contracts import (
    AdjudicatesEvaluationRelation,
    AgentInventoryRevision,
    ArtifactRef,
    BudgetSpec,
    CapturePolicySpec,
    CheckpointPolicyRevision,
    CheckpointRecord,
    ContractRef,
    ContractType,
    EvaluationRecord,
    EvaluationValidator,
    EvidenceRef,
    ExtensionRef,
    GoalRevision,
    GoalSpec,
    HumanAttestationRecord,
    InputBinding,
    InteractionProtocolRevision,
    ProgressArtifactContent,
    ProgressArtifactPolicyRevision,
    RepositoryFixtureDecisionAuthority,
    RevisionDecisionRecord,
    RevisionEnvelope,
    RunSpec,
    StudyRevision,
    VariantSpec,
    VerifiedHumanDecisionAuthority,
    WorkspaceTemplateRevision,
    normalize_event_payload,
    semantic_model_dump,
)
from evidrun.contracts.admission import (
    CapabilityCatalogEntry,
    ProviderCatalogEntry,
)
from evidrun.contracts.authoring import (
    AlwaysTrigger,
    CapabilityRequirement,
    CheckpointCaptureSpec,
    CheckpointDefinition,
    CheckpointPolicySpec,
    EvaluationDimension,
    EvaluationDisclosure,
    EvaluationPlanRevision,
    EvaluationPlanSpec,
    EvaluationStage,
    EvaluationTrigger,
    HumanAdjudicationPolicy,
    InteractionEdge,
    InteractionNode,
    InteractionProtocolSpec,
    ManualCheckpointTrigger,
    ProgressArtifactDefinition,
    ProgressArtifactPolicySpec,
    RunBlueprint,
    RuntimeRequirement,
    StopCondition,
    StudyIntent,
    StudySpec,
    SubjectEvaluationDisclosure,
    SubjectTurnIntervalProgressTrigger,
)
from evidrun.contracts.authority import HumanAttestationUnavailable
from evidrun.contracts.base import ContractModel
from evidrun.contracts.compiler import (
    EvaluatorEnvelopeCompiler,
    ExtensionSchemaRegistry,
    InMemoryContractRegistry,
    StudyCompiler,
    SubjectEnvelopeCompiler,
)
from evidrun.contracts.legacy import (
    ExperimentManifestV1Adapter,
    LegacyStudyPackage,
    capability_ref,
)
from evidrun.contracts.runtime import (
    CheckpointValidation,
    DimensionValue,
    EvaluationBoundary,
    ProgressStatement,
)
from evidrun.experiments import ExperimentManifest
from evidrun.shared.types import (
    Classification,
    EvidenceMode,
    sha256_bytes,
    sha256_json,
    utc_now,
)
from tests.support import admission_specs

_declared_service = admission_specs.declared_admission_service
_scripted_service = admission_specs.scripted_admission_service

ROOT = Path(__file__).resolve().parents[2]


def legacy_package() -> tuple[ExperimentManifest, LegacyStudyPackage]:
    manifest_path = ROOT / "benchmarks/experiments/crl-ctx-002-demo.yaml"
    fixture_path = ROOT / "benchmarks/scenarios/crl-ctx-002/fixtures/long.log"
    manifest = ExperimentManifest.model_validate(yaml.safe_load(manifest_path.read_text()))
    package = ExperimentManifestV1Adapter().convert(
        manifest,
        project_id="project-contract-tests",
        fixture_path=fixture_path,
    )
    return manifest, package


def accepted_registry(package: LegacyStudyPackage) -> InMemoryContractRegistry:
    revisions = package.revisions
    decisions = package.acceptance_decisions()
    registry = InMemoryContractRegistry(allow_repository_fixture=True)
    for revision in revisions:
        registry.add(revision)
    for decision in decisions:
        registry.decide(decision)
    return registry


def baseline_specs() -> tuple[
    ExperimentManifest,
    LegacyStudyPackage,
    InMemoryContractRegistry,
    tuple[RunSpec, ...],
]:
    manifest, package = legacy_package()
    registry = accepted_registry(package)
    specs = StudyCompiler(registry).compile(package.study)
    return manifest, package, registry, specs


def materialized_subject_inputs(spec: RunSpec) -> tuple[InputBinding, ...]:
    return tuple(
        item.model_copy(
            update={
                "source": item.source.model_copy(
                    update={
                        "artifact_id": f"context-snapshot:{item.id}",
                        "digest": sha256_bytes(f"materialized:{item.id}".encode()),
                    }
                )
            }
        )
        for item in spec.scenario.input_bindings
        if item.visibility in {"subject", "subject_and_evaluator"}
    )


def accept(registry: InMemoryContractRegistry, revision: RevisionEnvelope) -> None:
    registry.add(revision)
    registry.decide(
        RevisionDecisionRecord(
            revision_ref=revision.ref,
            decision="accepted",
            authority=RepositoryFixtureDecisionAuthority(
                fixture_digest=sha256_json(revision.ref.model_dump(mode="json")),
            ),
            rationale="Accepted by the contract test fixture.",
            decided_at_utc=utc_now(),
        )
    )


def test_revision_is_closed_immutable_and_has_stable_digest() -> None:
    _, package = legacy_package()
    study = package.study
    copy = StudyRevision.model_validate(study.semantic_document())
    assert copy.digest == study.digest
    with pytest.raises(ValidationError):
        StudyRevision.model_validate({**study.semantic_document(), "unexpected": True})
    with pytest.raises(ValidationError):
        study.title = "mutated"  # type: ignore[misc]


def test_all_core_contract_models_are_closed_and_frozen() -> None:
    pending = list(ContractModel.__subclasses__())
    models: set[type[ContractModel]] = set()
    while pending:
        model = pending.pop()
        if model in models:
            continue
        models.add(model)
        pending.extend(model.__subclasses__())
    assert models
    for model in models:
        assert model.model_config.get("extra") == "forbid"
        assert model.model_config.get("frozen") is True


def test_semantic_serialization_omits_absent_modules_and_digest_excludes_metadata() -> None:
    _, package = legacy_package()
    original = package.study
    document = original.semantic_document()
    assert "decision_to_inform" not in document["payload"]["intent"]
    assert "assumptions" not in document["payload"]["intent"]
    assert "checkpoint_policy_ref" not in document["payload"]["run_blueprint"]
    assert "digest" not in document

    renamed = original.model_copy(update={"title": "A storage-only title change"})
    assert renamed.digest == original.digest
    registry = InMemoryContractRegistry()
    registry.add(original)
    with pytest.raises(ValueError, match="immutable"):
        registry.add(renamed)


def test_revision_decisions_reject_unverified_human_claim_and_require_monotonic_revision() -> None:
    _, package = legacy_package()
    with pytest.raises(ValidationError):
        RevisionDecisionRecord.model_validate(
            {
                "revision_ref": package.study.ref.model_dump(mode="json"),
                "decision": "accepted",
                "authority": {"kind": "verified_human", "principal_id": "lab"},
                "rationale": "A Lab Agent cannot accept its own draft.",
                "decided_at_utc": utc_now().isoformat(),
            }
        )

    skipped = package.study.model_copy(update={"revision": 3})
    registry = InMemoryContractRegistry()
    registry.add(package.study)
    with pytest.raises(ValueError, match="monotonic"):
        registry.add(skipped)


def test_structurally_valid_human_decision_fails_closed_without_verifier() -> None:
    _, package = legacy_package()
    revision = package.study
    rationale = "I reviewed the exact revision content."
    decided_at = utc_now()
    subject_digest = sha256_json(
        {
            "revision_ref": revision.ref.model_dump(mode="json"),
            "decision": "accepted",
            "rationale": rationale,
        }
    )
    attestation = HumanAttestationRecord(
        attestation_id="human-attestation-test",
        principal_id="test-principal",
        credential_id="credential-test",
        action="revision.accepted",
        target_digest=revision.digest,
        subject_digest=subject_digest,
        challenge_digest="a" * 64,
        assertion_ref=ArtifactRef(
            artifact_id="webauthn-assertion-test",
            digest="b" * 64,
            media_type="application/webauthn+json",
        ),
        relying_party_id="evidrun.local",
        origin="https://evidrun.local",
        verifier_ref=capability_ref("evidrun.authority", "webauthn"),
        verified_at_utc=decided_at,
    )
    decision = RevisionDecisionRecord(
        revision_ref=revision.ref,
        decision="accepted",
        authority=VerifiedHumanDecisionAuthority(
            principal_id="test-principal", attestation=attestation
        ),
        rationale=rationale,
        decided_at_utc=decided_at,
    )
    registry = InMemoryContractRegistry()
    registry.add(revision)
    with pytest.raises(HumanAttestationUnavailable, match="no trusted verifier"):
        registry.decide(decision)

    fixture_registry = InMemoryContractRegistry()
    fixture_registry.add(revision)
    fixture_decision = next(
        item
        for item in package.acceptance_decisions()
        if item.revision_ref == revision.ref
    )
    with pytest.raises(PermissionError, match="legacy import path"):
        fixture_registry.decide(fixture_decision)


def test_reference_slots_and_extension_identity_are_validated() -> None:
    _, package = legacy_package()
    wrong_goal_ref = package.study.payload.scenario_refs[0]
    with pytest.raises(ValidationError, match="wrong contract type"):
        type(package.study.payload).model_validate(
            {
                **semantic_model_dump(package.study.payload),
                "goal_ref": wrong_goal_ref.model_dump(mode="json"),
            }
        )

    schema = ArtifactRef(
        artifact_id="extension-schema",
        digest="a" * 64,
        media_type="application/schema+json",
    )
    payload = ArtifactRef(
        artifact_id="extension-payload",
        digest="b" * 64,
        media_type="application/json",
    )
    with pytest.raises(ValidationError, match="digest must match"):
        ExtensionRef(
            namespace="example.extension",
            slot="analysis",
            schema_ref=schema,
            schema_version="1",
            payload_ref=payload,
            digest="c" * 64,
            classification=payload.classification,
        )
    with pytest.raises(ValidationError, match="Extra inputs"):
        ArtifactRef.model_validate(
            {
                "artifact_id": "storage-coupled-ref",
                "digest": "d" * 64,
                "media_type": "text/plain",
                "locator": "/private/laboratory/hidden.txt",
            }
        )


def test_legacy_study_compiles_two_specs_and_hides_laboratory_data() -> None:
    manifest, _, _, specs = baseline_specs()
    assert {spec.variant_id for spec in specs} == {"head-truncation", "tail-preservation"}
    assert all(spec.repetition_index == 1 for spec in specs)

    admission_service = _scripted_service(
        capability_ref("evidrun.runner", "scripted-log-investigator-v1")
    )
    baseline = next(spec for spec in specs if spec.variant_id == manifest.baseline_variant)
    admission = admission_service.admit(baseline)
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
    evaluator = EvaluatorEnvelopeCompiler.compile(
        baseline, baseline.evaluation_plan.stages[0].id
    )
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
                    summarizer_ref=capability_ref(
                        "evidrun.observer", "progress-summarizer"
                    ),
                ),
            ),
            limitations=(
                "The summary is provisional and does not replace the Run ledger.",
            ),
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
        spec.progress_artifact_policy.definitions[0].trigger.kind
        == "subject_turn_interval"
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
    admission = _scripted_service(specs[0].agent_inventory.runner_ref).admit(specs[0])
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
        revision
        for revision in package.revisions
        if isinstance(revision, EvaluationPlanRevision)
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
    service = _scripted_service(spec.agent_inventory.runner_ref)
    admission = service.admit(spec)
    assert admission.decision == "rejected"
    missing = admission.missing_requirements
    assert "runtime:subject_evaluation_guidance_delivery" in missing
    base_spec = StudyCompiler(registry).compile(base_study)[0]
    base_admission = service.admit(base_spec)
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
    assert [item.id for item in envelope.evaluation_guidance.dimensions] == [
        public_dimension.id
    ]
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


def test_controlled_comparison_rejects_an_unexplained_second_change() -> None:
    _, package, registry, _ = baseline_specs()
    study = package.study
    variants = list(study.payload.variants)
    candidate = variants[1]
    variants[1] = candidate.model_copy(
        update={
            "overrides": candidate.overrides.model_copy(
                update={"budgets": BudgetSpec(max_wall_seconds=99, max_turns=1)}
            )
        }
    )
    changed = StudyRevision(
        logical_id=study.logical_id,
        revision=2,
        project_id=study.project_id,
        title=study.title,
        payload=study.payload.model_copy(update={"variants": tuple(variants)}),
    )
    accept(registry, changed)
    with pytest.raises(ValueError, match="exactly its primary variable"):
        StudyCompiler(registry).compile(changed)


def test_exploratory_comparison_requires_declared_confounders_for_extra_differences() -> None:
    _, package, registry, _ = baseline_specs()
    study = package.study
    variants = list(study.payload.variants)
    candidate = variants[1]
    variants[1] = candidate.model_copy(
        update={
            "overrides": candidate.overrides.model_copy(
                update={"budgets": BudgetSpec(max_wall_seconds=99, max_turns=1)}
            ),
            "confounders": ("The execution budget also changed.",),
        }
    )
    explained = StudyRevision(
        logical_id=study.logical_id,
        revision=2,
        project_id=study.project_id,
        title=study.title,
        payload=study.payload.model_copy(
            update={
                "evidence_mode": EvidenceMode.EXPLORATORY,
                "variants": tuple(variants),
            }
        ),
    )
    accept(registry, explained)
    assert len(StudyCompiler(registry).compile(explained)) == 2

    variants[1] = variants[1].model_copy(update={"confounders": ()})
    unexplained = StudyRevision(
        logical_id=study.logical_id,
        revision=3,
        project_id=study.project_id,
        title=study.title,
        payload=explained.payload.model_copy(update={"variants": tuple(variants)}),
    )
    accept(registry, unexplained)
    with pytest.raises(ValueError, match="declare confounders"):
        StudyCompiler(registry).compile(unexplained)


def test_confounders_are_rejected_outside_exploratory_studies() -> None:
    _, package = legacy_package()
    document = package.study.semantic_document()
    payload = document["payload"]
    assert isinstance(payload, dict)
    payload["evidence_mode"] = EvidenceMode.RETROSPECTIVE_OBSERVATIONAL.value
    variants = payload["variants"]
    assert isinstance(variants, list)
    variants[0]["confounders"] = ["A known environment difference."]

    with pytest.raises(ValidationError, match="only valid in exploratory"):
        StudyRevision.model_validate(document)


def test_required_and_optional_capabilities_have_different_admission_results() -> None:
    _, _, _, specs = baseline_specs()
    baseline = specs[0]
    unavailable = capability_ref("example.tool", "repository-write")
    required_requirement = CapabilityRequirement(
        kind="tool",
        capability_ref=unavailable,
        required=True,
        minimum_interface_version="1",
        requested_permissions=("write",),
        exposure="schema_only",
    )
    required_agent = baseline.agent_inventory.model_copy(
        update={"capability_requirements": (required_requirement,)}
    )
    required_spec = baseline.model_copy(update={"agent_inventory": required_agent})
    service = _scripted_service(baseline.agent_inventory.runner_ref)

    rejected = service.admit(required_spec)
    assert rejected.decision == "rejected"
    assert rejected.resolved_inventory.capabilities[0].status == "unsupported"

    optional_requirement = required_requirement.model_copy(update={"required": False})
    optional_spec = baseline.model_copy(
        update={
            "agent_inventory": required_agent.model_copy(
                update={"capability_requirements": (optional_requirement,)}
            )
        }
    )
    admitted = service.admit(optional_spec)
    assert admitted.decision == "admitted"
    assert admitted.warnings
    envelope = SubjectEnvelopeCompiler.compile(
        optional_spec,
        admitted,
        materialized_inputs=materialized_subject_inputs(optional_spec),
    )
    assert envelope.effective_capabilities == ()


def test_admission_records_exact_capability_permissions_and_provider_resolution() -> None:
    _, _, _, specs = baseline_specs()
    baseline = specs[0]
    tool_ref = capability_ref("example.tool", "read-only-repository")
    instruction_ref = ArtifactRef(
        artifact_id="tool-instructions",
        digest=sha256_bytes(b"instructions that schema-only exposure must hide"),
        media_type="text/markdown",
    )
    requirement = CapabilityRequirement(
        kind="tool",
        capability_ref=tool_ref,
        required=True,
        minimum_interface_version="1",
        requested_permissions=("read",),
        exposure="schema_only",
        instruction_refs=(instruction_ref,),
        authority_constraints=("no-write",),
    )
    agent = baseline.agent_inventory.model_copy(
        update={
            "provider_profile_id": "test-provider",
            "capability_requirements": (requirement,),
        }
    )
    spec = baseline.model_copy(update={"agent_inventory": agent})
    provider_digest = sha256_json(
        {"id": "test-provider", "model": "test-model", "reasoning": "max"}
    )
    service = _declared_service(
        baseline.agent_inventory.runner_ref,
        capabilities=(
            CapabilityCatalogEntry(
                ref=tool_ref,
                adapter="test-read-adapter@1",
                allowed_permissions=frozenset({"read"}),
                compatible_interface_versions=frozenset({"1"}),
                satisfied_authority_constraints=frozenset({"no-write"}),
            ),
        ),
        providers=(
            ProviderCatalogEntry(
                profile_id="test-provider",
                profile_digest=provider_digest,
                model="test-model",
                reasoning_effort="max",
                adapter="openai-responses@1",
            ),
        ),
    )
    admission = service.admit(spec)
    resolved = admission.resolved_inventory.capabilities[0]
    assert admission.decision == "admitted"
    assert resolved.resolved_ref == tool_ref
    assert resolved.adapter == "test-read-adapter@1"
    assert resolved.effective_permissions == ("read",)
    assert resolved.effective_interface_version == "1"
    assert resolved.satisfied_authority_constraints == ("no-write",)
    assert resolved.context_refs == ()
    assert set(resolved.effective_permissions).issubset(requirement.requested_permissions)
    assert admission.resolved_inventory.provider_profile_digest == provider_digest
    assert admission.resolved_inventory.provider_adapter == "openai-responses@1"
    assert "api_key" not in admission.model_dump_json()
    assert "locator" not in admission.model_dump_json()

    instructions_requirement = requirement.model_copy(update={"exposure": "instructions"})
    instructions_spec = baseline.model_copy(
        update={
            "agent_inventory": agent.model_copy(
                update={"capability_requirements": (instructions_requirement,)}
            )
        }
    )
    instructions_admission = service.admit(instructions_spec)
    assert instructions_admission.decision == "admitted"
    assert instructions_admission.resolved_inventory.capabilities[0].context_refs == (
        instruction_ref,
    )
    instructions_envelope = SubjectEnvelopeCompiler.compile(
        instructions_spec,
        instructions_admission,
        materialized_inputs=materialized_subject_inputs(instructions_spec),
    )
    assert "locator" not in instructions_envelope.model_dump_json()

    excessive = requirement.model_copy(update={"requested_permissions": ("read", "write")})
    denied_spec = baseline.model_copy(
        update={
            "agent_inventory": agent.model_copy(
                update={"capability_requirements": (excessive,)}
            )
        }
    )
    denied = service.admit(denied_spec)
    assert denied.decision == "rejected"
    assert denied.resolved_inventory.capabilities[0].status == "denied"
    assert denied.resolved_inventory.capabilities[0].effective_permissions == ()

    incompatible = requirement.model_copy(update={"minimum_interface_version": "2"})
    incompatible_spec = baseline.model_copy(
        update={
            "agent_inventory": agent.model_copy(
                update={"capability_requirements": (incompatible,)}
            )
        }
    )
    incompatible_admission = service.admit(incompatible_spec)
    assert incompatible_admission.decision == "rejected"
    assert incompatible_admission.resolved_inventory.capabilities[0].status == "unsupported"

    unconstrained_service = _declared_service(
        baseline.agent_inventory.runner_ref,
        capabilities=(
            CapabilityCatalogEntry(
                ref=tool_ref,
                adapter="test-read-adapter@1",
                allowed_permissions=frozenset({"read"}),
                compatible_interface_versions=frozenset({"1"}),
            ),
        ),
        providers=service.envelope.providers.values(),
    )
    authority_denied = unconstrained_service.admit(spec)
    assert authority_denied.decision == "rejected"
    assert authority_denied.resolved_inventory.capabilities[0].status == "denied"


def test_nested_agent_graph_and_checkpoints_compile_but_admission_rejects_runtime() -> None:
    _, package, registry, _ = baseline_specs()
    base_study = package.study
    base_agent = next(
        revision
        for revision in package.revisions
        if isinstance(revision, AgentInventoryRevision)
    )
    tool = CapabilityRequirement(
        kind="tool",
        capability_ref=capability_ref("example.tool", "agent-builder"),
        minimum_interface_version="1",
        requested_permissions=("workspace.write",),
        exposure="schema_only",
    )
    skill = CapabilityRequirement(
        kind="skill",
        capability_ref=capability_ref("example.skill", "agent-design"),
        minimum_interface_version="1",
        exposure="instructions",
    )
    nested_agent = AgentInventoryRevision(
        logical_id="nested-agent-inventory",
        revision=1,
        project_id=base_study.project_id,
        title="Nested-agent inventory",
        payload=base_agent.payload.model_copy(
            update={
                "capability_requirements": (tool, skill),
                "runtime_requirements": (
                    RuntimeRequirement(capability="nested_agents", required=True),
                ),
            }
        ),
    )
    graph = InteractionProtocolRevision(
        logical_id="nested-agent-protocol",
        revision=1,
        project_id=base_study.project_id,
        title="Nested-agent graph",
        payload=InteractionProtocolSpec(
            mode="graph",
            max_turns=4,
            nodes=(
                InteractionNode(id="brief", kind="prompt"),
                InteractionNode(id="terminal", kind="terminal"),
            ),
            edges=(
                InteractionEdge(
                    source="brief",
                    target="terminal",
                    trigger=AlwaysTrigger(),
                ),
            ),
        ),
    )
    validator_ref = capability_ref("evidrun.checkpoint", "integrity")
    checkpoints = CheckpointPolicyRevision(
        logical_id="nested-agent-checkpoints",
        revision=1,
        project_id=base_study.project_id,
        title="Nested-agent checkpoints",
        payload=CheckpointPolicySpec(
            definitions=tuple(
                CheckpointDefinition(
                    id=f"phase-{index}",
                    label=f"Phase {index}",
                    order=index,
                    trigger=ManualCheckpointTrigger(),
                    validator_refs=(validator_ref,),
                    capture=CheckpointCaptureSpec(
                        context_snapshot=True,
                        artifact_manifest=True,
                        agent_inventory=True,
                    ),
                    required=True,
                )
                for index in range(1, 5)
            )
        ),
    )
    for revision in (nested_agent, graph, checkpoints):
        accept(registry, revision)
    blueprint = base_study.payload.run_blueprint.model_copy(
        update={
            "agent_inventory_ref": nested_agent.ref,
            "interaction_protocol_ref": graph.ref,
            "checkpoint_policy_ref": checkpoints.ref,
        }
    )
    study = StudyRevision(
        logical_id=base_study.logical_id,
        revision=2,
        project_id=base_study.project_id,
        title="Nested-agent builder dossier",
        payload=base_study.payload.model_copy(update={"run_blueprint": blueprint}),
    )
    accept(registry, study)

    specs = StudyCompiler(registry).compile(study)
    assert len(specs) == 2
    assert all(spec.checkpoint_policy is not None for spec in specs)
    assert all(
        len(spec.checkpoint_policy.definitions) == 4
        for spec in specs
        if spec.checkpoint_policy
    )
    for spec in specs:
        admission = _scripted_service(spec.agent_inventory.runner_ref).admit(spec)
        assert admission.decision == "rejected"
        assert admission.interaction_status == "unsupported"
        assert "runtime:nested_agents" in admission.missing_requirements
        assert "runtime:checkpoint_coordinator" in admission.missing_requirements
        assert {item.status for item in admission.resolved_inventory.capabilities} == {
            "unsupported"
        }


def test_admission_rejects_workspace_interaction_and_capture_features_not_executed() -> None:
    _, _, _, specs = baseline_specs()
    baseline = specs[0]
    service = _scripted_service(baseline.agent_inventory.runner_ref)

    writable = baseline.model_copy(
        update={
            "workspace": baseline.workspace.model_copy(
                update={"write_zones": ("subject-output",)}
            )
        }
    )
    assert service.admit(writable).decision == "rejected"

    prompt_ref = ArtifactRef(
        artifact_id="system-prompt",
        digest=sha256_bytes(b"system prompt"),
        media_type="text/plain",
    )
    prompted = baseline.model_copy(
        update={
            "interaction_protocol": baseline.interaction_protocol.model_copy(
                update={"system_prompt_ref": prompt_ref}
            )
        }
    )
    assert service.admit(prompted).interaction_status == "unsupported"

    raw_capture = baseline.model_copy(
        update={
            "capture_policy": CapturePolicySpec(
                default_mode="raw_encrypted", raw_sensitive="opt_in"
            )
        }
    )
    rejected_capture = service.admit(raw_capture)
    assert rejected_capture.decision == "rejected"
    assert "capture:raw_encrypted" in rejected_capture.denied_policies

    token_budget = baseline.model_copy(
        update={
            "budgets": baseline.budgets.model_copy(update={"max_output_tokens": 100})
        }
    )
    token_budget_admission = service.admit(token_budget)
    assert token_budget_admission.decision == "rejected"
    assert "runtime:budget:max_output_tokens" in (
        token_budget_admission.missing_requirements
    )

    unsupported_stop = baseline.model_copy(
        update={
            "stop_conditions": (
                *baseline.stop_conditions,
                StopCondition(kind="human_stop", action="pause"),
            )
        }
    )
    stop_admission = service.admit(unsupported_stop)
    assert stop_admission.decision == "rejected"
    assert "runtime:stop_condition_coordinator" in stop_admission.missing_requirements

    restricted_source = baseline.scenario.input_bindings[0].source.model_copy(
        update={"classification": Classification.RESTRICTED}
    )
    restricted_binding = baseline.scenario.input_bindings[0].model_copy(
        update={"source": restricted_source}
    )
    restricted_scenario = baseline.scenario.model_copy(
        update={"input_bindings": (restricted_binding,)}
    )
    restricted_mount = baseline.workspace.mounts[0].model_copy(
        update={"source": restricted_source}
    )
    restricted_workspace = baseline.workspace.model_copy(
        update={"mounts": (restricted_mount,)}
    )
    restricted_spec = baseline.model_copy(
        update={
            "scenario": restricted_scenario,
            "workspace": restricted_workspace,
        }
    )
    restricted_admission = service.admit(restricted_spec)
    assert restricted_admission.decision == "rejected"
    assert "classification:restricted" in restricted_admission.denied_policies


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
    admission = _scripted_service(specs[0].agent_inventory.runner_ref).admit(specs[0])
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


def test_secret_bindings_cannot_carry_credential_values() -> None:
    _, package = legacy_package()
    workspace = next(
        revision
        for revision in package.revisions
        if isinstance(revision, WorkspaceTemplateRevision)
    )
    document = workspace.payload.model_dump(mode="json")
    document["secret_binding_refs"] = [
        {
            "binding_id": "cliproxyapi-local",
            "source": "keychain",
            "value": "must-never-enter-a-contract",
        }
    ]
    with pytest.raises(ValidationError, match="Extra inputs"):
        type(workspace.payload).model_validate(document)


@given(st.binary(min_size=1, max_size=32))
@settings(deadline=None)
def test_contract_refs_reject_a_mismatched_digest(payload: bytes) -> None:
    _, package, registry, _ = baseline_specs()
    wrong_digest = sha256_bytes(payload)
    if wrong_digest == package.study.digest:
        return
    wrong_ref = package.study.ref.model_copy(update={"digest": wrong_digest})
    with pytest.raises(ValueError, match="digest mismatch"):
        registry.resolve(wrong_ref)


@given(repetitions=st.integers(min_value=1, max_value=4), variants=st.integers(1, 4))
@settings(deadline=None)
def test_study_matrix_size_is_deterministic(repetitions: int, variants: int) -> None:
    _, package, registry, _ = baseline_specs()
    study = StudyRevision(
        logical_id=package.study.logical_id,
        revision=2,
        project_id=package.study.project_id,
        title="Property-based Study matrix",
        payload=package.study.payload.model_copy(
            update={
                "evidence_mode": EvidenceMode.EXPLORATORY,
                "variants": tuple(
                    VariantSpec(id=f"variant-{index}", label=f"Variant {index}")
                    for index in range(variants)
                ),
                "repetitions": repetitions,
                "comparisons": (),
            }
        ),
    )
    accept(registry, study)
    specs = StudyCompiler(registry).compile(study)
    assert len(specs) == variants * repetitions * len(study.payload.scenario_refs)
    coordinates = {
        (spec.scenario_ref.logical_id, spec.variant_id, spec.repetition_index)
        for spec in specs
    }
    assert len(coordinates) == len(specs)


@given(st.dictionaries(st.text(min_size=1, max_size=8), st.integers(), max_size=12))
@settings(deadline=None)
def test_canonical_digest_is_independent_of_mapping_order(values: dict[str, int]) -> None:
    reversed_values = dict(reversed(tuple(values.items())))
    assert sha256_json(values) == sha256_json(reversed_values)
