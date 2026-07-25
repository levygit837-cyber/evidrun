"""RunSpec fixtures and the admission fingerprint used by the equivalence oracle.

The fingerprint freezes the observable admission surface: decision, statuses,
`missing_requirements`, `denied_policies`, warnings, resolved inventory, and the
exact `(category, subject_ref, reason.code, reason.detail, blocking)` tuple of
every issue. A refactor of either admission layer must not change one character.
"""

from __future__ import annotations

from collections.abc import Iterable

from evidrun.contracts.admission import (
    AdmissionService,
    CapabilityCatalogEntry,
    ProviderCatalogEntry,
    RuntimeCapabilityEnvelope,
)
from evidrun.contracts.authoring import (
    AgentInventorySpec,
    BudgetSpec,
    CapabilityRequirement,
    CapturePolicySpec,
    EvaluationDimension,
    EvaluationPlanSpec,
    EvaluationStage,
    EvaluationTrigger,
    ExternalEffectPolicy,
    GoalOutcome,
    GoalSpec,
    InputBinding,
    InteractionProtocolSpec,
    NetworkPolicy,
    RuntimeRequirement,
    ScenarioSpec,
    StopCondition,
    WorkspaceMount,
    WorkspaceTemplateSpec,
)
from evidrun.contracts.base import (
    ArtifactRef,
    CapabilityDescriptorRef,
    ContractRef,
    ContractType,
    KeyValue,
)
from evidrun.contracts.runtime import AdmissionRecord, RunSpec
from evidrun.experiments.models import ContextPolicySpec
from evidrun.providers import ProviderProfile
from evidrun.runs.adapters import (
    ExactReadAnswerGraderAdapter,
    ReadArtifactTextToolAdapter,
    ResponsesReadAgentAdapter,
)
from evidrun.shared.capabilities import capability_ref
from evidrun.shared.types import sha256_json

SCRIPTED_RUNNER_REF = capability_ref("evidrun.runner", "scripted-log-investigator-v1")
LEGACY_EVALUATOR_REF = capability_ref("evidrun.evaluator", "exact-root-cause-legacy-v1")
ORACLE_PROJECT_ID = "oracle-project"
EXPECTED_CAUSE = "SEARCH_INDEX_LAG"
SCRIPTED_INPUT_ID = "search-incident-log"
REAL_INPUT_ID = "incident-memo"

ORACLE_LOG_BYTES = (
    b"2026-07-23T10:00:00Z search replica healthy\n"
    b"2026-07-23T10:00:01Z queue delay rising\n"
    b"2026-07-23T10:00:02Z ROOT_CAUSE=SEARCH_INDEX_LAG\n"
)


def oracle_profile() -> ProviderProfile:
    """A local-only profile that never reaches a network during admission."""

    return ProviderProfile(
        id="oracle-responses-local",
        display_name="Oracle Responses provider",
        api="openai_responses",
        base_url="http://127.0.0.1:9/v1",
        model="oracle-read-agent-v1",
        reasoning_effort="max",
        local_only=True,
        credential_service="tests.evidrun.providers",
    )


def contract_ref(contract_type: ContractType, logical_id: str) -> ContractRef:
    """Build a deterministic, content-addressed slot reference for a fixture."""

    return ContractRef(
        contract_type=contract_type,
        logical_id=logical_id,
        revision=1,
        digest=sha256_json(
            {"contract_type": contract_type.value, "logical_id": logical_id}
        ),
    )


def _goal() -> GoalSpec:
    return GoalSpec(
        mode="goal_state",
        instruction="Identifique a causa-raiz usando somente o registro autorizado.",
        outcomes=(
            GoalOutcome(
                id="root-cause",
                description="Emitir uma causa-raiz terminal apoiada pelo registro.",
            ),
        ),
    )


def build_scripted_run_spec(*, source: ArtifactRef) -> RunSpec:
    """The exact RunSpec shape the scripted adapter pair admits, nothing extra."""

    return RunSpec(
        study_ref=contract_ref(ContractType.STUDY, "oracle-study"),
        scenario_ref=contract_ref(ContractType.SCENARIO, "oracle-scenario"),
        variant_id="oracle-baseline",
        repetition_index=1,
        seed=0,
        goal_ref=contract_ref(ContractType.GOAL, "oracle-goal"),
        goal=_goal(),
        scenario=ScenarioSpec(
            description="Registro sintetico criado exclusivamente para o oraculo.",
            input_bindings=(
                InputBinding(
                    id=SCRIPTED_INPUT_ID,
                    role="source_log",
                    source=source,
                    visibility="subject_and_evaluator",
                    mount_name=SCRIPTED_INPUT_ID,
                ),
            ),
            provenance=("tests/support/admission_specs.py",),
        ),
        agent_inventory_ref=contract_ref(ContractType.AGENT_INVENTORY, "oracle-agent"),
        agent_inventory=AgentInventorySpec(
            subject_id="oracle-scripted-subject",
            runner_ref=SCRIPTED_RUNNER_REF,
        ),
        workspace_template_ref=contract_ref(
            ContractType.WORKSPACE_TEMPLATE, "oracle-workspace"
        ),
        workspace=WorkspaceTemplateSpec(
            runtime_kind="in_process",
            mounts=(
                WorkspaceMount(
                    name=SCRIPTED_INPUT_ID,
                    source=source,
                    access="read_only",
                    target="context-source",
                ),
            ),
            network_policy=NetworkPolicy(mode="disabled"),
            external_effect_policy=ExternalEffectPolicy(mode="denied"),
        ),
        interaction_protocol_ref=contract_ref(
            ContractType.INTERACTION_PROTOCOL, "oracle-interaction"
        ),
        interaction_protocol=InteractionProtocolSpec(mode="single_turn", max_turns=1),
        evaluation_plan_ref=contract_ref(
            ContractType.EVALUATION_PLAN, "oracle-evaluation"
        ),
        evaluation_plan=EvaluationPlanSpec(
            dimensions=(
                EvaluationDimension(
                    id="root-cause-grounded",
                    description="A causa esperada aparece na resposta e na evidencia.",
                    value_type="boolean",
                ),
            ),
            stages=(
                EvaluationStage(
                    id="oracle-exact-cause-v1",
                    kind="deterministic_grader",
                    evaluator_ref=LEGACY_EVALUATOR_REF,
                    trigger=EvaluationTrigger(
                        kind="event", reference="subject.responded"
                    ),
                    output_dimensions=("root-cause-grounded",),
                    parameters=(KeyValue(key="expected", value=EXPECTED_CAUSE),),
                ),
            ),
        ),
        context_policy=ContextPolicySpec(
            id="oracle-full-context-v1", strategy="full", max_chars=4096
        ),
        budgets=BudgetSpec(max_wall_seconds=5, max_turns=1),
        stop_conditions=(
            StopCondition(kind="goal_complete"),
            StopCondition(kind="budget_exhausted"),
        ),
        capture_policy=CapturePolicySpec(
            default_mode="redacted", raw_sensitive="disabled"
        ),
    )


def build_real_run_spec(*, source: ArtifactRef, profile: ProviderProfile) -> RunSpec:
    """The exact RunSpec shape the provider/tool adapter pair admits."""

    return RunSpec(
        study_ref=contract_ref(ContractType.STUDY, "oracle-real-study"),
        scenario_ref=contract_ref(ContractType.SCENARIO, "oracle-real-scenario"),
        variant_id="oracle-real-baseline",
        repetition_index=1,
        seed=0,
        goal_ref=contract_ref(ContractType.GOAL, "oracle-real-goal"),
        goal=_goal(),
        scenario=ScenarioSpec(
            description="Memo sintetico usado apenas pelo oraculo de admissao.",
            input_bindings=(
                InputBinding(
                    id=REAL_INPUT_ID,
                    role="authorized_knowledge",
                    source=source,
                    visibility="subject_and_evaluator",
                    mount_name=REAL_INPUT_ID,
                ),
            ),
            provenance=("tests/support/admission_specs.py",),
        ),
        agent_inventory_ref=contract_ref(
            ContractType.AGENT_INVENTORY, "oracle-real-agent"
        ),
        agent_inventory=AgentInventorySpec(
            subject_id="oracle-real-subject",
            runner_ref=ResponsesReadAgentAdapter.ref,
            provider_profile_id=profile.id,
            capability_requirements=(
                CapabilityRequirement(
                    kind="tool",
                    capability_ref=ReadArtifactTextToolAdapter.ref,
                    required=True,
                    minimum_interface_version="1",
                    requested_permissions=(
                        ReadArtifactTextToolAdapter.allowed_permission,
                    ),
                    exposure="schema_only",
                    authority_constraints=(
                        ReadArtifactTextToolAdapter.authority_constraint,
                    ),
                ),
            ),
            runtime_requirements=(
                RuntimeRequirement(capability="provider_tool_loop", required=True),
            ),
        ),
        workspace_template_ref=contract_ref(
            ContractType.WORKSPACE_TEMPLATE, "oracle-real-workspace"
        ),
        workspace=WorkspaceTemplateSpec(
            runtime_kind="in_process",
            mounts=(
                WorkspaceMount(
                    name=REAL_INPUT_ID,
                    source=source,
                    access="read_only",
                    target="subject-envelope-input",
                ),
            ),
            network_policy=NetworkPolicy(mode="provider_only"),
            external_effect_policy=ExternalEffectPolicy(mode="denied"),
        ),
        interaction_protocol_ref=contract_ref(
            ContractType.INTERACTION_PROTOCOL, "oracle-real-interaction"
        ),
        interaction_protocol=InteractionProtocolSpec(mode="single_turn", max_turns=1),
        evaluation_plan_ref=contract_ref(
            ContractType.EVALUATION_PLAN, "oracle-real-evaluation"
        ),
        evaluation_plan=EvaluationPlanSpec(
            dimensions=(
                EvaluationDimension(
                    id="exact-grounded-answer",
                    description="Resposta exata e linha citada presente na tool.",
                    value_type="boolean",
                ),
            ),
            stages=(
                EvaluationStage(
                    id="oracle-exact-grounded-read-v1",
                    kind="deterministic_grader",
                    evaluator_ref=ExactReadAnswerGraderAdapter.ref,
                    trigger=EvaluationTrigger(
                        kind="event", reference="subject.responded"
                    ),
                    output_dimensions=("exact-grounded-answer",),
                    hard_gate=True,
                    parameters=(KeyValue(key="expected", value=EXPECTED_CAUSE),),
                ),
            ),
        ),
        context_policy=ContextPolicySpec(
            id="oracle-real-context-v1", strategy="full", max_chars=16_384
        ),
        budgets=BudgetSpec(max_wall_seconds=120, max_turns=1, max_tool_calls=2),
        stop_conditions=(
            StopCondition(kind="goal_complete"),
            StopCondition(kind="budget_exhausted"),
        ),
        capture_policy=CapturePolicySpec(
            default_mode="raw_encrypted", raw_sensitive="opt_in", sensitive_ttl_days=7
        ),
    )


def admission_fingerprint(record: AdmissionRecord) -> tuple[str, ...]:
    """Render every observable admission field as an order-preserving line set."""

    inventory = record.resolved_inventory
    lines: list[str] = [
        f"decision={record.decision}",
        f"workspace_status={record.workspace_status}",
        f"interaction_status={record.interaction_status}",
        f"runner={inventory.runner_ref.name}@{inventory.runner_ref.version}",
        f"provider_profile_id={inventory.provider_profile_id or ''}",
        f"provider_model={inventory.provider_model or ''}",
        f"provider_adapter={inventory.provider_adapter or ''}",
    ]
    lines.extend(f"missing={item}" for item in record.missing_requirements)
    lines.extend(f"denied={item}" for item in record.denied_policies)
    for issue in record.issues:
        lines.append(
            f"issue={issue.category}|{issue.subject_ref}|{issue.reason.code}"
            f"|{issue.reason.detail}|blocking={issue.blocking}"
        )
    lines.extend(f"warning={item}" for item in record.warnings)
    for capability in inventory.capabilities:
        reason = capability.reason
        lines.append(
            f"capability={capability.kind}|{capability.requested_ref.name}"
            f"|required={capability.required}|{capability.status}"
            f"|{'' if reason is None else reason.code}"
            f"|{'' if reason is None else reason.detail}"
        )
    lines.extend(
        f"runtime_capability={item}" for item in inventory.runtime_capabilities
    )
    return tuple(lines)


def scripted_admission_service(
    runner_ref: CapabilityDescriptorRef,
) -> AdmissionService:
    """An envelope declaring only one offline runner, as the default runtime does."""

    return AdmissionService(
        envelope=RuntimeCapabilityEnvelope.declare(runners=(runner_ref,))
    )


def declared_admission_service(
    runner_ref: CapabilityDescriptorRef,
    *,
    capabilities: Iterable[CapabilityCatalogEntry] = (),
    providers: Iterable[ProviderCatalogEntry] = (),
) -> AdmissionService:
    """An envelope that also declares tool and provider entries."""

    return AdmissionService(
        envelope=RuntimeCapabilityEnvelope.declare(
            runners=(runner_ref,), capabilities=capabilities, providers=providers
        )
    )
