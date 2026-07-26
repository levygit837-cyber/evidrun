from __future__ import annotations

from evidrun.contracts import ArtifactRef, RevisionEnvelope
from evidrun.contracts.authoring.evaluation import (
    EvaluationDimension,
    EvaluationPlanRevision,
    EvaluationPlanSpec,
    EvaluationStage,
    EvaluationTrigger,
)
from evidrun.contracts.authoring.goal import GoalOutcome, GoalRevision, GoalSpec
from evidrun.contracts.authoring.inventory import (
    AgentInventoryRevision,
    AgentInventorySpec,
    CapabilityRequirement,
    RuntimeRequirement,
)
from evidrun.contracts.authoring.protocol import (
    InteractionProtocolRevision,
    InteractionProtocolSpec,
)
from evidrun.contracts.authoring.run import (
    BudgetSpec,
    CapturePolicySpec,
    RunBlueprint,
    StopCondition,
)
from evidrun.contracts.authoring.scenario import InputBinding, ScenarioRevision, ScenarioSpec
from evidrun.contracts.authoring.study import StudyRevision, StudySpec
from evidrun.contracts.authoring.study_intent import StudyIntent
from evidrun.contracts.authoring.workspace import (
    ExternalEffectPolicy,
    NetworkPolicy,
    WorkspaceMount,
    WorkspaceTemplateRevision,
    WorkspaceTemplateSpec,
)
from evidrun.contracts.base import KeyValue
from evidrun.experiments.models import ContextPolicySpec
from evidrun.providers import ProviderProfile
from evidrun.runs.adapters import (
    ExactReadAnswerGraderAdapter,
    ReadArtifactTextToolAdapter,
    ResponsesReadAgentAdapter,
)
from evidrun.shared.types import EvidenceMode


def build_live_read_study(
    *,
    project_id: str,
    source: ArtifactRef,
    expected: str,
    profile: ProviderProfile,
) -> tuple[tuple[RevisionEnvelope, ...], StudyRevision]:
    """Create a fresh tool-grounded Study without any legacy benchmark adapter."""

    goal = GoalRevision(
        logical_id="live-read-root-cause-goal",
        revision=1,
        project_id=project_id,
        title="Localizar o codigo confirmado no memo autorizado",
        payload=GoalSpec(
            mode="goal_state",
            instruction=(
                "Use read_text para ler o input incident-memo e determine o valor exato "
                "de ROOT_CAUSE_CODE cuja confirmacao esta ativa. Responda somente com um "
                "objeto JSON contendo exatamente answer (string) e evidence (array nao vazio "
                "de objetos com exatamente input_id e line). A linha citada deve ser uma linha "
                "numerada que a ferramenta realmente retornou."
            ),
            outcomes=(
                GoalOutcome(
                    id="grounded-root-cause",
                    description=(
                        "Retornar o codigo exato e uma citacao de linha observada pela tool."
                    ),
                ),
            ),
        ),
    )
    scenario = ScenarioRevision(
        logical_id="live-read-fresh-incident",
        revision=1,
        project_id=project_id,
        title="Memo sintetico inedito com distractors",
        payload=ScenarioSpec(
            description=(
                "Corpus sintetico fresco; o nonce esperado nao aparece no prompt do Subject."
            ),
            input_bindings=(
                InputBinding(
                    id="incident-memo",
                    role="authorized_knowledge",
                    source=source,
                    visibility="subject_and_evaluator",
                    mount_name="incident-memo",
                ),
            ),
            provenance=("tests/support/live_read_study.py",),
        ),
    )
    agent = AgentInventoryRevision(
        logical_id="live-responses-read-agent",
        revision=1,
        project_id=project_id,
        title="Agente real com uma tool de leitura cercada",
        payload=AgentInventorySpec(
            subject_id="live-read-subject",
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
    )
    workspace = WorkspaceTemplateRevision(
        logical_id="live-provider-only-workspace",
        revision=1,
        project_id=project_id,
        title="Workspace local com rede exclusiva ao provider",
        payload=WorkspaceTemplateSpec(
            runtime_kind="in_process",
            mounts=(
                WorkspaceMount(
                    name="incident-memo",
                    source=source,
                    access="read_only",
                    target="subject-envelope-input",
                ),
            ),
            network_policy=NetworkPolicy(mode="provider_only"),
            external_effect_policy=ExternalEffectPolicy(mode="denied"),
        ),
    )
    interaction = InteractionProtocolRevision(
        logical_id="live-single-subject-interaction",
        revision=1,
        project_id=project_id,
        title="Uma interacao do Subject com rounds internos de tool",
        payload=InteractionProtocolSpec(mode="single_turn", max_turns=1),
    )
    evaluation = EvaluationPlanRevision(
        logical_id="live-grounded-exact-evaluation",
        revision=1,
        project_id=project_id,
        title="Avaliacao exata fundamentada no resultado persistido da tool",
        payload=EvaluationPlanSpec(
            dimensions=(
                EvaluationDimension(
                    id="exact-grounded-answer",
                    description=(
                        "JSON fechado, resposta exata e linha citada presente em tool.completed."
                    ),
                    value_type="boolean",
                ),
            ),
            stages=(
                EvaluationStage(
                    id="exact-grounded-read-v1",
                    kind="deterministic_grader",
                    evaluator_ref=ExactReadAnswerGraderAdapter.ref,
                    trigger=EvaluationTrigger(
                        kind="event", reference="subject.responded"
                    ),
                    output_dimensions=("exact-grounded-answer",),
                    hard_gate=True,
                    parameters=(KeyValue(key="expected", value=expected),),
                ),
            ),
            limitations=(
                "Uma Run valida integracao, nao capacidade geral do modelo.",
                "O corpus sintetico reduz contaminacao, mas nao mede pesquisa aberta.",
            ),
        ),
    )
    study = StudyRevision(
        logical_id="live-read-runtime-study",
        revision=1,
        project_id=project_id,
        title="Study live do Runtime Kernel com modelo e tool reais",
        payload=StudySpec(
            intent=StudyIntent(
                purpose=(
                    "Validar provider, tool tracing, avaliacao deterministica e durabilidade."
                )
            ),
            evidence_mode=EvidenceMode.RETROSPECTIVE_OBSERVATIONAL,
            goal_ref=goal.ref,
            scenario_refs=(scenario.ref,),
            run_blueprint=RunBlueprint(
                agent_inventory_ref=agent.ref,
                workspace_template_ref=workspace.ref,
                interaction_protocol_ref=interaction.ref,
                evaluation_plan_ref=evaluation.ref,
                context_policy=ContextPolicySpec(
                    id="live-full-memo-v1", strategy="full", max_chars=16_384
                ),
                budgets=BudgetSpec(
                    max_wall_seconds=120,
                    max_turns=1,
                    max_tool_calls=2,
                ),
                stop_conditions=(
                    StopCondition(kind="goal_complete"),
                    StopCondition(kind="budget_exhausted"),
                ),
                capture_policy=CapturePolicySpec(
                    default_mode="raw_encrypted",
                    raw_sensitive="opt_in",
                    sensitive_ttl_days=7,
                ),
            ),
        ),
    )
    revisions: tuple[RevisionEnvelope, ...] = (
        goal,
        scenario,
        agent,
        workspace,
        interaction,
        evaluation,
        study,
    )
    return revisions, study


def fresh_incident_memo(expected: str) -> str:
    """Return a deterministic-shaped but per-run fresh retrieval corpus."""

    lines = [
        "INCIDENT_MEMO_VERSION=2026-07-23",
        "SCOPE=synthetic-local-runtime-validation",
        "STATUS=review-in-progress",
    ]
    for index in range(4, 31):
        lines.append(f"OBSERVATION_{index:02d}=nominal telemetry window {index:02d}")
    lines.extend(
        [
            "PRIOR_HYPOTHESIS_CODE=CACHE_STAMPEDE_R2",
            "PRIOR_HYPOTHESIS_STATUS=REJECTED",
            "NOTE=The prior hypothesis is not the confirmed root cause.",
            "CONTROL_CODE=ION_MESH_K9_ARCHIVED",
            "CONTROL_STATUS=INACTIVE",
            f"ROOT_CAUSE_CODE={expected}",
            "ROOT_CAUSE_STATUS=CONFIRMED",
            "CONFIRMATION_SOURCE=independent synthetic sensor quorum",
        ]
    )
    for index in range(39, 66):
        lines.append(f"FOLLOWUP_{index:02d}=bounded remediation note {index:02d}")
    return "\n".join(lines) + "\n"
