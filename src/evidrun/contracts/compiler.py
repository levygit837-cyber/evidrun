from __future__ import annotations

from typing import Protocol, TypeVar

from evidrun.contracts.authoring import (
    AgentInventoryRevision,
    ComparisonPlan,
    EvaluationPlanRevision,
    GoalRevision,
    InputBinding,
    InteractionProtocolRevision,
    ProgressArtifactPolicyRevision,
    ScenarioRevision,
    StudyRevision,
    VariantSpec,
    WorkspaceTemplateRevision,
)
from evidrun.contracts.authority import (
    HumanAttestationVerifier,
    UnavailableHumanAttestationVerifier,
)
from evidrun.contracts.base import (
    ArtifactRef,
    ContractRef,
    ContractType,
    ExtensionRef,
    RevisionDecisionRecord,
    RevisionEnvelope,
)
from evidrun.contracts.runtime import (
    AdmissionRecord,
    EvaluatorEnvelope,
    RunSpec,
    SubjectEnvelope,
    SubjectEvaluationDimension,
    SubjectEvaluationGuidance,
    SubjectWorkspace,
)
from evidrun.shared.types import EvidenceMode

RevisionT = TypeVar("RevisionT", bound=RevisionEnvelope)


class ContractResolver(Protocol):
    def resolve(self, reference: ContractRef) -> RevisionEnvelope: ...


class ExtensionValidator(Protocol):
    def validate(self, payload_ref: ArtifactRef) -> None: ...


class ExtensionSchemaRegistry:
    def __init__(self) -> None:
        self._validators: dict[tuple[str, str, str], ExtensionValidator] = {}

    def register(
        self,
        *,
        namespace: str,
        schema_version: str,
        schema_digest: str,
        validator: ExtensionValidator,
    ) -> None:
        self._validators[(namespace, schema_version, schema_digest)] = validator

    def validate(self, extension: ExtensionRef) -> None:
        key = (extension.namespace, extension.schema_version, extension.schema_ref.digest)
        validator = self._validators.get(key)
        if validator is None:
            if extension.required:
                raise ValueError(f"unregistered required extension schema: {extension.namespace}")
            return
        validator.validate(extension.payload_ref)


class InMemoryContractRegistry(ContractResolver):
    def __init__(
        self,
        human_attestation_verifier: HumanAttestationVerifier | None = None,
        *,
        allow_repository_fixture: bool = False,
    ) -> None:
        self._revisions: dict[tuple[ContractType, str, int], RevisionEnvelope] = {}
        self._decisions: dict[tuple[ContractType, str, int], RevisionDecisionRecord] = {}
        self._human_attestation_verifier = (
            human_attestation_verifier or UnavailableHumanAttestationVerifier()
        )
        self._allow_repository_fixture = allow_repository_fixture

    @staticmethod
    def _key(reference: ContractRef | RevisionEnvelope) -> tuple[ContractType, str, int]:
        ref = reference if isinstance(reference, ContractRef) else reference.ref
        return (ref.contract_type, ref.logical_id, ref.revision)

    def add(self, revision: RevisionEnvelope) -> None:
        key = self._key(revision)
        existing = self._revisions.get(key)
        if existing is not None:
            if (
                existing.digest != revision.digest
                or existing.semantic_document() != revision.semantic_document()
            ):
                raise ValueError(
                    "an immutable contract revision already exists with different content"
                )
            return
        if existing is None:
            prior_revisions = [
                candidate.revision
                for candidate in self._revisions.values()
                if candidate.ref.contract_type == revision.ref.contract_type
                and candidate.logical_id == revision.logical_id
            ]
            expected = max(prior_revisions, default=0) + 1
            if revision.revision != expected:
                raise ValueError(
                    f"contract revision must be monotonic; expected {expected}, "
                    f"received {revision.revision}"
                )
        self._revisions[key] = revision

    def decide(self, decision: RevisionDecisionRecord) -> None:
        if decision.authority.kind == "verified_human":
            self._human_attestation_verifier.verify(
                decision.authority.attestation,
                expected_subject_digest=decision.human_subject_digest(),
            )
        elif not self._allow_repository_fixture:
            raise PermissionError(
                "repository fixture acceptance is restricted to the legacy import path"
            )
        key = self._key(decision.revision_ref)
        revision = self._revisions.get(key)
        if revision is None or revision.digest != decision.revision_ref.digest:
            raise ValueError("decision references an unknown or mismatched revision")
        existing = self._decisions.get(key)
        if existing is None and decision.decision == "superseded":
            raise ValueError("only an accepted revision can be superseded")
        if (
            existing is not None
            and existing.decision != decision.decision
            and not (
                existing.decision == "accepted" and decision.decision == "superseded"
            )
        ):
            raise ValueError("contract revision already has a conflicting decision")
        self._decisions[key] = decision

    def add_accepted(self, revision: RevisionEnvelope, decision: RevisionDecisionRecord) -> None:
        self.add(revision)
        self.decide(decision)

    def resolve(self, reference: ContractRef) -> RevisionEnvelope:
        key = self._key(reference)
        revision = self._revisions.get(key)
        if revision is None:
            raise KeyError(
                f"contract revision not found: {reference.logical_id}@{reference.revision}"
            )
        if revision.digest != reference.digest:
            raise ValueError("contract reference digest mismatch")
        decision = self._decisions.get(key)
        if decision is None or decision.decision != "accepted":
            raise ValueError("only accepted contract revisions can be resolved")
        return revision

    def revisions(self) -> tuple[RevisionEnvelope, ...]:
        return tuple(self._revisions.values())

    def decisions(self) -> tuple[RevisionDecisionRecord, ...]:
        return tuple(self._decisions.values())


class VariantDiffer:
    _SLOTS = (
        "goal",
        "scenario",
        "agent_inventory",
        "workspace_template",
        "interaction_protocol",
        "evaluation_plan",
        "checkpoint_policy",
        "progress_artifact_policy",
        "context_policy",
        "budgets",
        "stop_conditions",
        "capture_policy",
        "extensions",
    )

    @classmethod
    def changed_slots(cls, baseline: RunSpec, candidate: RunSpec) -> frozenset[str]:
        changed: set[str] = set()
        for slot in cls._SLOTS:
            if cls._slot_value(baseline, slot) != cls._slot_value(candidate, slot):
                changed.add(slot)
        return frozenset(changed)

    @staticmethod
    def _slot_value(spec: RunSpec, slot: str) -> object:
        if slot == "goal":
            return (spec.goal_ref, spec.goal)
        if slot == "scenario":
            return (spec.scenario_ref, spec.scenario)
        if slot == "agent_inventory":
            return (spec.agent_inventory_ref, spec.agent_inventory)
        if slot == "workspace_template":
            return (spec.workspace_template_ref, spec.workspace)
        if slot == "interaction_protocol":
            return (spec.interaction_protocol_ref, spec.interaction_protocol)
        if slot == "evaluation_plan":
            return (spec.evaluation_plan_ref, spec.evaluation_plan)
        if slot == "checkpoint_policy":
            return (spec.checkpoint_policy_ref, spec.checkpoint_policy)
        if slot == "progress_artifact_policy":
            return (spec.progress_artifact_policy_ref, spec.progress_artifact_policy)
        return getattr(spec, slot)


class StudyCompiler:
    def __init__(
        self,
        resolver: ContractResolver,
        extension_registry: ExtensionSchemaRegistry | None = None,
    ) -> None:
        self.resolver = resolver
        self.extension_registry = extension_registry or ExtensionSchemaRegistry()

    def compile(self, study: StudyRevision) -> tuple[RunSpec, ...]:
        resolved_study = self.resolver.resolve(study.ref)
        if not isinstance(resolved_study, StudyRevision):
            raise TypeError("study ref did not resolve to StudyRevision")
        self._validate_comparisons(study)
        specs: list[RunSpec] = []
        for scenario_ref in study.payload.scenario_refs:
            for variant in study.payload.variants:
                for repetition_index in range(1, study.payload.repetitions + 1):
                    specs.append(
                        self._materialize(study, scenario_ref, variant, repetition_index)
                    )
        return tuple(specs)

    def _resolve_typed(
        self, reference: ContractRef, expected: type[RevisionT]
    ) -> RevisionT:
        revision = self.resolver.resolve(reference)
        if not isinstance(revision, expected):
            raise TypeError(
                f"{reference.logical_id} resolved as {type(revision).__name__}, "
                f"expected {expected.__name__}"
            )
        return revision

    def _materialize(
        self,
        study: StudyRevision,
        matrix_scenario_ref: ContractRef,
        variant: VariantSpec,
        repetition_index: int,
    ) -> RunSpec:
        blueprint = study.payload.run_blueprint
        overrides = variant.overrides
        goal_ref = overrides.goal_ref or study.payload.goal_ref
        scenario_ref = overrides.scenario_ref or matrix_scenario_ref
        agent_ref = overrides.agent_inventory_ref or blueprint.agent_inventory_ref
        workspace_ref = overrides.workspace_template_ref or blueprint.workspace_template_ref
        interaction_ref = overrides.interaction_protocol_ref or blueprint.interaction_protocol_ref
        evaluation_ref = overrides.evaluation_plan_ref or blueprint.evaluation_plan_ref
        checkpoint_ref = overrides.checkpoint_policy_ref or blueprint.checkpoint_policy_ref
        progress_ref = (
            overrides.progress_artifact_policy_ref
            or blueprint.progress_artifact_policy_ref
        )

        goal = self._resolve_typed(goal_ref, GoalRevision)
        scenario = self._resolve_typed(scenario_ref, ScenarioRevision)
        agent = self._resolve_typed(agent_ref, AgentInventoryRevision)
        workspace = self._resolve_typed(workspace_ref, WorkspaceTemplateRevision)
        interaction = self._resolve_typed(interaction_ref, InteractionProtocolRevision)
        evaluation = self._resolve_typed(evaluation_ref, EvaluationPlanRevision)
        checkpoint_payload = None
        if checkpoint_ref is not None:
            from evidrun.contracts.authoring import CheckpointPolicyRevision

            checkpoint_payload = self._resolve_typed(
                checkpoint_ref, CheckpointPolicyRevision
            ).payload
        progress_payload = None
        if progress_ref is not None:
            progress_payload = self._resolve_typed(
                progress_ref, ProgressArtifactPolicyRevision
            ).payload
            checkpoint_ids: set[str] = (
                {item.id for item in checkpoint_payload.definitions}
                if checkpoint_payload is not None
                else set()
            )
            for definition in progress_payload.definitions:
                if (
                    definition.trigger.kind == "checkpoint_reached"
                    and definition.trigger.checkpoint_definition_id not in checkpoint_ids
                ):
                    raise ValueError(
                        "progress artifact trigger references an unknown checkpoint definition"
                    )

        extensions = (
            overrides.extensions if overrides.extensions is not None else blueprint.extensions
        )
        for extension in extensions:
            self.extension_registry.validate(extension)

        return RunSpec(
            study_ref=study.ref,
            scenario_ref=scenario.ref,
            variant_id=variant.id,
            repetition_index=repetition_index,
            seed=self._seed(study, repetition_index),
            goal_ref=goal.ref,
            goal=goal.payload,
            scenario=scenario.payload,
            agent_inventory_ref=agent.ref,
            agent_inventory=agent.payload,
            workspace_template_ref=workspace.ref,
            workspace=workspace.payload,
            interaction_protocol_ref=interaction.ref,
            interaction_protocol=interaction.payload,
            evaluation_plan_ref=evaluation.ref,
            evaluation_plan=evaluation.payload,
            checkpoint_policy_ref=checkpoint_ref,
            checkpoint_policy=checkpoint_payload,
            progress_artifact_policy_ref=progress_ref,
            progress_artifact_policy=progress_payload,
            context_policy=(
                overrides.context_policy
                if overrides.context_policy is not None
                else blueprint.context_policy
            ),
            budgets=overrides.budgets or blueprint.budgets,
            stop_conditions=(
                overrides.stop_conditions
                if overrides.stop_conditions is not None
                else blueprint.stop_conditions
            ),
            capture_policy=overrides.capture_policy or blueprint.capture_policy,
            extensions=extensions,
            limitations=study.payload.limitations + scenario.payload.limitations,
        )

    @staticmethod
    def _seed(study: StudyRevision, repetition_index: int) -> int | None:
        strategy = study.payload.seed_strategy
        if strategy.kind == "deterministic":
            return 0
        if strategy.kind == "fixed":
            return strategy.seed
        return (strategy.seed or 0) + repetition_index - 1

    def _validate_comparisons(self, study: StudyRevision) -> None:
        if not study.payload.comparisons:
            return
        scenario_ref = study.payload.scenario_refs[0]
        by_id = {variant.id: variant for variant in study.payload.variants}
        for comparison in study.payload.comparisons:
            baseline = self._materialize(
                study, scenario_ref, by_id[comparison.baseline_variant], 1
            )
            candidate = self._materialize(
                study, scenario_ref, by_id[comparison.candidate_variant], 1
            )
            changed = VariantDiffer.changed_slots(baseline, candidate)
            expected = self._expected_slot(comparison)
            if (
                study.payload.evidence_mode == EvidenceMode.PROSPECTIVE_CONTROLLED
                and changed != frozenset({expected})
            ):
                rendered = ", ".join(sorted(changed)) or "none"
                raise ValueError(
                    "controlled comparison must change exactly its primary variable; "
                    f"expected {expected}, observed {rendered}"
                )
            if study.payload.evidence_mode == EvidenceMode.EXPLORATORY:
                unexplained = changed - {expected}
                candidate_variant = by_id[comparison.candidate_variant]
                if unexplained and not candidate_variant.confounders:
                    rendered = ", ".join(sorted(unexplained))
                    raise ValueError(
                        "exploratory comparison must declare confounders for additional "
                        f"differences: {rendered}"
                    )

    @staticmethod
    def _expected_slot(comparison: ComparisonPlan) -> str:
        if comparison.primary_variable.startswith("extension:"):
            return "extensions"
        return comparison.primary_variable


class SubjectEnvelopeCompiler:
    @staticmethod
    def compile(
        spec: RunSpec,
        admission: AdmissionRecord,
        *,
        materialized_inputs: tuple[InputBinding, ...] | None = None,
    ) -> SubjectEnvelope:
        if admission.run_spec_digest != spec.digest:
            raise ValueError("admission does not belong to the RunSpec")
        if admission.decision != "admitted":
            raise ValueError("subject envelope cannot be created for rejected admission")
        declared_visible_inputs = tuple(
            item
            for item in spec.scenario.input_bindings
            if item.visibility in {"subject", "subject_and_evaluator"}
        )
        if spec.context_policy is not None and materialized_inputs is None:
            raise ValueError(
                "context-limited RunSpec requires materialized Subject inputs"
            )
        visible_inputs = (
            materialized_inputs
            if materialized_inputs is not None
            else declared_visible_inputs
        )
        if {item.id for item in visible_inputs} != {
            item.id for item in declared_visible_inputs
        }:
            raise ValueError("materialized Subject inputs must match visible scenario inputs")
        declared_by_id = {item.id: item for item in declared_visible_inputs}
        for materialized in visible_inputs:
            declared = declared_by_id[materialized.id]
            if (
                materialized.role != declared.role
                or materialized.visibility != declared.visibility
                or materialized.mount_access != declared.mount_access
                or materialized.mount_name != declared.mount_name
                or materialized.source.media_type != declared.source.media_type
                or materialized.source.classification != declared.source.classification
            ):
                raise ValueError(
                    "materialized Subject input changed its declared authority metadata"
                )
        effective_capabilities = tuple(
            item
            for item in admission.resolved_inventory.capabilities
            if item.status == "resolved"
        )
        workspace = SubjectWorkspace(
            runtime_kind=spec.workspace.runtime_kind,
            mounts=tuple(item.name for item in spec.workspace.mounts),
            write_zones=spec.workspace.write_zones,
            network_mode=spec.workspace.network_policy.mode,
            external_effect_mode=spec.workspace.external_effect_policy.mode,
        )
        disclosure = spec.evaluation_plan.disclosure.subject
        evaluation_guidance: SubjectEvaluationGuidance | None = None
        if disclosure.mode == "pre_run":
            dimensions_by_id = {
                item.id: item for item in spec.evaluation_plan.dimensions
            }
            public_dimensions: list[SubjectEvaluationDimension] = []
            for dimension_id in disclosure.dimension_ids:
                dimension = dimensions_by_id[dimension_id]
                public_dimensions.append(
                    SubjectEvaluationDimension(
                        id=dimension.id,
                        description=dimension.description,
                        value_type=dimension.value_type,
                        minimum=(
                            dimension.minimum if disclosure.include_scale else None
                        ),
                        maximum=(
                            dimension.maximum if disclosure.include_scale else None
                        ),
                        anchors=(
                            dimension.anchors if disclosure.include_anchors else ()
                        ),
                    )
                )
            evaluation_guidance = SubjectEvaluationGuidance(
                plan_ref=spec.evaluation_plan_ref,
                dimensions=tuple(public_dimensions),
            )
        return SubjectEnvelope(
            run_spec_digest=spec.digest,
            goal=spec.goal,
            inputs=visible_inputs,
            interaction_protocol=spec.interaction_protocol,
            effective_capabilities=effective_capabilities,
            workspace=workspace,
            budgets=spec.budgets,
            stop_conditions=spec.stop_conditions,
            evaluation_guidance=evaluation_guidance,
        )


class EvaluatorEnvelopeCompiler:
    @staticmethod
    def compile(spec: RunSpec, stage_id: str) -> EvaluatorEnvelope:
        stage = next(
            (item for item in spec.evaluation_plan.stages if item.id == stage_id), None
        )
        if stage is None:
            raise ValueError("evaluation stage does not belong to the RunSpec")
        dimension_by_id = {
            item.id: item for item in spec.evaluation_plan.dimensions
        }
        visible_inputs = tuple(
            item
            for item in spec.scenario.input_bindings
            if item.visibility in {"evaluator", "subject_and_evaluator"}
        )
        return EvaluatorEnvelope(
            run_spec_digest=spec.digest,
            plan_ref=spec.evaluation_plan_ref,
            stage=stage,
            dimensions=tuple(
                dimension_by_id[dimension_id]
                for dimension_id in stage.output_dimensions
            ),
            inputs=visible_inputs,
            hidden_input_refs=spec.evaluation_plan.disclosure.hidden_input_refs,
            blinded_fields=spec.evaluation_plan.blinding_policy.hidden_fields,
        )
