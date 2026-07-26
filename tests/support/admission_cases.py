"""The admission oracle case matrix: one RunSpec per rejection branch.

Every case runs the production path `catalog.admission_service().admit(spec)`, so
both admission layers execute exactly as they do in a worker. Each case declares
which adapter pair the catalog must resolve.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel

from evidrun.contracts import capability_ref
from evidrun.contracts.authoring.checkpoint import (
    CheckpointCaptureSpec,
    CheckpointDefinition,
    CheckpointPolicySpec,
    ManualCheckpointTrigger,
)
from evidrun.contracts.authoring.evaluation import (
    AggregationSpec,
    BlindingPolicy,
    EvaluationDisclosure,
    EvaluationStage,
    EvaluationTrigger,
    HumanAdjudicationPolicy,
    SubjectEvaluationDisclosure,
)
from evidrun.contracts.authoring.goal import GoalOutcome
from evidrun.contracts.authoring.inventory import CapabilityRequirement, RuntimeRequirement
from evidrun.contracts.authoring.progress import (
    ProgressArtifactDefinition,
    ProgressArtifactPolicySpec,
    SubjectTurnIntervalProgressTrigger,
)
from evidrun.contracts.authoring.protocol import AlwaysTrigger, InteractionEdge, InteractionNode
from evidrun.contracts.authoring.run import StopCondition
from evidrun.contracts.authoring.workspace import (
    CleanupPolicy,
    ExternalEffectPolicy,
    NetworkPolicy,
    SecretBindingRef,
    SnapshotPolicy,
)
from evidrun.contracts.base import ArtifactRef, ContractType, ExtensionRef
from evidrun.contracts.runtime.spec import RunSpec
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.providers import ProviderProfile
from evidrun.runs.adapters import (
    ArtifactInputMaterializer,
    ReadArtifactTextToolAdapter,
    ResponsesReadAgentAdapter,
    RuntimeAdapterCatalog,
)
from evidrun.shared.types import Classification, sha256_bytes
from tests.support.admission_specs import (
    EXPECTED_CAUSE,
    ORACLE_LOG_BYTES,
    ORACLE_PROJECT_ID,
    build_real_run_spec,
    build_scripted_run_spec,
    contract_ref,
    oracle_profile,
)

CatalogKind = Literal[
    "scripted", "scripted_without_materializer", "real", "real_without_credential"
]

UNKNOWN_TOOL_REF = capability_ref("evidrun.tool", "unregistered-tool-v1")
UNKNOWN_EVALUATOR_REF = capability_ref("evidrun.evaluator", "unregistered-evaluator-v1")
ORACLE_SUMMARIZER_REF = capability_ref("evidrun.observer", "progress-summarizer")
ORACLE_VALIDATOR_REF = capability_ref("evidrun.checkpoint", "integrity")
ORACLE_PROJECTOR_REF = capability_ref("evidrun.evaluator", "mean-projector")
ORACLE_ADJUDICATOR_REF = capability_ref("evidrun.authority", "human-adjudicator")
ORACLE_VERIFIER_REF = capability_ref("evidrun.authority", "attestation-verifier")


class UnusedProvider:
    """Provider port proving admission never performs a provider call."""

    async def invoke(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        raise AssertionError("admission must not invoke the provider")


@dataclass(frozen=True)
class AdmissionCase:
    name: str
    catalog: CatalogKind
    spec: RunSpec


def build_catalogs(
    store: ArtifactStore, *, profile: ProviderProfile
) -> dict[CatalogKind, RuntimeAdapterCatalog]:
    """One catalog per adapter pair the oracle exercises."""

    materializer = ArtifactInputMaterializer(store)

    def project_id(spec: RunSpec) -> str:
        del spec
        return ORACLE_PROJECT_ID

    def real_subject(*, credential_available: bool) -> ResponsesReadAgentAdapter:
        return ResponsesReadAgentAdapter(
            UnusedProvider(), profile, credential_available=credential_available
        )

    return {
        "scripted": RuntimeAdapterCatalog(
            materializer=materializer, project_id_for_spec=project_id
        ),
        "scripted_without_materializer": RuntimeAdapterCatalog(),
        "real": RuntimeAdapterCatalog(
            real_subject=real_subject(credential_available=True),
            materializer=materializer,
            project_id_for_spec=project_id,
        ),
        "real_without_credential": RuntimeAdapterCatalog(
            real_subject=real_subject(credential_available=False),
            materializer=materializer,
            project_id_for_spec=project_id,
        ),
    }


def _respec(spec: RunSpec, **updates: object) -> RunSpec:
    """Rebuild the RunSpec through validation, keeping its own validators live."""

    return _revalidate(spec, updates)


def _rebind(spec: RunSpec, source: ArtifactRef) -> RunSpec:
    """Point the scenario binding and the workspace mount at one artifact."""

    binding = _revalidate(spec.scenario.input_bindings[0], {"source": source})
    mount = _revalidate(spec.workspace.mounts[0], {"source": source})
    return _respec(
        spec,
        scenario=_revalidate(spec.scenario, {"input_bindings": (binding,)}),
        workspace=_revalidate(spec.workspace, {"mounts": (mount,)}),
    )


def _revalidate[ModelT: BaseModel](model: ModelT, updates: Mapping[str, object]) -> ModelT:
    """Rebuild a model through validation, so a misspelled field fails loudly.

    `model_copy(update=...)` is documented as unvalidated: a typo like
    `runtime_knd` would silently attach an extra attribute, leave the real field
    untouched, and freeze an admitted baseline under a rejection case name.
    """

    document = model.model_dump(mode="python", exclude_computed_fields=True)
    return type(model).model_validate({**document, **updates})


def _with_workspace(spec: RunSpec, **updates: object) -> RunSpec:
    return _respec(spec, workspace=_revalidate(spec.workspace, updates))


def _with_inventory(spec: RunSpec, **updates: object) -> RunSpec:
    return _respec(spec, agent_inventory=_revalidate(spec.agent_inventory, updates))


def _with_interaction(spec: RunSpec, **updates: object) -> RunSpec:
    return _respec(
        spec, interaction_protocol=_revalidate(spec.interaction_protocol, updates)
    )


def _with_plan(spec: RunSpec, **updates: object) -> RunSpec:
    return _respec(spec, evaluation_plan=_revalidate(spec.evaluation_plan, updates))


def _with_budgets(spec: RunSpec, **updates: object) -> RunSpec:
    return _respec(spec, budgets=_revalidate(spec.budgets, updates))


def _with_capture(spec: RunSpec, **updates: object) -> RunSpec:
    return _respec(spec, capture_policy=_revalidate(spec.capture_policy, updates))


def _requirement(**updates: object) -> CapabilityRequirement:
    base = CapabilityRequirement(
        kind="tool",
        capability_ref=ReadArtifactTextToolAdapter.ref,
        required=True,
        minimum_interface_version="1",
        requested_permissions=(ReadArtifactTextToolAdapter.allowed_permission,),
        exposure="schema_only",
        authority_constraints=(ReadArtifactTextToolAdapter.authority_constraint,),
    )
    return _revalidate(base, updates)


def _extension() -> ExtensionRef:
    payload = ArtifactRef(
        artifact_id="oracle-extension-payload",
        digest=sha256_bytes(b"oracle extension payload"),
        media_type="application/json",
    )
    return ExtensionRef(
        namespace="oracle.extension",
        slot="analysis",
        schema_ref=ArtifactRef(
            artifact_id="oracle-extension-schema",
            digest=sha256_bytes(b"oracle extension schema"),
            media_type="application/schema+json",
        ),
        schema_version="1",
        payload_ref=payload,
        digest=payload.digest,
        classification=payload.classification,
    )


def _read_write_mount(spec: RunSpec) -> RunSpec:
    binding = spec.scenario.input_bindings[0].model_copy(
        update={"mount_access": "read_write"}
    )
    mount = spec.workspace.mounts[0].model_copy(update={"access": "read_write"})
    return spec.model_copy(
        update={
            "scenario": spec.scenario.model_copy(update={"input_bindings": (binding,)}),
            "workspace": spec.workspace.model_copy(update={"mounts": (mount,)}),
        }
    )


def _second_scenario_input(spec: RunSpec) -> RunSpec:
    extra = spec.scenario.input_bindings[0].model_copy(
        update={
            "id": "oracle-laboratory-note",
            "role": "laboratory_note",
            "visibility": "laboratory",
            "mount_name": None,
        }
    )
    return spec.model_copy(
        update={
            "scenario": spec.scenario.model_copy(
                update={"input_bindings": (spec.scenario.input_bindings[0], extra)}
            )
        }
    )


def _with_progress_policy(spec: RunSpec) -> RunSpec:
    return spec.model_copy(
        update={
            "progress_artifact_policy_ref": contract_ref(
                ContractType.PROGRESS_ARTIFACT_POLICY, "oracle-progress"
            ),
            "progress_artifact_policy": ProgressArtifactPolicySpec(
                definitions=(
                    ProgressArtifactDefinition(
                        id="every-five-subject-turns",
                        label="Every five completed Subject responses",
                        trigger=SubjectTurnIntervalProgressTrigger(every_n_turns=5),
                        summarizer_ref=ORACLE_SUMMARIZER_REF,
                    ),
                ),
                limitations=("O resumo e provisorio e nao substitui o ledger.",),
            ),
        }
    )


def _with_checkpoint_policy(spec: RunSpec) -> RunSpec:
    return spec.model_copy(
        update={
            "checkpoint_policy_ref": contract_ref(
                ContractType.CHECKPOINT_POLICY, "oracle-checkpoints"
            ),
            "checkpoint_policy": CheckpointPolicySpec(
                definitions=(
                    CheckpointDefinition(
                        id="phase-1",
                        label="Phase 1",
                        order=1,
                        trigger=ManualCheckpointTrigger(),
                        validator_refs=(ORACLE_VALIDATOR_REF,),
                        capture=CheckpointCaptureSpec(context_snapshot=True),
                        required=True,
                    ),
                )
            ),
        }
    )


def _bounded_exploration(spec: RunSpec) -> RunSpec:
    return spec.model_copy(
        update={
            "goal": spec.goal.model_copy(
                update={
                    "mode": "bounded_exploration",
                    "outcomes": (
                        GoalOutcome(
                            id="explored",
                            description="Registrar o que foi explorado sem veredito.",
                        ),
                    ),
                }
            ),
            "stop_conditions": (
                StopCondition(kind="bounded_exploration_complete"),
                StopCondition(kind="budget_exhausted"),
            ),
        }
    )


def _graph_interaction(spec: RunSpec) -> RunSpec:
    return _with_interaction(
        spec,
        mode="graph",
        nodes=(
            InteractionNode(id="brief", kind="prompt"),
            InteractionNode(id="terminal", kind="terminal"),
        ),
        edges=(
            InteractionEdge(source="brief", target="terminal", trigger=AlwaysTrigger()),
        ),
    )


def _scripted_specs(spec: RunSpec, source: ArtifactRef) -> list[tuple[str, RunSpec]]:
    stage = spec.evaluation_plan.stages[0]
    return [
        ("scripted_baseline_admitted", spec),
        (
            "runner_digest_mismatch",
            _with_inventory(
                spec,
                runner_ref=spec.agent_inventory.runner_ref.model_copy(
                    update={"digest": "0" * 64}
                ),
            ),
        ),
        (
            "runner_unregistered",
            _with_inventory(
                spec, runner_ref=capability_ref("evidrun.runner", "ghost-runner-v1")
            ),
        ),
        (
            "provider_profile_unavailable",
            _with_inventory(spec, provider_profile_id="ghost-profile"),
        ),
        (
            "required_capability_unregistered",
            _with_inventory(
                spec, capability_requirements=(_requirement(capability_ref=UNKNOWN_TOOL_REF),)
            ),
        ),
        (
            "optional_capability_unregistered",
            _with_inventory(
                spec,
                capability_requirements=(
                    _requirement(capability_ref=UNKNOWN_TOOL_REF, required=False),
                ),
            ),
        ),
        (
            "required_runtime_capability_missing",
            _with_inventory(
                spec,
                runtime_requirements=(
                    RuntimeRequirement(capability="nested_agents", required=True),
                ),
            ),
        ),
        (
            "optional_runtime_capability_missing",
            _with_inventory(
                spec,
                runtime_requirements=(
                    RuntimeRequirement(capability="nested_agents", required=False),
                ),
            ),
        ),
        (
            "sensitive_input_classification",
            _rebind(
                spec, source.model_copy(update={"classification": Classification.SENSITIVE})
            ),
        ),
        (
            "restricted_input_classification",
            _rebind(
                spec, source.model_copy(update={"classification": Classification.RESTRICTED})
            ),
        ),
        ("workspace_runtime_kind_unsupported", _with_workspace(spec, runtime_kind="container")),
        (
            "workspace_mount_authority_mismatch",
            _with_workspace(
                spec,
                mounts=(spec.workspace.mounts[0].model_copy(update={"name": "unbound-mount"}),),
            ),
        ),
        ("workspace_read_write_mount", _read_write_mount(spec)),
        ("workspace_write_zones", _with_workspace(spec, write_zones=("subject-output",))),
        (
            "workspace_secret_bindings",
            _with_workspace(
                spec,
                secret_binding_refs=(
                    SecretBindingRef(binding_id="provider-token", source="keychain"),
                ),
            ),
        ),
        (
            "workspace_snapshot_capture",
            _with_workspace(spec, snapshot_policy=SnapshotPolicy(capture_workspace=True)),
        ),
        (
            "workspace_cleanup_retain",
            _with_workspace(spec, cleanup_policy=CleanupPolicy(mode="retain")),
        ),
        (
            "network_allowlist_denied",
            _with_workspace(
                spec,
                network_policy=NetworkPolicy(
                    mode="allowlist", allowed_endpoint_refs=("endpoint:oracle",)
                ),
            ),
        ),
        (
            "external_effect_approval_required",
            _with_workspace(
                spec, external_effect_policy=ExternalEffectPolicy(mode="approval_required")
            ),
        ),
        ("interaction_graph_unsupported", _graph_interaction(spec)),
        ("interaction_max_turns_two", _with_interaction(spec, max_turns=2)),
        (
            "interaction_system_prompt_materialized",
            _with_interaction(
                spec,
                system_prompt_ref=ArtifactRef(
                    artifact_id="oracle-system-prompt",
                    digest=sha256_bytes(b"oracle system prompt"),
                    media_type="text/plain",
                ),
            ),
        ),
        ("capture_raw_encrypted_denied", _with_capture(spec, default_mode="raw_encrypted")),
        ("progress_artifact_policy_present", _with_progress_policy(spec)),
        ("checkpoint_policy_present", _with_checkpoint_policy(spec)),
        ("bounded_exploration_goal", _bounded_exploration(spec)),
        (
            "evaluation_two_stages",
            _with_plan(
                spec,
                stages=(
                    stage,
                    stage.model_copy(update={"id": "oracle-second-stage", "hard_gate": True}),
                ),
            ),
        ),
        (
            "evaluation_stage_not_boolean_event",
            _with_plan(
                spec,
                stages=(
                    EvaluationStage(
                        id="oracle-run-terminal-stage",
                        kind="model_judge",
                        evaluator_ref=UNKNOWN_EVALUATOR_REF,
                        trigger=EvaluationTrigger(kind="run_terminal"),
                        output_dimensions=("root-cause-grounded",),
                    ),
                ),
            ),
        ),
        (
            "human_adjudication_required",
            _with_plan(
                spec,
                human_adjudication_policy=HumanAdjudicationPolicy(
                    required=True,
                    adjudicator_ref=ORACLE_ADJUDICATOR_REF,
                    adjudicable_stage_ids=(stage.id,),
                    attestation_verifier_ref=ORACLE_VERIFIER_REF,
                ),
            ),
        ),
        (
            "subject_disclosure_pre_run",
            _with_plan(
                spec,
                disclosure=EvaluationDisclosure(
                    subject=SubjectEvaluationDisclosure(
                        mode="pre_run", dimension_ids=("root-cause-grounded",)
                    )
                ),
            ),
        ),
        (
            "evaluation_hidden_inputs",
            _with_plan(spec, disclosure=EvaluationDisclosure(hidden_input_refs=(source,))),
        ),
        (
            "evaluation_blinding_fields",
            _with_plan(spec, blinding_policy=BlindingPolicy(hidden_fields=("goal",))),
        ),
        (
            "evaluation_aggregation",
            _with_plan(spec, aggregation=AggregationSpec(projector_ref=ORACLE_PROJECTOR_REF)),
        ),
        (
            "evaluator_adapter_unknown",
            _with_plan(
                spec, stages=(stage.model_copy(update={"evaluator_ref": UNKNOWN_EVALUATOR_REF}),)
            ),
        ),
        ("budget_max_input_tokens", _with_budgets(spec, max_input_tokens=1024)),
        ("budget_max_output_tokens", _with_budgets(spec, max_output_tokens=512)),
        ("budget_max_tool_calls", _with_budgets(spec, max_tool_calls=4)),
        ("budget_max_cost", _with_budgets(spec, max_cost=1.5)),
        ("budget_max_turns_two", _with_budgets(spec, max_turns=2)),
        (
            "stop_condition_pause_action",
            spec.model_copy(
                update={
                    "stop_conditions": (
                        StopCondition(kind="goal_complete"),
                        StopCondition(kind="budget_exhausted"),
                        StopCondition(kind="human_stop", action="pause"),
                    )
                }
            ),
        ),
        (
            "stop_condition_without_budget_exhausted",
            spec.model_copy(
                update={"stop_conditions": (StopCondition(kind="goal_complete"),)}
            ),
        ),
        ("scenario_two_inputs", _second_scenario_input(spec)),
        (
            "subject_input_media_type_json",
            _rebind(spec, source.model_copy(update={"media_type": "application/json"})),
        ),
        (
            "subject_input_absent_from_store",
            _rebind(
                spec,
                ArtifactRef(
                    artifact_id="oracle-never-stored",
                    digest=sha256_bytes(b"oracle never stored"),
                    media_type="text/plain",
                ),
            ),
        ),
        ("context_policy_absent", spec.model_copy(update={"context_policy": None})),
        (
            "runtime_extensions_present",
            spec.model_copy(update={"extensions": (_extension(),)}),
        ),
    ]


def _real_specs(spec: RunSpec, source: ArtifactRef) -> list[tuple[str, CatalogKind, RunSpec]]:
    stage = spec.evaluation_plan.stages[0]
    return [
        ("real_baseline_admitted", "real", spec),
        ("real_credential_unavailable", "real_without_credential", spec),
        (
            "real_capability_interface_version_unsupported",
            "real",
            _with_inventory(
                spec, capability_requirements=(_requirement(minimum_interface_version="2"),)
            ),
        ),
        (
            "real_capability_permission_denied",
            "real",
            _with_inventory(
                spec,
                capability_requirements=(
                    _requirement(requested_permissions=("write:subject_artifacts",)),
                ),
            ),
        ),
        (
            "real_capability_authority_denied",
            "real",
            _with_inventory(
                spec,
                capability_requirements=(
                    _requirement(authority_constraints=("unbounded-filesystem",)),
                ),
            ),
        ),
        (
            "real_optional_capability_interface_warning",
            "real",
            _with_inventory(
                spec,
                capability_requirements=(
                    _requirement(minimum_interface_version="2", required=False),
                ),
            ),
        ),
        (
            "real_optional_capability_permission_warning",
            "real",
            _with_inventory(
                spec,
                capability_requirements=(
                    _requirement(
                        requested_permissions=("write:subject_artifacts",), required=False
                    ),
                ),
            ),
        ),
        (
            "real_optional_capability_authority_warning",
            "real",
            _with_inventory(
                spec,
                capability_requirements=(
                    _requirement(
                        authority_constraints=("unbounded-filesystem",), required=False
                    ),
                ),
            ),
        ),
        (
            "real_provider_profile_mismatch",
            "real",
            _with_inventory(spec, provider_profile_id="ghost-profile"),
        ),
        (
            "real_instruction_refs_present",
            "real",
            _with_inventory(
                spec,
                capability_requirements=(
                    _requirement(
                        exposure="instructions_and_schema", instruction_refs=(source,)
                    ),
                ),
            ),
        ),
        ("real_tool_budget_absent", "real", _with_budgets(spec, max_tool_calls=None)),
        ("real_tool_budget_too_high", "real", _with_budgets(spec, max_tool_calls=9)),
        (
            "real_network_disabled",
            "real",
            _with_workspace(spec, network_policy=NetworkPolicy(mode="disabled")),
        ),
        (
            "real_capture_not_recoverable",
            "real",
            _with_capture(spec, default_mode="redacted", raw_sensitive="disabled"),
        ),
        (
            "real_evaluator_unknown",
            "real",
            _with_plan(
                spec, stages=(stage.model_copy(update={"evaluator_ref": UNKNOWN_EVALUATOR_REF}),)
            ),
        ),
    ]


def build_admission_cases(store: ArtifactStore) -> tuple[AdmissionCase, ...]:
    """Store the shared source artifacts and materialize every oracle case."""

    scripted_source = store.put_ref(
        ORACLE_LOG_BYTES,
        project_id=ORACLE_PROJECT_ID,
        media_type="text/plain",
        classification=Classification.INTERNAL,
    )
    real_memo = (
        "1 incident memo for the admission oracle\n"
        f"2 ROOT_CAUSE_CODE={EXPECTED_CAUSE} confirmed\n"
    )
    real_source = store.put_ref(
        real_memo.encode("utf-8"),
        project_id=ORACLE_PROJECT_ID,
        media_type="text/plain",
        classification=Classification.INTERNAL,
    )
    scripted = build_scripted_run_spec(source=scripted_source)
    real = build_real_run_spec(source=real_source, profile=oracle_profile())
    cases = [
        AdmissionCase(name=name, catalog="scripted", spec=case)
        for name, case in _scripted_specs(scripted, scripted_source)
    ]
    cases.append(
        AdmissionCase(
            name="subject_input_materializer_absent",
            catalog="scripted_without_materializer",
            spec=scripted,
        )
    )
    cases.extend(
        AdmissionCase(name=name, catalog=catalog, spec=case)
        for name, catalog, case in _real_specs(real, real_source)
    )
    return tuple(cases)
