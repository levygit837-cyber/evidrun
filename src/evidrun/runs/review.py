"""Deterministic ReviewPackage projection and diff over persisted ReviewTargets."""

from __future__ import annotations

from html import escape

from evidrun.contracts import (
    ContractRef,
    ExecutionTrustRecord,
    ReviewPackage,
    ReviewPackageDiff,
    ReviewRevisionChange,
    ReviewRevisionDocument,
    ReviewRunSpec,
    ReviewRunSpecChange,
    RunSpec,
    semantic_model_dump,
)
from evidrun.contracts.admission.service import AdmissionService
from evidrun.infrastructure.database import Repository
from evidrun.infrastructure.database.trust import ExecutionReviewMaterial
from evidrun.shared.types import Classification, canonical_json

RevisionKey = tuple[str, str]
RunSpecSlot = tuple[str, str, int]


class ReviewPackageService:
    """Build packages only from targets whose complete lineage is already stored."""

    def __init__(
        self,
        repository: Repository,
        admission_service: AdmissionService,
    ) -> None:
        self._repository = repository
        self._admission_service = admission_service

    def build(
        self,
        review_target_digest: str,
        *,
        compare_to_digest: str | None = None,
    ) -> ReviewPackage:
        current = self._repository.execution_trust.get_review_material(
            review_target_digest
        )
        package = self._project(current)
        if compare_to_digest is None:
            return package
        previous = self._repository.execution_trust.get_review_material(
            compare_to_digest
        )
        if previous.target.project_id != current.target.project_id:
            raise ValueError("ReviewPackage diff cannot cross a Project boundary")
        return package.model_copy(update={"diff": self._diff(previous, current)})

    def _project(self, material: ExecutionReviewMaterial) -> ReviewPackage:
        target = material.target
        study_ref = next(
            revision.ref
            for revision in material.revisions
            if revision.ref.contract_type.value == "study"
        )
        closure = tuple(
            ReviewRevisionDocument(
                ref=revision.ref,
                document=semantic_model_dump(revision),
            )
            for revision in material.revisions
        )
        run_specs = tuple(
            _project_run_spec(spec, trust, self._admission_service)
            for spec, trust in zip(
                material.run_specs, material.trust_records, strict=True
            )
        )
        return ReviewPackage(
            review_target=target,
            review_target_digest=target.review_target_digest,
            study_ref=study_ref,
            closure=closure,
            run_specs=run_specs,
        )

    @staticmethod
    def _diff(
        previous: ExecutionReviewMaterial,
        current: ExecutionReviewMaterial,
    ) -> ReviewPackageDiff:
        old_refs = {_revision_key(item.ref): item.ref for item in previous.revisions}
        new_refs = {_revision_key(item.ref): item.ref for item in current.revisions}
        added_keys = sorted(new_refs.keys() - old_refs.keys())
        removed_keys = sorted(old_refs.keys() - new_refs.keys())
        shared_ref_keys = sorted(old_refs.keys() & new_refs.keys())
        changed_refs = tuple(
            ReviewRevisionChange(
                contract_type=new_refs[key].contract_type,
                logical_id=new_refs[key].logical_id,
                before=old_refs[key],
                after=new_refs[key],
            )
            for key in shared_ref_keys
            if old_refs[key] != new_refs[key]
        )

        old_specs = {_run_spec_slot(spec): spec for spec in previous.run_specs}
        new_specs = {_run_spec_slot(spec): spec for spec in current.run_specs}
        added_slots = sorted(new_specs.keys() - old_specs.keys())
        removed_slots = sorted(old_specs.keys() - new_specs.keys())
        shared_slots = sorted(old_specs.keys() & new_specs.keys())
        changed_specs = tuple(
            ReviewRunSpecChange(
                slot=_slot_label(slot),
                before_digest=old_specs[slot].digest,
                after_digest=new_specs[slot].digest,
            )
            for slot in shared_slots
            if old_specs[slot].digest != new_specs[slot].digest
        )
        semantic_changes = _semantic_changes(
            old_specs,
            new_specs,
            added_keys=added_keys,
            removed_keys=removed_keys,
            changed_refs=changed_refs,
        )
        return ReviewPackageDiff(
            base_review_target_digest=previous.target.review_target_digest,
            revision_refs_added=tuple(new_refs[key] for key in added_keys),
            revision_refs_removed=tuple(old_refs[key] for key in removed_keys),
            revision_refs_changed=changed_refs,
            run_specs_added=tuple(new_specs[slot].digest for slot in added_slots),
            run_specs_removed=tuple(old_specs[slot].digest for slot in removed_slots),
            run_specs_changed=changed_specs,
            semantic_changes=semantic_changes,
        )


def _project_run_spec(
    spec: RunSpec,
    trust: ExecutionTrustRecord,
    admission_service: AdmissionService,
) -> ReviewRunSpec:
    permissions = tuple(
        sorted(
            {
                permission
                for requirement in spec.agent_inventory.capability_requirements
                for permission in requirement.requested_permissions
            }
        )
    )
    classifications = tuple(sorted(_classifications(spec), key=lambda item: item.value))
    limitations = tuple(
        dict.fromkeys(
            (
                *spec.limitations,
                *spec.evaluation_plan.limitations,
                "ReviewPackage is a projection, not human authority",
                "The isolation label does not claim an operating-system sandbox",
            )
        )
    )
    admission = admission_service.admit(spec, trust)
    return ReviewRunSpec(
        run_spec_digest=spec.digest,
        run_spec=spec,
        subject_disclosure=spec.evaluation_plan.disclosure.subject,
        capability_requirements=spec.agent_inventory.capability_requirements,
        requested_permissions=permissions,
        classifications=classifications,
        network=spec.workspace.network_policy,
        external_effects=spec.workspace.external_effect_policy,
        evaluation_plan=spec.evaluation_plan,
        hidden_input_refs=spec.evaluation_plan.disclosure.hidden_input_refs,
        limitations=limitations,
        isolation=spec.workspace.runtime_kind,
        known_admission_refusals=(
            admission.issues if admission.decision == "rejected" else ()
        ),
        missing_requirements=(
            admission.missing_requirements
            if admission.decision == "rejected"
            else ()
        ),
        denied_policies=(
            admission.denied_policies if admission.decision == "rejected" else ()
        ),
    )


def _classifications(spec: RunSpec) -> set[Classification]:
    refs = [item.source for item in spec.scenario.input_bindings]
    refs.extend(item.source for item in spec.workspace.mounts)
    refs.extend(spec.evaluation_plan.disclosure.hidden_input_refs)
    refs.extend(
        artifact
        for requirement in spec.agent_inventory.capability_requirements
        for artifact in requirement.instruction_refs
    )
    refs.extend(spec.interaction_protocol.initial_message_refs)
    refs.extend(
        artifact
        for extension in spec.extensions
        for artifact in (extension.schema_ref, extension.payload_ref)
    )
    if spec.interaction_protocol.system_prompt_ref is not None:
        refs.append(spec.interaction_protocol.system_prompt_ref)
    return {item.classification for item in refs}


def _revision_key(reference: ContractRef) -> RevisionKey:
    return reference.contract_type.value, reference.logical_id


def _run_spec_slot(spec: RunSpec) -> RunSpecSlot:
    return spec.scenario_ref.logical_id, spec.variant_id, spec.repetition_index


def _slot_label(slot: RunSpecSlot) -> str:
    return f"{slot[0]}:{slot[1]}:{slot[2]}"


def _semantic_changes(
    old_specs: dict[RunSpecSlot, RunSpec],
    new_specs: dict[RunSpecSlot, RunSpec],
    *,
    added_keys: list[RevisionKey],
    removed_keys: list[RevisionKey],
    changed_refs: tuple[ReviewRevisionChange, ...],
) -> tuple[str, ...]:
    changes = [f"closure.added[{kind}:{logical_id}]" for kind, logical_id in added_keys]
    changes.extend(
        f"closure.removed[{kind}:{logical_id}]" for kind, logical_id in removed_keys
    )
    changes.extend(
        f"closure.changed[{item.contract_type.value}:{item.logical_id}]"
        for item in changed_refs
    )
    fields = (
        "agent_inventory",
        "workspace",
        "interaction_protocol",
        "evaluation_plan",
        "goal",
        "scenario",
        "budgets",
        "stop_conditions",
        "capture_policy",
        "limitations",
    )
    for slot in sorted(old_specs.keys() & new_specs.keys()):
        old_document = semantic_model_dump(old_specs[slot])
        new_document = semantic_model_dump(new_specs[slot])
        for field in fields:
            if canonical_json(old_document.get(field)) != canonical_json(
                new_document.get(field)
            ):
                changes.append(f"run_specs[{_slot_label(slot)}].{field}")
    return tuple(changes)


def render_review_package_html(package: ReviewPackage) -> str:
    """Printable projection; never introduces a review_package_digest."""

    rows = "".join(
        "<tr>"
        f"<td>{escape(item.run_spec.variant_id)}</td>"
        f"<td>{item.run_spec.repetition_index}</td>"
        f"<td><code>{escape(item.run_spec_digest)}</code></td>"
        f"<td>{escape(item.subject_disclosure.mode)}</td>"
        f"<td>{escape(item.network.mode)}</td>"
        f"<td>{escape(item.external_effects.mode)}</td>"
        f"<td>{escape(item.isolation)}</td>"
        "</tr>"
        for item in package.run_specs
    )
    return (
        "<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
        "<title>ReviewPackage</title><style>"
        "@page{margin:22mm 14mm}body{font:14px sans-serif;color:#17202a}"
        "header,footer{position:fixed;left:0;right:0;font-size:10px}"
        "header{top:-16mm}footer{bottom:-16mm}table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #bbb;padding:6px;text-align:left}code{word-break:break-all}"
        "</style></head><body>"
        f"<header>ReviewTarget {escape(package.review_target_digest)} · "
        f"Project {escape(package.review_target.project_id)}</header>"
        f"<footer>ReviewTarget {escape(package.review_target_digest)} · "
        "Projeção de revisão, não autoridade humana</footer>"
        "<h1>ReviewPackage</h1><p><strong>Identidade:</strong> ReviewTarget "
        f"<code>{escape(package.review_target_digest)}</code></p>"
        "<p>Este documento não possui <code>review_package_digest</code> e não constitui "
        "confirmação humana.</p><h2>RunSpecs</h2><table><thead><tr>"
        "<th>Variant</th><th>Repetição</th><th>Digest</th><th>Disclosure</th>"
        "<th>Network</th><th>Efeitos</th><th>Isolamento</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></body></html>"
    )
