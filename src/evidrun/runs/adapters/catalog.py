"""The catalog: which adapters are wired, and what that entitles a Run to.

Two responsibilities that must not drift apart:

- `capability_envelope()` is the ONLY producer of the declared execution surface.
  A capability reaches it exclusively when an adapter backs it, which is why the
  provider block, the tool catalog, and the raw-capture flag all turn on together
  with `real_subject`.
- `subject_for` and `evaluator_for` resolve an adapter only when the admission
  record still matches it. They are authority gates, not lookups.
"""

from __future__ import annotations

from collections.abc import Callable

from evidrun.contracts import AdmissionRecord, CapabilityDescriptorRef, RunSpec
from evidrun.contracts.admission import (
    AdmissionService,
    CapabilityCatalogEntry,
    ProviderCatalogEntry,
    RuntimeCapabilityEnvelope,
)
from evidrun.contracts.runtime.spec import AdmissionIssue
from evidrun.runs.adapters.grader_cause import ExactCauseGraderAdapter
from evidrun.runs.adapters.grader_read_answer import ExactReadAnswerGraderAdapter
from evidrun.runs.adapters.materializer import ArtifactInputMaterializer
from evidrun.runs.adapters.subject_responses import ResponsesReadAgentAdapter
from evidrun.runs.adapters.subject_scripted import ScriptedLogInvestigatorAdapter
from evidrun.runs.admission import (
    RealSubjectContract,
    check_evaluator_resolution,
    check_real_spec,
    check_scripted_spec,
    check_shared_spec,
)
from evidrun.runs.admission import issue as catalog_issue

PROVIDER_ADAPTER = "openai-responses@1"
READ_TOOL_ADAPTER = "read-artifact-text@1"

SubjectKey = tuple[str, str, str, str]
SubjectAdapter = ScriptedLogInvestigatorAdapter | ResponsesReadAgentAdapter
EvaluatorAdapter = ExactCauseGraderAdapter | ExactReadAnswerGraderAdapter


class RuntimeAdapterCatalog:
    def __init__(
        self,
        *,
        subject: ScriptedLogInvestigatorAdapter | None = None,
        real_subject: ResponsesReadAgentAdapter | None = None,
        evaluator: ExactCauseGraderAdapter | None = None,
        real_evaluator: ExactReadAnswerGraderAdapter | None = None,
        materializer: ArtifactInputMaterializer | None = None,
        project_id_for_spec: Callable[[RunSpec], str] | None = None,
    ) -> None:
        self.subject = subject or ScriptedLogInvestigatorAdapter()
        self.real_subject = real_subject
        self.evaluator = evaluator or ExactCauseGraderAdapter()
        self.real_evaluator = real_evaluator or ExactReadAnswerGraderAdapter()
        self.materializer = materializer
        self.project_id_for_spec = project_id_for_spec
        self._subjects: dict[SubjectKey, SubjectAdapter] = {
            self._subject_key(self.subject.ref): self.subject
        }
        if self.real_subject is not None:
            self._subjects[self._subject_key(self.real_subject.ref)] = self.real_subject

    @staticmethod
    def _subject_key(reference: CapabilityDescriptorRef) -> SubjectKey:
        return (
            reference.namespace,
            reference.name,
            reference.version,
            reference.digest,
        )

    def capability_envelope(self) -> RuntimeCapabilityEnvelope:
        """Declare the execution surface from the adapters that are actually wired."""

        runners = tuple(adapter.ref for adapter in self._subjects.values())
        if self.real_subject is None:
            return RuntimeCapabilityEnvelope.declare(runners=runners)
        tool = self.real_subject.tool
        return RuntimeCapabilityEnvelope.declare(
            runners=runners,
            capabilities=(
                CapabilityCatalogEntry(
                    ref=tool.ref,
                    adapter=READ_TOOL_ADAPTER,
                    allowed_permissions=frozenset({tool.allowed_permission}),
                    compatible_interface_versions=frozenset({"1"}),
                    satisfied_authority_constraints=frozenset({tool.authority_constraint}),
                ),
            ),
            providers=(
                ProviderCatalogEntry(
                    profile_id=self.real_subject.profile.id,
                    profile_digest=self.real_subject.profile_digest,
                    model=self.real_subject.profile.model,
                    reasoning_effort=self.real_subject.profile.reasoning_effort,
                    adapter=PROVIDER_ADAPTER,
                ),
            ),
            runtime_capabilities=("provider_tool_loop",),
            network_modes=("disabled", "provider_only"),
            supported_budget_fields=("max_tool_calls",),
            supports_raw_encrypted_capture=True,
        )

    def admission_service(self) -> AdmissionService:
        return AdmissionService(
            envelope=self.capability_envelope(),
            execution_validators=(self.validate_spec,),
        )

    def validate_spec(self, spec: RunSpec) -> tuple[AdmissionIssue, ...]:
        """Run the concrete adapter layer for the pair resolved for this RunSpec.

        Order matters: the shared checks, then the pair-specific ones, then the
        evaluator resolution. `AdmissionRecord.issues` is a persisted tuple, so a
        reordering here is an observable change.
        """

        subject = self._subjects.get(self._subject_key(spec.agent_inventory.runner_ref))
        if subject is None:
            return (
                catalog_issue(
                    "runner_adapter",
                    "the admitted runner has no exact executable adapter",
                ),
            )
        issues = check_shared_spec(
            spec,
            materializer=self.materializer,
            project_id_for_spec=self.project_id_for_spec,
        )
        if isinstance(subject, ScriptedLogInvestigatorAdapter):
            issues.extend(check_scripted_spec(spec, evaluator=self.evaluator))
        else:
            issues.extend(
                check_real_spec(
                    spec,
                    contract=self._real_subject_contract(subject),
                    evaluator=self.real_evaluator,
                )
            )
        issues.extend(
            check_evaluator_resolution(
                spec, evaluators=(self.evaluator, self.real_evaluator)
            )
        )
        return tuple(issues)

    @staticmethod
    def _real_subject_contract(
        subject: ResponsesReadAgentAdapter,
    ) -> RealSubjectContract:
        """Project the wired real adapter into the contract its checks assert."""

        return RealSubjectContract(
            profile_id=subject.profile.id,
            tool_ref=subject.tool.ref,
            allowed_permission=subject.tool.allowed_permission,
            authority_constraint=subject.tool.authority_constraint,
            credential_available=subject.credential_available,
        )

    def subject_for(self, spec: RunSpec, admission: AdmissionRecord) -> SubjectAdapter:
        """Resolve the Subject only when the admitted record still matches it."""

        subject = self._subjects.get(self._subject_key(spec.agent_inventory.runner_ref))
        if (
            subject is None
            or admission.resolved_inventory.runner_ref != subject.ref
            or admission.run_spec_digest != spec.digest
            or admission.decision != "admitted"
        ):
            raise ValueError("admitted runner cannot be resolved by the active catalog")
        if isinstance(subject, ResponsesReadAgentAdapter):
            self._assert_provider_resolution(admission, subject)
        return subject

    @staticmethod
    def _assert_provider_resolution(
        admission: AdmissionRecord, subject: ResponsesReadAgentAdapter
    ) -> None:
        """The admitted provider and tool must still be exactly what is wired."""

        resolved = admission.resolved_inventory
        if (
            resolved.provider_profile_id != subject.profile.id
            or resolved.provider_profile_digest != subject.profile_digest
            or resolved.provider_model != subject.profile.model
            or resolved.provider_reasoning_effort != subject.profile.reasoning_effort
            or resolved.provider_adapter != PROVIDER_ADAPTER
            or len(resolved.capabilities) != 1
            or resolved.capabilities[0].status != "resolved"
            or resolved.capabilities[0].resolved_ref != subject.tool.ref
        ):
            raise ValueError(
                "admitted provider or tool resolution drifted from the active catalog"
            )

    def evaluator_for(self, spec: RunSpec) -> EvaluatorAdapter:
        for evaluator in (self.evaluator, self.real_evaluator):
            if evaluator.supports(spec):
                return evaluator
        raise ValueError("EvaluationPlan cannot be resolved by the active catalog")
