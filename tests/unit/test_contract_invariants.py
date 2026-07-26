"""Cross-cutting contract invariants: secret bindings, digests and matrix determinism."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from evidrun.contracts import (
    StudyRevision,
    VariantSpec,
    WorkspaceTemplateRevision,
)
from evidrun.contracts.compiler import (
    StudyCompiler,
)
from evidrun.shared.types import (
    EvidenceMode,
    sha256_bytes,
    sha256_json,
)
from tests.support.contract_fixtures import (
    accept,
    baseline_specs,
    legacy_package,
)


def test_secret_bindings_cannot_carry_credential_values() -> None:
    _, package = legacy_package()
    workspace = next(
        revision
        for revision in package.revisions
        if isinstance(revision, WorkspaceTemplateRevision)
    )
    document = workspace.payload.model_dump(mode="json")
    document["secret_binding_refs"] = [
        {
            "binding_id": "cliproxyapi-local",
            "source": "keychain",
            "value": "must-never-enter-a-contract",
        }
    ]
    with pytest.raises(ValidationError, match="Extra inputs"):
        type(workspace.payload).model_validate(document)


@given(st.binary(min_size=1, max_size=32))
@settings(deadline=None)
def test_contract_refs_reject_a_mismatched_digest(payload: bytes) -> None:
    _, package, registry, _ = baseline_specs()
    wrong_digest = sha256_bytes(payload)
    if wrong_digest == package.study.digest:
        return
    wrong_ref = package.study.ref.model_copy(update={"digest": wrong_digest})
    with pytest.raises(ValueError, match="digest mismatch"):
        registry.resolve(wrong_ref)


@given(repetitions=st.integers(min_value=1, max_value=4), variants=st.integers(1, 4))
@settings(deadline=None)
def test_study_matrix_size_is_deterministic(repetitions: int, variants: int) -> None:
    _, package, registry, _ = baseline_specs()
    study = StudyRevision(
        logical_id=package.study.logical_id,
        revision=2,
        project_id=package.study.project_id,
        title="Property-based Study matrix",
        payload=package.study.payload.model_copy(
            update={
                "evidence_mode": EvidenceMode.EXPLORATORY,
                "variants": tuple(
                    VariantSpec(id=f"variant-{index}", label=f"Variant {index}")
                    for index in range(variants)
                ),
                "repetitions": repetitions,
                "comparisons": (),
            }
        ),
    )
    accept(registry, study)
    specs = StudyCompiler(registry).compile(study)
    assert len(specs) == variants * repetitions * len(study.payload.scenario_refs)
    coordinates = {
        (spec.scenario_ref.logical_id, spec.variant_id, spec.repetition_index)
        for spec in specs
    }
    assert len(coordinates) == len(specs)


@given(st.dictionaries(st.text(min_size=1, max_size=8), st.integers(), max_size=12))
@settings(deadline=None)
def test_canonical_digest_is_independent_of_mapping_order(values: dict[str, int]) -> None:
    reversed_values = dict(reversed(tuple(values.items())))
    assert sha256_json(values) == sha256_json(reversed_values)
