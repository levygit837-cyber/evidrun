from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from evidrun.contracts.authoring import (
    AgentInventoryRevision,
    AgentInventorySpec,
    BudgetSpec,
    CapturePolicySpec,
    ComparisonPlan,
    EvaluationDimension,
    EvaluationDisclosure,
    EvaluationPlanRevision,
    EvaluationPlanSpec,
    EvaluationStage,
    EvaluationTrigger,
    ExternalEffectPolicy,
    GoalConstraint,
    GoalOutcome,
    GoalRevision,
    GoalSpec,
    InputBinding,
    IntentScope,
    InteractionProtocolRevision,
    InteractionProtocolSpec,
    NetworkPolicy,
    RunBlueprint,
    ScenarioRevision,
    ScenarioSpec,
    SeedStrategy,
    StopCondition,
    StudyIntent,
    StudyRevision,
    StudySpec,
    VariantOverrides,
    VariantSpec,
    WorkspaceMount,
    WorkspaceTemplateRevision,
    WorkspaceTemplateSpec,
)
from evidrun.contracts.base import (
    ArtifactRef,
    CapabilityDescriptorRef,
    KeyValue,
    RevisionDecisionRecord,
    RevisionEnvelope,
)
from evidrun.experiments import ExperimentManifest
from evidrun.shared.types import Classification, sha256_bytes, sha256_json, utc_now


def capability_ref(namespace: str, name: str, version: str = "1") -> CapabilityDescriptorRef:
    return CapabilityDescriptorRef(
        namespace=namespace,
        name=name,
        version=version,
        digest=sha256_json({"namespace": namespace, "name": name, "version": version}),
    )


@dataclass(frozen=True)
class LegacyStudyPackage:
    revisions: tuple[RevisionEnvelope, ...]
    study: StudyRevision

    def acceptance_decisions(
        self, actor_id: str = "repository-owner"
    ) -> tuple[RevisionDecisionRecord, ...]:
        decided_at = utc_now()
        return tuple(
            RevisionDecisionRecord(
                revision_ref=revision.ref,
                decision="accepted",
                actor_id=actor_id,
                rationale="Accepted repository benchmark imported from ExperimentManifest v1.",
                decided_at_utc=decided_at,
            )
            for revision in self.revisions
        )


class ExperimentManifestV1Adapter:
    def convert(
        self,
        manifest: ExperimentManifest,
        *,
        project_id: str,
        fixture_path: Path,
    ) -> LegacyStudyPackage:
        fixture_bytes = fixture_path.read_bytes()
        fixture_ref = ArtifactRef(
            artifact_id=f"fixture:{manifest.scenario_refs[0]}",
            digest=sha256_bytes(fixture_bytes),
            media_type="text/plain",
            classification=Classification.INTERNAL,
            locator=str(fixture_path),
        )

        goal = GoalRevision(
            logical_id=f"{manifest.id}-goal",
            revision=1,
            project_id=project_id,
            title=f"Goal — {manifest.title}",
            payload=GoalSpec(
                mode="goal_state",
                instruction=manifest.objective,
                outcomes=(
                    GoalOutcome(
                        id="terminal-answer",
                        description="Produce one terminal answer with cited evidence.",
                    ),
                ),
                constraints=(
                    GoalConstraint(
                        id="authorized-context-only",
                        rule="must",
                        description="Use only the context selected from the authorized fixture.",
                    ),
                    GoalConstraint(
                        id="no-external-access",
                        rule="must_not",
                        description=(
                            "Access network, additional files, tools, or external knowledge."
                        ),
                    ),
                ),
                evidence_expectations=("Cite the decisive log evidence when observable.",),
                completion_observations=("A single terminal response is produced.",),
            ),
        )

        scenario_id, scenario_revision = self._parse_scenario_ref(manifest.scenario_refs[0])
        scenario = ScenarioRevision(
            logical_id=scenario_id,
            revision=scenario_revision,
            project_id=project_id,
            title=f"Scenario — {scenario_id}",
            payload=ScenarioSpec(
                description="Investigate the supplied deterministic log fixture.",
                input_bindings=(
                    InputBinding(
                        id="incident-log",
                        role="source_log",
                        source=fixture_ref,
                        visibility="subject_and_evaluator",
                        mount_name="incident-log",
                    ),
                ),
                observable_conditions=(
                    "The complete fixture is immutable before context selection.",
                ),
                limitations=(
                    "The deterministic runner validates infrastructure, not "
                    "language-model capability.",
                    "One repetition does not establish statistical stability.",
                ),
                provenance=("ExperimentManifest v1 compatibility adapter",),
            ),
        )

        runner_ref = capability_ref("evidrun.runner", manifest.subject_profile.runner)
        agent = AgentInventoryRevision(
            logical_id=f"{manifest.id}-agent",
            revision=1,
            project_id=project_id,
            title=f"Agent inventory — {manifest.subject_profile.runner}",
            payload=AgentInventorySpec(
                subject_id=manifest.subject_profile.runner,
                runner_ref=runner_ref,
                provider_profile_id=None,
            ),
        )

        workspace = WorkspaceTemplateRevision(
            logical_id=f"{manifest.id}-workspace",
            revision=1,
            project_id=project_id,
            title="Deterministic offline execution workspace",
            payload=WorkspaceTemplateSpec(
                runtime_kind="in_process",
                mounts=(
                    WorkspaceMount(
                        name="incident-log",
                        source=fixture_ref,
                        access="read_only",
                        target="context-source",
                    ),
                ),
                network_policy=NetworkPolicy(mode="disabled"),
                external_effect_policy=ExternalEffectPolicy(mode="denied"),
            ),
        )

        interaction = InteractionProtocolRevision(
            logical_id=f"{manifest.id}-interaction",
            revision=1,
            project_id=project_id,
            title="Single-turn deterministic interaction",
            payload=InteractionProtocolSpec(mode="single_turn", max_turns=1),
        )

        grader = manifest.graders[0]
        grader_ref = capability_ref("evidrun.evaluator", grader.id)
        evaluation = EvaluationPlanRevision(
            logical_id=f"{manifest.id}-evaluation",
            revision=1,
            project_id=project_id,
            title=f"Evaluation plan — {grader.id}",
            payload=EvaluationPlanSpec(
                dimensions=(
                    EvaluationDimension(
                        id="root-cause-grounded",
                        description="Expected root cause appears in output and cited evidence.",
                        value_type="boolean",
                    ),
                ),
                stages=(
                    EvaluationStage(
                        id=grader.id,
                        kind="deterministic_grader",
                        evaluator_ref=grader_ref,
                        trigger=EvaluationTrigger(kind="run_terminal"),
                        output_dimensions=("root-cause-grounded",),
                        parameters=(KeyValue(key="expected", value=grader.expected),),
                    ),
                ),
                disclosure=EvaluationDisclosure(),
                limitations=(
                    "The expected value is hidden from the SubjectEnvelope.",
                ),
            ),
        )

        policy_by_id = {policy.id: policy for policy in manifest.context_policies}
        baseline_policy = policy_by_id[
            next(
                item.context_policy
                for item in manifest.variants
                if item.id == manifest.baseline_variant
            )
        ]
        variants: list[VariantSpec] = []
        for variant in manifest.variants:
            context_policy = policy_by_id[variant.context_policy]
            override = (
                VariantOverrides()
                if variant.id == manifest.baseline_variant
                else VariantOverrides(context_policy=context_policy)
            )
            variants.append(
                VariantSpec(
                    id=variant.id,
                    label=variant.label,
                    overrides=override,
                    confounders=variant.confounders,
                )
            )

        comparisons = tuple(
            ComparisonPlan(
                baseline_variant=manifest.baseline_variant,
                candidate_variant=variant.id,
                primary_variable="context_policy",
            )
            for variant in manifest.variants
            if variant.id != manifest.baseline_variant
        )
        raw_max_wall_seconds = cast(object, manifest.budgets.get("max_wall_seconds", 60))
        max_wall_seconds = (
            raw_max_wall_seconds
            if isinstance(raw_max_wall_seconds, int) and not isinstance(raw_max_wall_seconds, bool)
            else 60
        )
        raw_capture_default = cast(object, manifest.capture_policy.get("default", "redacted"))
        capture_default = (
            raw_capture_default if isinstance(raw_capture_default, str) else "redacted"
        )
        if capture_default not in {"metadata", "redacted", "raw_encrypted", "disabled"}:
            capture_default = "redacted"

        study = StudyRevision(
            logical_id=manifest.id,
            revision=1,
            project_id=project_id,
            title=manifest.title,
            payload=StudySpec(
                intent=StudyIntent(
                    purpose=manifest.hypothesis,
                    questions=(manifest.objective,),
                    hypothesis=manifest.hypothesis,
                    scope=IntentScope(included=(scenario_id,), excluded=("external systems",)),
                ),
                evidence_mode=manifest.evidence_mode,
                goal_ref=goal.ref,
                scenario_refs=(scenario.ref,),
                run_blueprint=RunBlueprint(
                    agent_inventory_ref=agent.ref,
                    workspace_template_ref=workspace.ref,
                    interaction_protocol_ref=interaction.ref,
                    evaluation_plan_ref=evaluation.ref,
                    context_policy=baseline_policy,
                    budgets=BudgetSpec(max_wall_seconds=max_wall_seconds, max_turns=1),
                    stop_conditions=(
                        StopCondition(kind="goal_complete"),
                        StopCondition(kind="budget_exhausted"),
                        StopCondition(kind="provider_error"),
                    ),
                    capture_policy=CapturePolicySpec(
                        default_mode=cast_capture_mode(capture_default),
                        raw_sensitive="disabled",
                    ),
                ),
                variants=tuple(variants),
                repetitions=manifest.repetitions,
                seed_strategy=SeedStrategy(kind="deterministic"),
                comparisons=comparisons,
                limitations=(
                    "Compatibility import of ExperimentManifest v1.",
                ),
                tags=manifest.tags,
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
        return LegacyStudyPackage(revisions=revisions, study=study)

    @staticmethod
    def _parse_scenario_ref(value: str) -> tuple[str, int]:
        if "@" not in value:
            return value, 1
        logical_id, raw_revision = value.rsplit("@", 1)
        return logical_id, int(raw_revision)


def cast_capture_mode(
    value: str,
) -> Literal["metadata", "redacted", "raw_encrypted", "disabled"]:
    return cast(
        Literal["metadata", "redacted", "raw_encrypted", "disabled"],
        value,
    )
