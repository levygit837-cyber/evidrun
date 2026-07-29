"""Bundle v4: a terminal Run plus its immutable execution trust record."""

from __future__ import annotations

from pathlib import Path

from evidrun.contracts import ContractRef, semantic_model_dump
from evidrun.evidence import archive as ar
from evidrun.evidence.export.run_v3 import TERMINAL_RUN_STATUSES
from evidrun.infrastructure.database import Repository


def export_run_v4(repository: Repository, run_id: str, output_path: Path) -> Path:
    run = repository.read_model.get_run(run_id)
    contracts = repository.read_model.get_run_contracts(run_id)
    if contracts is None or run.run_spec_id is None or run.admission_id is None:
        raise ValueError("Evidence Bundle v4 requires a Study-based Run")
    if run.status not in TERMINAL_RUN_STATUSES:
        raise ValueError("Evidence Bundle v4 requires a terminal Run")
    spec, admission = contracts
    run_record = repository.read_model.get_run_record(run_id)
    if run_record is None or run_record.execution_trust is None:
        raise ValueError("Evidence Bundle v4 requires recorded execution trust")
    if admission.execution_trust != run_record.execution_trust:
        raise ValueError("Run and admission execution trust do not match")
    trust = repository.execution_trust.get_record(run_record.execution_trust.trust_id)
    if trust.ref != run_record.execution_trust or trust.run_spec_digest != spec.digest:
        raise ValueError("execution trust does not bind the exported RunSpec")
    if trust.kind != "unverified_revision_set":
        raise ValueError("verified Bundle v4 export requires revision decisions")

    events = repository.read_model.get_run_events(run_id)
    try:
        subject_record = repository.read_model.get_subject_envelope(run_id)
    except KeyError:
        subject_record = None
    execution = repository.lease.get_run_execution(run_id)
    if execution is None:
        raise ValueError("Evidence Bundle v4 requires durable execution records")
    job, attempts = execution
    checkpoints = repository.read_model.get_checkpoint_records(run_id)
    files: dict[str, bytes] = {
        "bundle.json": ar.json_bytes(
            {
                "schema_version": "4",
                "kind": "run",
                "profile": "audit",
                "artifact_content": "references_only",
                "portable": False,
                "replayable": False,
                "run_ids": [run_id],
                "execution_trust": {
                    "kind": trust.kind,
                    "trust_id": trust.trust_id,
                    "digest": trust.digest,
                },
                "isolation": {"kind": spec.workspace.runtime_kind},
            }
        ),
        f"run-specs/{run.run_spec_id}.json": ar.json_bytes(ar.record_dict(spec)),
        f"admissions/{run.admission_id}.json": ar.json_bytes(ar.record_dict(admission)),
        f"runs/{run_id}.json": ar.json_bytes(semantic_model_dump(run_record)),
        f"execution-trust/{trust.trust_id}.json": ar.json_bytes(ar.record_dict(trust)),
        f"events/{run_id}.jsonl": ar.jsonl_bytes(events),
        f"evaluations/{run_id}.json": ar.json_bytes(
            [
                ar.record_dict(record)
                for record in repository.read_model.get_evaluation_records(run_id)
            ]
        ),
        f"checkpoints/{run_id}.json": ar.json_bytes(
            [
                ar.record_dict(record, digest_field="checkpoint_hash")
                for record in checkpoints
            ]
        ),
        f"execution/jobs/{job.job_id}.json": ar.json_bytes(ar.record_dict(job)),
        f"execution/attempts/{job.job_id}.json": ar.json_bytes(
            [ar.record_dict(attempt) for attempt in attempts]
        ),
    }
    if subject_record is not None:
        files[f"subject-envelopes/{run_id}.json"] = ar.json_bytes(
            ar.record_dict(subject_record)
        )
    _add_trust_contract_members(repository, files, trust.revision_refs)
    entries = ar.spec_artifact_entries(run_id, spec)
    if subject_record is not None:
        entries.extend(ar.subject_artifact_entries(subject_record))
    entries.extend(ar.event_artifact_entries(run_id, events))
    entries.extend(ar.checkpoint_artifact_entries(run_id, checkpoints))
    files["artifact-manifest.json"] = ar.json_bytes(
        ar.record_dict(ar.artifact_manifest(entries))
    )
    return ar.write_bundle(output_path, files, schema_version="4")


def _add_trust_contract_members(
    repository: Repository,
    files: dict[str, bytes],
    references: tuple[ContractRef, ...],
) -> None:
    for reference in references:
        revision = repository.read_model.get_contract_revision_by_ref(reference)
        files[ar.contract_member_name(reference)] = ar.json_bytes(
            ar.record_dict(revision)
        )
