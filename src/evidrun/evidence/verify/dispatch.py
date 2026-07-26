"""Bundle verification entrypoint: checksums, event chain, and dispatch by version.

Three independent axes decide validity, and all three must hold. Checksums prove the
bytes are the ones sealed. The event chain replays the ledger's own rules: hash chain,
lifecycle transitions, and the subject/tool pairing invariants. Record checks are
dispatched by `schema_version`, which is the only place format knowledge lives.

A bundle that only checksums is not audited: `audit_complete` stays false when no
record layer ran.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any, cast

from evidrun.contracts import normalize_event_payload
from evidrun.contracts.runtime import (
    EVENT_ALLOWED_RUN_STATUSES,
    UNSUPPORTED_RUNTIME_EVENT_TYPES,
)
from evidrun.evidence.verify.v2 import verify_v2_records, verify_v2_structure
from evidrun.evidence.verify.v3 import verify_v3_records, verify_v3_structure
from evidrun.shared.types import canonical_json, sha256_json

TERMINAL_STATES = frozenset(
    {"completed", "failed", "cancelled", "budget_exhausted", "guardrail_stopped"}
)

ALLOWED_ACTOR_TYPES = frozenset(
    {"system", "subject", "evaluator", "tool", "skill", "observer"}
)

PRE_TERMINAL_STATES = frozenset({"queued", "preparing", "running", "paused", "evaluating"})

TRANSITIONS: dict[str, tuple[frozenset[str], str]] = {
    "run.preparing": (frozenset({"queued"}), "preparing"),
    "run.running": (frozenset({"preparing"}), "running"),
    "run.paused": (frozenset({"running"}), "paused"),
    "run.resumed": (frozenset({"paused"}), "running"),
    "run.evaluating": (frozenset({"running"}), "evaluating"),
    "run.completed": (frozenset({"evaluating"}), "completed"),
    "run.failed": (PRE_TERMINAL_STATES, "failed"),
    "run.cancelled": (PRE_TERMINAL_STATES, "cancelled"),
    "run.budget_exhausted": (PRE_TERMINAL_STATES, "budget_exhausted"),
    "run.guardrail_stopped": (PRE_TERMINAL_STATES, "guardrail_stopped"),
}

TOOL_TERMINAL_TYPES = frozenset({"tool.completed", "tool.denied", "tool.failed"})


def verify(bundle_path: Path) -> dict[str, Any]:
    """Verifica um bundle nos três eixos. `valid` exige que todos passem."""

    with zipfile.ZipFile(bundle_path) as archive:
        member_names = archive.namelist()
        names = set(member_names)
        if "checksums.json" not in names:
            raise ValueError("bundle has no checksums.json")
        checksum_results = _verify_checksums(archive, member_names, names)
        chain_results = {
            name: _chain_valid(
                [json.loads(line) for line in archive.read(name).splitlines() if line],
                run_id=Path(name).stem,
            )
            for name in sorted(item for item in names if item.startswith("events/"))
        }
        record_results = _verify_records(archive, names)

    valid = (
        all(checksum_results.values())
        and all(chain_results.values())
        and all(record_results.values())
    )
    return {
        "valid": valid,
        "integrity_valid": valid,
        "audit_complete": valid and bool(record_results),
        "portable": False,
        "replayable": False,
        "checksums": checksum_results,
        "event_chains": chain_results,
        "records": record_results,
    }


def _verify_checksums(
    archive: zipfile.ZipFile, member_names: list[str], names: set[str]
) -> dict[str, bool]:
    """Todo membro casa com seu digest, a lista é exata, e não há nome duplicado.

    A lista exata é o que impede arquivo injetado sem entrada de checksum; o nome
    duplicado é o que impede dois membros com o mesmo caminho no zip.
    """

    checksums = json.loads(archive.read("checksums.json"))["files"]
    results: dict[str, bool] = {}
    for name, expected in checksums.items():
        try:
            actual = hashlib.sha256(archive.read(name)).hexdigest()
        except KeyError:
            results[name] = False
        else:
            results[name] = actual == expected
    results["__complete_file_list__"] = set(checksums) == names - {"checksums.json"}
    results["__unique_file_names__"] = len(member_names) == len(names)
    return results


def _verify_records(archive: zipfile.ZipFile, names: set[str]) -> dict[str, bool]:
    """Despacho por `schema_version`: v1 não tem camada de record, logo não é auditável."""

    if "bundle.json" not in names:
        return {}
    bundle_manifest = json.loads(archive.read("bundle.json"))
    version = bundle_manifest.get("schema_version")
    if version == "2":
        results = verify_v2_records(archive, names)
        results["__bundle_structure__"] = verify_v2_structure(bundle_manifest, names)
        return results
    if version == "3":
        results = verify_v3_records(archive, names)
        results["__bundle_structure__"] = verify_v3_structure(bundle_manifest, names)
        return results
    return {}


class _ChainState:
    """Estado corrente do replay de uma cadeia de eventos de uma Run."""

    __slots__ = (
        "current_status",
        "offered_capabilities",
        "previous",
        "subject_invocations",
        "subject_responses",
        "tool_calls",
        "tool_terminals",
    )

    def __init__(self) -> None:
        self.previous: str | None = None
        self.current_status = "queued"
        self.subject_invocations = 0
        self.subject_responses = 0
        self.offered_capabilities: set[str] = set()
        self.tool_calls: dict[str, str] = {}
        self.tool_terminals: set[str] = set()

    @property
    def subject_open(self) -> bool:
        """Há uma invocação do Subject aguardando resposta."""

        return self.subject_invocations == self.subject_responses + 1


def _chain_valid(events: list[dict[str, Any]], *, run_id: str) -> bool:
    """Replay do ledger: hash chain, lifecycle, e o pareamento subject/tool.

    Todo `tool.called` precisa terminar: uma chamada sem terminal invalida a cadeia,
    o que é verificado ao final e não durante o loop.
    """

    state = _ChainState()
    for expected_sequence, event in enumerate(events, start=1):
        stored_event = dict(event)
        stored_hash = event.pop("event_hash")
        event_type = str(event.get("type"))
        payload = event.get("payload")
        if not _envelope_valid(
            event, run_id=run_id, sequence=expected_sequence, stored_hash=stored_hash, state=state
        ):
            return False
        try:
            if normalize_event_payload(event_type, payload) != payload:
                return False
        except TypeError, ValueError:
            return False
        if not _ordering_valid(event_type, sequence=expected_sequence, state=state):
            return False
        if not _subject_and_tool_valid(event_type, payload, state=state):
            return False
        if not _transition_valid(event, event_type, state=state):
            return False
        state.previous = stored_hash
        event.update(stored_event)
    return set(state.tool_calls) == state.tool_terminals


def _envelope_valid(
    event: dict[str, Any],
    *,
    run_id: str,
    sequence: int,
    stored_hash: str,
    state: _ChainState,
) -> bool:
    """O envelope do evento: identidade, ator, elo anterior e o próprio hash."""

    return not (
        event.get("schema_version") != "1"
        or event.get("run_id") != run_id
        or event.get("sequence") != sequence
        or event.get("actor_type") not in ALLOWED_ACTOR_TYPES
        or not str(event.get("actor_id", "")).strip()
        or str(event.get("type")) in UNSUPPORTED_RUNTIME_EVENT_TYPES
        or event.get("prev_event_hash") != state.previous
        or sha256_json(event) != stored_hash
    )


def _ordering_valid(event_type: str, *, sequence: int, state: _ChainState) -> bool:
    """`run.queued` abre a Run e só ela; nada segue um estado terminal."""

    if sequence == 1:
        return event_type == "run.queued"
    if event_type == "run.queued" or state.current_status in TERMINAL_STATES:
        return False
    allowed_statuses = EVENT_ALLOWED_RUN_STATUSES.get(event_type)
    return allowed_statuses is None or state.current_status in allowed_statuses


def _subject_and_tool_valid(event_type: str, payload: Any, *, state: _ChainState) -> bool:
    """Uma interação por vez: tool só existe dentro de um turno aberto do Subject."""

    if event_type == "subject.invoked":
        if state.subject_invocations != state.subject_responses:
            return False
        state.subject_invocations += 1
    if event_type == "subject.responded":
        if not state.subject_open:
            return False
        state.subject_responses += 1
    if event_type == "capability.offered":
        state.offered_capabilities.add(canonical_json(payload["capability_ref"]))
    if event_type == "tool.called" and not _tool_call_valid(payload, state=state):
        return False
    if event_type in TOOL_TERMINAL_TYPES and not _tool_terminal_valid(
        event_type, payload, state=state
    ):
        return False
    return not (
        event_type in {"run.evaluating", "run.completed"} and state.subject_responses == 0
    )


def _tool_call_valid(payload: Any, *, state: _ChainState) -> bool:
    """Tool chamada uma vez, sobre capability oferecida, com argumentos referenciados."""

    call_id = str(payload["call_id"])
    capability = canonical_json(payload["capability_ref"])
    arguments_ref = payload.get("arguments_ref")
    if (
        not state.subject_open
        or call_id in state.tool_calls
        or capability not in state.offered_capabilities
        or not isinstance(arguments_ref, dict)
    ):
        return False
    arguments_document = cast("dict[str, object]", arguments_ref)
    if (
        arguments_document.get("media_type") != "application/json"
        or arguments_document.get("classification") != "internal"
    ):
        return False
    state.tool_calls[call_id] = capability
    return True


def _tool_terminal_valid(event_type: str, payload: Any, *, state: _ChainState) -> bool:
    """Um único terminal por chamada, coerente com a capability que foi chamada."""

    call_id = str(payload["call_id"])
    if (
        not state.subject_open
        or call_id not in state.tool_calls
        or call_id in state.tool_terminals
    ):
        return False
    if event_type in {"tool.completed", "tool.failed"} and (
        canonical_json(payload["capability_ref"]) != state.tool_calls[call_id]
    ):
        return False
    if event_type == "tool.completed" and not isinstance(payload.get("result_ref"), dict):
        return False
    state.tool_terminals.add(call_id)
    return True


def _transition_valid(event: dict[str, Any], event_type: str, *, state: _ChainState) -> bool:
    """Transição de lifecycle declarada tem de casar com o estado corrente."""

    transition = TRANSITIONS.get(event_type)
    if transition is None:
        return True
    allowed_from, target = transition
    payload = event.get("payload", {})
    if (
        state.current_status not in allowed_from
        or payload.get("from_status") not in {None, state.current_status}
        or payload.get("status") not in {None, target}
    ):
        return False
    state.current_status = target
    return True
