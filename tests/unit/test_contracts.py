from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from evidrun.contracts import (
    AgentInventoryRevision,
    ArtifactRef,
    BudgetSpec,
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
    InteractionProtocolRevision,
    RevisionDecisionRecord,
    RevisionEnvelope,
    RunSpec,
    StudyRevision,
    VariantSpec,
    WorkspaceTemplateRevision,
    normalize_event_payload,
    semantic_model_dump,
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
    RunBlueprint,
    RuntimeRequirement,
    StudyIntent,
    StudySpec,
)
from evidrun.contracts.base import ContractModel
from evidrun.contracts.compiler import (
    AdmissionService,
    CapabilityCatalogEntry,
    EvaluatorEnvelopeCompiler,
    ExtensionSchemaRegistry,
    InMemoryContractRegistry,
    ProviderCatalogEntry,
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
)
from evidrun.experiments import ExperimentManifest
from evidrun.shared.types import EvidenceMode, sha256_bytes, sha256_json, utc_now

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
    registry = InMemoryContractRegistry()
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


def accept(registry: InMemoryContractRegistry, revision: RevisionEnvelope) -> None:
    registry.add(revision)
    registry.decide(
        RevisionDecisionRecord(
            revision_ref=revision.ref,
            decision="accepted",
            actor_id="test-human",
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


def test_revision_decisions_require_human_actor_and_monotonic_revision() -> None:
    _, package = legacy_package()
    with pytest.raises(ValidationError):
        RevisionDecisionRecord.model_validate(
            {
                "revision_ref": package.study.ref.model_dump(mode="json"),
                "decision": "accepted",
                "actor_type": "lab_agent",
                "actor_id": "lab",
                "rationale": "A Lab Agent cannot accept its own draft.",
                "decided_at_utc": utc_now().isoformat(),
            }
        )

    skipped = package.study.model_copy(update={"revision": 3})
    registry = InMemoryContractRegistry()
    registry.add(package.study)
    with pytest.raises(ValueError, match="monotonic"):
        registry.add(skipped)


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


def test_legacy_study_compiles_two_specs_and_hides_laboratory_data() -> None:
    manifest, _, _, specs = baseline_specs()
    assert {spec.variant_id for spec in specs} == {"head-truncation", "tail-preservation"}
    assert all(spec.repetition_index == 1 for spec in specs)

    admission_service = AdmissionService(
        runners=(capability_ref("evidrun.runner", "scripted-log-investigator-v1"),)
    )
    baseline = next(spec for spec in specs if spec.variant_id == manifest.baseline_variant)
    admission = admission_service.admit(baseline)
    envelope = SubjectEnvelopeCompiler.compile(baseline, admission)
    serialized = envelope.model_dump_json()

    assert admission.decision == "admitted"
    assert manifest.hypothesis not in serialized
    assert manifest.graders[0].expected not in serialized
    assert "evaluation_plan" not in serialized
    assert "provider_profile_id" not in serialized
    evaluator = EvaluatorEnvelopeCompiler.compile(
        baseline, baseline.evaluation_plan.stages[0].id
    )
    evaluator_serialized = evaluator.model_dump_json()
    assert manifest.graders[0].expected in evaluator_serialized
    assert manifest.hypothesis not in evaluator_serialized


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
    service = AdmissionService(runners=(baseline.agent_inventory.runner_ref,))

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
    envelope = SubjectEnvelopeCompiler.compile(optional_spec, admitted)
    assert envelope.effective_capabilities == ()


def test_admission_records_exact_capability_permissions_and_provider_resolution() -> None:
    _, _, _, specs = baseline_specs()
    baseline = specs[0]
    tool_ref = capability_ref("example.tool", "read-only-repository")
    requirement = CapabilityRequirement(
        kind="tool",
        capability_ref=tool_ref,
        required=True,
        minimum_interface_version="1",
        requested_permissions=("read",),
        exposure="schema_only",
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
    service = AdmissionService(
        runners=(baseline.agent_inventory.runner_ref,),
        capabilities=(
            CapabilityCatalogEntry(
                ref=tool_ref,
                adapter="test-read-adapter@1",
                allowed_permissions=frozenset({"read"}),
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
    assert set(resolved.effective_permissions).issubset(requirement.requested_permissions)
    assert admission.resolved_inventory.provider_profile_digest == provider_digest
    assert admission.resolved_inventory.provider_adapter == "openai-responses@1"
    assert "api_key" not in admission.model_dump_json()

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
        admission = AdmissionService(runners=(spec.agent_inventory.runner_ref,)).admit(spec)
        assert admission.decision == "rejected"
        assert admission.interaction_status == "unsupported"
        assert "runtime:nested_agents" in admission.missing_requirements
        assert {item.status for item in admission.resolved_inventory.capabilities} == {
            "unsupported"
        }


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
            human_adjudication_policy=HumanAdjudicationPolicy(required=True),
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
    admission = AdmissionService(runners=(specs[0].agent_inventory.runner_ref,)).admit(specs[0])
    envelope = SubjectEnvelopeCompiler.compile(specs[0], admission)
    assert "hidden-calibration" not in envelope.model_dump_json()


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
def test_contract_refs_reject_a_mismatched_digest(payload: bytes) -> None:
    _, package, registry, _ = baseline_specs()
    wrong_digest = sha256_bytes(payload)
    if wrong_digest == package.study.digest:
        return
    wrong_ref = package.study.ref.model_copy(update={"digest": wrong_digest})
    with pytest.raises(ValueError, match="digest mismatch"):
        registry.resolve(wrong_ref)


@given(repetitions=st.integers(min_value=1, max_value=4), variants=st.integers(1, 4))
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
def test_canonical_digest_is_independent_of_mapping_order(values: dict[str, int]) -> None:
    reversed_values = dict(reversed(tuple(values.items())))
    assert sha256_json(values) == sha256_json(reversed_values)
