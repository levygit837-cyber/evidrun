"""Bundle v2: a comparison of two contract-linked Runs.

v2 requires Study-based Runs: without RunSpec and AdmissionRecord there is nothing to
audit against, so a missing link raises instead of exporting a weaker bundle. The
profile is `audit` and never portable or replayable — artifact identity travels, bytes
do not.
"""

from __future__ import annotations

from pathlib import Path

from evidrun.contracts import (
    AdmissionRecord,
    ArtifactManifestEntry,
    ContractRef,
    RunSpec,
    semantic_model_dump,
)
from evidrun.evidence import archive as ar
from evidrun.evidence.export.comparison_v1 import comparison_document
from evidrun.infrastructure.database import Repository
from evidrun.infrastructure.database.models import RunRow


def export_comparison_v2(
    repository: Repository, comparison_id: str, output_path: Path
) -> Path:
    comparison = repository.read_model.get_comparison(comparison_id)
    run_rows = [
        repository.read_model.get_run(comparison.baseline_run_id),
        repository.read_model.get_run(comparison.candidate_run_id),
    ]
    run_contracts: dict[str, tuple[RunSpec, AdmissionRecord]] = {}
    for run in run_rows:
        contracts = repository.read_model.get_run_contracts(run.id)
        if contracts is None:
            raise ValueError("Evidence Bundle v2 requires Study-based Runs")
        run_contracts[run.id] = contracts

    files: dict[str, bytes] = {
        "bundle.json": ar.json_bytes(
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
        "comparison.json": ar.json_bytes(comparison_document(comparison)),
        "report.md": comparison.report_markdown.encode("utf-8"),
    }

    revision_refs: dict[tuple[str, str, int], ContractRef] = {}
    artifact_entries: list[ArtifactManifestEntry] = []
    for run in run_rows:
        spec, admission = run_contracts[run.id]
        artifact_entries.extend(
            _add_run_members(repository, files, run, spec=spec, admission=admission)
        )
        for reference in ar.spec_revision_refs(spec):
            key = (reference.contract_type.value, reference.logical_id, reference.revision)
            revision_refs[key] = reference

    for reference in revision_refs.values():
        revision = repository.read_model.get_contract_revision_by_ref(reference)
        files[ar.contract_member_name(reference)] = ar.json_bytes(ar.record_dict(revision))

    files["artifact-manifest.json"] = ar.json_bytes(
        ar.record_dict(ar.artifact_manifest(artifact_entries))
    )
    return ar.write_bundle(output_path, files, schema_version="2")


def _add_run_members(
    repository: Repository,
    files: dict[str, bytes],
    run: RunRow,
    *,
    spec: RunSpec,
    admission: AdmissionRecord,
) -> list[ArtifactManifestEntry]:
    """Escreve os membros de uma Run e devolve suas entradas de artifact."""

    if run.run_spec_id is None or run.admission_id is None:
        raise ValueError("Evidence Bundle v2 requires Run contract links")
    run_record = repository.read_model.get_run_record(run.id)
    if run_record is None:
        raise ValueError("Evidence Bundle v2 requires a canonical RunRecord")
    checkpoints = repository.read_model.get_checkpoint_records(run.id)
    files[f"run-specs/{run.run_spec_id}.json"] = ar.json_bytes(ar.record_dict(spec))
    files[f"admissions/{run.admission_id}.json"] = ar.json_bytes(ar.record_dict(admission))
    files[f"runs/{run.id}.json"] = ar.json_bytes(semantic_model_dump(run_record))
    files[f"events/{run.id}.jsonl"] = ar.jsonl_bytes(
        repository.read_model.get_run_events(run.id)
    )
    files[f"evaluations/{run.id}.json"] = ar.json_bytes(
        [
            ar.record_dict(record)
            for record in repository.read_model.get_evaluation_records(run.id)
        ]
    )
    files[f"checkpoints/{run.id}.json"] = ar.json_bytes(
        [ar.record_dict(record, digest_field="checkpoint_hash") for record in checkpoints]
    )
    return [
        *ar.spec_artifact_entries(run.id, spec),
        *ar.checkpoint_artifact_entries(run.id, checkpoints),
    ]
