from __future__ import annotations

import asyncio
import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from evidrun.contracts import ExecutionTrustRecord
from evidrun.evidence import archive as ar
from evidrun.evidence.bundle import EvidenceBundleService
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.infrastructure.database import Database, Repository
from evidrun.runs import DurableRunWorker, EvidrunService
from evidrun.settings import Settings
from evidrun.shared.types import Classification, new_id
from tests.support.runtime_study import build_runtime_study


def _archive_files(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def _write_resealed(path: Path, files: dict[str, bytes]) -> None:
    checksums = {
        name: hashlib.sha256(content).hexdigest()
        for name, content in files.items()
        if name != "checksums.json"
    }
    files["checksums.json"] = (
        json.dumps(
            {
                "schema_version": "4",
                "created_at": "2026-07-28T00:00:00+00:00",
                "files": checksums,
            },
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)


def test_draft_study_executes_offline_and_bundle_v4_rejects_trust_tampering(
    tmp_path: Path,
) -> None:
    settings = Settings.load(tmp_path)
    settings.ensure_directories()
    database = Database(settings.database_path)
    database.create_all()
    repository = Repository(database)
    workspace = repository.catalog.create_workspace("Unverified offline workspace")
    project = repository.catalog.create_project(workspace.id, "Unverified draft project")
    source = ArtifactStore(settings.artifacts_dir).put_ref(
        b"start\nROOT_CAUSE=SEARCH_INDEX_LAG\nend\n",
        project_id=project.id,
        media_type="text/plain",
        classification=Classification.INTERNAL,
    )
    revisions, original_study = build_runtime_study(
        project_id=project.id, source=source
    )
    study = original_study.model_copy(
        update={
            "payload": original_study.payload.model_copy(
                update={"repetitions": 2}
            )
        }
    )
    revisions = (*revisions[:-1], study)
    study_row_id = ""
    for revision in revisions:
        row = repository.registry.save_contract_revision(revision, status="draft")
        if revision == study:
            study_row_id = row.id

    service = EvidrunService(repository)
    preparation = service.execution_preparation.prepare(study_row_id)
    assert len(preparation.run_specs) == 2
    assert preparation.review_target.run_spec_digests == tuple(
        sorted(item.spec.digest for item in preparation.run_specs)
    )
    prepared = preparation.run_specs[0]
    assert prepared.execution_trust.kind == "unverified_revision_set"
    assert prepared.execution_trust.verified_decisions == ()
    admission = service.admission_service.admit(
        prepared.spec, prepared.execution_trust
    )
    assert admission.decision == "admitted"
    admission_row = repository.catalog.save_admission_record(
        prepared.row_id, admission
    )
    run_id, job = service.runtime.coordinator.enqueue(
        run_spec_id=prepared.row_id,
        admission_id=admission_row.id,
        idempotency_key="unverified-draft-offline-v1",
    )
    worker = DurableRunWorker(
        repository,
        service.runtime.coordinator,
        worker_id="unverified-offline-worker",
    )
    assert asyncio.run(worker.process_once(job_id=job.job_id)) is True
    assert repository.read_model.get_run(run_id).status == "completed"
    run_record = repository.read_model.get_run_record(run_id)
    assert run_record is not None
    assert run_record.execution_trust == prepared.execution_trust.ref
    assert admission.execution_trust == prepared.execution_trust.ref

    bundle = tmp_path / "unverified-run-v4.evidrun.zip"
    bundles = EvidenceBundleService(repository)
    with pytest.raises(
        ValueError,
        match="Bundle v3 applies only to legacy Runs without execution trust",
    ):
        bundles.export_run_v3(run_id, tmp_path / "wrong-version-v3.zip")
    bundles.export_run_v4(run_id, bundle)
    verification = bundles.verify(bundle)
    assert verification["valid"] is True, verification
    assert verification["records"]["__execution_trust_lineage__"] is True

    omitted = tmp_path / "omitted-trust.zip"
    omitted_files = _archive_files(bundle)
    trust_name = next(
        name for name in omitted_files if name.startswith("execution-trust/")
    )
    omitted_files.pop(trust_name)
    _write_resealed(omitted, omitted_files)
    assert bundles.verify(omitted)["valid"] is False

    forged = tmp_path / "forged-trust.zip"
    forged_files = _archive_files(bundle)
    trust_document = json.loads(forged_files[trust_name])
    trust_document["run_spec_digest"] = "f" * 64
    forged_files[trust_name] = (
        json.dumps(trust_document, sort_keys=True, indent=2) + "\n"
    ).encode()
    _write_resealed(forged, forged_files)
    assert bundles.verify(forged)["valid"] is False

    swapped = tmp_path / "swapped-trust.zip"
    swapped_files = _archive_files(bundle)
    original_document = json.loads(swapped_files.pop(trust_name))
    original_document.pop("digest")
    substituted = ExecutionTrustRecord.model_validate(original_document).model_copy(
        update={"trust_id": new_id("trust")}
    )
    substituted_name = f"execution-trust/{substituted.trust_id}.json"
    swapped_files[substituted_name] = ar.json_bytes(ar.record_dict(substituted))
    bundle_document = json.loads(swapped_files["bundle.json"])
    bundle_document["execution_trust"] = {
        "kind": substituted.kind,
        "trust_id": substituted.trust_id,
        "digest": substituted.digest,
    }
    swapped_files["bundle.json"] = ar.json_bytes(bundle_document)
    _write_resealed(swapped, swapped_files)
    assert bundles.verify(swapped)["valid"] is False

    duplicate = tmp_path / "duplicate-trust.zip"
    duplicate_files = _archive_files(bundle)
    _write_resealed(duplicate, duplicate_files)
    with (
        pytest.warns(UserWarning, match="Duplicate name"),
        zipfile.ZipFile(duplicate, "a") as archive,
    ):
        archive.writestr(trust_name, duplicate_files[trust_name])
    assert bundles.verify(duplicate)["valid"] is False
    database.dispose()
