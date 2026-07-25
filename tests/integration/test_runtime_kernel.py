from __future__ import annotations

import hashlib
import inspect
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import evidrun.entrypoints.cli.app as cli_app_module
import evidrun.entrypoints.worker.app as worker_app_module
from evidrun.contracts.authority import UnavailableHumanAttestationVerifier
from evidrun.contracts.compiler import StudyCompiler
from evidrun.entrypoints.api.app import create_app
from evidrun.evidence.bundle import EvidenceBundleService
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.infrastructure.database import Database, Repository
from evidrun.runs import RuntimeAdapterCatalog, build_runtime_kernel
from evidrun.shared.settings import Settings
from evidrun.shared.types import Classification
from tests.support.human_attestation import (
    TestHumanAttestationVerifier,
    accepted_decision,
)
from tests.support.runtime_study import build_runtime_study


def test_generic_run_survives_restart_and_executes_in_worker_subprocess(
    tmp_path: Path,
) -> None:
    settings = Settings.load(tmp_path)
    settings.ensure_directories()
    database = Database(settings.database_path)
    database.create_all()
    repository = Repository(database, TestHumanAttestationVerifier())
    workspace = repository.catalog.create_workspace("Workspace Runtime Kernel")
    project = repository.catalog.create_project(workspace.id, "Projeto Runtime Kernel")
    source = ArtifactStore(settings.artifacts_dir).put_ref(
        b"2026-07-23T10:00:00Z search replica healthy\n"
        b"2026-07-23T10:00:01Z queue delay rising\n"
        b"2026-07-23T10:00:02Z ROOT_CAUSE=SEARCH_INDEX_LAG\n",
        project_id=project.id,
        media_type="text/plain",
        classification=Classification.INTERNAL,
    )
    revisions, study = build_runtime_study(project_id=project.id, source=source)
    for revision in revisions:
        repository.registry.save_contract_revision(revision, status="proposed")
        repository.registry.decide_contract_revision(accepted_decision(revision))

    specs = StudyCompiler(repository.registry.contract_registry(project.id)).compile(study)
    assert len(specs) == 1
    spec_row = repository.catalog.save_run_spec(specs[0])
    kernel = build_runtime_kernel(repository, settings.artifacts_dir)
    admission = kernel.coordinator.admission_service.admit(specs[0])
    assert admission.decision == "admitted"
    admission_row = repository.catalog.save_admission_record(spec_row.id, admission)
    run_id, job = kernel.coordinator.enqueue(
        run_spec_id=spec_row.id,
        admission_id=admission_row.id,
        idempotency_key="generic-runtime-study-1",
    )
    database.dispose()

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "evidrun.entrypoints.worker.app",
            "--data-dir",
            str(tmp_path),
            "--worker-id",
            "transverse-subprocess-worker",
            "--once",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert completed.returncode == 0, completed.stderr

    reopened = Database(settings.database_path)
    reopened.create_all()
    durable_repository = Repository(reopened)
    assert durable_repository.read_model.get_run(run_id).status == "completed"
    execution = durable_repository.lease.get_run_execution(run_id)
    assert execution is not None
    assert execution[0].job_id == job.job_id
    assert execution[0].status == "completed"
    assert [item.ordinal for item in execution[1]] == [1]
    assert execution[1][0].worker_id == "transverse-subprocess-worker"
    event_types = [item["type"] for item in durable_repository.read_model.get_run_events(run_id)]
    assert event_types == [
        "run.queued",
        "run.preparing",
        "context.composed",
        "run.running",
        "subject.invoked",
        "subject.responded",
        "run.evaluating",
        "evaluation.completed",
        "run.completed",
    ]
    assert durable_repository.read_model.get_evaluation_records(run_id)[0].gate_status == "passed"
    envelope = durable_repository.read_model.get_subject_envelope(run_id)
    assert envelope.digest == envelope.envelope.digest
    bundle_path = tmp_path / "generic-run.evidrun.zip"
    bundle_service = EvidenceBundleService(durable_repository)
    bundle_service.export_run_v3(run_id, bundle_path)
    verification = bundle_service.verify(bundle_path)
    assert verification["valid"] is True
    assert verification["records"]["__v3_records__"] is True
    tamper_cases = {
        "subject-envelopes/": lambda document: document["envelope"]["goal"].update(
            {"instruction": "tampered instruction"}
        ),
        "execution/jobs/": lambda document: document.update({"request_digest": "f" * 64}),
        "execution/attempts/": lambda document: document[0].update({"worker_id": "forged-worker"}),
        "artifact-manifest.json": lambda document: document["entries"].pop(),
    }
    for index, (prefix, mutate) in enumerate(tamper_cases.items(), start=1):
        target = tmp_path / f"tampered-run-{index}.zip"
        with zipfile.ZipFile(bundle_path) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        name = next(item for item in files if item.startswith(prefix))
        document = json.loads(files[name])
        mutate(document)
        files[name] = (
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode()
        checksums = json.loads(files["checksums.json"])
        checksums["files"][name] = hashlib.sha256(files[name]).hexdigest()
        files["checksums.json"] = (
            json.dumps(checksums, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode()
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for member_name, content in files.items():
                archive.writestr(member_name, content)
        assert bundle_service.verify(target)["valid"] is False
    covered_extra = tmp_path / "tampered-run-covered-extra.zip"
    with zipfile.ZipFile(bundle_path) as archive:
        files = {name: archive.read(name) for name in archive.namelist()}
    files["unallowlisted.json"] = b"{}\n"
    checksums = json.loads(files["checksums.json"])
    checksums["files"]["unallowlisted.json"] = hashlib.sha256(
        files["unallowlisted.json"]
    ).hexdigest()
    files["checksums.json"] = (
        json.dumps(checksums, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()
    with zipfile.ZipFile(covered_extra, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for member_name, content in files.items():
            archive.writestr(member_name, content)
    extra_verification = bundle_service.verify(covered_extra)
    assert extra_verification["valid"] is False
    assert extra_verification["records"]["__exact_file_allowlist__"] is False
    reopened.dispose()


def test_test_human_verifier_is_not_a_production_fallback(tmp_path: Path) -> None:
    app = create_app(data_dir=tmp_path)
    assert isinstance(
        app.state.repository.human_attestation_verifier,
        UnavailableHumanAttestationVerifier,
    )
    separate_database = Database(tmp_path / "separate.db")
    assert isinstance(
        Repository(separate_database).human_attestation_verifier,
        UnavailableHumanAttestationVerifier,
    )
    production_composition = "\n".join(
        (
            inspect.getsource(cli_app_module),
            inspect.getsource(worker_app_module),
            inspect.getsource(Settings),
            inspect.getsource(RuntimeAdapterCatalog),
        )
    )
    assert "tests.support" not in production_composition
    separate_database.dispose()
    app.state.repository.database.dispose()


def test_admission_rejects_artifact_owned_by_another_project(tmp_path: Path) -> None:
    settings = Settings.load(tmp_path)
    settings.ensure_directories()
    database = Database(settings.database_path)
    database.create_all()
    repository = Repository(database, TestHumanAttestationVerifier())
    workspace = repository.catalog.create_workspace("Cross-project workspace")
    project = repository.catalog.create_project(workspace.id, "Benchmark project")
    foreign_project = repository.catalog.create_project(workspace.id, "Foreign artifact project")
    source = ArtifactStore(settings.artifacts_dir).put_ref(
        b"ROOT_CAUSE=FOREIGN_PROJECT_DATA\n",
        project_id=foreign_project.id,
        media_type="text/plain",
        classification=Classification.INTERNAL,
    )
    revisions, study = build_runtime_study(project_id=project.id, source=source)
    for revision in revisions:
        repository.registry.save_contract_revision(revision, status="proposed")
        repository.registry.decide_contract_revision(accepted_decision(revision))
    spec = StudyCompiler(repository.registry.contract_registry(project.id)).compile(study)[0]
    kernel = build_runtime_kernel(repository, settings.artifacts_dir)

    admission = kernel.coordinator.admission_service.admit(spec)

    assert admission.decision == "rejected"
    assert any(issue.subject_ref == "subject_input_artifact" for issue in admission.issues)
    with database.raw_engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT COUNT(*) FROM runs").scalar_one() == 0
    database.dispose()
