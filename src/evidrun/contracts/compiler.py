from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, Protocol, TypeVar

from evidrun.contracts.authoring import (
    AgentInventoryRevision,
    ComparisonPlan,
    EvaluationPlanRevision,
    GoalRevision,
    InputBinding,
    InteractionProtocolRevision,
    ScenarioRevision,
    StudyRevision,
    VariantSpec,
    WorkspaceTemplateRevision,
)
from evidrun.contracts.base import (
    ArtifactRef,
    CapabilityDescriptorRef,
    ContractRef,
    ContractType,
    ExtensionRef,
    RevisionDecisionRecord,
    RevisionEnvelope,
)
from evidrun.contracts.runtime import (
    AdmissionIssue,
    AdmissionRecord,
    EvaluatorEnvelope,
    ResolutionReason,
    ResolvedAgentInventory,
    ResolvedCapability,
    RunSpec,
    SubjectEnvelope,
    SubjectWorkspace,
)
from evidrun.shared.types import EvidenceMode, utc_now

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
    def __init__(self) -> None:
        self._revisions: dict[tuple[ContractType, str, int], RevisionEnvelope] = {}
        self._decisions: dict[tuple[ContractType, str, int], RevisionDecisionRecord] = {}

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


@dataclass(frozen=True)
class CapabilityCatalogEntry:
    ref: CapabilityDescriptorRef
    adapter: str
    allowed_permissions: frozenset[str]
    compatible_interface_versions: frozenset[str] = frozenset()
    satisfied_authority_constraints: frozenset[str] = frozenset()


@dataclass(frozen=True)
class ProviderCatalogEntry:
    profile_id: str
    profile_digest: str
    model: str
    reasoning_effort: str
    adapter: str


class AdmissionService:
    def __init__(
        self,
        *,
        runners: Iterable[CapabilityDescriptorRef],
        capabilities: Iterable[CapabilityCatalogEntry] = (),
        providers: Iterable[ProviderCatalogEntry] = (),
        workspace_runtime_kinds: Iterable[str] = ("in_process",),
        interaction_modes: Iterable[str] = ("single_turn",),
        runtime_capabilities: Iterable[str] = (),
        network_modes: Iterable[str] = ("disabled",),
        external_effect_modes: Iterable[str] = ("denied",),
    ) -> None:
        self.runners = {self._capability_key(item): item for item in runners}
        self.capabilities = {
            self._capability_key(item.ref): item for item in capabilities
        }
        self.providers = {item.profile_id: item for item in providers}
        self.workspace_runtime_kinds = frozenset(workspace_runtime_kinds)
        self.interaction_modes = frozenset(interaction_modes)
        self.runtime_capabilities = frozenset(runtime_capabilities)
        self.network_modes = frozenset(network_modes)
        self.external_effect_modes = frozenset(external_effect_modes)

    @staticmethod
    def _capability_key(reference: CapabilityDescriptorRef) -> tuple[str, str, str]:
        return (reference.namespace, reference.name, reference.version)

    def admit(self, spec: RunSpec) -> AdmissionRecord:
        missing: list[str] = []
        denied_policies: list[str] = []
        warnings: list[str] = []
        issues: list[AdmissionIssue] = []
        runner = self.runners.get(self._capability_key(spec.agent_inventory.runner_ref))
        if runner is None or runner.digest != spec.agent_inventory.runner_ref.digest:
            missing.append(f"runner:{spec.agent_inventory.runner_ref.name}")
            issues.append(
                AdmissionIssue(
                    category="runner",
                    subject_ref=spec.agent_inventory.runner_ref.name,
                    reason=ResolutionReason(
                        code="unsupported",
                        detail="runner is not registered with the required digest",
                    ),
                    blocking=True,
                )
            )

        provider_model: str | None = None
        provider_reasoning: str | None = None
        provider_digest: str | None = None
        provider_adapter: str | None = None
        provider_id = spec.agent_inventory.provider_profile_id
        if provider_id is not None:
            provider = self.providers.get(provider_id)
            if provider is None:
                missing.append(f"provider:{provider_id}")
                issues.append(
                    AdmissionIssue(
                        category="provider",
                        subject_ref=provider_id,
                        reason=ResolutionReason(
                            code="unavailable",
                            detail="provider profile is not available in the active runtime",
                        ),
                        blocking=True,
                    )
                )
            else:
                provider_model = provider.model
                provider_reasoning = provider.reasoning_effort
                provider_digest = provider.profile_digest
                provider_adapter = provider.adapter

        resolved: list[ResolvedCapability] = []
        for requirement in spec.agent_inventory.capability_requirements:
            entry = self.capabilities.get(self._capability_key(requirement.capability_ref))
            if entry is None or entry.ref.digest != requirement.capability_ref.digest:
                resolved.append(
                    ResolvedCapability(
                        kind=requirement.kind,
                        requested_ref=requirement.capability_ref,
                        required=requirement.required,
                        exposure=requirement.exposure,
                        status="unsupported",
                        reason=ResolutionReason(
                            code="unsupported",
                            detail="capability is not registered in the active runtime",
                        ),
                    )
                )
                if not requirement.required:
                    warnings.append(
                        "optional capability unavailable: "
                        f"{requirement.capability_ref.name}"
                    )
                continue
            if requirement.minimum_interface_version not in entry.compatible_interface_versions:
                resolved.append(
                    ResolvedCapability(
                        kind=requirement.kind,
                        requested_ref=requirement.capability_ref,
                        required=requirement.required,
                        exposure=requirement.exposure,
                        status="unsupported",
                        reason=ResolutionReason(
                            code="unsupported",
                            detail=(
                                "capability adapter does not support the required "
                                "interface version"
                            ),
                        ),
                    )
                )
                if not requirement.required:
                    warnings.append(
                        "optional capability interface unavailable: "
                        f"{requirement.capability_ref.name}"
                    )
                continue
            requested_permissions = frozenset(requirement.requested_permissions)
            if not requested_permissions.issubset(entry.allowed_permissions):
                resolved.append(
                    ResolvedCapability(
                        kind=requirement.kind,
                        requested_ref=requirement.capability_ref,
                        required=requirement.required,
                        exposure=requirement.exposure,
                        status="denied",
                        reason=ResolutionReason(
                            code="denied",
                            detail="requested permissions exceed the catalog allowlist",
                        ),
                    )
                )
                if not requirement.required:
                    warnings.append(
                        "optional capability permission denied: "
                        f"{requirement.capability_ref.name}"
                    )
                continue
            requested_constraints = frozenset(requirement.authority_constraints)
            if not requested_constraints.issubset(
                entry.satisfied_authority_constraints
            ):
                resolved.append(
                    ResolvedCapability(
                        kind=requirement.kind,
                        requested_ref=requirement.capability_ref,
                        required=requirement.required,
                        exposure=requirement.exposure,
                        status="denied",
                        reason=ResolutionReason(
                            code="denied",
                            detail=(
                                "capability adapter cannot prove all requested "
                                "authority constraints"
                            ),
                        ),
                    )
                )
                if not requirement.required:
                    warnings.append(
                        "optional capability authority constraint denied: "
                        f"{requirement.capability_ref.name}"
                    )
                continue
            resolved.append(
                ResolvedCapability(
                    kind=requirement.kind,
                    requested_ref=requirement.capability_ref,
                    required=requirement.required,
                    exposure=requirement.exposure,
                    status="resolved",
                    resolved_ref=entry.ref,
                    adapter=entry.adapter,
                    effective_interface_version=requirement.minimum_interface_version,
                    effective_permissions=tuple(sorted(requested_permissions)),
                    satisfied_authority_constraints=tuple(
                        sorted(requested_constraints)
                    ),
                    context_refs=(
                        requirement.instruction_refs
                        if requirement.exposure
                        in {"instructions", "instructions_and_schema"}
                        else ()
                    ),
                )
            )

        for runtime_requirement in spec.agent_inventory.runtime_requirements:
            if runtime_requirement.capability not in self.runtime_capabilities:
                if runtime_requirement.required:
                    missing.append(f"runtime:{runtime_requirement.capability}")
                    issues.append(
                        AdmissionIssue(
                            category="runtime",
                            subject_ref=runtime_requirement.capability,
                            reason=ResolutionReason(
                                code="unsupported",
                                detail="runtime capability is not implemented",
                            ),
                            blocking=True,
                        )
                    )
                else:
                    warnings.append(
                        f"optional runtime capability unavailable: {runtime_requirement.capability}"
                    )

        workspace_status: Literal["resolved", "unsupported", "denied", "unavailable"]
        if spec.workspace.runtime_kind not in self.workspace_runtime_kinds:
            workspace_status = "unsupported"
            issues.append(
                AdmissionIssue(
                    category="workspace",
                    subject_ref=spec.workspace.runtime_kind,
                    reason=ResolutionReason(
                        code="unsupported", detail="workspace runtime is not implemented"
                    ),
                    blocking=True,
                )
            )
        elif any(
            not any(
                binding.visibility in {"subject", "subject_and_evaluator"}
                and binding.mount_name == mount.name
                and binding.source == mount.source
                and binding.mount_access == mount.access
                for binding in spec.scenario.input_bindings
            )
            for mount in spec.workspace.mounts
        ):
            workspace_status = "denied"
            issues.append(
                AdmissionIssue(
                    category="workspace",
                    subject_ref="mount_authority",
                    reason=ResolutionReason(
                        code="denied",
                        detail="workspace mount is not an exact Subject-visible scenario input",
                    ),
                    blocking=True,
                )
            )
        elif any(item.access != "read_only" for item in spec.workspace.mounts):
            workspace_status = "unsupported"
            issues.append(
                AdmissionIssue(
                    category="workspace",
                    subject_ref="read_write_mount",
                    reason=ResolutionReason(
                        code="unsupported",
                        detail="the active workspace adapter only supports read-only inputs",
                    ),
                    blocking=True,
                )
            )
        elif (
            spec.workspace.write_zones
            or spec.workspace.secret_binding_refs
            or spec.workspace.snapshot_policy.capture_workspace
            or spec.workspace.snapshot_policy.include_zones
            or spec.workspace.cleanup_policy.mode != "discard"
        ):
            workspace_status = "unsupported"
            issues.append(
                AdmissionIssue(
                    category="workspace",
                    subject_ref=spec.workspace.runtime_kind,
                    reason=ResolutionReason(
                        code="unsupported",
                        detail=(
                            "workspace requests write, secret, snapshot, or retention "
                            "features that the active adapter does not implement"
                        ),
                    ),
                    blocking=True,
                )
            )
        elif spec.workspace.network_policy.mode not in self.network_modes:
            workspace_status = "denied"
            denied_policies.append(f"network:{spec.workspace.network_policy.mode}")
            issues.append(
                AdmissionIssue(
                    category="policy",
                    subject_ref=f"network:{spec.workspace.network_policy.mode}",
                    reason=ResolutionReason(
                        code="denied", detail="network policy is not allowed by this runtime"
                    ),
                    blocking=True,
                )
            )
        elif spec.workspace.external_effect_policy.mode not in self.external_effect_modes:
            workspace_status = "denied"
            denied_policies.append(
                f"external_effect:{spec.workspace.external_effect_policy.mode}"
            )
            issues.append(
                AdmissionIssue(
                    category="policy",
                    subject_ref=(
                        f"external_effect:{spec.workspace.external_effect_policy.mode}"
                    ),
                    reason=ResolutionReason(
                        code="denied",
                        detail="external effect policy is not allowed by this runtime",
                    ),
                    blocking=True,
                )
            )
        else:
            workspace_status = "resolved"
        interaction_status: Literal["resolved", "unsupported"] = (
            "resolved"
            if spec.interaction_protocol.mode in self.interaction_modes
            else "unsupported"
        )
        if interaction_status != "resolved":
            issues.append(
                AdmissionIssue(
                    category="interaction",
                    subject_ref=spec.interaction_protocol.mode,
                    reason=ResolutionReason(
                        code="unsupported", detail="interaction mode is not implemented"
                    ),
                    blocking=True,
                )
            )
        elif (
            spec.interaction_protocol.max_turns != 1
            or spec.interaction_protocol.system_prompt_ref is not None
            or spec.interaction_protocol.initial_message_refs
        ):
            interaction_status = "unsupported"
            issues.append(
                AdmissionIssue(
                    category="interaction",
                    subject_ref="single_turn_materialization",
                    reason=ResolutionReason(
                        code="unsupported",
                        detail=(
                            "the active runner supports one direct turn without "
                            "materialized prompt artifacts"
                        ),
                    ),
                    blocking=True,
                )
            )
        if spec.capture_policy.default_mode == "raw_encrypted":
            denied_policies.append("capture:raw_encrypted")
            issues.append(
                AdmissionIssue(
                    category="policy",
                    subject_ref="capture:raw_encrypted",
                    reason=ResolutionReason(
                        code="denied",
                        detail=(
                            "the active runner has no encrypted Subject-output artifact sink"
                        ),
                    ),
                    blocking=True,
                )
            )
        required_capability_failed = any(
            item.required and item.status != "resolved" for item in resolved
        )
        blocked = bool(missing or denied_policies) or required_capability_failed
        blocked = blocked or workspace_status != "resolved" or interaction_status != "resolved"

        inventory = ResolvedAgentInventory(
            requirement_ref=spec.agent_inventory_ref,
            runner_ref=runner or spec.agent_inventory.runner_ref,
            provider_profile_id=provider_id,
            provider_profile_digest=provider_digest,
            provider_model=provider_model,
            provider_reasoning_effort=provider_reasoning,
            provider_adapter=provider_adapter,
            capabilities=tuple(resolved),
            runtime_capabilities=tuple(sorted(self.runtime_capabilities)),
        )
        return AdmissionRecord(
            run_spec_ref=f"run-spec:{spec.digest}",
            run_spec_digest=spec.digest,
            decision="rejected" if blocked else "admitted",
            resolved_inventory=inventory,
            workspace_status=workspace_status,
            interaction_status=interaction_status,
            missing_requirements=tuple(missing),
            denied_policies=tuple(denied_policies),
            issues=tuple(issues),
            warnings=tuple(warnings),
            created_at_utc=utc_now(),
        )


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
            else tuple(
                item.model_copy(
                    update={
                        "source": item.source.model_copy(update={"locator": None})
                    }
                )
                for item in declared_visible_inputs
            )
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
        if any(item.source.locator is not None for item in visible_inputs):
            raise ValueError("Subject inputs cannot expose storage locators")
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
        return SubjectEnvelope(
            run_spec_digest=spec.digest,
            goal=spec.goal,
            inputs=visible_inputs,
            interaction_protocol=spec.interaction_protocol,
            effective_capabilities=effective_capabilities,
            workspace=workspace,
            budgets=spec.budgets,
            stop_conditions=spec.stop_conditions,
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
