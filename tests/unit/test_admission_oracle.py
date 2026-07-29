"""Equivalence oracle for the two admission layers.

`admit()` always runs the declared capability envelope AND the concrete adapter
validators. This module freezes their combined observable output, so a structural
refactor cannot silently promote a capability, drop a rejection, or reword a
`reason.detail`.

The expected fingerprints live in `tests/unit/admission_oracle.json`. Regenerate
only when a behavioural change is intended and reviewed:

    uv run python -m tests.support.admission_oracle_snapshot
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evidrun.infrastructure.artifacts.store import ArtifactStore, MemoryKeyProvider
from tests.support.admission_cases import build_admission_cases, build_catalogs
from tests.support.admission_specs import admission_fingerprint, oracle_profile
from tests.support.execution_trust import unpersisted_unverified_trust

SNAPSHOT_PATH = Path(__file__).with_name("admission_oracle.json")


def _oracle(tmp_path: Path) -> dict[str, tuple[str, ...]]:
    store = ArtifactStore(tmp_path / "artifacts", MemoryKeyProvider())
    catalogs = build_catalogs(store, profile=oracle_profile())
    observed: dict[str, tuple[str, ...]] = {}
    for case in build_admission_cases(store):
        service = catalogs[case.catalog].admission_service()
        observed[case.name] = admission_fingerprint(
            service.admit(case.spec, unpersisted_unverified_trust(case.spec))
        )
    return observed


def _snapshot() -> dict[str, list[str]]:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def test_admission_case_names_are_unique_and_snapshotted(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts", MemoryKeyProvider())
    cases = build_admission_cases(store)
    names = [case.name for case in cases]

    assert len(names) == len(set(names))
    assert set(names) == set(_snapshot())


@pytest.mark.parametrize("case_name", sorted(_snapshot()))
def test_admission_decision_is_byte_identical_to_the_oracle(case_name: str, tmp_path: Path) -> None:
    expected = tuple(_snapshot()[case_name])

    assert _oracle(tmp_path)[case_name] == expected


def test_unavailable_provider_profile_rejects_instead_of_raising(
    tmp_path: Path,
) -> None:
    """A provider profile absent from the catalog is a rejection, never an exception.

    Both admission callers persist the returned record; raising instead would leave
    the RunSpec with no AdmissionRecord at all, and no Run can exist without one.
    """

    store = ArtifactStore(tmp_path / "artifacts", MemoryKeyProvider())
    cases = {case.name: case for case in build_admission_cases(store)}
    catalogs = build_catalogs(store, profile=oracle_profile())
    case = cases["provider_profile_unavailable"]

    record = (
        catalogs[case.catalog]
        .admission_service()
        .admit(case.spec, unpersisted_unverified_trust(case.spec))
    )

    assert record.decision == "rejected"
    assert "provider:ghost-profile" in record.missing_requirements
    assert (
        "issue=provider|ghost-profile|unavailable|provider profile is not available "
        "in the active runtime|blocking=True"
    ) in admission_fingerprint(record)
    assert record.resolved_inventory.provider_profile_id is None
    assert record.resolved_inventory.provider_model is None


def test_only_declared_supported_shapes_are_admitted(tmp_path: Path) -> None:
    """An optional requirement that the runtime cannot serve warns; it never blocks."""

    observed = _oracle(tmp_path)
    admitted = {name for name, lines in observed.items() if "decision=admitted" in lines}

    assert admitted == {
        "scripted_baseline_admitted",
        "real_baseline_admitted",
        "optional_runtime_capability_missing",
    }
    assert (
        "warning=optional runtime capability unavailable: nested_agents"
        in observed["optional_runtime_capability_missing"]
    )


def test_every_rejected_case_carries_a_blocking_issue_or_a_denied_policy(
    tmp_path: Path,
) -> None:
    for name, lines in _oracle(tmp_path).items():
        if "decision=admitted" in lines:
            continue
        blocking = any(line.endswith("|blocking=True") for line in lines)
        accounted = any(line.startswith(("missing=", "denied=")) for line in lines)
        assert blocking or accounted, f"{name} rejects without an observable reason"


def test_promotion_attack_specs_stay_rejected_with_their_exact_message(
    tmp_path: Path,
) -> None:
    """The nine promotion attempts named by WS-12 keep their exact rejection."""

    observed = _oracle(tmp_path)
    attacks: dict[str, str] = {
        "evaluation_two_stages": (
            "issue=runtime|evaluation_pipeline|unsupported|the active runtime supports "
            "one deterministic boolean grader triggered by subject.responded|blocking=True"
        ),
        "checkpoint_policy_present": (
            "issue=runtime|checkpoint_coordinator|unsupported|checkpoint contracts are "
            "valid, but the active runtime does not observe triggers, execute "
            "validators, or create records|blocking=True"
        ),
        "progress_artifact_policy_present": (
            "issue=observer|background_progress_observer|unsupported|background progress "
            "observer is not implemented|blocking=True"
        ),
        "subject_disclosure_pre_run": (
            "issue=interaction|evaluation_disclosure:pre_run|unsupported|the active "
            "runner receives objective and context only; it does not consume Subject "
            "evaluation guidance|blocking=True"
        ),
        "bounded_exploration_goal": (
            "issue=runtime|bounded_exploration_terminal|unsupported|the active "
            "deterministic runner only emits goal_state terminal results|blocking=True"
        ),
        "interaction_max_turns_two": (
            "issue=interaction|single_turn_materialization|unsupported|the active runner "
            "supports one direct turn without materialized prompt artifacts|blocking=True"
        ),
        "workspace_runtime_kind_unsupported": (
            "issue=workspace|container|unsupported|workspace runtime is not "
            "implemented|blocking=True"
        ),
        "workspace_read_write_mount": (
            "issue=workspace|read_write_mount|unsupported|the active workspace adapter "
            "only supports read-only inputs|blocking=True"
        ),
        "real_credential_unavailable": (
            "issue=provider|provider_credential|unavailable|the provider credential is "
            "unavailable to the worker composition|blocking=True"
        ),
    }
    for name, expected_issue in attacks.items():
        lines = observed[name]
        assert "decision=rejected" in lines, f"{name} was promoted"
        assert expected_issue in lines, f"{name} lost its exact rejection message"


def test_uncovered_branches_named_by_the_brief_are_now_exercised(tmp_path: Path) -> None:
    """The five branches WS-12 measured as having zero coverage."""

    observed = _oracle(tmp_path)
    assert (
        "issue=runner|scripted-log-investigator-v1|unsupported|runner is not registered "
        "with the required digest|blocking=True"
    ) in observed["runner_digest_mismatch"]
    assert (
        "issue=workspace|mount_authority|denied|workspace mount is not an exact "
        "Subject-visible scenario input|blocking=True"
    ) in observed["workspace_mount_authority_mismatch"]
    assert (
        "issue=workspace|read_write_mount|unsupported|the active workspace adapter only "
        "supports read-only inputs|blocking=True"
    ) in observed["workspace_read_write_mount"]
    assert (
        "issue=workspace|container|unsupported|workspace runtime is not implemented|blocking=True"
    ) in observed["workspace_runtime_kind_unsupported"]
    assert (
        "issue=provider|provider_credential|unavailable|the provider credential is "
        "unavailable to the worker composition|blocking=True"
    ) in observed["real_credential_unavailable"]
