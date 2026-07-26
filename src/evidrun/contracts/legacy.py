from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from evidrun.contracts.authoring.evaluation import (
    EvaluationDimension,
    EvaluationDisclosure,
    EvaluationPlanRevision,
    EvaluationPlanSpec,
    EvaluationStage,
    EvaluationTrigger,
)
from evidrun.contracts.authoring.goal import GoalConstraint, GoalOutcome, GoalRevision, GoalSpec
from evidrun.contracts.authoring.inventory import AgentInventoryRevision, AgentInventorySpec
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
from evidrun.contracts.authoring.study import (
    ComparisonPlan,
    SeedStrategy,
    StudyRevision,
    StudySpec,
    VariantOverrides,
    VariantSpec,
)
from evidrun.contracts.authoring.study_intent import IntentScope, StudyIntent
from evidrun.contracts.authoring.workspace import (
    ExternalEffectPolicy,
    NetworkPolicy,
    WorkspaceMount,
    WorkspaceTemplateRevision,
    WorkspaceTemplateSpec,
)
from evidrun.contracts.base import (
    ArtifactRef,
    KeyValue,
    RepositoryFixtureDecisionAuthority,
    RevisionDecisionRecord,
    RevisionEnvelope,
)
from evidrun.experiments import ExperimentManifest
from evidrun.experiments.models import ContextPolicySpec
from evidrun.shared.capabilities import capability_ref
from evidrun.shared.types import Classification, sha256_bytes, sha256_json, utc_now


@dataclass(frozen=True)
class LegacyStudyPackage:
    revisions: tuple[RevisionEnvelope, ...]
    study: StudyRevision

    @property
    def fixture_digest(self) -> str:
        return sha256_json(
            [revision.ref.model_dump(mode="json") for revision in self.revisions]
        )

    def acceptance_decisions(self) -> tuple[RevisionDecisionRecord, ...]:
        decided_at = utc_now()
        return tuple(
            RevisionDecisionRecord(
                revision_ref=revision.ref,
                decision="accepted",
                authority=RepositoryFixtureDecisionAuthority(
                    fixture_id="experiment-manifest-v1:crl-ctx-002",
                    fixture_digest=self.fixture_digest,
                ),
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
        fixture_path: Path | None = None,
        fixture_ref: ArtifactRef | None = None,
    ) -> LegacyStudyPackage:
        """Translate a v1 manifest into the accepted contract revisions.

        Each section below is built independently from the manifest; only
        `project_id` and the resolved fixture cross between them. The Study is last
        because it references the refs the other sections produced.
        """

        source = self._resolve_fixture(
            manifest, fixture_path=fixture_path, fixture_ref=fixture_ref
        )
        scenario_id, scenario_revision = self._parse_scenario_ref(manifest.scenario_refs[0])

        goal = self._goal(manifest, project_id=project_id)
        scenario = self._scenario(
            project_id=project_id,
            scenario_id=scenario_id,
            revision=scenario_revision,
            source=source,
        )
        agent = self._agent_inventory(manifest, project_id=project_id)
        workspace = self._workspace(manifest, project_id=project_id, source=source)
        interaction = self._interaction(manifest, project_id=project_id)
        evaluation = self._evaluation_plan(manifest, project_id=project_id)
        study = self._study(
            manifest,
            project_id=project_id,
            scenario_id=scenario_id,
            goal=goal,
            scenario=scenario,
            agent=agent,
            workspace=workspace,
            interaction=interaction,
            evaluation=evaluation,
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
    def _resolve_fixture(
        manifest: ExperimentManifest,
        *,
        fixture_path: Path | None,
        fixture_ref: ArtifactRef | None,
    ) -> ArtifactRef:
        """Exactly one materialization source: a path to hash, or a ref already known."""

        if fixture_ref is not None:
            if fixture_path is not None:
                raise ValueError(
                    "legacy conversion accepts only one fixture materialization source"
                )
            return fixture_ref
        if fixture_path is None:
            raise ValueError("legacy conversion requires fixture_path or fixture_ref")
        return ArtifactRef(
            artifact_id=f"fixture:{manifest.scenario_refs[0]}",
            digest=sha256_bytes(fixture_path.read_bytes()),
            media_type="text/plain",
            classification=Classification.INTERNAL,
        )

    @staticmethod
    def _goal(manifest: ExperimentManifest, *, project_id: str) -> GoalRevision:
        return GoalRevision(
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

    @staticmethod
    def _scenario(
        *, project_id: str, scenario_id: str, revision: int, source: ArtifactRef
    ) -> ScenarioRevision:
        return ScenarioRevision(
            logical_id=scenario_id,
            revision=revision,
            project_id=project_id,
            title=f"Scenario — {scenario_id}",
            payload=ScenarioSpec(
                description="Investigate the supplied deterministic log fixture.",
                input_bindings=(
                    InputBinding(
                        id="incident-log",
                        role="source_log",
                        source=source,
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

    @staticmethod
    def _agent_inventory(
        manifest: ExperimentManifest, *, project_id: str
    ) -> AgentInventoryRevision:
        return AgentInventoryRevision(
            logical_id=f"{manifest.id}-agent",
            revision=1,
            project_id=project_id,
            title=f"Agent inventory — {manifest.subject_profile.runner}",
            payload=AgentInventorySpec(
                subject_id=manifest.subject_profile.runner,
                runner_ref=capability_ref("evidrun.runner", manifest.subject_profile.runner),
                provider_profile_id=None,
            ),
        )

    @staticmethod
    def _workspace(
        manifest: ExperimentManifest, *, project_id: str, source: ArtifactRef
    ) -> WorkspaceTemplateRevision:
        return WorkspaceTemplateRevision(
            logical_id=f"{manifest.id}-workspace",
            revision=1,
            project_id=project_id,
            title="Deterministic offline execution workspace",
            payload=WorkspaceTemplateSpec(
                runtime_kind="in_process",
                mounts=(
                    WorkspaceMount(
                        name="incident-log",
                        source=source,
                        access="read_only",
                        target="context-source",
                    ),
                ),
                network_policy=NetworkPolicy(mode="disabled"),
                external_effect_policy=ExternalEffectPolicy(mode="denied"),
            ),
        )

    @staticmethod
    def _interaction(
        manifest: ExperimentManifest, *, project_id: str
    ) -> InteractionProtocolRevision:
        return InteractionProtocolRevision(
            logical_id=f"{manifest.id}-interaction",
            revision=1,
            project_id=project_id,
            title="Single-turn deterministic interaction",
            payload=InteractionProtocolSpec(mode="single_turn", max_turns=1),
        )

    @staticmethod
    def _evaluation_plan(
        manifest: ExperimentManifest, *, project_id: str
    ) -> EvaluationPlanRevision:
        grader = manifest.graders[0]
        return EvaluationPlanRevision(
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
                        evaluator_ref=capability_ref(
                            "evidrun.evaluator", "exact-root-cause-legacy-v1"
                        ),
                        trigger=EvaluationTrigger(
                            kind="event", reference="subject.responded"
                        ),
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

    def _study(
        self,
        manifest: ExperimentManifest,
        *,
        project_id: str,
        scenario_id: str,
        goal: GoalRevision,
        scenario: ScenarioRevision,
        agent: AgentInventoryRevision,
        workspace: WorkspaceTemplateRevision,
        interaction: InteractionProtocolRevision,
        evaluation: EvaluationPlanRevision,
    ) -> StudyRevision:
        policy_by_id = {policy.id: policy for policy in manifest.context_policies}
        baseline_policy = policy_by_id[
            next(
                item.context_policy
                for item in manifest.variants
                if item.id == manifest.baseline_variant
            )
        ]
        return StudyRevision(
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
                    budgets=BudgetSpec(
                        max_wall_seconds=self._max_wall_seconds(manifest), max_turns=1
                    ),
                    stop_conditions=(
                        StopCondition(kind="goal_complete"),
                        StopCondition(kind="budget_exhausted"),
                    ),
                    capture_policy=CapturePolicySpec(
                        default_mode=cast_capture_mode(self._capture_default(manifest)),
                        raw_sensitive="disabled",
                    ),
                ),
                variants=self._variants(manifest, policy_by_id=policy_by_id),
                repetitions=manifest.repetitions,
                seed_strategy=SeedStrategy(kind="deterministic"),
                comparisons=self._comparisons(manifest),
                limitations=(
                    "Compatibility import of ExperimentManifest v1.",
                ),
                tags=manifest.tags,
            ),
        )

    @staticmethod
    def _variants(
        manifest: ExperimentManifest, *, policy_by_id: dict[str, ContextPolicySpec]
    ) -> tuple[VariantSpec, ...]:
        """The baseline carries no override; every other variant overrides the policy."""

        return tuple(
            VariantSpec(
                id=variant.id,
                label=variant.label,
                overrides=(
                    VariantOverrides()
                    if variant.id == manifest.baseline_variant
                    else VariantOverrides(context_policy=policy_by_id[variant.context_policy])
                ),
                confounders=variant.confounders,
            )
            for variant in manifest.variants
        )

    @staticmethod
    def _comparisons(manifest: ExperimentManifest) -> tuple[ComparisonPlan, ...]:
        return tuple(
            ComparisonPlan(
                baseline_variant=manifest.baseline_variant,
                candidate_variant=variant.id,
                primary_variable="context_policy",
            )
            for variant in manifest.variants
            if variant.id != manifest.baseline_variant
        )

    @staticmethod
    def _max_wall_seconds(manifest: ExperimentManifest) -> int:
        """The manifest budget map is untyped; a non-int value falls back to 60."""

        raw = cast(object, manifest.budgets.get("max_wall_seconds", 60))
        if isinstance(raw, int) and not isinstance(raw, bool):
            return raw
        return 60

    @staticmethod
    def _capture_default(manifest: ExperimentManifest) -> str:
        """An unknown or non-string capture mode falls back to redacted."""

        raw = cast(object, manifest.capture_policy.get("default", "redacted"))
        if not isinstance(raw, str):
            return "redacted"
        if raw not in {"metadata", "redacted", "raw_encrypted", "disabled"}:
            return "redacted"
        return raw

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
