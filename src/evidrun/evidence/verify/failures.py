"""Stable codes for what a bundle verification actually refused.

`verify()` answers three boolean maps: checksums, event chains and records. That is enough
to decide `valid`, but a consumer cannot say *why* a bundle failed without reading key names
and guessing their meaning. A refused bundle is an observable outcome of a public seam, so it
gets codes on the same terms as the triage phases.

The derivation is additive by construction: it reads the maps `verify()` already produces and
never changes `valid`, `checksums`, `event_chains` or `records`. Existing consumers keep
working; a new consumer classifies by `code` instead of by key naming convention.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType

__all__ = [
    "CATEGORY_BY_CODE",
    "BundleVerificationCategory",
    "BundleVerificationCode",
    "BundleVerificationFailure",
    "BundleVerificationRefused",
    "bundle_failures",
    "validate_bundle_failure_tables",
]

#: Result keys that report a whole-archive property rather than one member.
_COMPLETE_FILE_LIST_KEY = "__complete_file_list__"
_UNIQUE_FILE_NAMES_KEY = "__unique_file_names__"
_BUNDLE_STRUCTURE_KEY = "__bundle_structure__"


class BundleVerificationCode(StrEnum):
    """Why a bundle was refused. Prefixed by seam, like every other stable code."""

    CHECKSUMS_ABSENT = "bundle.checksums_absent"
    CHECKSUM_MISMATCH = "bundle.checksum_mismatch"
    FILE_LIST_INCOMPLETE = "bundle.file_list_incomplete"
    DUPLICATE_FILE_NAME = "bundle.duplicate_file_name"
    EVENT_CHAIN_INVALID = "bundle.event_chain_invalid"
    STRUCTURE_INVALID = "bundle.structure_invalid"
    RECORD_INVALID = "bundle.record_invalid"


class BundleVerificationCategory(StrEnum):
    """The axis a refusal belongs to, derived from the code and never from text."""

    #: The bytes are not the ones sealed, or the archive does not enumerate itself.
    INTEGRITY = "integrity"
    #: The ledger replay contradicts the runtime's own rules.
    LEDGER = "ledger"
    #: A persisted record or the bundle layout does not reproduce.
    RECORD = "record"


class BundleVerificationFailure:
    """One refusal: the code, its category and the subject it was found on."""

    __slots__ = ("code", "subject")

    def __init__(self, code: BundleVerificationCode, subject: str | None = None) -> None:
        self.code = code
        self.subject = subject

    @property
    def category(self) -> BundleVerificationCategory:
        return CATEGORY_BY_CODE[self.code]

    def document(self) -> dict[str, str | None]:
        return {
            "code": self.code.value,
            "category": self.category.value,
            "subject": self.subject,
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BundleVerificationFailure):
            return NotImplemented
        return (self.code, self.subject) == (other.code, other.subject)

    def __hash__(self) -> int:
        return hash((self.code, self.subject))

    def __repr__(self) -> str:
        return f"BundleVerificationFailure({self.code.value!r}, {self.subject!r})"


class BundleVerificationRefused(ValueError):
    """A bundle could not be verified at all, named rather than described.

    Derives from `ValueError` so existing callers keep catching it, but carries the
    failure so a border classifies by code instead of by message text.
    """

    def __init__(self, failure: BundleVerificationFailure) -> None:
        super().__init__(failure.code.value)
        self.failure = failure


CATEGORY_BY_CODE: Mapping[BundleVerificationCode, BundleVerificationCategory] = (
    MappingProxyType(
        {
            BundleVerificationCode.CHECKSUMS_ABSENT: BundleVerificationCategory.INTEGRITY,
            BundleVerificationCode.CHECKSUM_MISMATCH: BundleVerificationCategory.INTEGRITY,
            BundleVerificationCode.FILE_LIST_INCOMPLETE: BundleVerificationCategory.INTEGRITY,
            BundleVerificationCode.DUPLICATE_FILE_NAME: BundleVerificationCategory.INTEGRITY,
            BundleVerificationCode.EVENT_CHAIN_INVALID: BundleVerificationCategory.LEDGER,
            BundleVerificationCode.STRUCTURE_INVALID: BundleVerificationCategory.RECORD,
            BundleVerificationCode.RECORD_INVALID: BundleVerificationCategory.RECORD,
        }
    )
)


def validate_bundle_failure_tables() -> None:
    """Every declared code has a category. Adding one without a category fails import."""

    declared = set(BundleVerificationCode)
    missing = declared - set(CATEGORY_BY_CODE)
    orphaned = set(CATEGORY_BY_CODE) - declared
    if missing or orphaned:
        raise ValueError(
            "bundle verification category table must match declared codes; "
            f"missing={sorted(str(item) for item in missing)}, "
            f"orphaned={sorted(str(item) for item in orphaned)}"
        )


def bundle_failures(
    *,
    checksums: Mapping[str, bool],
    event_chains: Mapping[str, bool],
    records: Mapping[str, bool],
) -> tuple[BundleVerificationFailure, ...]:
    """Name every refusal in the maps `verify()` produced, in canonical order.

    Order is deterministic: integrity, then ledger, then record, each sorted by subject.
    A bundle that verifies produces an empty tuple, so `failures` and `valid` cannot
    disagree about whether something was refused.
    """

    failures: list[BundleVerificationFailure] = []
    for name in sorted(checksums):
        if checksums[name]:
            continue
        if name == _COMPLETE_FILE_LIST_KEY:
            failures.append(
                BundleVerificationFailure(BundleVerificationCode.FILE_LIST_INCOMPLETE)
            )
        elif name == _UNIQUE_FILE_NAMES_KEY:
            failures.append(
                BundleVerificationFailure(BundleVerificationCode.DUPLICATE_FILE_NAME)
            )
        else:
            failures.append(
                BundleVerificationFailure(
                    BundleVerificationCode.CHECKSUM_MISMATCH, subject=name
                )
            )
    failures.extend(
        BundleVerificationFailure(
            BundleVerificationCode.EVENT_CHAIN_INVALID, subject=name
        )
        for name in sorted(event_chains)
        if not event_chains[name]
    )
    for name in sorted(records):
        if records[name]:
            continue
        code = (
            BundleVerificationCode.STRUCTURE_INVALID
            if name == _BUNDLE_STRUCTURE_KEY
            else BundleVerificationCode.RECORD_INVALID
        )
        subject = None if name == _BUNDLE_STRUCTURE_KEY else name
        failures.append(BundleVerificationFailure(code, subject=subject))
    return tuple(failures)


validate_bundle_failure_tables()
