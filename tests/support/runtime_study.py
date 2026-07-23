from __future__ import annotations

from evidrun.contracts import ArtifactRef, RevisionEnvelope
from evidrun.contracts.authoring import (
    AgentInventoryRevision,
    AgentInventorySpec,
    BudgetSpec,
    CapturePolicySpec,
    EvaluationDimension,
    EvaluationPlanRevision,
    EvaluationPlanSpec,
    EvaluationStage,
    EvaluationTrigger,
    ExternalEffectPolicy,
    GoalOutcome,
    GoalRevision,
    GoalSpec,
    InputBinding,
    InteractionProtocolRevision,
    InteractionProtocolSpec,
    NetworkPolicy,
    RunBlueprint,
    ScenarioRevision,
    ScenarioSpec,
    StopCondition,
    StudyIntent,
    StudyRevision,
    StudySpec,
    WorkspaceMount,
    WorkspaceTemplateRevision,
    WorkspaceTemplateSpec,
)
from evidrun.contracts.base import KeyValue
from evidrun.experiments.models import ContextPolicySpec
from evidrun.shared.capabilities import capability_ref
from evidrun.shared.types import EvidenceMode


def build_runtime_study(
    *, project_id: str, source: ArtifactRef
) -> tuple[tuple[RevisionEnvelope, ...], StudyRevision]:
    """Create a new Study directly from v1 contracts, without legacy adapters."""

    goal = GoalRevision(
        logical_id="runtime-search-index-goal",
        revision=1,
        project_id=project_id,
        title="Diagnosticar atraso no indice de busca",
        payload=GoalSpec(
            mode="goal_state",
            instruction="Identifique a causa-raiz usando somente o registro autorizado.",
            outcomes=(
                GoalOutcome(
                    id="root-cause",
                    description="Emitir uma causa-raiz terminal apoiada pelo registro.",
                ),
            ),
        ),
    )
    scenario = ScenarioRevision(
        logical_id="runtime-search-index-scenario",
        revision=1,
        project_id=project_id,
        title="Incidente inedito de indice de busca",
        payload=ScenarioSpec(
            description="Registro sintetico criado exclusivamente para o Runtime Kernel.",
            input_bindings=(
                InputBinding(
                    id="search-incident-log",
                    role="source_log",
                    source=source,
                    visibility="subject_and_evaluator",
                    mount_name="search-incident-log",
                ),
            ),
            provenance=("tests/support/runtime_study.py",),
        ),
    )
    agent = AgentInventoryRevision(
        logical_id="runtime-scripted-agent",
        revision=1,
        project_id=project_id,
        title="Subject deterministico do Runtime Kernel",
        payload=AgentInventorySpec(
            subject_id="runtime-scripted-subject",
            runner_ref=capability_ref(
                "evidrun.runner", "scripted-log-investigator-v1"
            ),
        ),
    )
    workspace = WorkspaceTemplateRevision(
        logical_id="runtime-in-process-workspace",
        revision=1,
        project_id=project_id,
        title="Workspace local sem rede",
        payload=WorkspaceTemplateSpec(
            runtime_kind="in_process",
            mounts=(
                WorkspaceMount(
                    name="search-incident-log",
                    source=source,
                    access="read_only",
                    target="context-source",
                ),
            ),
            network_policy=NetworkPolicy(mode="disabled"),
            external_effect_policy=ExternalEffectPolicy(mode="denied"),
        ),
    )
    interaction = InteractionProtocolRevision(
        logical_id="runtime-single-turn",
        revision=1,
        project_id=project_id,
        title="Interacao unica do Runtime Kernel",
        payload=InteractionProtocolSpec(mode="single_turn", max_turns=1),
    )
    evaluation = EvaluationPlanRevision(
        logical_id="runtime-search-index-evaluation",
        revision=1,
        project_id=project_id,
        title="Avaliacao exata do incidente de busca",
        payload=EvaluationPlanSpec(
            dimensions=(
                EvaluationDimension(
                    id="root-cause-grounded",
                    description="A causa esperada aparece na resposta e na evidencia.",
                    value_type="boolean",
                ),
            ),
            stages=(
                EvaluationStage(
                    id="exact-search-cause-v1",
                    kind="deterministic_grader",
                    evaluator_ref=capability_ref(
                        "evidrun.evaluator", "exact-root-cause-legacy-v1"
                    ),
                    trigger=EvaluationTrigger(
                        kind="event", reference="subject.responded"
                    ),
                    output_dimensions=("root-cause-grounded",),
                    parameters=(
                        KeyValue(key="expected", value="SEARCH_INDEX_LAG"),
                    ),
                ),
            ),
        ),
    )
    study = StudyRevision(
        logical_id="runtime-kernel-study",
        revision=1,
        project_id=project_id,
        title="Study transversal do Runtime Kernel",
        payload=StudySpec(
            intent=StudyIntent(
                purpose="Validar uma Run duravel sem o pacote de benchmark legado."
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
                    id="runtime-full-context-v1", strategy="full", max_chars=4096
                ),
                budgets=BudgetSpec(max_wall_seconds=5, max_turns=1),
                stop_conditions=(
                    StopCondition(kind="goal_complete"),
                    StopCondition(kind="budget_exhausted"),
                ),
                capture_policy=CapturePolicySpec(
                    default_mode="redacted", raw_sensitive="disabled"
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
