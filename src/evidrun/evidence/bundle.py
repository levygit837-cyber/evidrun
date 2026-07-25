from __future__ import annotations

import hashlib
import json
import zipfile
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel

from evidrun.contracts import (
    AdmissionRecord,
    ArtifactManifest,
    ArtifactManifestEntry,
    ArtifactRef,
    CheckpointRecord,
    ContractRef,
    EvaluationRecord,
    EvaluationValidator,
    RunExecutionAttempt,
    RunExecutionJob,
    RunRecord,
    RunSpec,
    SubjectEnvelopeRecord,
    normalize_event_payload,
    parse_revision,
    semantic_model_dump,
)
from evidrun.contracts.runtime import (
    EVENT_ALLOWED_RUN_STATUSES,
    UNSUPPORTED_RUNTIME_EVENT_TYPES,
)
from evidrun.infrastructure.database import Repository
from evidrun.shared.types import canonical_json, sha256_json, utc_now


class EvidenceBundleService:
    def __init__(self, repository: Repository):
        self.repository = repository

    def export_comparison(self, comparison_id: str, output_path: Path) -> Path:
        comparison = self.repository.read_model.get_comparison(comparison_id)
        experiment = self.repository.read_model.get_experiment(comparison.experiment_revision_id)
        baseline = self.repository.read_model.get_run(comparison.baseline_run_id)
        candidate = self.repository.read_model.get_run(comparison.candidate_run_id)
        grades = [
            self._grade_dict(self.repository.read_model.get_grade(baseline.id)),
            self._grade_dict(self.repository.read_model.get_grade(candidate.id)),
        ]
        events = {
            baseline.id: self.repository.read_model.get_run_events(baseline.id),
            candidate.id: self.repository.read_model.get_run_events(candidate.id),
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
        comparison = self.repository.read_model.get_comparison(comparison_id)
        run_rows = [
            self.repository.read_model.get_run(comparison.baseline_run_id),
            self.repository.read_model.get_run(comparison.candidate_run_id),
        ]
        run_contracts: dict[str, tuple[RunSpec, AdmissionRecord]] = {}
        for run in run_rows:
            contracts = self.repository.read_model.get_run_contracts(run.id)
            if contracts is None:
                raise ValueError("Evidence Bundle v2 requires Study-based Runs")
            run_contracts[run.id] = contracts

        files: dict[str, bytes] = {
            "bundle.json": self._json_bytes(
                {
                    "schema_version": "2",
                    "kind": "comparison",
                    "profile": "audit",
                    "artifact_content": "references_only",
                    "portable": False,
                    "replayable": False,
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
        artifact_entries: list[ArtifactManifestEntry] = []
        for run in run_rows:
            spec, admission = run_contracts[run.id]
            if run.run_spec_id is None or run.admission_id is None:
                raise ValueError("Evidence Bundle v2 requires Run contract links")
            files[f"run-specs/{run.run_spec_id}.json"] = self._json_bytes(self._record_dict(spec))
            files[f"admissions/{run.admission_id}.json"] = self._json_bytes(
                self._record_dict(admission)
            )
            run_record = self.repository.read_model.get_run_record(run.id)
            if run_record is None:
                raise ValueError("Evidence Bundle v2 requires a canonical RunRecord")
            files[f"runs/{run.id}.json"] = self._json_bytes(semantic_model_dump(run_record))
            files[f"events/{run.id}.jsonl"] = self._jsonl_bytes(
                self.repository.read_model.get_run_events(run.id)
            )
            files[f"evaluations/{run.id}.json"] = self._json_bytes(
                [
                    self._record_dict(record)
                    for record in self.repository.read_model.get_evaluation_records(run.id)
                ]
            )
            files[f"checkpoints/{run.id}.json"] = self._json_bytes(
                [
                    self._record_dict(record, digest_field="checkpoint_hash")
                    for record in self.repository.read_model.get_checkpoint_records(run.id)
                ]
            )
            artifact_entries.extend(self._spec_artifact_entries(run.id, spec))
            artifact_entries.extend(
                self._checkpoint_artifact_entries(
                    run.id, self.repository.read_model.get_checkpoint_records(run.id)
                )
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
            if spec.progress_artifact_policy_ref is not None:
                reference = spec.progress_artifact_policy_ref
                revision_refs[
                    (
                        reference.contract_type.value,
                        reference.logical_id,
                        reference.revision,
                    )
                ] = reference

        for (contract_type, logical_id, revision_number), reference in revision_refs.items():
            revision = self.repository.read_model.get_contract_revision_by_ref(reference)
            safe_id = logical_id.replace("/", "_")
            files[f"contracts/{contract_type}/{safe_id}@{revision_number}.json"] = self._json_bytes(
                self._record_dict(revision)
            )

        unique_entries = {
            (item.run_id, item.role, item.artifact_ref.artifact_id): item
            for item in artifact_entries
        }
        artifact_manifest = ArtifactManifest(
            entries=tuple(unique_entries[key] for key in sorted(unique_entries))
        )
        files["artifact-manifest.json"] = self._json_bytes(self._record_dict(artifact_manifest))

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

    def export_run_v3(self, run_id: str, output_path: Path) -> Path:
        run = self.repository.read_model.get_run(run_id)
        contracts = self.repository.read_model.get_run_contracts(run_id)
        if contracts is None or run.run_spec_id is None or run.admission_id is None:
            raise ValueError("Evidence Bundle v3 requires a Study-based Run")
        if run.status not in {
            "completed",
            "failed",
            "cancelled",
            "budget_exhausted",
            "guardrail_stopped",
        }:
            raise ValueError("Evidence Bundle v3 requires a terminal Run")
        spec, admission = contracts
        run_record = self.repository.read_model.get_run_record(run_id)
        if run_record is None:
            raise ValueError("Evidence Bundle v3 requires a canonical RunRecord")
        events = self.repository.read_model.get_run_events(run_id)
        try:
            subject_record = self.repository.read_model.get_subject_envelope(run_id)
        except KeyError:
            subject_record = None
        execution = self.repository.lease.get_run_execution(run_id)
        if execution is None:
            raise ValueError("Evidence Bundle v3 requires durable execution records")
        job, attempts = execution
        files: dict[str, bytes] = {
            "bundle.json": self._json_bytes(
                {
                    "schema_version": "3",
                    "kind": "run",
                    "profile": "audit",
                    "artifact_content": "references_only",
                    "portable": False,
                    "replayable": False,
                    "run_ids": [run_id],
                }
            ),
            f"run-specs/{run.run_spec_id}.json": self._json_bytes(self._record_dict(spec)),
            f"admissions/{run.admission_id}.json": self._json_bytes(self._record_dict(admission)),
            f"runs/{run_id}.json": self._json_bytes(semantic_model_dump(run_record)),
            f"events/{run_id}.jsonl": self._jsonl_bytes(events),
            f"evaluations/{run_id}.json": self._json_bytes(
                [
                    self._record_dict(record)
                    for record in self.repository.read_model.get_evaluation_records(run_id)
                ]
            ),
            f"checkpoints/{run_id}.json": self._json_bytes(
                [
                    self._record_dict(record, digest_field="checkpoint_hash")
                    for record in self.repository.read_model.get_checkpoint_records(run_id)
                ]
            ),
            f"execution/jobs/{job.job_id}.json": self._json_bytes(self._record_dict(job)),
            f"execution/attempts/{job.job_id}.json": self._json_bytes(
                [self._record_dict(attempt) for attempt in attempts]
            ),
        }
        if subject_record is not None:
            files[f"subject-envelopes/{run_id}.json"] = self._json_bytes(
                self._record_dict(subject_record)
            )
        revision_refs = (
            spec.study_ref,
            spec.goal_ref,
            spec.scenario_ref,
            spec.agent_inventory_ref,
            spec.workspace_template_ref,
            spec.interaction_protocol_ref,
            spec.evaluation_plan_ref,
        )
        optional_refs = tuple(
            item
            for item in (
                spec.checkpoint_policy_ref,
                spec.progress_artifact_policy_ref,
            )
            if item is not None
        )
        for reference in (*revision_refs, *optional_refs):
            revision = self.repository.read_model.get_contract_revision_by_ref(reference)
            safe_id = reference.logical_id.replace("/", "_")
            files[
                f"contracts/{reference.contract_type.value}/{safe_id}@{reference.revision}.json"
            ] = self._json_bytes(self._record_dict(revision))

        entries = self._spec_artifact_entries(run_id, spec)
        if subject_record is not None:
            entries.extend(self._subject_artifact_entries(subject_record))
        entries.extend(self._event_artifact_entries(run_id, events))
        entries.extend(
            self._checkpoint_artifact_entries(
                run_id, self.repository.read_model.get_checkpoint_records(run_id)
            )
        )
        unique_entries = {
            (item.run_id, item.role, item.artifact_ref.artifact_id): item for item in entries
        }
        manifest = ArtifactManifest(
            entries=tuple(unique_entries[key] for key in sorted(unique_entries))
        )
        files["artifact-manifest.json"] = self._json_bytes(self._record_dict(manifest))
        checksums = {name: hashlib.sha256(content).hexdigest() for name, content in files.items()}
        files["checksums.json"] = self._json_bytes(
            {
                "schema_version": "3",
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
                current_status = "queued"
                valid = True
                terminal_states = {
                    "completed",
                    "failed",
                    "cancelled",
                    "budget_exhausted",
                    "guardrail_stopped",
                }
                transitions = {
                    "run.preparing": ({"queued"}, "preparing"),
                    "run.running": ({"preparing"}, "running"),
                    "run.paused": ({"running"}, "paused"),
                    "run.resumed": ({"paused"}, "running"),
                    "run.evaluating": ({"running"}, "evaluating"),
                    "run.completed": ({"evaluating"}, "completed"),
                    "run.failed": (
                        {"queued", "preparing", "running", "paused", "evaluating"},
                        "failed",
                    ),
                    "run.cancelled": (
                        {"queued", "preparing", "running", "paused", "evaluating"},
                        "cancelled",
                    ),
                    "run.budget_exhausted": (
                        {"queued", "preparing", "running", "paused", "evaluating"},
                        "budget_exhausted",
                    ),
                    "run.guardrail_stopped": (
                        {"queued", "preparing", "running", "paused", "evaluating"},
                        "guardrail_stopped",
                    ),
                }
                allowed_actor_types = {
                    "system",
                    "subject",
                    "evaluator",
                    "tool",
                    "skill",
                    "observer",
                }
                run_id = Path(name).stem
                subject_invocations = 0
                subject_responses = 0
                offered_capabilities: set[str] = set()
                tool_calls: dict[str, str] = {}
                tool_terminals: set[str] = set()
                for expected_sequence, event in enumerate(events, start=1):
                    stored_event = dict(event)
                    stored_hash = event.pop("event_hash")
                    event_type = str(event.get("type"))
                    payload = event.get("payload")
                    if (
                        event.get("schema_version") != "1"
                        or event.get("run_id") != run_id
                        or event.get("sequence") != expected_sequence
                        or event.get("actor_type") not in allowed_actor_types
                        or not str(event.get("actor_id", "")).strip()
                        or event_type in UNSUPPORTED_RUNTIME_EVENT_TYPES
                        or event.get("prev_event_hash") != previous
                        or sha256_json(event) != stored_hash
                    ):
                        valid = False
                        break
                    try:
                        if normalize_event_payload(event_type, payload) != payload:
                            valid = False
                            break
                    except TypeError, ValueError:
                        valid = False
                        break
                    if expected_sequence == 1:
                        if event_type != "run.queued":
                            valid = False
                            break
                    elif event_type == "run.queued" or current_status in terminal_states:
                        valid = False
                        break
                    allowed_statuses = EVENT_ALLOWED_RUN_STATUSES.get(event_type)
                    if allowed_statuses is not None and current_status not in allowed_statuses:
                        valid = False
                        break
                    if event_type == "subject.invoked":
                        if subject_invocations != subject_responses:
                            valid = False
                            break
                        subject_invocations += 1
                    if event_type == "subject.responded":
                        if subject_invocations != subject_responses + 1:
                            valid = False
                            break
                        subject_responses += 1
                    if event_type == "capability.offered":
                        offered_capabilities.add(canonical_json(payload["capability_ref"]))
                    if event_type == "tool.called":
                        call_id = str(payload["call_id"])
                        capability = canonical_json(payload["capability_ref"])
                        arguments_ref = payload.get("arguments_ref")
                        if (
                            subject_invocations != subject_responses + 1
                            or call_id in tool_calls
                            or capability not in offered_capabilities
                            or not isinstance(arguments_ref, dict)
                        ):
                            valid = False
                            break
                        arguments_document = cast(dict[str, object], arguments_ref)
                        if (
                            arguments_document.get("media_type") != "application/json"
                            or arguments_document.get("classification") != "internal"
                        ):
                            valid = False
                            break
                        tool_calls[call_id] = capability
                    if event_type in {"tool.completed", "tool.denied", "tool.failed"}:
                        call_id = str(payload["call_id"])
                        if (
                            subject_invocations != subject_responses + 1
                            or call_id not in tool_calls
                            or call_id in tool_terminals
                        ):
                            valid = False
                            break
                        if event_type in {"tool.completed", "tool.failed"} and (
                            canonical_json(payload["capability_ref"]) != tool_calls[call_id]
                        ):
                            valid = False
                            break
                        if event_type == "tool.completed" and not isinstance(
                            payload.get("result_ref"), dict
                        ):
                            valid = False
                            break
                        tool_terminals.add(call_id)
                    if event_type == "run.evaluating" and subject_responses == 0:
                        valid = False
                        break
                    if event_type == "run.completed" and subject_responses == 0:
                        valid = False
                        break
                    transition = transitions.get(event_type)
                    if transition is not None:
                        allowed_from, target = transition
                        if current_status not in allowed_from:
                            valid = False
                            break
                        if event.get("payload", {}).get("from_status") not in {
                            None,
                            current_status,
                        }:
                            valid = False
                            break
                        if event.get("payload", {}).get("status") not in {
                            None,
                            target,
                        }:
                            valid = False
                            break
                        current_status = target
                    previous = stored_hash
                    event.update(stored_event)
                chain_results[name] = valid and set(tool_calls) == tool_terminals

            record_results: dict[str, bool] = {}
            if "bundle.json" in names:
                bundle_manifest = json.loads(archive.read("bundle.json"))
                if bundle_manifest.get("schema_version") == "2":
                    record_results = self._verify_v2_records(archive, names)
                    record_results["__bundle_structure__"] = self._verify_v2_structure(
                        bundle_manifest, names
                    )
                elif bundle_manifest.get("schema_version") == "3":
                    record_results = self._verify_v3_records(archive, names)
                    record_results["__bundle_structure__"] = self._verify_v3_structure(
                        bundle_manifest, names
                    )

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

    @staticmethod
    def _verify_v2_structure(bundle_manifest: dict[str, Any], names: set[str]) -> bool:
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
    def _verify_v2_records(archive: zipfile.ZipFile, names: set[str]) -> dict[str, bool]:
        results: dict[str, bool] = {}
        run_specs: dict[str, RunSpec] = {}
        run_records: dict[str, RunRecord] = {}
        admissions: dict[str, AdmissionRecord] = {}
        for name in sorted(item for item in names if item.startswith("runs/")):
            try:
                run_document = json.loads(archive.read(name))
                run_record = RunRecord.model_validate(run_document)
                spec_document = json.loads(archive.read(f"run-specs/{run_record.run_spec_id}.json"))
                expected = spec_document.pop("digest")
                spec = RunSpec.model_validate(spec_document)
                admission_document = json.loads(
                    archive.read(f"admissions/{run_record.admission_id}.json")
                )
                admission_digest = admission_document.pop("digest")
                admission = AdmissionRecord.model_validate(admission_document)
                if (
                    spec.digest == expected
                    and admission.digest == admission_digest
                    and admission.decision == "admitted"
                    and admission.run_spec_digest == spec.digest
                ):
                    run_specs[run_record.run_id] = spec
                    run_records[run_record.run_id] = run_record
                    admissions[run_record.run_id] = admission
            except KeyError, TypeError, ValueError:
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
                referenced_contracts.append((spec.checkpoint_policy_ref, spec.checkpoint_policy))
            if spec.progress_artifact_policy_ref is not None:
                referenced_contracts.append(
                    (spec.progress_artifact_policy_ref, spec.progress_artifact_policy)
                )
            for reference, expected_payload in referenced_contracts:
                safe_id = reference.logical_id.replace("/", "_")
                contract_name = (
                    f"contracts/{reference.contract_type.value}/{safe_id}@{reference.revision}.json"
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
                except AttributeError, KeyError, TypeError, ValueError:
                    results[result_key] = False
        try:
            manifest_document = json.loads(archive.read("artifact-manifest.json"))
            manifest_digest = manifest_document.pop("digest")
            artifact_manifest = ArtifactManifest.model_validate(manifest_document)
            expected_entries: list[ArtifactManifestEntry] = []
            for run_id, spec in run_specs.items():
                expected_entries.extend(EvidenceBundleService._spec_artifact_entries(run_id, spec))
                checkpoint_name = f"checkpoints/{run_id}.json"
                checkpoint_documents = json.loads(archive.read(checkpoint_name))
                expected_entries.extend(
                    EvidenceBundleService._checkpoint_artifact_entries(
                        run_id,
                        [
                            CheckpointRecord.model_validate(
                                {
                                    key: value
                                    for key, value in document.items()
                                    if key != "checkpoint_hash"
                                }
                            )
                            for document in checkpoint_documents
                        ],
                    )
                )
            expected_documents = {
                canonical_json(semantic_model_dump(item)) for item in expected_entries
            }
            actual_documents = {
                canonical_json(semantic_model_dump(item)) for item in artifact_manifest.entries
            }
            results["artifact-manifest.json"] = (
                artifact_manifest.digest == manifest_digest
                and artifact_manifest.profile == "audit"
                and not artifact_manifest.portable
                and not artifact_manifest.replayable
                and expected_documents == actual_documents
            )
        except KeyError, TypeError, ValueError:
            results["artifact-manifest.json"] = False
        event_boundaries: dict[str, dict[int, str]] = {}
        event_types: dict[str, dict[int, str]] = {}
        event_sequences_by_id: dict[str, dict[str, int]] = {}
        events_by_run: dict[str, list[dict[str, Any]]] = {}
        for name in sorted(item for item in names if item.startswith("events/")):
            run_id = Path(name).stem
            events = [json.loads(line) for line in archive.read(name).splitlines() if line]
            events_by_run[run_id] = events
            event_boundaries[run_id] = {
                int(event["sequence"]): str(event["event_hash"]) for event in events
            }
            event_types[run_id] = {int(event["sequence"]): str(event["type"]) for event in events}
            event_sequences_by_id[run_id] = {
                str(event["event_id"]): int(event["sequence"]) for event in events
            }
            terminal_types = {
                "run.completed",
                "run.failed",
                "run.cancelled",
                "run.budget_exhausted",
                "run.guardrail_stopped",
            }
            results[f"__terminal_event__:{run_id}"] = (
                bool(events) and str(events[-1]["type"]) in terminal_types
            )
            spec = run_specs.get(run_id)
            run_record = run_records.get(run_id)
            admission = admissions.get(run_id)
            if (
                not events
                or str(events[-1].get("type")) not in terminal_types
                or spec is None
                or run_record is None
                or admission is None
            ):
                results[f"__event_contracts__:{run_id}"] = False
            else:
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
        checkpoint_ids: dict[str, set[str]] = {}
        checkpoint_sequences: dict[str, dict[str, int]] = {}
        checkpoint_definitions: dict[str, dict[str, str]] = {}
        for name in sorted(item for item in names if item.startswith("checkpoints/")):
            run_id = Path(name).stem
            documents = json.loads(archive.read(name))
            checkpoint_ids[run_id] = {str(document["checkpoint_id"]) for document in documents}
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
                        and admission.digest == admission_digest == record.admission_digest
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
                    run_events = events_by_run.get(run_id, [])
                    terminal_event = run_events[-1] if run_events else None
                    completed_terminal = (
                        terminal_event is not None and terminal_event["type"] == "run.completed"
                    )
                    records_by_id = {str(document["record_id"]): document for document in documents}
                    record_keys = [
                        (str(document["stage_id"]), str(document["source_type"]))
                        for document in documents
                    ]
                    completion_event_payloads = [
                        event["payload"]
                        for event in events_by_run.get(run_id, [])
                        if event["type"] == "evaluation.completed"
                    ]
                    completion_events = {
                        str(payload["evaluation_record_id"]): payload
                        for payload in completion_event_payloads
                    }
                    records_valid = (bool(documents) or not completed_terminal) and (
                        len(records_by_id) == len(documents)
                        and len(set(record_keys)) == len(record_keys)
                        and len(completion_events) == len(completion_event_payloads)
                        and set(completion_events) == set(records_by_id)
                    )
                    records_valid = records_valid and all(
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
                            records_by_id=records_by_id,
                        )
                        for document in documents
                    )
                    records_valid = records_valid and all(
                        str(document["record_id"]) in completion_events
                        and completion_events[str(document["record_id"])][
                            "evaluation_record_digest"
                        ]
                        == document["digest"]
                        and completion_events[str(document["record_id"])]["gate_status"]
                        == document["gate_status"]
                        for document in documents
                    )
                    if not run_events:
                        records_valid = False
                    if terminal_event is not None:
                        terminal_refs = {
                            str(item)
                            for item in terminal_event["payload"].get("evaluation_record_refs", [])
                        }
                        records_valid = records_valid and (terminal_refs == set(records_by_id))
                    if completed_terminal:
                        spec = run_specs.get(run_id)
                        if spec is None:
                            records_valid = False
                        else:
                            parsed_records = [
                                EvaluationRecord.model_validate(
                                    {
                                        key: value
                                        for key, value in document.items()
                                        if key != "digest"
                                    }
                                )
                                for document in documents
                            ]
                            gate_results = EvaluationValidator.gate_results(
                                spec.evaluation_plan,
                                parsed_records,
                            )
                            required_stages = EvaluationValidator.stages_visible_after_gates(
                                spec.evaluation_plan,
                                gate_results,
                            )
                            records_valid = records_valid and set(required_stages).issubset(
                                gate_results
                            )
                    results[name] = records_valid
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
            except KeyError, TypeError, ValueError:
                results[name] = False
        try:
            bundle_document = json.loads(archive.read("bundle.json"))
            comparison_document = json.loads(archive.read("comparison.json"))
            run_ids = {str(item) for item in bundle_document["run_ids"]}
            comparison_run_ids = {
                str(comparison_document["baseline_run_id"]),
                str(comparison_document["candidate_run_id"]),
            }
            results["comparison.json"] = (
                len(run_ids) == 2
                and run_ids == comparison_run_ids == set(run_specs)
                and comparison_document["id"] == bundle_document["comparison_id"]
            )
        except KeyError, TypeError, ValueError:
            results["comparison.json"] = False
        return results

    @staticmethod
    def _verify_v3_structure(bundle_manifest: dict[str, Any], names: set[str]) -> bool:
        raw_run_ids = bundle_manifest.get("run_ids")
        if not isinstance(raw_run_ids, list):
            return False
        run_ids = cast(list[object], raw_run_ids)
        if (
            bundle_manifest.get("kind") != "run"
            or bundle_manifest.get("profile") != "audit"
            or bundle_manifest.get("artifact_content") != "references_only"
            or bundle_manifest.get("portable") is not False
            or bundle_manifest.get("replayable") is not False
            or len(run_ids) != 1
            or not isinstance(run_ids[0], str)
            or "artifact-manifest.json" not in names
        ):
            return False
        run_id = run_ids[0]
        required = {
            f"runs/{run_id}.json",
            f"events/{run_id}.jsonl",
            f"evaluations/{run_id}.json",
            f"checkpoints/{run_id}.json",
        }
        return (
            required.issubset(names)
            and any(name.startswith("execution/jobs/") for name in names)
            and any(name.startswith("execution/attempts/") for name in names)
        )

    @staticmethod
    def _verify_v3_records(archive: zipfile.ZipFile, names: set[str]) -> dict[str, bool]:
        results = EvidenceBundleService._verify_v2_records(archive, names)
        results.pop("comparison.json", None)
        results.pop("artifact-manifest.json", None)
        try:
            bundle = json.loads(archive.read("bundle.json"))
            run_id = str(bundle["run_ids"][0])
            run_document = json.loads(archive.read(f"runs/{run_id}.json"))
            run_record = RunRecord.model_validate(run_document)
            spec_document = json.loads(archive.read(f"run-specs/{run_record.run_spec_id}.json"))
            spec_digest = spec_document.pop("digest")
            spec = RunSpec.model_validate(spec_document)
            admission_document = json.loads(
                archive.read(f"admissions/{run_record.admission_id}.json")
            )
            admission_digest = admission_document.pop("digest")
            admission = AdmissionRecord.model_validate(admission_document)
            events = [
                json.loads(line)
                for line in archive.read(f"events/{run_id}.jsonl").splitlines()
                if line
            ]
            invocations = [event for event in events if event["type"] == "subject.invoked"]
            subject_name = f"subject-envelopes/{run_id}.json"
            subject_record: SubjectEnvelopeRecord | None = None
            if subject_name in names:
                envelope_document = json.loads(archive.read(subject_name))
                envelope_digest = envelope_document.pop("digest")
                subject_record = SubjectEnvelopeRecord.model_validate(envelope_document)
                visible_by_id = {
                    item.id: item
                    for item in spec.scenario.input_bindings
                    if item.visibility in {"subject", "subject_and_evaluator"}
                }
                envelope_inputs_valid = set(visible_by_id) == {
                    item.id for item in subject_record.envelope.inputs
                } and all(
                    item.role == visible_by_id[item.id].role
                    and item.visibility == visible_by_id[item.id].visibility
                    and item.mount_name == visible_by_id[item.id].mount_name
                    and item.mount_access == visible_by_id[item.id].mount_access
                    and item.source.media_type == visible_by_id[item.id].source.media_type
                    and item.source.classification == visible_by_id[item.id].source.classification
                    for item in subject_record.envelope.inputs
                )
                resolved_capabilities = tuple(
                    item
                    for item in admission.resolved_inventory.capabilities
                    if item.status == "resolved"
                )
                results[subject_name] = (
                    subject_record.run_id == run_id
                    and subject_record.digest == envelope_digest
                    and subject_record.envelope.run_spec_digest == spec.digest == spec_digest
                    and admission.digest == admission_digest
                    and subject_record.envelope.effective_capabilities == resolved_capabilities
                    and envelope_inputs_valid
                    and len(invocations) <= 1
                    and all(
                        event["payload"]["subject_envelope_digest"] == subject_record.digest
                        for event in invocations
                    )
                )
            else:
                materialization_events = {
                    "context.composed",
                    "capability.offered",
                    "subject.invoked",
                    "subject.responded",
                }
                results["__subject_envelope_absence__"] = not any(
                    event["type"] in materialization_events for event in events
                )

            resolved_capabilities = tuple(
                item
                for item in admission.resolved_inventory.capabilities
                if item.status == "resolved"
            )
            expected_offers = {
                canonical_json(
                    {
                        "capability_ref": semantic_model_dump(item.resolved_ref),
                        "required": item.required,
                        "exposure": item.exposure,
                        "effective_permissions": list(item.effective_permissions),
                    }
                )
                for item in resolved_capabilities
                if item.resolved_ref is not None
            }
            actual_offer_documents = [
                event["payload"] for event in events if event["type"] == "capability.offered"
            ]
            actual_offers = {canonical_json(item) for item in actual_offer_documents}
            offers_valid = len(actual_offer_documents) == len(actual_offers) and actual_offers == (
                expected_offers if subject_record is not None else set()
            )
            expected_invocation = {
                "runner": admission.resolved_inventory.runner_ref.name,
                "network": spec.workspace.network_policy.mode,
                "provider_profile_id": admission.resolved_inventory.provider_profile_id,
                "provider_model": admission.resolved_inventory.provider_model,
                "provider_reasoning_effort": (
                    admission.resolved_inventory.provider_reasoning_effort
                ),
                "provider_adapter": admission.resolved_inventory.provider_adapter,
            }
            invocations_valid = len(invocations) <= 1 and all(
                all(
                    event["payload"].get(key) == value for key, value in expected_invocation.items()
                )
                for event in invocations
            )
            results["__runtime_admission_binding__"] = offers_valid and invocations_valid

            job_names = sorted(name for name in names if name.startswith("execution/jobs/"))
            if len(job_names) != 1:
                raise ValueError("Bundle v3 requires exactly one execution job")
            job_document = json.loads(archive.read(job_names[0]))
            job_digest = job_document.pop("digest")
            job = RunExecutionJob.model_validate(job_document)
            attempts_name = f"execution/attempts/{job.job_id}.json"
            attempts_documents = json.loads(archive.read(attempts_name))
            attempts: list[RunExecutionAttempt] = []
            attempts_valid = True
            for document in attempts_documents:
                expected = document.pop("digest")
                attempt = RunExecutionAttempt.model_validate(document)
                attempts.append(attempt)
                attempts_valid = attempts_valid and attempt.digest == expected
            attempts_valid = (
                attempts_valid
                and bool(attempts)
                and all(
                    attempt.job_id == job.job_id
                    and attempt.ordinal == index
                    and attempt.lease_generation == index
                    for index, attempt in enumerate(attempts, start=1)
                )
            )
            attempts_valid = attempts_valid and len(
                {attempt.ordinal for attempt in attempts}
            ) == len(attempts)
            attempts_valid = attempts_valid and len(
                {attempt.lease_generation for attempt in attempts}
            ) == len(attempts)
            attempts_valid = (
                attempts_valid
                and job.lease_generation == attempts[-1].lease_generation
                and all(attempt.status in {"released", "expired"} for attempt in attempts[:-1])
                and (
                    (job.status == "completed" and attempts[-1].status == "completed")
                    or (job.status == "rejected" and attempts[-1].status == "rejected")
                )
            )
            attempts_valid = attempts_valid and all(
                attempt.last_heartbeat_at_utc < attempt.lease_expires_at_utc
                and attempt.finished_at_utc is not None
                and attempt.finished_at_utc >= attempt.leased_at_utc
                and attempt.last_heartbeat_at_utc <= attempt.finished_at_utc
                and (
                    attempt.status != "expired"
                    or attempt.finished_at_utc >= attempt.lease_expires_at_utc
                )
                for attempt in attempts
            )
            attempts_valid = attempts_valid and all(
                earlier.leased_at_utc <= later.leased_at_utc
                for earlier, later in pairwise(attempts)
            )
            results[job_names[0]] = (
                job.digest == job_digest
                and job.run_id == run_id
                and job.status in {"completed", "rejected"}
                and job.active_attempt_id is None
                and job.created_at_utc <= attempts[0].leased_at_utc
                and job.finished_at_utc is not None
                and attempts[-1].finished_at_utc is not None
                and job.finished_at_utc == attempts[-1].finished_at_utc
            )
            results[attempts_name] = attempts_valid

            manifest_document = json.loads(archive.read("artifact-manifest.json"))
            manifest_digest = manifest_document.pop("digest")
            manifest = ArtifactManifest.model_validate(manifest_document)
            checkpoint_documents = json.loads(archive.read(f"checkpoints/{run_id}.json"))
            expected_entries = EvidenceBundleService._spec_artifact_entries(run_id, spec)
            if subject_record is not None:
                expected_entries.extend(
                    EvidenceBundleService._subject_artifact_entries(subject_record)
                )
            expected_entries.extend(EvidenceBundleService._event_artifact_entries(run_id, events))
            expected_entries.extend(
                EvidenceBundleService._checkpoint_artifact_entries(
                    run_id,
                    [
                        CheckpointRecord.model_validate(
                            {
                                key: value
                                for key, value in document.items()
                                if key != "checkpoint_hash"
                            }
                        )
                        for document in checkpoint_documents
                    ],
                )
            )
            expected_set = {canonical_json(semantic_model_dump(item)) for item in expected_entries}
            actual_set = {canonical_json(semantic_model_dump(item)) for item in manifest.entries}
            results["artifact-manifest.json"] = (
                manifest.digest == manifest_digest
                and expected_set == actual_set
                and not manifest.portable
                and not manifest.replayable
            )
            contract_names = {
                "contracts/"
                f"{reference.contract_type.value}/"
                f"{reference.logical_id.replace('/', '_')}@{reference.revision}.json"
                for reference in (
                    spec.study_ref,
                    spec.goal_ref,
                    spec.scenario_ref,
                    spec.agent_inventory_ref,
                    spec.workspace_template_ref,
                    spec.interaction_protocol_ref,
                    spec.evaluation_plan_ref,
                    *(
                        (spec.checkpoint_policy_ref,)
                        if spec.checkpoint_policy_ref is not None
                        else ()
                    ),
                    *(
                        (spec.progress_artifact_policy_ref,)
                        if spec.progress_artifact_policy_ref is not None
                        else ()
                    ),
                )
            }
            expected_names = {
                "bundle.json",
                "checksums.json",
                "artifact-manifest.json",
                f"run-specs/{run_record.run_spec_id}.json",
                f"admissions/{run_record.admission_id}.json",
                f"runs/{run_id}.json",
                f"events/{run_id}.jsonl",
                f"evaluations/{run_id}.json",
                f"checkpoints/{run_id}.json",
                job_names[0],
                attempts_name,
                *contract_names,
            }
            if subject_record is not None:
                expected_names.add(subject_name)
            results["__exact_file_allowlist__"] = names == expected_names
        except AttributeError, IndexError, KeyError, TypeError, ValueError:
            results["__v3_records__"] = False
        else:
            results["__v3_records__"] = True
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
        records_by_id: dict[str, dict[str, Any]],
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
        if record.source_type == "human_adjudicator":
            policy = spec.evaluation_plan.human_adjudication_policy
            if (
                not policy.required
                or record.stage_id not in policy.adjudicable_stage_ids
                or record.evaluator_ref != policy.adjudicator_ref
                or record.human_attestation is None
                or record.human_attestation.verifier_ref != policy.attestation_verifier_ref
                or record.relation is None
                or record.relation.kind != "adjudicates"
            ):
                return False
            adjudications_for_stage = [
                document
                for document in records_by_id.values()
                if document.get("source_type") == "human_adjudicator"
                and document.get("stage_id") == record.stage_id
            ]
            if len(adjudications_for_stage) != 1:
                return False
            for target_ref in record.relation.target_record_refs:
                target_document = records_by_id.get(target_ref)
                if target_document is None:
                    return False
                target = EvaluationRecord.model_validate(
                    {key: value for key, value in target_document.items() if key != "digest"}
                )
                if (
                    target.run_id != run_id
                    or target.plan_ref != record.plan_ref
                    or target.stage_id != record.stage_id
                ):
                    return False
        if record.source_type == "human_reviewer":
            if record.relation is None or record.relation.kind != "independent_review":
                return False
            for considered_ref in record.relation.considers_record_refs:
                considered = records_by_id.get(considered_ref)
                if considered is None or considered.get("run_id") != run_id:
                    return False
        boundary = record.boundary
        if (
            boundary.up_to_event_sequence is not None
            and event_boundaries.get(run_id, {}).get(boundary.up_to_event_sequence)
            != boundary.event_hash
        ):
            return False
        if boundary.checkpoint_id is not None and boundary.checkpoint_id not in checkpoint_ids.get(
            run_id, set()
        ):
            return False
        stage = next(item for item in spec.evaluation_plan.stages if item.id == record.stage_id)
        boundary_sequence = boundary.up_to_event_sequence
        if boundary.checkpoint_id is not None:
            boundary_sequence = checkpoint_sequences.get(run_id, {}).get(boundary.checkpoint_id)
        if boundary_sequence is None:
            return False
        if record.source_type in {"human_reviewer", "human_adjudicator"}:
            relation = record.relation
            if relation is None:
                return False
            related_refs = (
                relation.target_record_refs
                if relation.kind == "adjudicates"
                else relation.considers_record_refs
            )
            related_records: list[tuple[EvaluationRecord, int]] = []
            for related_ref in related_refs:
                related_document = records_by_id.get(related_ref)
                if related_document is None:
                    return False
                related_record = EvaluationRecord.model_validate(
                    {key: value for key, value in related_document.items() if key != "digest"}
                )
                related_sequence = related_record.boundary.up_to_event_sequence
                if related_record.boundary.checkpoint_id is not None:
                    related_sequence = checkpoint_sequences.get(run_id, {}).get(
                        related_record.boundary.checkpoint_id
                    )
                if related_sequence is None:
                    return False
                related_records.append((related_record, related_sequence))
            try:
                EvaluationValidator.validate_human_relation_boundary(
                    record,
                    boundary_sequence=boundary_sequence,
                    related_records=related_records,
                )
            except ValueError:
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
            {key: value for key, value in document.items() if key != "checkpoint_hash"}
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
            or record.definition_digest != sha256_json(semantic_model_dump(definition))
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
            event_types.get(run_id, {}).get(record.up_to_event_sequence) != trigger.event_type
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
    def _spec_artifact_entries(run_id: str, spec: RunSpec) -> list[ArtifactManifestEntry]:
        entries: list[ArtifactManifestEntry] = []

        def add(
            role: Literal[
                "scenario_input",
                "agent_instruction",
                "interaction_prompt",
                "hidden_calibration",
                "extension_schema",
                "extension_payload",
            ],
            artifact_ref: Any,
            source_label: str,
        ) -> None:
            entries.append(
                ArtifactManifestEntry(
                    run_id=run_id,
                    role=role,
                    artifact_ref=artifact_ref,
                    source_label=source_label,
                    content_included=False,
                    omission_reason=(
                        "audit profile includes identity and digest, not artifact bytes"
                    ),
                    required_for_portability=True,
                )
            )

        for binding in spec.scenario.input_bindings:
            add("scenario_input", binding.source, f"scenario_input:{binding.id}")
        interaction_refs = tuple(
            item
            for item in (
                spec.interaction_protocol.system_prompt_ref,
                *spec.interaction_protocol.initial_message_refs,
            )
            if item is not None
        )
        for index, artifact_ref in enumerate(interaction_refs):
            add("interaction_prompt", artifact_ref, f"interaction_prompt:{index}")
        for requirement in spec.agent_inventory.capability_requirements:
            for index, artifact_ref in enumerate(requirement.instruction_refs):
                add(
                    "agent_instruction",
                    artifact_ref,
                    f"capability_instruction:{requirement.capability_ref.name}:{index}",
                )
        for index, artifact_ref in enumerate(spec.evaluation_plan.disclosure.hidden_input_refs):
            add("hidden_calibration", artifact_ref, f"hidden_calibration:{index}")
        for extension in spec.extensions:
            add(
                "extension_schema",
                extension.schema_ref,
                f"extension_schema:{extension.namespace}:{extension.slot}",
            )
            add(
                "extension_payload",
                extension.payload_ref,
                f"extension_payload:{extension.namespace}:{extension.slot}",
            )
        return entries

    @staticmethod
    def _checkpoint_artifact_entries(
        run_id: str, records: list[CheckpointRecord]
    ) -> list[ArtifactManifestEntry]:
        entries: list[ArtifactManifestEntry] = []
        for record in records:
            refs = (
                record.protocol_state_ref,
                record.artifact_manifest_ref,
                record.workspace_snapshot_ref,
            )
            for index, artifact_ref in enumerate(item for item in refs if item is not None):
                entries.append(
                    ArtifactManifestEntry(
                        run_id=run_id,
                        role="checkpoint_capture",
                        artifact_ref=artifact_ref,
                        source_label=f"checkpoint:{record.checkpoint_id}:{index}",
                        content_included=False,
                        omission_reason=(
                            "audit profile includes identity and digest, not artifact bytes"
                        ),
                        required_for_portability=True,
                    )
                )
        return entries

    @staticmethod
    def _subject_artifact_entries(
        record: SubjectEnvelopeRecord,
    ) -> list[ArtifactManifestEntry]:
        return [
            ArtifactManifestEntry(
                run_id=record.run_id,
                role="subject_input_materialized",
                artifact_ref=binding.source,
                source_label=f"subject_input_materialized:{binding.id}",
                content_included=False,
                omission_reason=("audit profile includes identity and digest, not artifact bytes"),
                required_for_portability=True,
            )
            for binding in record.envelope.inputs
        ]

    @staticmethod
    def _event_artifact_entries(
        run_id: str,
        events: list[dict[str, Any]],
    ) -> list[ArtifactManifestEntry]:
        entries: list[ArtifactManifestEntry] = []
        omission_reason = "audit profile includes identity and digest, not artifact bytes"
        for event in events:
            payload_value: object = event.get("payload")
            if not isinstance(payload_value, dict):
                continue
            payload = cast(dict[str, object], payload_value)
            event_id = str(event.get("event_id", "unknown"))
            arguments_ref = payload.get("arguments_ref")
            if event.get("type") == "tool.called" and isinstance(arguments_ref, dict):
                entries.append(
                    ArtifactManifestEntry(
                        run_id=run_id,
                        role="tool_arguments",
                        artifact_ref=ArtifactRef.model_validate(arguments_ref),
                        source_label=f"tool_arguments:{event_id}",
                        content_included=False,
                        omission_reason=omission_reason,
                        required_for_portability=True,
                    )
                )
            result_ref = payload.get("result_ref")
            if event.get("type") in {"tool.completed", "tool.failed"} and isinstance(
                result_ref, dict
            ):
                entries.append(
                    ArtifactManifestEntry(
                        run_id=run_id,
                        role="tool_result",
                        artifact_ref=ArtifactRef.model_validate(result_ref),
                        source_label=f"tool_result:{event_id}",
                        content_included=False,
                        omission_reason=omission_reason,
                        required_for_portability=True,
                    )
                )
            output_ref = payload.get("output_ref")
            if event.get("type") == "subject.responded" and isinstance(output_ref, dict):
                entries.append(
                    ArtifactManifestEntry(
                        run_id=run_id,
                        role="run_output",
                        artifact_ref=ArtifactRef.model_validate(output_ref),
                        source_label=f"run_output:{event_id}",
                        content_included=False,
                        omission_reason=omission_reason,
                        required_for_portability=True,
                    )
                )
        return entries

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
