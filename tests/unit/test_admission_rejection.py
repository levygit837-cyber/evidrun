"""Operator-visible admission rejection causes, sourced from the admission oracle."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evidrun.contracts.admission import admission_rejection_error
from evidrun.infrastructure.artifacts.store import ArtifactStore, MemoryKeyProvider
from tests.support.admission_cases import build_admission_cases, build_catalogs
from tests.support.admission_specs import oracle_profile
from tests.support.execution_trust import unpersisted_unverified_trust

SNAPSHOT_PATH = Path(__file__).with_name("admission_oracle.json")
SNAPSHOT: dict[str, list[str]] = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
ISSUE_ONLY_REJECTIONS = tuple(
    name
    for name, fingerprint in SNAPSHOT.items()
    if "decision=rejected" in fingerprint
    and not any(line.startswith(("missing=", "denied=")) for line in fingerprint)
)


@pytest.mark.parametrize("case_name", ISSUE_ONLY_REJECTIONS)
def test_issue_only_oracle_rejection_cites_every_blocking_subject(
    case_name: str, tmp_path: Path
) -> None:
    """Every formerly empty cause names the persisted blocking issues in order."""

    assert len(ISSUE_ONLY_REJECTIONS) == 35
    store = ArtifactStore(tmp_path / "artifacts", MemoryKeyProvider())
    cases = {case.name: case for case in build_admission_cases(store)}
    catalogs = build_catalogs(store, profile=oracle_profile())
    case = cases[case_name]
    record = catalogs[case.catalog].admission_service().admit(case.spec, unpersisted_unverified_trust(case.spec))

    error = admission_rejection_error(record)
    blocking_refs = tuple(item.subject_ref for item in record.issues if item.blocking)

    assert error.issues == record.issues
    assert error.missing_requirements == record.missing_requirements
    assert error.denied_policies == record.denied_policies
    assert blocking_refs
    assert all(subject_ref in error.message for subject_ref in blocking_refs)
    assert [error.message.index(subject_ref) for subject_ref in blocking_refs] == sorted(
        error.message.index(subject_ref) for subject_ref in blocking_refs
    )


def test_required_unresolved_capability_is_visible_without_changing_the_record(
    tmp_path: Path,
) -> None:
    store = ArtifactStore(tmp_path / "artifacts", MemoryKeyProvider())
    cases = {case.name: case for case in build_admission_cases(store)}
    catalogs = build_catalogs(store, profile=oracle_profile())
    case = cases["required_capability_unregistered"]

    record = catalogs[case.catalog].admission_service().admit(case.spec, unpersisted_unverified_trust(case.spec))
    record_before = record.model_dump(mode="json")
    error = admission_rejection_error(record)

    assert "unregistered-tool-v1" in error.message
    assert error.unresolved_required_capabilities == (
        record.resolved_inventory.capabilities[0].requested_ref,
    )
    payload = error.model_dump(mode="json")
    assert payload["unresolved_required_capabilities"] == [
        record.resolved_inventory.capabilities[0].requested_ref.model_dump(mode="json")
    ]
    assert record.model_dump(mode="json") == record_before
    assert record.missing_requirements == ()
    assert record.denied_policies == ()


@pytest.mark.parametrize(
    ("case_name", "later_prefix"),
    (
        ("provider_profile_unavailable", "missing:"),
        ("restricted_input_classification", "denied:"),
    ),
)
def test_structured_finding_groups_keep_the_record_order_in_the_message(
    case_name: str, later_prefix: str, tmp_path: Path
) -> None:
    store = ArtifactStore(tmp_path / "artifacts", MemoryKeyProvider())
    cases = {case.name: case for case in build_admission_cases(store)}
    catalogs = build_catalogs(store, profile=oracle_profile())
    case = cases[case_name]
    record = catalogs[case.catalog].admission_service().admit(case.spec, unpersisted_unverified_trust(case.spec))

    error = admission_rejection_error(record)

    assert error.issues == record.issues
    assert error.missing_requirements == record.missing_requirements
    assert error.denied_policies == record.denied_policies
    assert error.message.index("issue:") < error.message.index(later_prefix)
