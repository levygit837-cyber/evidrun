"""Catálogo de capabilities executáveis e recusas ativas da admissão."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, cast

from evidrun.contracts.admission.checks.unsupported import (
    check_budgets,
    check_checkpoint_coordinator,
    check_evaluation_pipeline,
    check_goal_mode,
    check_human_adjudication,
    check_progress_observer,
    check_stop_conditions,
    check_subject_disclosure,
)
from evidrun.contracts.admission.envelope import RuntimeCapabilityEnvelope
from evidrun.contracts.authoring.evaluation import SubjectEvaluationDisclosure

Readable = Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class CapabilityCatalog:
    """As duas metades derivadas da mesma admissão/catálogo ativo."""

    admitted: tuple[Readable, ...]
    active_rejections: tuple[Readable, ...]

    def __post_init__(self) -> None:
        if not self.admitted or not self.active_rejections:
            raise ValueError("capability catalog requires admitted and rejected entries")
        if any(not item.get("code") for item in self.active_rejections):
            raise ValueError("every active capability rejection requires its admission code")


class CapabilityCatalogSource(Protocol):
    def capability_catalog(self) -> CapabilityCatalog: ...


_MODE_SCHEMA = SubjectEvaluationDisclosure.model_json_schema()["properties"]["mode"]
_DISCLOSURE_MODES = tuple(
    str(item) for item in _MODE_SCHEMA["enum"] if item != "none"
)


@dataclass(frozen=True, slots=True)
class AdmissionCapabilityCatalog:
    """Deriva o catálogo do envelope ativo e dos próprios checkers de admissão."""

    envelope: RuntimeCapabilityEnvelope

    def capability_catalog(self) -> CapabilityCatalog:
        admitted_entries = (
            *(
                _entry("interaction_mode", item)
                for item in self.envelope.interaction_modes
            ),
            *(
                _entry("runtime_capability", item)
                for item in self.envelope.runtime_capabilities
            ),
            *(
                _entry("budget", item)
                for item in self.envelope.supported_budget_fields
            ),
            *(
                {
                    "kind": "capability",
                    "name": entry.ref.name,
                    "namespace": entry.ref.namespace,
                    "version": entry.ref.version,
                    "digest": entry.ref.digest,
                }
                for entry in self.envelope.capabilities.values()
            ),
        )
        budget_fields = set(_budget_fields()) - set(self.envelope.supported_budget_fields)
        rejection_entries = (
            *(
                {"name": field, "code": f"{_budget_prefix()}{field}"}
                for field in sorted(budget_fields)
            ),
            *_missing_entries(check_checkpoint_coordinator),
            *_missing_entries(check_progress_observer),
            *_missing_entries(check_evaluation_pipeline),
            *_missing_entries(check_human_adjudication),
            *_missing_entries(check_goal_mode),
            *_missing_entries(check_stop_conditions),
            *(
                {
                    "name": "subject_disclosure",
                    "code": f"{_disclosure_prefix()}{mode}",
                }
                for mode in _DISCLOSURE_MODES
            ),
        )
        return CapabilityCatalog(
            admitted=admitted_entries,
            active_rejections=tuple(rejection_entries),
        )


def _entry(kind: str, name: str) -> Readable:
    return {"kind": kind, "name": name}


def _missing_entries(checker: object, prefix: str = "runtime:") -> tuple[Readable, ...]:
    codes = _checker_string_constants(checker)
    return tuple(
        {"name": code.removeprefix(prefix), "code": code}
        for code in codes
        if code.startswith(prefix)
    )


def _budget_fields() -> tuple[str, ...]:
    constants = _checker_string_constants(check_budgets)
    fields = (
        "max_turns",
        "max_input_tokens",
        "max_output_tokens",
        "max_tool_calls",
        "max_cost",
    )
    return tuple(item for item in fields if item in constants)


def _budget_prefix() -> str:
    return _source_value(check_budgets, "runtime:budget:")


def _disclosure_prefix() -> str:
    return _source_value(check_subject_disclosure, "evaluation_disclosure:")


def _source_value(checker: object, expected: str) -> str:
    if expected not in _checker_string_constants(checker):
        raise RuntimeError(f"admission checker no longer declares {expected}")
    return expected


def _checker_string_constants(checker: object) -> tuple[str, ...]:
    code = getattr(checker, "__code__", None)
    constants = cast(tuple[object, ...], getattr(code, "co_consts", ()))
    flattened: list[str] = []
    for item in constants:
        if isinstance(item, str):
            flattened.append(item)
        elif isinstance(item, tuple):
            nested = cast(tuple[object, ...], item)
            flattened.extend(
                value for value in nested if isinstance(value, str)
            )
    return tuple(flattened)
