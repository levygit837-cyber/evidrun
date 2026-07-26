"""Zip writing, checksums and the artifact manifest of a bundle.

The audit profile records artifact identity and digest, never bytes: every entry
here carries `content_included=False`. An `ArtifactRef` names content; it grants no
access, mount, export or read.
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any, cast

from evidrun.contracts import (
    ArtifactManifest,
    ArtifactManifestEntry,
    ArtifactRef,
    ArtifactRole,
    CheckpointRecord,
    ContractRef,
    RunSpec,
    SubjectEnvelopeRecord,
    semantic_model_dump,
)
from evidrun.infrastructure.database.models import ComparisonRow
from evidrun.shared.types import canonical_json, utc_now

OMISSION_REASON = "audit profile includes identity and digest, not artifact bytes"


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def jsonl_bytes(events: list[dict[str, Any]]) -> bytes:
    return ("\n".join(canonical_json(event) for event in events) + "\n").encode()


def read_json(archive: zipfile.ZipFile, name: str) -> Any:
    return json.loads(archive.read(name))


def read_events(archive: zipfile.ZipFile, name: str) -> list[dict[str, Any]]:
    """One JSON line per event; the trailing blank line is format, not an event."""

    return [json.loads(line) for line in archive.read(name).splitlines() if line]


def record_dict(model: Any, *, digest_field: str = "digest") -> dict[str, Any]:
    document = semantic_model_dump(model)
    document[digest_field] = getattr(model, digest_field)
    return document


def grade_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row.id,
        "run_id": row.run_id,
        "grader_id": row.grader_id,
        "score": row.score,
        "passed": row.passed,
        "rationale": row.rationale,
        "evidence": json.loads(row.evidence_json),
    }


def comparison_document(comparison: ComparisonRow) -> dict[str, object]:
    """The comparison document, byte-identical in v1 and v2."""

    return {
        "id": comparison.id,
        "baseline_run_id": comparison.baseline_run_id,
        "candidate_run_id": comparison.candidate_run_id,
        "primary_variable": comparison.primary_variable,
        "validity": comparison.validity,
        "baseline_score": comparison.baseline_score,
        "candidate_score": comparison.candidate_score,
        "delta": comparison.delta,
    }


def write_bundle(output_path: Path, files: dict[str, bytes], *, schema_version: str) -> Path:
    """Seal the bundle: a checksum per member, `checksums.json`, and the zip.

    The checksum covers every member but itself, and the verifier demands the exact
    list — a file injected without a checksum entry invalidates the bundle.
    """

    checksums = {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}
    files["checksums.json"] = json_bytes(
        {
            "schema_version": schema_version,
            "created_at": utc_now().isoformat(),
            "files": checksums,
        }
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output_path


def artifact_manifest(entries: list[ArtifactManifestEntry]) -> ArtifactManifest:
    """Sorted, duplicate-free manifest: intentional refs, never read telemetry."""

    unique = {(item.run_id, item.role, item.artifact_ref.artifact_id): item for item in entries}
    return ArtifactManifest(entries=tuple(unique[key] for key in sorted(unique)))


def contract_member_name(reference: ContractRef) -> str:
    safe_id = reference.logical_id.replace("/", "_")
    return f"contracts/{reference.contract_type.value}/{safe_id}@{reference.revision}.json"


def spec_revision_refs(spec: RunSpec) -> tuple[ContractRef, ...]:
    """The seven required RunSpec refs plus whichever of the two optional ones exist."""

    return (
        spec.study_ref,
        spec.goal_ref,
        spec.scenario_ref,
        spec.agent_inventory_ref,
        spec.workspace_template_ref,
        spec.interaction_protocol_ref,
        spec.evaluation_plan_ref,
        *(
            item
            for item in (spec.checkpoint_policy_ref, spec.progress_artifact_policy_ref)
            if item is not None
        ),
    )


def _entry(
    run_id: str, role: ArtifactRole, artifact_ref: ArtifactRef, source_label: str
) -> ArtifactManifestEntry:
    return ArtifactManifestEntry(
        run_id=run_id,
        role=role,
        artifact_ref=artifact_ref,
        source_label=source_label,
        content_included=False,
        omission_reason=OMISSION_REASON,
        required_for_portability=True,
    )


def spec_artifact_entries(run_id: str, spec: RunSpec) -> list[ArtifactManifestEntry]:
    entries = [
        _entry(run_id, "scenario_input", binding.source, f"scenario_input:{binding.id}")
        for binding in spec.scenario.input_bindings
    ]
    interaction_refs = tuple(
        item
        for item in (
            spec.interaction_protocol.system_prompt_ref,
            *spec.interaction_protocol.initial_message_refs,
        )
        if item is not None
    )
    entries.extend(
        _entry(run_id, "interaction_prompt", artifact_ref, f"interaction_prompt:{index}")
        for index, artifact_ref in enumerate(interaction_refs)
    )
    for requirement in spec.agent_inventory.capability_requirements:
        entries.extend(
            _entry(
                run_id,
                "agent_instruction",
                artifact_ref,
                f"capability_instruction:{requirement.capability_ref.name}:{index}",
            )
            for index, artifact_ref in enumerate(requirement.instruction_refs)
        )
    entries.extend(
        _entry(run_id, "hidden_calibration", artifact_ref, f"hidden_calibration:{index}")
        for index, artifact_ref in enumerate(spec.evaluation_plan.disclosure.hidden_input_refs)
    )
    for extension in spec.extensions:
        slot = f"{extension.namespace}:{extension.slot}"
        entries.append(
            _entry(run_id, "extension_schema", extension.schema_ref, f"extension_schema:{slot}")
        )
        entries.append(
            _entry(run_id, "extension_payload", extension.payload_ref, f"extension_payload:{slot}")
        )
    return entries


def checkpoint_artifact_entries(
    run_id: str, records: list[CheckpointRecord]
) -> list[ArtifactManifestEntry]:
    entries: list[ArtifactManifestEntry] = []
    for record in records:
        refs = (
            record.protocol_state_ref,
            record.artifact_manifest_ref,
            record.workspace_snapshot_ref,
        )
        entries.extend(
            _entry(
                run_id,
                "checkpoint_capture",
                artifact_ref,
                f"checkpoint:{record.checkpoint_id}:{index}",
            )
            for index, artifact_ref in enumerate(item for item in refs if item is not None)
        )
    return entries


def subject_artifact_entries(record: SubjectEnvelopeRecord) -> list[ArtifactManifestEntry]:
    return [
        _entry(
            record.run_id,
            "subject_input_materialized",
            binding.source,
            f"subject_input_materialized:{binding.id}",
        )
        for binding in record.envelope.inputs
    ]


def event_artifact_entries(
    run_id: str, events: list[dict[str, Any]]
) -> list[ArtifactManifestEntry]:
    """Refs que os eventos do ledger carregam: argumentos e resultado de tool, e output."""

    roles: tuple[tuple[frozenset[str], str, ArtifactRole], ...] = (
        (frozenset({"tool.called"}), "arguments_ref", "tool_arguments"),
        (frozenset({"tool.completed", "tool.failed"}), "result_ref", "tool_result"),
        (frozenset({"subject.responded"}), "output_ref", "run_output"),
    )
    entries: list[ArtifactManifestEntry] = []
    for event in events:
        payload_value: object = event.get("payload")
        if not isinstance(payload_value, dict):
            continue
        payload = cast("dict[str, object]", payload_value)
        event_id = str(event.get("event_id", "unknown"))
        event_type = event.get("type")
        for types, payload_key, role in roles:
            reference = payload.get(payload_key)
            if event_type in types and isinstance(reference, dict):
                entries.append(
                    _entry(
                        run_id,
                        role,
                        ArtifactRef.model_validate(reference),
                        f"{role}:{event_id}",
                    )
                )
    return entries
