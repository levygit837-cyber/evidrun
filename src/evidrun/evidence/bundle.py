from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel

from evidrun.contracts import (
    AdmissionRecord,
    CheckpointRecord,
    ContractRef,
    EvaluationRecord,
    EvaluationValidator,
    RunRecord,
    RunSpec,
    parse_revision,
    semantic_model_dump,
)
from evidrun.infrastructure.database import Repository
from evidrun.shared.types import canonical_json, sha256_json, utc_now


class EvidenceBundleService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def export_comparison(self, comparison_id: str, output_path: Path) -> Path:
        comparison = self.repository.get_comparison(comparison_id)
        experiment = self.repository.get_experiment(comparison.experiment_revision_id)
        baseline = self.repository.get_run(comparison.baseline_run_id)
        candidate = self.repository.get_run(comparison.candidate_run_id)
        grades = [
            self._grade_dict(self.repository.get_grade(baseline.id)),
            self._grade_dict(self.repository.get_grade(candidate.id)),
        ]
        events = {
            baseline.id: self.repository.get_run_events(baseline.id),
            candidate.id: self.repository.get_run_events(candidate.id),
        }
        files: dict[str, bytes] = {
            "manifest.json": self._json_bytes(json.loads(experiment.manifest_json)),
            "comparison.json": self._json_bytes(
                {
                    "id": comparison.id,
                    "baseline_run_id": comparison.baseline_run_id,
                    "candidate_run_id": comparison.candidate_run_id,
                    "primary_variable": comparison.primary_variable,
                    "validity": comparison.validity,
                    "baseline_score": comparison.baseline_score,
                    "candidate_score": comparison.candidate_score,
                    "delta": comparison.delta,
                }
            ),
            "grades.json": self._json_bytes(grades),
            "report.md": comparison.report_markdown.encode("utf-8"),
            f"events/{baseline.id}.jsonl": self._jsonl_bytes(events[baseline.id]),
            f"events/{candidate.id}.jsonl": self._jsonl_bytes(events[candidate.id]),
        }
        checksums = {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}
        files["checksums.json"] = self._json_bytes(
            {
                "schema_version": "1",
                "created_at": utc_now().isoformat(),
                "files": checksums,
            }
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        return output_path

    def export_comparison_v2(self, comparison_id: str, output_path: Path) -> Path:
        comparison = self.repository.get_comparison(comparison_id)
        run_rows = [
            self.repository.get_run(comparison.baseline_run_id),
            self.repository.get_run(comparison.candidate_run_id),
        ]
        run_contracts: dict[str, tuple[RunSpec, AdmissionRecord]] = {}
        for run in run_rows:
            contracts = self.repository.get_run_contracts(run.id)
            if contracts is None:
                raise ValueError("Evidence Bundle v2 requires Study-based Runs")
            run_contracts[run.id] = contracts

        files: dict[str, bytes] = {
            "bundle.json": self._json_bytes(
                {
                    "schema_version": "2",
                    "kind": "comparison",
                    "comparison_id": comparison.id,
                    "run_ids": [run.id for run in run_rows],
                }
            ),
            "comparison.json": self._json_bytes(
                {
                    "id": comparison.id,
                    "baseline_run_id": comparison.baseline_run_id,
                    "candidate_run_id": comparison.candidate_run_id,
                    "primary_variable": comparison.primary_variable,
                    "validity": comparison.validity,
                    "baseline_score": comparison.baseline_score,
                    "candidate_score": comparison.candidate_score,
                    "delta": comparison.delta,
                }
            ),
            "report.md": comparison.report_markdown.encode("utf-8"),
        }

        revision_refs: dict[tuple[str, str, int], ContractRef] = {}
        for run in run_rows:
            spec, admission = run_contracts[run.id]
            if run.run_spec_id is None or run.admission_id is None:
                raise ValueError("Evidence Bundle v2 requires Run contract links")
            files[f"run-specs/{run.run_spec_id}.json"] = self._json_bytes(
                self._record_dict(spec)
            )
            files[f"admissions/{run.admission_id}.json"] = self._json_bytes(
                self._record_dict(admission)
            )
            run_record = self.repository.get_run_record(run.id)
            if run_record is None:
                raise ValueError("Evidence Bundle v2 requires a canonical RunRecord")
            files[f"runs/{run.id}.json"] = self._json_bytes(
                semantic_model_dump(run_record)
            )
            files[f"events/{run.id}.jsonl"] = self._jsonl_bytes(
                self.repository.get_run_events(run.id)
            )
            files[f"evaluations/{run.id}.json"] = self._json_bytes(
                [
                    self._record_dict(record)
                    for record in self.repository.get_evaluation_records(run.id)
                ]
            )
            files[f"checkpoints/{run.id}.json"] = self._json_bytes(
                [
                    self._record_dict(record, digest_field="checkpoint_hash")
                    for record in self.repository.get_checkpoint_records(run.id)
                ]
            )
            refs = (
                spec.study_ref,
                spec.goal_ref,
                spec.scenario_ref,
                spec.agent_inventory_ref,
                spec.workspace_template_ref,
                spec.interaction_protocol_ref,
                spec.evaluation_plan_ref,
            )
            for reference in refs:
                revision_refs[
                    (
                        reference.contract_type.value,
                        reference.logical_id,
                        reference.revision,
                    )
                ] = reference
            if spec.checkpoint_policy_ref is not None:
                reference = spec.checkpoint_policy_ref
                revision_refs[
                    (
                        reference.contract_type.value,
                        reference.logical_id,
                        reference.revision,
                    )
                ] = reference

        for (contract_type, logical_id, revision_number), reference in revision_refs.items():
            revision = self.repository.get_contract_revision_by_ref(reference)
            safe_id = logical_id.replace("/", "_")
            files[
                f"contracts/{contract_type}/{safe_id}@{revision_number}.json"
            ] = self._json_bytes(self._record_dict(revision))

        checksums = {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}
        files["checksums.json"] = self._json_bytes(
            {
                "schema_version": "2",
                "created_at": utc_now().isoformat(),
                "files": checksums,
            }
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        return output_path

    def verify(self, bundle_path: Path) -> dict[str, Any]:
        with zipfile.ZipFile(bundle_path) as archive:
            member_names = archive.namelist()
            names = set(member_names)
            if "checksums.json" not in names:
                raise ValueError("bundle has no checksums.json")
            checksums = json.loads(archive.read("checksums.json"))["files"]
            checksum_results: dict[str, bool] = {}
            for name, expected in checksums.items():
                try:
                    actual = hashlib.sha256(archive.read(name)).hexdigest()
                except KeyError:
                    checksum_results[name] = False
                else:
                    checksum_results[name] = actual == expected
            checksum_results["__complete_file_list__"] = set(checksums) == names - {
                "checksums.json"
            }
            checksum_results["__unique_file_names__"] = len(member_names) == len(names)

            chain_results: dict[str, bool] = {}
            for name in sorted(item for item in names if item.startswith("events/")):
                events = [json.loads(line) for line in archive.read(name).splitlines() if line]
                previous: str | None = None
                valid = True
                for event in events:
                    stored_hash = event.pop("event_hash")
                    if event["prev_event_hash"] != previous or sha256_json(event) != stored_hash:
                        valid = False
                        break
                    previous = stored_hash
                chain_results[name] = valid

            record_results: dict[str, bool] = {}
            if "bundle.json" in names:
                bundle_manifest = json.loads(archive.read("bundle.json"))
                if bundle_manifest.get("schema_version") == "2":
                    record_results = self._verify_v2_records(archive, names)
                    record_results["__bundle_structure__"] = (
                        self._verify_v2_structure(bundle_manifest, names)
                    )

        valid = (
            all(checksum_results.values())
            and all(chain_results.values())
            and all(record_results.values())
        )
        return {
            "valid": valid,
            "checksums": checksum_results,
            "event_chains": chain_results,
            "records": record_results,
        }

    @staticmethod
    def _verify_v2_structure(
        bundle_manifest: dict[str, Any], names: set[str]
    ) -> bool:
        raw_run_ids = bundle_manifest.get("run_ids")
        if (
            bundle_manifest.get("kind") != "comparison"
            or not isinstance(raw_run_ids, list)
            or "comparison.json" not in names
            or "report.md" not in names
        ):
            return False
        run_ids = cast(list[object], raw_run_ids)
        if len(run_ids) != 2 or len({str(item) for item in run_ids}) != 2:
            return False
        for run_id in run_ids:
            if not isinstance(run_id, str):
                return False
            required = {
                f"runs/{run_id}.json",
                f"events/{run_id}.jsonl",
                f"evaluations/{run_id}.json",
                f"checkpoints/{run_id}.json",
            }
            if not required.issubset(names):
                return False
        return True

    @staticmethod
    def _verify_v2_records(
        archive: zipfile.ZipFile, names: set[str]
    ) -> dict[str, bool]:
        results: dict[str, bool] = {}
        run_specs: dict[str, RunSpec] = {}
        for name in sorted(item for item in names if item.startswith("runs/")):
            try:
                run_document = json.loads(archive.read(name))
                run_record = RunRecord.model_validate(run_document)
                spec_document = json.loads(
                    archive.read(f"run-specs/{run_record.run_spec_id}.json")
                )
                expected = spec_document.pop("digest")
                spec = RunSpec.model_validate(spec_document)
                if spec.digest == expected:
                    run_specs[run_record.run_id] = spec
            except (KeyError, TypeError, ValueError):
                continue
        for run_id, spec in run_specs.items():
            referenced_contracts: list[tuple[ContractRef, BaseModel | None]] = [
                (spec.study_ref, None),
                (spec.goal_ref, spec.goal),
                (spec.scenario_ref, spec.scenario),
                (spec.agent_inventory_ref, spec.agent_inventory),
                (spec.workspace_template_ref, spec.workspace),
                (spec.interaction_protocol_ref, spec.interaction_protocol),
                (spec.evaluation_plan_ref, spec.evaluation_plan),
            ]
            if spec.checkpoint_policy_ref is not None:
                referenced_contracts.append(
                    (spec.checkpoint_policy_ref, spec.checkpoint_policy)
                )
            for reference, expected_payload in referenced_contracts:
                safe_id = reference.logical_id.replace("/", "_")
                contract_name = (
                    f"contracts/{reference.contract_type.value}/"
                    f"{safe_id}@{reference.revision}.json"
                )
                result_key = f"__contract_ref__:{run_id}:{contract_name}"
                try:
                    contract_document = json.loads(archive.read(contract_name))
                    contract_document.pop("digest")
                    revision = parse_revision(contract_document)
                    actual_payload = revision.semantic_document().get("payload")
                    results[result_key] = revision.ref == reference and (
                        expected_payload is None
                        or actual_payload == semantic_model_dump(expected_payload)
                    )
                except (AttributeError, KeyError, TypeError, ValueError):
                    results[result_key] = False
        event_boundaries: dict[str, dict[int, str]] = {}
        event_types: dict[str, dict[int, str]] = {}
        event_sequences_by_id: dict[str, dict[str, int]] = {}
        for name in sorted(item for item in names if item.startswith("events/")):
            run_id = Path(name).stem
            events = [json.loads(line) for line in archive.read(name).splitlines() if line]
            event_boundaries[run_id] = {
                int(event["sequence"]): str(event["event_hash"]) for event in events
            }
            event_types[run_id] = {
                int(event["sequence"]): str(event["type"]) for event in events
            }
            event_sequences_by_id[run_id] = {
                str(event["event_id"]): int(event["sequence"]) for event in events
            }
        checkpoint_ids: dict[str, set[str]] = {}
        checkpoint_sequences: dict[str, dict[str, int]] = {}
        checkpoint_definitions: dict[str, dict[str, str]] = {}
        for name in sorted(item for item in names if item.startswith("checkpoints/")):
            run_id = Path(name).stem
            documents = json.loads(archive.read(name))
            checkpoint_ids[run_id] = {
                str(document["checkpoint_id"]) for document in documents
            }
            checkpoint_sequences[run_id] = {
                str(document["checkpoint_id"]): int(document["up_to_event_sequence"])
                for document in documents
            }
            checkpoint_definitions[run_id] = {
                str(document["checkpoint_id"]): str(document["definition_id"])
                for document in documents
            }
        for name in sorted(names):
            try:
                if name.startswith("contracts/") and name.endswith(".json"):
                    document = json.loads(archive.read(name))
                    expected = document.pop("digest")
                    results[name] = parse_revision(document).digest == expected
                elif name.startswith("run-specs/") and name.endswith(".json"):
                    document = json.loads(archive.read(name))
                    expected = document.pop("digest")
                    results[name] = RunSpec.model_validate(document).digest == expected
                elif name.startswith("admissions/") and name.endswith(".json"):
                    document = json.loads(archive.read(name))
                    expected = document.pop("digest")
                    results[name] = AdmissionRecord.model_validate(document).digest == expected
                elif name.startswith("runs/") and name.endswith(".json"):
                    document = json.loads(archive.read(name))
                    record = RunRecord.model_validate(document)
                    spec_name = f"run-specs/{record.run_spec_id}.json"
                    admission_name = f"admissions/{record.admission_id}.json"
                    spec_document = json.loads(archive.read(spec_name))
                    admission_document = json.loads(archive.read(admission_name))
                    spec_digest = spec_document.pop("digest")
                    admission_digest = admission_document.pop("digest")
                    spec = RunSpec.model_validate(spec_document)
                    admission = AdmissionRecord.model_validate(admission_document)
                    results[name] = (
                        record.run_id == Path(name).stem
                        and spec.digest == spec_digest == record.run_spec_digest
                        and admission.digest
                        == admission_digest
                        == record.admission_digest
                        and admission.decision == "admitted"
                        and admission.run_spec_digest == spec.digest
                        and record.study_ref == spec.study_ref
                        and record.scenario_ref == spec.scenario_ref
                        and record.variant_id == spec.variant_id
                        and record.repetition_index == spec.repetition_index
                    )
                elif name.startswith("evaluations/") and name.endswith(".json"):
                    documents = json.loads(archive.read(name))
                    run_id = Path(name).stem
                    results[name] = all(
                        EvidenceBundleService._evaluation_record_valid(
                            document,
                            run_id=run_id,
                            spec=run_specs.get(run_id),
                            event_boundaries=event_boundaries,
                            event_types=event_types,
                            event_sequences_by_id=event_sequences_by_id,
                            checkpoint_ids=checkpoint_ids,
                            checkpoint_sequences=checkpoint_sequences,
                            checkpoint_definitions=checkpoint_definitions,
                        )
                        for document in documents
                    )
                elif name.startswith("checkpoints/") and name.endswith(".json"):
                    documents = json.loads(archive.read(name))
                    run_id = Path(name).stem
                    results[name] = all(
                        EvidenceBundleService._checkpoint_record_valid(
                            document,
                            run_id=run_id,
                            spec=run_specs.get(run_id),
                            event_boundaries=event_boundaries,
                            event_types=event_types,
                        )
                        for document in documents
                    )
            except (KeyError, TypeError, ValueError):
                results[name] = False
        return results

    @staticmethod
    def _evaluation_record_valid(
        document: dict[str, Any],
        *,
        run_id: str,
        spec: RunSpec | None,
        event_boundaries: dict[str, dict[int, str]],
        event_types: dict[str, dict[int, str]],
        event_sequences_by_id: dict[str, dict[str, int]],
        checkpoint_ids: dict[str, set[str]],
        checkpoint_sequences: dict[str, dict[str, int]],
        checkpoint_definitions: dict[str, dict[str, str]],
    ) -> bool:
        expected = document["digest"]
        record = EvaluationRecord.model_validate(
            {key: value for key, value in document.items() if key != "digest"}
        )
        if (
            spec is None
            or record.digest != expected
            or record.run_id != run_id
            or record.plan_ref != spec.evaluation_plan_ref
        ):
            return False
        try:
            EvaluationValidator.validate(spec.evaluation_plan, record)
        except ValueError:
            return False
        boundary = record.boundary
        if (
            boundary.up_to_event_sequence is not None
            and event_boundaries.get(run_id, {}).get(boundary.up_to_event_sequence)
            != boundary.event_hash
        ):
            return False
        if (
            boundary.checkpoint_id is not None
            and boundary.checkpoint_id not in checkpoint_ids.get(run_id, set())
        ):
            return False
        stage = next(item for item in spec.evaluation_plan.stages if item.id == record.stage_id)
        boundary_sequence = boundary.up_to_event_sequence
        if boundary.checkpoint_id is not None:
            boundary_sequence = checkpoint_sequences.get(run_id, {}).get(
                boundary.checkpoint_id
            )
        if boundary_sequence is None:
            return False
        if stage.trigger.kind == "event" and (
            boundary.up_to_event_sequence is None
            or event_types.get(run_id, {}).get(boundary.up_to_event_sequence)
            != stage.trigger.reference
        ):
            return False
        if stage.trigger.kind == "checkpoint" and (
            boundary.checkpoint_id is None
            or (
                stage.trigger.reference is not None
                and checkpoint_definitions.get(run_id, {}).get(boundary.checkpoint_id)
                != stage.trigger.reference
            )
        ):
            return False
        if stage.trigger.kind == "run_terminal" and (
            boundary.up_to_event_sequence is None
            or event_types.get(run_id, {}).get(boundary.up_to_event_sequence)
            not in {
                "run.completed",
                "run.failed",
                "run.cancelled",
                "run.budget_exhausted",
                "run.guardrail_stopped",
            }
        ):
            return False
        for dimension in record.dimension_values:
            for evidence_ref in dimension.evidence_refs:
                scheme, target = evidence_ref.ref.split(":", 1)
                if scheme == "run" and target != run_id:
                    return False
                if scheme == "event":
                    sequence = event_sequences_by_id.get(run_id, {}).get(target)
                    if sequence is None or sequence > boundary_sequence:
                        return False
        return True

    @staticmethod
    def _checkpoint_record_valid(
        document: dict[str, Any],
        *,
        run_id: str,
        spec: RunSpec | None,
        event_boundaries: dict[str, dict[int, str]],
        event_types: dict[str, dict[int, str]],
    ) -> bool:
        expected = document["checkpoint_hash"]
        record = CheckpointRecord.model_validate(
            {
                key: value
                for key, value in document.items()
                if key != "checkpoint_hash"
            }
        )
        if (
            spec is None
            or spec.checkpoint_policy is None
            or spec.checkpoint_policy_ref != record.policy_ref
        ):
            return False
        definition = next(
            (
                item
                for item in spec.checkpoint_policy.definitions
                if item.id == record.definition_id
            ),
            None,
        )
        if (
            definition is None
            or record.definition_digest
            != sha256_json(semantic_model_dump(definition))
            or set(item.validator_ref for item in record.validations)
            != set(definition.validator_refs)
        ):
            return False
        capture = definition.capture
        captures_match = all(
            requested == present
            for requested, present in (
                (capture.context_snapshot, bool(record.context_snapshot_refs)),
                (capture.protocol_state, record.protocol_state_ref is not None),
                (capture.artifact_manifest, record.artifact_manifest_ref is not None),
                (capture.workspace_snapshot, record.workspace_snapshot_ref is not None),
                (capture.evaluation_records, bool(record.evaluation_record_refs)),
                (
                    capture.provider_resolution or capture.agent_inventory,
                    record.admission_record_id is not None,
                ),
            )
        )
        trigger = definition.trigger
        if trigger.kind == "event" and (
            event_types.get(run_id, {}).get(record.up_to_event_sequence)
            != trigger.event_type
        ):
            return False
        if trigger.kind not in {"manual", "event"}:
            return False
        return (
            captures_match
            and record.replayability != "deterministic"
            and record.checkpoint_hash == expected
            and record.run_id == run_id
            and event_boundaries.get(run_id, {}).get(record.up_to_event_sequence)
            == record.event_hash
        )

    @staticmethod
    def _json_bytes(value: Any) -> bytes:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()

    @staticmethod
    def _jsonl_bytes(events: list[dict[str, Any]]) -> bytes:
        return ("\n".join(canonical_json(event) for event in events) + "\n").encode()

    @staticmethod
    def _record_dict(model: Any, *, digest_field: str = "digest") -> dict[str, Any]:
        document = semantic_model_dump(model)
        document[digest_field] = getattr(model, digest_field)
        return document

    @staticmethod
    def _grade_dict(row: Any) -> dict[str, Any]:
        return {
            "id": row.id,
            "run_id": row.run_id,
            "grader_id": row.grader_id,
            "score": row.score,
            "passed": row.passed,
            "rationale": row.rationale,
            "evidence": json.loads(row.evidence_json),
        }
