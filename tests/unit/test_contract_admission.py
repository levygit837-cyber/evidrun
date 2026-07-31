"""Admission outcomes: comparison rules, capabilities, providers and unsupported runtime."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from evidrun.contracts import (
    AgentInventoryRevision,
    ArtifactRef,
    BudgetSpec,
    CapturePolicySpec,
    CheckpointDefinition,
    CheckpointPolicyRevision,
    CheckpointPolicySpec,
    InteractionProtocolRevision,
    InteractionProtocolSpec,
    StudyRevision,
)
from evidrun.contracts.admission import (
    CapabilityCatalogEntry,
    ProviderCatalogEntry,
)
from evidrun.contracts.authoring.checkpoint import CheckpointCaptureSpec, ManualCheckpointTrigger
from evidrun.contracts.authoring.inventory import CapabilityRequirement, RuntimeRequirement
from evidrun.contracts.authoring.protocol import AlwaysTrigger, InteractionEdge, InteractionNode
from evidrun.contracts.authoring.run import StopCondition
from evidrun.contracts.compiler import (
    StudyCompiler,
    SubjectEnvelopeCompiler,
)
from evidrun.contracts.legacy import (
    capability_ref,
)
from evidrun.contracts.triage import TriageErrorCode, TriageRejected
from evidrun.shared.types import (
    Classification,
    EvidenceMode,
    sha256_bytes,
    sha256_json,
)
from tests.support.admission_specs import (
    declared_admission_service as declared_service,
)
from tests.support.admission_specs import (
    scripted_admission_service as scripted_service,
)
from tests.support.contract_fixtures import (
    accept,
    baseline_specs,
    legacy_package,
    materialized_subject_inputs,
)
from tests.support.execution_trust import unpersisted_unverified_trust


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
    with pytest.raises(TriageRejected) as captured:
        StudyCompiler(registry).compile(changed)
    assert captured.value.error.code == TriageErrorCode.COMPILE_CONTROLLED_SLOTS_MISMATCH


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
    with pytest.raises(TriageRejected) as captured:
        StudyCompiler(registry).compile(unexplained)
    assert captured.value.error.code == TriageErrorCode.COMPILE_CONFOUNDER_MISSING


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
    service = scripted_service(baseline.agent_inventory.runner_ref)

    rejected = service.admit(required_spec, unpersisted_unverified_trust(required_spec))
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
    admitted = service.admit(optional_spec, unpersisted_unverified_trust(optional_spec))
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
    service = declared_service(
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
    admission = service.admit(spec, unpersisted_unverified_trust(spec))
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
    instructions_admission = service.admit(
        instructions_spec, unpersisted_unverified_trust(instructions_spec)
    )
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
            "agent_inventory": agent.model_copy(update={"capability_requirements": (excessive,)})
        }
    )
    denied = service.admit(denied_spec, unpersisted_unverified_trust(denied_spec))
    assert denied.decision == "rejected"
    assert denied.resolved_inventory.capabilities[0].status == "denied"
    assert denied.resolved_inventory.capabilities[0].effective_permissions == ()

    incompatible = requirement.model_copy(update={"minimum_interface_version": "2"})
    incompatible_spec = baseline.model_copy(
        update={
            "agent_inventory": agent.model_copy(update={"capability_requirements": (incompatible,)})
        }
    )
    incompatible_admission = service.admit(
        incompatible_spec, unpersisted_unverified_trust(incompatible_spec)
    )
    assert incompatible_admission.decision == "rejected"
    assert incompatible_admission.resolved_inventory.capabilities[0].status == "unsupported"

    unconstrained_service = declared_service(
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
    authority_denied = unconstrained_service.admit(spec, unpersisted_unverified_trust(spec))
    assert authority_denied.decision == "rejected"
    assert authority_denied.resolved_inventory.capabilities[0].status == "denied"


def test_nested_agent_graph_and_checkpoints_compile_but_admission_rejects_runtime() -> None:
    _, package, registry, _ = baseline_specs()
    base_study = package.study
    base_agent = next(
        revision for revision in package.revisions if isinstance(revision, AgentInventoryRevision)
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
        len(spec.checkpoint_policy.definitions) == 4 for spec in specs if spec.checkpoint_policy
    )
    for spec in specs:
        admission = scripted_service(spec.agent_inventory.runner_ref).admit(
            spec, unpersisted_unverified_trust(spec)
        )
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
    service = scripted_service(baseline.agent_inventory.runner_ref)

    writable = baseline.model_copy(
        update={
            "workspace": baseline.workspace.model_copy(update={"write_zones": ("subject-output",)})
        }
    )
    assert service.admit(writable, unpersisted_unverified_trust(writable)).decision == "rejected"

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
    assert (
        service.admit(prompted, unpersisted_unverified_trust(prompted)).interaction_status
        == "unsupported"
    )

    raw_capture = baseline.model_copy(
        update={
            "capture_policy": CapturePolicySpec(
                default_mode="raw_encrypted", raw_sensitive="opt_in"
            )
        }
    )
    rejected_capture = service.admit(raw_capture, unpersisted_unverified_trust(raw_capture))
    assert rejected_capture.decision == "rejected"
    assert "capture:raw_encrypted" in rejected_capture.denied_policies

    token_budget = baseline.model_copy(
        update={"budgets": baseline.budgets.model_copy(update={"max_output_tokens": 100})}
    )
    token_budget_admission = service.admit(token_budget, unpersisted_unverified_trust(token_budget))
    assert token_budget_admission.decision == "rejected"
    assert "runtime:budget:max_output_tokens" in (token_budget_admission.missing_requirements)

    unsupported_stop = baseline.model_copy(
        update={
            "stop_conditions": (
                *baseline.stop_conditions,
                StopCondition(kind="human_stop", action="pause"),
            )
        }
    )
    stop_admission = service.admit(unsupported_stop, unpersisted_unverified_trust(unsupported_stop))
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
    restricted_mount = baseline.workspace.mounts[0].model_copy(update={"source": restricted_source})
    restricted_workspace = baseline.workspace.model_copy(update={"mounts": (restricted_mount,)})
    restricted_spec = baseline.model_copy(
        update={
            "scenario": restricted_scenario,
            "workspace": restricted_workspace,
        }
    )
    restricted_admission = service.admit(
        restricted_spec, unpersisted_unverified_trust(restricted_spec)
    )
    assert restricted_admission.decision == "rejected"
    assert "classification:restricted" in restricted_admission.denied_policies
