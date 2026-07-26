"""Bundle v2: comparison structure plus the record checks v3 also reuses.

Every check returns a named boolean in a result dict; the bundle is valid only when
all of them hold. Checksum alone never suffices — lifecycle, queued/terminal
contracts, comparison IDs, evaluation records and the full artifact entry set are all
verified here.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel

from evidrun.contracts import (
    AdmissionRecord,
    ArtifactManifest,
    ArtifactManifestEntry,
    CheckpointRecord,
    ContractRef,
    EvaluationRecord,
    EvaluationValidator,
    RunRecord,
    RunSpec,
    parse_revision,
    semantic_model_dump,
)
from evidrun.evidence import archive as ar
from evidrun.evidence.verify.records import (
    TERMINAL_EVENT_TYPES,
    LedgerIndex,
    build_ledger_index,
    checkpoint_record_valid,
    evaluation_record_valid,
    run_members,
    strip,
)
from evidrun.shared.types import canonical_json


class RunContracts:
    """The spec, record and admission of one Run, kept together because every
    downstream check needs all three or none of them."""

    __slots__ = ("admissions", "run_records", "run_specs")

    def __init__(self) -> None:
        self.run_specs: dict[str, RunSpec] = {}
        self.run_records: dict[str, RunRecord] = {}
        self.admissions: dict[str, AdmissionRecord] = {}

    def spec(self, run_id: str) -> RunSpec | None:
        return self.run_specs.get(run_id)


def verify_v2_structure(bundle_manifest: dict[str, Any], names: set[str]) -> bool:
    raw_run_ids = bundle_manifest.get("run_ids")
    if (
        bundle_manifest.get("kind") != "comparison"
        or bundle_manifest.get("profile") != "audit"
        or bundle_manifest.get("artifact_content") != "references_only"
        or bundle_manifest.get("portable") is not False
        or bundle_manifest.get("replayable") is not False
        or not isinstance(raw_run_ids, list)
        or "comparison.json" not in names
        or "report.md" not in names
        or "artifact-manifest.json" not in names
    ):
        return False
    run_ids = cast("list[object]", raw_run_ids)
    if len(run_ids) != 2 or len({str(item) for item in run_ids}) != 2:
        return False
    return all(
        isinstance(run_id, str) and run_members(run_id).issubset(names) for run_id in run_ids
    )


def verify_v2_records(archive: zipfile.ZipFile, names: set[str]) -> dict[str, bool]:
    results: dict[str, bool] = {}
    contracts = _load_run_contracts(archive, names)
    results.update(_contract_ref_results(archive, contracts))
    results["artifact-manifest.json"] = _artifact_manifest_valid(archive, contracts)
    index = _index_ledger(archive, names)
    results.update(_lifecycle_results(contracts, index))
    results.update(_member_results(archive, names, contracts, index))
    results["comparison.json"] = _comparison_valid(archive, contracts)
    return results


def _load_run_contracts(archive: zipfile.ZipFile, names: set[str]) -> RunContracts:
    """Only an internally coherent spec/record/admission trio is kept; the rest is
    skipped here and failed by the per-member checks."""

    contracts = RunContracts()
    for name in sorted(item for item in names if item.startswith("runs/")):
        try:
            run_record = RunRecord.model_validate(ar.read_json(archive, name))
            spec_document = ar.read_json(archive, f"run-specs/{run_record.run_spec_id}.json")
            expected = spec_document.pop("digest")
            spec = RunSpec.model_validate(spec_document)
            admission_document = ar.read_json(
                archive, f"admissions/{run_record.admission_id}.json"
            )
            admission_digest = admission_document.pop("digest")
            admission = AdmissionRecord.model_validate(admission_document)
            if (
                spec.digest == expected
                and admission.digest == admission_digest
                and admission.decision == "admitted"
                and admission.run_spec_digest == spec.digest
            ):
                contracts.run_specs[run_record.run_id] = spec
                contracts.run_records[run_record.run_id] = run_record
                contracts.admissions[run_record.run_id] = admission
        except KeyError, TypeError, ValueError:
            continue
    return contracts


def _referenced_contracts(spec: RunSpec) -> list[tuple[ContractRef, BaseModel | None]]:
    """Each RunSpec ref paired with the payload the spec itself carries, if any."""

    pairs: list[tuple[ContractRef, BaseModel | None]] = [
        (spec.study_ref, None),
        (spec.goal_ref, spec.goal),
        (spec.scenario_ref, spec.scenario),
        (spec.agent_inventory_ref, spec.agent_inventory),
        (spec.workspace_template_ref, spec.workspace),
        (spec.interaction_protocol_ref, spec.interaction_protocol),
        (spec.evaluation_plan_ref, spec.evaluation_plan),
    ]
    if spec.checkpoint_policy_ref is not None:
        pairs.append((spec.checkpoint_policy_ref, spec.checkpoint_policy))
    if spec.progress_artifact_policy_ref is not None:
        pairs.append((spec.progress_artifact_policy_ref, spec.progress_artifact_policy))
    return pairs


def _contract_ref_results(
    archive: zipfile.ZipFile, contracts: RunContracts
) -> dict[str, bool]:
    """The bundled revision must be the one the ref names, with the same payload."""

    results: dict[str, bool] = {}
    for run_id, spec in contracts.run_specs.items():
        for reference, expected_payload in _referenced_contracts(spec):
            contract_name = ar.contract_member_name(reference)
            result_key = f"__contract_ref__:{run_id}:{contract_name}"
            try:
                contract_document = ar.read_json(archive, contract_name)
                contract_document.pop("digest")
                revision = parse_revision(contract_document)
                actual_payload = revision.semantic_document().get("payload")
                results[result_key] = revision.ref == reference and (
                    expected_payload is None
                    or actual_payload == semantic_model_dump(expected_payload)
                )
            except AttributeError, KeyError, TypeError, ValueError:
                results[result_key] = False
    return results


def _checkpoint_records(archive: zipfile.ZipFile, run_id: str) -> list[CheckpointRecord]:
    return [
        CheckpointRecord.model_validate(strip(document, "checkpoint_hash"))
        for document in ar.read_json(archive, f"checkpoints/{run_id}.json")
    ]


def _expected_artifact_entries(
    archive: zipfile.ZipFile, contracts: RunContracts
) -> list[ArtifactManifestEntry]:
    entries: list[ArtifactManifestEntry] = []
    for run_id, spec in contracts.run_specs.items():
        entries.extend(ar.spec_artifact_entries(run_id, spec))
        entries.extend(
            ar.checkpoint_artifact_entries(run_id, _checkpoint_records(archive, run_id))
        )
    return entries


def _artifact_manifest_valid(archive: zipfile.ZipFile, contracts: RunContracts) -> bool:
    """O manifest enumera exatamente as refs intencionais, e nunca promete portabilidade."""

    try:
        manifest_document = ar.read_json(archive, "artifact-manifest.json")
        manifest_digest = manifest_document.pop("digest")
        manifest = ArtifactManifest.model_validate(manifest_document)
        expected = _documents(_expected_artifact_entries(archive, contracts))
        return (
            manifest.digest == manifest_digest
            and manifest.profile == "audit"
            and not manifest.portable
            and not manifest.replayable
            and expected == _documents(manifest.entries)
        )
    except KeyError, TypeError, ValueError:
        return False


def _documents(entries: Any) -> set[str]:
    return {canonical_json(semantic_model_dump(item)) for item in entries}


def _index_ledger(archive: zipfile.ZipFile, names: set[str]) -> LedgerIndex:
    return build_ledger_index(
        {
            Path(name).stem: ar.read_events(archive, name)
            for name in sorted(item for item in names if item.startswith("events/"))
        },
        {
            Path(name).stem: ar.read_json(archive, name)
            for name in sorted(item for item in names if item.startswith("checkpoints/"))
        },
    )


def _lifecycle_results(contracts: RunContracts, index: LedgerIndex) -> dict[str, bool]:
    """The Run must end on a terminal event, and its queued/terminal pair must bind to
    the RunSpec and AdmissionRecord the bundle carries."""

    results: dict[str, bool] = {}
    for run_id, events in index.events_by_run.items():
        results[f"__terminal_event__:{run_id}"] = (
            bool(events) and str(events[-1]["type"]) in TERMINAL_EVENT_TYPES
        )
        spec = contracts.run_specs.get(run_id)
        run_record = contracts.run_records.get(run_id)
        admission = contracts.admissions.get(run_id)
        if (
            not events
            or str(events[-1].get("type")) not in TERMINAL_EVENT_TYPES
            or spec is None
            or run_record is None
            or admission is None
        ):
            results[f"__event_contracts__:{run_id}"] = False
            continue
        queued_payload = events[0]["payload"]
        terminal_payload = events[-1]["payload"]
        bounded_stop_valid = True
        if terminal_payload["goal_result"]["goal_mode"] == "bounded_exploration":
            bounded_stop_valid = terminal_payload["goal_result"]["stop_condition_kind"] in {
                item.kind for item in spec.stop_conditions
            }
        results[f"__event_contracts__:{run_id}"] = (
            events[0]["type"] == "run.queued"
            and queued_payload["run_id"] == run_record.run_id
            and queued_payload["variant_id"] == spec.variant_id
            and queued_payload["run_spec_digest"] == spec.digest
            and queued_payload["admission_digest"] == admission.digest
            and terminal_payload["goal_result"]["goal_mode"] == spec.goal.mode
            and bounded_stop_valid
        )
    return results


def _member_results(
    archive: zipfile.ZipFile,
    names: set[str],
    contracts: RunContracts,
    index: LedgerIndex,
) -> dict[str, bool]:
    """Each digestible member is checked against its own document type."""

    results: dict[str, bool] = {}
    for name in sorted(names):
        try:
            if name.startswith("contracts/") and name.endswith(".json"):
                results[name] = _digest_matches(archive, name, parse_revision)
            elif name.startswith("run-specs/") and name.endswith(".json"):
                results[name] = _digest_matches(archive, name, RunSpec.model_validate)
            elif name.startswith("admissions/") and name.endswith(".json"):
                results[name] = _digest_matches(archive, name, AdmissionRecord.model_validate)
            elif name.startswith("runs/") and name.endswith(".json"):
                results[name] = _run_record_valid(archive, name)
            elif name.startswith("evaluations/") and name.endswith(".json"):
                results[name] = _evaluations_valid(archive, name, contracts, index)
            elif name.startswith("checkpoints/") and name.endswith(".json"):
                run_id = Path(name).stem
                results[name] = all(
                    checkpoint_record_valid(
                        document,
                        run_id=run_id,
                        spec=contracts.spec(run_id),
                        index=index,
                    )
                    for document in ar.read_json(archive, name)
                )
        except KeyError, TypeError, ValueError:
            results[name] = False
    return results


def _digest_matches(archive: zipfile.ZipFile, name: str, parse: Any) -> bool:
    document = ar.read_json(archive, name)
    expected = document.pop("digest")
    return bool(parse(document).digest == expected)


def _run_record_valid(archive: zipfile.ZipFile, name: str) -> bool:
    """The RunRecord must agree with the spec and admission it references."""

    record = RunRecord.model_validate(ar.read_json(archive, name))
    spec_document = ar.read_json(archive, f"run-specs/{record.run_spec_id}.json")
    admission_document = ar.read_json(archive, f"admissions/{record.admission_id}.json")
    spec_digest = spec_document.pop("digest")
    admission_digest = admission_document.pop("digest")
    spec = RunSpec.model_validate(spec_document)
    admission = AdmissionRecord.model_validate(admission_document)
    return (
        record.run_id == Path(name).stem
        and spec.digest == spec_digest == record.run_spec_digest
        and admission.digest == admission_digest == record.admission_digest
        and admission.decision == "admitted"
        and admission.run_spec_digest == spec.digest
        and record.study_ref == spec.study_ref
        and record.scenario_ref == spec.scenario_ref
        and record.variant_id == spec.variant_id
        and record.repetition_index == spec.repetition_index
    )


def _evaluations_valid(
    archive: zipfile.ZipFile,
    name: str,
    contracts: RunContracts,
    index: LedgerIndex,
) -> bool:
    """Every EvaluationRecord has a matching `evaluation.completed`, and the terminal
    event references exactly the set of records present."""

    documents = ar.read_json(archive, name)
    run_id = Path(name).stem
    run_events = index.events(run_id)
    terminal_event = index.terminal_event(run_id)
    completed_terminal = terminal_event is not None and terminal_event["type"] == "run.completed"
    records_by_id = {str(document["record_id"]): document for document in documents}
    record_keys = [
        (str(document["stage_id"]), str(document["source_type"])) for document in documents
    ]
    completion_payloads = [
        event["payload"] for event in run_events if event["type"] == "evaluation.completed"
    ]
    completion_events = {
        str(payload["evaluation_record_id"]): payload for payload in completion_payloads
    }
    valid = (bool(documents) or not completed_terminal) and (
        len(records_by_id) == len(documents)
        and len(set(record_keys)) == len(record_keys)
        and len(completion_events) == len(completion_payloads)
        and set(completion_events) == set(records_by_id)
    )
    valid = valid and all(
        evaluation_record_valid(
            document,
            run_id=run_id,
            spec=contracts.spec(run_id),
            index=index,
            records_by_id=records_by_id,
        )
        for document in documents
    )
    valid = valid and all(
        str(document["record_id"]) in completion_events
        and completion_events[str(document["record_id"])]["evaluation_record_digest"]
        == document["digest"]
        and completion_events[str(document["record_id"])]["gate_status"]
        == document["gate_status"]
        for document in documents
    )
    if not run_events:
        return False
    if terminal_event is not None:
        terminal_refs = {
            str(item) for item in terminal_event["payload"].get("evaluation_record_refs", [])
        }
        valid = valid and terminal_refs == set(records_by_id)
    if completed_terminal:
        valid = valid and _gates_satisfied(documents, contracts.spec(run_id))
    return valid


def _gates_satisfied(documents: list[dict[str, Any]], spec: RunSpec | None) -> bool:
    """A completed Run needs a record for every stage the gates left visible."""

    if spec is None:
        return False
    parsed = [
        EvaluationRecord.model_validate(strip(document, "digest")) for document in documents
    ]
    gate_results = EvaluationValidator.gate_results(spec.evaluation_plan, parsed)
    required = EvaluationValidator.stages_visible_after_gates(spec.evaluation_plan, gate_results)
    return set(required).issubset(gate_results)


def _comparison_valid(archive: zipfile.ZipFile, contracts: RunContracts) -> bool:
    """The bundle's two run_ids are exactly the two sides of the comparison."""

    try:
        bundle_document = ar.read_json(archive, "bundle.json")
        comparison_document = ar.read_json(archive, "comparison.json")
        run_ids = {str(item) for item in bundle_document["run_ids"]}
        comparison_run_ids = {
            str(comparison_document["baseline_run_id"]),
            str(comparison_document["candidate_run_id"]),
        }
        return (
            len(run_ids) == 2
            and run_ids == comparison_run_ids == set(contracts.run_specs)
            and comparison_document["id"] == bundle_document["comparison_id"]
        )
    except KeyError, TypeError, ValueError:
        return False
