"""Per-family factual checks for `append_event`.

Each function answers one question: given the Run, its prior events and the
normalized payload, may this event type be appended right now? They only raise —
the caller owns the session, the hash chain and the status advance, so an event
that fails here leaves nothing written.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, cast

from evidrun.contracts import (
    AdmissionRecord,
    RunSpec,
)
from evidrun.infrastructure.database.models import (
    AdmissionRecordRow,
    RunEventRow,
    RunRow,
    RunSpecRow,
    SubjectEnvelopeRow,
)
from evidrun.shared.types import canonical_json

__all__ = [
    "check_capability_offered",
    "check_subject_invoked",
    "check_subject_responded",
    "check_tool_events",
]


def check_subject_invoked(
    session: Any,
    run: RunRow,
    run_id: str,
    normalized_payload: Mapping[str, Any],
) -> None:
    if run.run_spec_id is None or run.admission_id is None:
        raise ValueError("Subject invocation requires canonical Run contracts")
    invoked_spec_row = session.get(RunSpecRow, run.run_spec_id)
    invoked_admission_row = session.get(AdmissionRecordRow, run.admission_id)
    invoked_envelope_row = session.get(SubjectEnvelopeRow, run_id)
    if (
        invoked_spec_row is None
        or invoked_admission_row is None
        or invoked_envelope_row is None
    ):
        raise ValueError("Subject invocation references missing canonical evidence")
    invoked_spec = RunSpec.model_validate(json.loads(invoked_spec_row.spec_json))
    invoked_admission = AdmissionRecord.model_validate(
        json.loads(invoked_admission_row.record_json)
    )
    provider_fields = {
        "provider_profile_id": (
            invoked_admission.resolved_inventory.provider_profile_id
        ),
        "provider_model": invoked_admission.resolved_inventory.provider_model,
        "provider_reasoning_effort": (
            invoked_admission.resolved_inventory.provider_reasoning_effort
        ),
        "provider_adapter": invoked_admission.resolved_inventory.provider_adapter,
    }
    if (
        normalized_payload.get("runner")
        != invoked_admission.resolved_inventory.runner_ref.name
        or normalized_payload.get("network")
        != invoked_spec.workspace.network_policy.mode
        or normalized_payload.get("subject_envelope_digest")
        != invoked_envelope_row.digest
        or any(
            normalized_payload.get(field) != value
            for field, value in provider_fields.items()
        )
    ):
        raise ValueError(
            "Subject invocation does not match admitted runner/provider evidence"
        )


def check_subject_responded(
    session: Any,
    run: RunRow,
    normalized_payload: Mapping[str, Any],
) -> None:
    if run.run_spec_id is None:
        raise ValueError("Subject response requires a canonical RunSpec")
    response_spec_row = session.get(RunSpecRow, run.run_spec_id)
    if response_spec_row is None:
        raise ValueError("Subject response references a missing RunSpec")
    response_spec = RunSpec.model_validate(json.loads(response_spec_row.spec_json))
    if (
        normalized_payload.get("capture_mode")
        != response_spec.capture_policy.default_mode
    ):
        raise ValueError(
            "Subject response capture mode does not match the RunSpec policy"
        )


def check_capability_offered(
    session: Any,
    run: RunRow,
    normalized_payload: Mapping[str, Any],
) -> None:
    if run.admission_id is None:
        raise ValueError("capability offer requires a canonical admission")
    offered_admission_row = session.get(AdmissionRecordRow, run.admission_id)
    if offered_admission_row is None:
        raise ValueError("capability offer references a missing admission")
    offered_admission = AdmissionRecord.model_validate(
        json.loads(offered_admission_row.record_json)
    )
    offered_ref = normalized_payload["capability_ref"]
    matches = [
        item
        for item in offered_admission.resolved_inventory.capabilities
        if item.status == "resolved"
        and item.resolved_ref is not None
        and item.resolved_ref.model_dump(mode="json") == offered_ref
    ]
    if len(matches) != 1 or (
        matches[0].required != normalized_payload["required"]
        or matches[0].exposure != normalized_payload["exposure"]
        or list(matches[0].effective_permissions)
        != normalized_payload["effective_permissions"]
    ):
        raise ValueError("capability offer does not match the admitted inventory")


def check_tool_events(
    event_type: str,
    normalized_payload: Mapping[str, Any],
    prior_events: Sequence[RunEventRow],
    prior_event_types: Sequence[str],
) -> None:
    if prior_event_types.count("subject.invoked") != (
        prior_event_types.count("subject.responded") + 1
    ):
        raise ValueError("tool events require one active Subject invocation")
    tool_calls: dict[str, tuple[dict[str, object], str]] = {}
    tool_terminals: set[str] = set()
    offered_refs: set[str] = set()
    for prior in prior_events:
        prior_payload = json.loads(prior.payload_json)
        if prior.event_type == "capability.offered":
            offered_refs.add(canonical_json(prior_payload["capability_ref"]))
        elif prior.event_type == "tool.called":
            tool_calls[str(prior_payload["call_id"])] = (
                prior_payload,
                prior.id,
            )
        elif prior.event_type in {
            "tool.denied",
            "tool.completed",
            "tool.failed",
        }:
            tool_terminals.add(str(prior_payload["call_id"]))
    call_id = str(normalized_payload["call_id"])
    if event_type == "tool.called":
        capability_document = normalized_payload["capability_ref"]
        arguments_ref = normalized_payload.get("arguments_ref")
        if (
            call_id in tool_calls
            or canonical_json(capability_document) not in offered_refs
            or not isinstance(arguments_ref, dict)
        ):
            raise ValueError(
                "tool call is duplicate, unoffered, or missing canonical arguments"
            )
        arguments_document = cast(dict[str, object], arguments_ref)
        if (
            arguments_document.get("media_type") != "application/json"
            or arguments_document.get("classification") != "internal"
        ):
            raise ValueError(
                "tool call is duplicate, unoffered, or missing canonical arguments"
            )
    else:
        called = tool_calls.get(call_id)
        if called is None or call_id in tool_terminals:
            raise ValueError("tool result requires one unmatched canonical call")
        called_capability = called[0]["capability_ref"]
        if event_type in {"tool.completed", "tool.failed"} and (
            normalized_payload["capability_ref"] != called_capability
        ):
            raise ValueError("tool result capability does not match its call")
        if event_type == "tool.completed" and not isinstance(
            normalized_payload.get("result_ref"), dict
        ):
            raise ValueError("completed tool call requires a result artifact")
