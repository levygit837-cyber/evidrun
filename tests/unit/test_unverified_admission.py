from __future__ import annotations

from collections.abc import Callable

import pytest

from evidrun.contracts import (
    ArtifactRef,
    ExecutionRevisionSet,
    ExecutionTrustRecord,
    RunSpec,
)
from evidrun.contracts.authoring.workspace import ExternalEffectPolicy, NetworkPolicy
from evidrun.evidence import archive as ar
from evidrun.shared.types import Classification, new_id, sha256_bytes, utc_now
from tests.support.admission_specs import (
    ORACLE_LOG_BYTES,
    ORACLE_PROJECT_ID,
    build_scripted_run_spec,
    scripted_admission_service,
)


def _trust(spec: RunSpec) -> ExecutionTrustRecord:
    references = tuple(
        sorted(
            ar.spec_revision_refs(spec),
            key=lambda item: (
                item.contract_type.value,
                item.logical_id,
                item.revision,
                item.digest,
            ),
        )
    )
    revision_set = ExecutionRevisionSet(
        project_id=ORACLE_PROJECT_ID,
        study_ref=spec.study_ref,
        revision_refs=references,
    )
    return ExecutionTrustRecord(
        trust_id=new_id("trust"),
        kind="unverified_revision_set",
        project_id=ORACLE_PROJECT_ID,
        study_ref=spec.study_ref,
        revision_refs=references,
        revision_set_digest=revision_set.revision_set_digest,
        run_spec_digest=spec.digest,
        created_at_utc=utc_now(),
    )


def _source(classification: Classification = Classification.INTERNAL) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=f"unverified-{classification.value}",
        digest=sha256_bytes(ORACLE_LOG_BYTES),
        media_type="text/plain",
        classification=classification,
    )


def test_unverified_internal_offline_policy_is_admitted() -> None:
    spec = build_scripted_run_spec(source=_source())
    admission = scripted_admission_service(spec.agent_inventory.runner_ref).admit(
        spec, _trust(spec)
    )
    assert admission.decision == "admitted"
    assert admission.execution_trust is not None


def _sensitive(spec: RunSpec) -> RunSpec:
    source = _source(Classification.SENSITIVE)
    return spec.model_copy(
        update={
            "scenario": spec.scenario.model_copy(
                update={
                    "input_bindings": (
                        spec.scenario.input_bindings[0].model_copy(
                            update={"source": source}
                        ),
                    )
                }
            ),
            "workspace": spec.workspace.model_copy(
                update={
                    "mounts": (
                        spec.workspace.mounts[0].model_copy(
                            update={"source": source}
                        ),
                    )
                }
            ),
        }
    )


def _external_effect(spec: RunSpec) -> RunSpec:
    return spec.model_copy(
        update={
            "workspace": spec.workspace.model_copy(
                update={
                    "external_effect_policy": ExternalEffectPolicy(
                        mode="approval_required"
                    )
                }
            )
        }
    )


def _allowlist_network(spec: RunSpec) -> RunSpec:
    return spec.model_copy(
        update={
            "workspace": spec.workspace.model_copy(
                update={
                    "network_policy": NetworkPolicy(
                        mode="allowlist",
                        allowed_endpoint_refs=("network:forbidden",),
                    )
                }
            )
        }
    )


def _unproved_provider_only(spec: RunSpec) -> RunSpec:
    return spec.model_copy(
        update={
            "workspace": spec.workspace.model_copy(
                update={"network_policy": NetworkPolicy(mode="provider_only")}
            )
        }
    )


POLICY_CASES: list[tuple[Callable[[RunSpec], RunSpec], str]] = [
    (_sensitive, "unverified_classification:sensitive"),
    (_external_effect, "unverified_external_effect:approval_required"),
    (_allowlist_network, "unverified_network:allowlist"),
    (_unproved_provider_only, "provider_only:resolved_provider"),
]


@pytest.mark.parametrize(
    ("mutate", "expected_policy"),
    POLICY_CASES,
)
def test_unverified_policy_rejects_unsafe_or_unproved_execution(
    mutate: Callable[[RunSpec], RunSpec],
    expected_policy: str,
) -> None:
    spec = mutate(build_scripted_run_spec(source=_source()))
    admission = scripted_admission_service(spec.agent_inventory.runner_ref).admit(
        spec, _trust(spec)
    )
    assert admission.decision == "rejected"
    assert expected_policy in (
        *admission.denied_policies,
        *admission.missing_requirements,
    )


def test_execution_trust_cannot_be_swapped_between_run_specs() -> None:
    spec = build_scripted_run_spec(source=_source())
    other = spec.model_copy(update={"variant_id": "other-variant"})
    with pytest.raises(ValueError, match="exact RunSpec"):
        scripted_admission_service(other.agent_inventory.runner_ref).admit(
            other, _trust(spec)
        )
