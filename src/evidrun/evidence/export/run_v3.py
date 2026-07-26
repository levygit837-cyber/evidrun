"""Bundle v3: one terminal Run, with its durable execution records.

A Run only exports once it is terminal and its durable job and attempts exist: the
lease chain is part of the evidence, not metadata about it. The bundle is `audit`
profile — never portable, never replayable.
"""

from __future__ import annotations

from pathlib import Path

from evidrun.contracts import RunSpec, semantic_model_dump
from evidrun.evidence import archive as ar
from evidrun.infrastructure.database import Repository

TERMINAL_RUN_STATUSES = frozenset(
    {"completed", "failed", "cancelled", "budget_exhausted", "guardrail_stopped"}
)


def export_run_v3(repository: Repository, run_id: str, output_path: Path) -> Path:
    run = repository.read_model.get_run(run_id)
    contracts = repository.read_model.get_run_contracts(run_id)
    if contracts is None or run.run_spec_id is None or run.admission_id is None:
        raise ValueError("Evidence Bundle v3 requires a Study-based Run")
    if run.status not in TERMINAL_RUN_STATUSES:
        raise ValueError("Evidence Bundle v3 requires a terminal Run")
    spec, admission = contracts
    run_record = repository.read_model.get_run_record(run_id)
    if run_record is None:
        raise ValueError("Evidence Bundle v3 requires a canonical RunRecord")
    events = repository.read_model.get_run_events(run_id)
    try:
        subject_record = repository.read_model.get_subject_envelope(run_id)
    except KeyError:
        subject_record = None
    execution = repository.lease.get_run_execution(run_id)
    if execution is None:
        raise ValueError("Evidence Bundle v3 requires durable execution records")
    job, attempts = execution
    checkpoints = repository.read_model.get_checkpoint_records(run_id)

    files: dict[str, bytes] = {
        "bundle.json": ar.json_bytes(
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
        f"run-specs/{run.run_spec_id}.json": ar.json_bytes(ar.record_dict(spec)),
        f"admissions/{run.admission_id}.json": ar.json_bytes(ar.record_dict(admission)),
        f"runs/{run_id}.json": ar.json_bytes(semantic_model_dump(run_record)),
        f"events/{run_id}.jsonl": ar.jsonl_bytes(events),
        f"evaluations/{run_id}.json": ar.json_bytes(
            [
                ar.record_dict(record)
                for record in repository.read_model.get_evaluation_records(run_id)
            ]
        ),
        f"checkpoints/{run_id}.json": ar.json_bytes(
            [ar.record_dict(record, digest_field="checkpoint_hash") for record in checkpoints]
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
    _add_contract_members(repository, files, spec)

    entries = ar.spec_artifact_entries(run_id, spec)
    if subject_record is not None:
        entries.extend(ar.subject_artifact_entries(subject_record))
    entries.extend(ar.event_artifact_entries(run_id, events))
    entries.extend(ar.checkpoint_artifact_entries(run_id, checkpoints))
    files["artifact-manifest.json"] = ar.json_bytes(ar.record_dict(ar.artifact_manifest(entries)))
    return ar.write_bundle(output_path, files, schema_version="3")


def _add_contract_members(
    repository: Repository, files: dict[str, bytes], spec: RunSpec
) -> None:
    for reference in ar.spec_revision_refs(spec):
        revision = repository.read_model.get_contract_revision_by_ref(reference)
        files[ar.contract_member_name(reference)] = ar.json_bytes(ar.record_dict(revision))
