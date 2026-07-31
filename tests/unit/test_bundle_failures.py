"""Bundle verification names why it refused, on the same terms as the triage phases.

`verify()` answers three boolean maps. They decide `valid`, but a consumer cannot say *why*
a bundle failed without reading key names and guessing their meaning. These pin the derived
codes as the stable answer, and pin that the derivation stays additive: it reads the maps
and never contradicts `valid`.
"""

from __future__ import annotations

import pytest

from evidrun.evidence.verify.failures import (
    CATEGORY_BY_CODE,
    BundleVerificationCategory,
    BundleVerificationCode,
    BundleVerificationFailure,
    BundleVerificationRefused,
    bundle_failures,
    validate_bundle_failure_tables,
)

EXPECTED_CODES = {
    "bundle.checksums_absent",
    "bundle.checksum_mismatch",
    "bundle.file_list_incomplete",
    "bundle.duplicate_file_name",
    "bundle.event_chain_invalid",
    "bundle.structure_invalid",
    "bundle.record_invalid",
}


def test_codes_and_category_table_are_exhaustive() -> None:
    assert {code.value for code in BundleVerificationCode} == EXPECTED_CODES
    assert set(CATEGORY_BY_CODE) == set(BundleVerificationCode)
    assert all(code.value.startswith("bundle.") for code in BundleVerificationCode)
    validate_bundle_failure_tables()


def test_the_category_table_is_immutable() -> None:
    assert type(CATEGORY_BY_CODE).__name__ == "mappingproxy"


def test_a_verified_bundle_names_no_failure() -> None:
    failures = bundle_failures(
        checksums={"bundle.json": True, "__complete_file_list__": True},
        event_chains={"events/run-1.jsonl": True},
        records={"__v4_records__": True, "__bundle_structure__": True},
    )
    # `failures` and `valid` cannot disagree about whether something was refused.
    assert failures == ()


def test_whole_archive_properties_get_their_own_codes() -> None:
    failures = bundle_failures(
        checksums={"__complete_file_list__": False, "__unique_file_names__": False},
        event_chains={},
        records={},
    )

    # An injected file and a duplicated member name are different attacks, so a consumer
    # must be able to tell them apart without parsing a key name.
    assert failures == (
        BundleVerificationFailure(BundleVerificationCode.FILE_LIST_INCOMPLETE),
        BundleVerificationFailure(BundleVerificationCode.DUPLICATE_FILE_NAME),
    )
    assert all(
        item.category is BundleVerificationCategory.INTEGRITY for item in failures
    )


def test_a_member_mismatch_carries_the_member_as_its_subject() -> None:
    failures = bundle_failures(
        checksums={"evaluations/run-1.json": False, "bundle.json": True},
        event_chains={},
        records={},
    )

    assert failures == (
        BundleVerificationFailure(
            BundleVerificationCode.CHECKSUM_MISMATCH, subject="evaluations/run-1.json"
        ),
    )
    assert failures[0].document() == {
        "code": "bundle.checksum_mismatch",
        "category": "integrity",
        "subject": "evaluations/run-1.json",
    }


def test_each_axis_maps_to_its_declared_category() -> None:
    failures = bundle_failures(
        checksums={"bundle.json": False},
        event_chains={"events/run-1.jsonl": False},
        records={"__bundle_structure__": False, "run-records/run-1.json": False},
    )
    by_code = {item.code: item for item in failures}

    assert by_code[BundleVerificationCode.CHECKSUM_MISMATCH].category is (
        BundleVerificationCategory.INTEGRITY
    )
    assert by_code[BundleVerificationCode.EVENT_CHAIN_INVALID].category is (
        BundleVerificationCategory.LEDGER
    )
    assert by_code[BundleVerificationCode.STRUCTURE_INVALID].category is (
        BundleVerificationCategory.RECORD
    )
    assert by_code[BundleVerificationCode.RECORD_INVALID].category is (
        BundleVerificationCategory.RECORD
    )


def test_ordering_is_deterministic_across_axes_and_subjects() -> None:
    arguments = {
        "checksums": {"z.json": False, "a.json": False},
        "event_chains": {"events/z.jsonl": False, "events/a.jsonl": False},
        "records": {"z-record.json": False, "a-record.json": False},
    }

    # Integrity, then ledger, then record; each sorted by subject. A stable order is what
    # lets a caller diff two verifications without sorting first.
    assert [(item.code.value, item.subject) for item in bundle_failures(**arguments)] == [
        ("bundle.checksum_mismatch", "a.json"),
        ("bundle.checksum_mismatch", "z.json"),
        ("bundle.event_chain_invalid", "events/a.jsonl"),
        ("bundle.event_chain_invalid", "events/z.jsonl"),
        ("bundle.record_invalid", "a-record.json"),
        ("bundle.record_invalid", "z-record.json"),
    ]
    assert bundle_failures(**arguments) == bundle_failures(**arguments)


def test_a_structure_failure_has_no_subject() -> None:
    failures = bundle_failures(
        checksums={}, event_chains={}, records={"__bundle_structure__": False}
    )

    # The layout of the whole bundle is the subject; naming a member would be wrong.
    assert failures[0].subject is None
    assert failures[0].document()["subject"] is None


def test_the_refusal_exception_stays_catchable_as_value_error() -> None:
    failure = BundleVerificationFailure(BundleVerificationCode.CHECKSUMS_ABSENT)

    with pytest.raises(ValueError) as captured:
        raise BundleVerificationRefused(failure)

    assert isinstance(captured.value, BundleVerificationRefused)
    assert captured.value.failure.code is BundleVerificationCode.CHECKSUMS_ABSENT
    assert captured.value.failure.category is BundleVerificationCategory.INTEGRITY


def test_a_refusal_projects_the_same_shape_a_completed_verification_returns() -> None:
    refused = BundleVerificationRefused(
        BundleVerificationFailure(BundleVerificationCode.CHECKSUMS_ABSENT)
    )

    # A border prints this instead of a generic message, so a caller reads `valid` and
    # `failures` identically whether verification completed or refused outright.
    assert refused.document() == {
        "valid": False,
        "failures": [
            {
                "code": "bundle.checksums_absent",
                "category": "integrity",
                "subject": None,
            }
        ],
    }


def test_adding_a_code_without_a_category_fails_the_table_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    incomplete = {
        code: category
        for code, category in CATEGORY_BY_CODE.items()
        if code is not BundleVerificationCode.RECORD_INVALID
    }
    monkeypatch.setattr(
        "evidrun.evidence.verify.failures.CATEGORY_BY_CODE", incomplete
    )

    with pytest.raises(ValueError, match="must match declared codes"):
        validate_bundle_failure_tables()
