from __future__ import annotations

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, timedelta
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy.exc import OperationalError

import evidrun.infrastructure.database.clock as db_clock_module
import evidrun.infrastructure.database.evaluation.records as evaluation_records_module
import evidrun.infrastructure.database.queue.preparation as preparation_module
import evidrun.runs.coordinator as coordinator_module
from evidrun.contracts import GoalStateTerminalResult
from evidrun.contracts.compiler import StudyCompiler
from evidrun.evidence.bundle import EvidenceBundleService
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.infrastructure.database import Database, LeaseLost, Repository
from evidrun.runs import DurableRunWorker, RuntimeAdapterCatalog, build_runtime_kernel
from evidrun.runs.adapters import ScriptedLogInvestigatorAdapter
from evidrun.runs.coordinator import RunExecutionCoordinator
from evidrun.shared.settings import Settings
from evidrun.shared.types import Classification, utc_now
from tests.support.human_attestation import (
    TestHumanAttestationVerifier,
    accepted_decision,
)
from tests.support.runtime_study import build_runtime_study


@dataclass
class RuntimeFixture:
    settings: Settings
    database: Database
    repository: Repository
    spec_id: str
    admission_id: str


def _runtime_fixture(tmp_path: Path) -> RuntimeFixture:
    settings = Settings.load(tmp_path)
    settings.ensure_directories()
    database = Database(settings.database_path)
    database.create_all()
    repository = Repository(database, TestHumanAttestationVerifier())
    workspace = repository.catalog.create_workspace("Queue workspace")
    project = repository.catalog.create_project(workspace.id, "Queue project")
    source = ArtifactStore(settings.artifacts_dir).put_ref(
        b"start\nROOT_CAUSE=SEARCH_INDEX_LAG\nend\n",
        project_id=project.id,
        media_type="text/plain",
        classification=Classification.INTERNAL,
    )
    revisions, study = build_runtime_study(project_id=project.id, source=source)
    for revision in revisions:
        repository.registry.save_contract_revision(revision, status="proposed")
        repository.registry.decide_contract_revision(accepted_decision(revision))
    spec = StudyCompiler(repository.registry.contract_registry(project.id)).compile(study)[0]
    spec_row = repository.catalog.save_run_spec(spec)
    admission = build_runtime_kernel(
        repository, settings.artifacts_dir
    ).coordinator.admission_service.admit(spec)
    assert admission.decision == "admitted"
    admission_row = repository.catalog.save_admission_record(spec_row.id, admission)
    return RuntimeFixture(
        settings=settings,
        database=database,
        repository=repository,
        spec_id=spec_row.id,
        admission_id=admission_row.id,
    )


def test_enqueue_is_idempotent_and_two_connections_cannot_claim_same_attempt(
    tmp_path: Path,
) -> None:
    fixture = _runtime_fixture(tmp_path)
    kernel = build_runtime_kernel(fixture.repository, fixture.settings.artifacts_dir)
    first_run_id, first_job = kernel.coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=fixture.admission_id,
        idempotency_key="same-request",
    )
    repeated_run_id, repeated_job = kernel.coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=fixture.admission_id,
        idempotency_key="same-request",
    )
    assert (repeated_run_id, repeated_job.job_id) == (
        first_run_id,
        first_job.job_id,
    )
    second_admission = kernel.coordinator.admission_service.admit(
        fixture.repository.read_model.get_run_spec(fixture.spec_id)
    )
    second_admission_row = fixture.repository.catalog.save_admission_record(
        fixture.spec_id, second_admission
    )
    with pytest.raises(ValueError, match="idempotency key"):
        kernel.coordinator.enqueue(
            run_spec_id=fixture.spec_id,
            admission_id=second_admission_row.id,
            idempotency_key="same-request",
        )
    original_spec = fixture.repository.read_model.get_run_spec(fixture.spec_id)
    divergent_spec_row = fixture.repository.catalog.save_run_spec(
        original_spec.model_copy(update={"variant_id": "divergent-variant"})
    )
    runs_before_divergence = len(fixture.repository.read_model.latest_dashboard()["runs"])
    with pytest.raises(ValueError, match="exact RunSpec"):
        kernel.coordinator.enqueue(
            run_spec_id=divergent_spec_row.id,
            admission_id=fixture.admission_id,
            idempotency_key="divergent-contracts",
        )
    assert len(fixture.repository.read_model.latest_dashboard()["runs"]) == runs_before_divergence

    databases = [Database(fixture.settings.database_path) for _ in range(2)]
    repositories = [Repository(item) for item in databases]
    with ThreadPoolExecutor(max_workers=2) as pool:
        concurrent_enqueues = list(
            pool.map(
                lambda item: item.enqueue.enqueue_run(
                    run_spec_id=fixture.spec_id,
                    admission_id=fixture.admission_id,
                    idempotency_key="concurrent-same-request",
                ),
                repositories,
            )
        )
    assert len({item[0].id for item in concurrent_enqueues}) == 1
    assert len({item[1].job_id for item in concurrent_enqueues}) == 1
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(
            pool.map(
                lambda item: item.lease.claim_next_job(
                    worker_id=f"worker-{id(item)}",
                    lease_seconds=30,
                    job_id=first_job.job_id,
                ),
                repositories,
            )
        )
    assert sum(item is not None for item in claims) == 1
    execution = fixture.repository.lease.get_run_execution(first_run_id)
    assert execution is not None
    assert len(execution[1]) == 1
    for database in databases:
        database.dispose()
    fixture.database.dispose()


def test_transient_storage_error_before_invocation_requeues_job(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _runtime_fixture(tmp_path)
    kernel = build_runtime_kernel(fixture.repository, fixture.settings.artifacts_dir)
    run_id, job = kernel.coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=fixture.admission_id,
        idempotency_key="transient-storage-requeue",
    )

    async def fail_before_invocation(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise OperationalError(
            "BEGIN IMMEDIATE",
            {},
            RuntimeError("simulated transient SQLite unavailability"),
        )

    monkeypatch.setattr(kernel.coordinator, "execute_attempt", fail_before_invocation)
    worker = DurableRunWorker(
        fixture.repository,
        kernel.coordinator,
        worker_id="transient-storage-worker",
        lease_seconds=30,
        heartbeat_seconds=5,
    )
    assert asyncio.run(worker.process_once(job_id=job.job_id)) is True

    execution = fixture.repository.lease.get_run_execution(run_id)
    assert execution is not None
    requeued_job, attempts = execution
    assert requeued_job.status == "queued"
    assert requeued_job.active_attempt_id is None
    assert [attempt.status for attempt in attempts] == ["released"]
    assert attempts[0].reason_code == "transient_storage_error"
    events = fixture.repository.read_model.get_run_events(run_id)
    assert not any(event["type"] == "subject.invoked" for event in events)
    fixture.database.dispose()


def test_heartbeat_expiry_fencing_release_and_reject(tmp_path: Path) -> None:
    fixture = _runtime_fixture(tmp_path)
    kernel = build_runtime_kernel(fixture.repository, fixture.settings.artifacts_dir)
    run_id, job = kernel.coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=fixture.admission_id,
        idempotency_key="lease-expiry",
    )
    leased_at = utc_now()
    claim = fixture.repository.lease.claim_next_job(
        worker_id="worker-one",
        lease_seconds=4,
        job_id=job.job_id,
        now=leased_at,
    )
    assert claim is not None
    _, attempt_one = claim
    heartbeat = fixture.repository.lease.heartbeat_lease(
        job_id=job.job_id,
        attempt_id=attempt_one.attempt_id,
        worker_id="worker-one",
        lease_generation=attempt_one.lease_generation,
        lease_seconds=4,
        now=leased_at + timedelta(seconds=2),
    )
    assert heartbeat.lease_expires_at_utc == leased_at + timedelta(seconds=6)
    with pytest.raises(LeaseLost):
        fixture.repository.lease.heartbeat_lease(
            job_id=job.job_id,
            attempt_id=attempt_one.attempt_id,
            worker_id="worker-one",
            lease_generation=attempt_one.lease_generation,
            lease_seconds=4,
            now=leased_at + timedelta(seconds=7),
        )
    second_claim = fixture.repository.lease.claim_next_job(
        worker_id="worker-two",
        lease_seconds=30,
        job_id=job.job_id,
        now=leased_at + timedelta(seconds=7),
    )
    assert second_claim is not None
    _, attempt_two = second_claim
    assert attempt_two.ordinal == 2
    assert attempt_two.lease_generation == 2
    with pytest.raises(LeaseLost):
        fixture.repository.ledger.append_event(
            run_id=run_id,
            event_type="run.preparing",
            payload={
                "scenario_ref": fixture.repository.read_model.get_run_spec(
                    fixture.spec_id
                ).scenario_ref.model_dump(mode="json")
            },
            operation_key="stale-write",
            lease=(
                job.job_id,
                attempt_one.attempt_id,
                attempt_one.worker_id,
                attempt_one.lease_generation,
            ),
        )
    fixture.repository.lease.release_lease(
        job_id=job.job_id,
        attempt_id=attempt_two.attempt_id,
        worker_id=attempt_two.worker_id,
        lease_generation=attempt_two.lease_generation,
        now=leased_at + timedelta(seconds=8),
    )
    third_claim = fixture.repository.lease.claim_next_job(
        worker_id="worker-three",
        lease_seconds=30,
        job_id=job.job_id,
        now=leased_at + timedelta(seconds=9),
    )
    assert third_claim is not None
    _, attempt_three = third_claim
    fixture.repository.lease.reject_lease(
        job_id=job.job_id,
        attempt_id=attempt_three.attempt_id,
        worker_id=attempt_three.worker_id,
        lease_generation=attempt_three.lease_generation,
        reason_code="canonical_contract_failure",
        now=leased_at + timedelta(seconds=10),
    )
    assert fixture.repository.lease.get_execution_job(job.job_id).status == "rejected"
    assert (
        fixture.repository.lease.claim_next_job(
            worker_id="worker-four",
            lease_seconds=30,
            job_id=job.job_id,
            now=leased_at + timedelta(seconds=11),
        )
        is None
    )
    fixture.database.dispose()


def test_expired_worker_after_run_running_is_recovered_by_attempt_two(
    tmp_path: Path,
) -> None:
    fixture = _runtime_fixture(tmp_path)
    kernel = build_runtime_kernel(fixture.repository, fixture.settings.artifacts_dir)
    run_id, job = kernel.coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=fixture.admission_id,
        idempotency_key="recover-running",
    )
    leased_at = utc_now()
    claim_one = fixture.repository.lease.claim_next_job(
        worker_id="crashed-worker",
        lease_seconds=1,
        job_id=job.job_id,
        now=leased_at,
    )
    assert claim_one is not None
    claimed_job, attempt_one = claim_one
    contracts = fixture.repository.read_model.get_run_contracts(run_id)
    assert contracts is not None
    kernel.coordinator._prepare(claimed_job, attempt_one, *contracts)
    assert fixture.repository.read_model.get_run(run_id).status == "running"

    claim_two = fixture.repository.lease.claim_next_job(
        worker_id="recovery-worker",
        lease_seconds=30,
        job_id=job.job_id,
        now=leased_at + timedelta(seconds=2),
    )
    assert claim_two is not None
    asyncio.run(kernel.coordinator.execute_attempt(*claim_two))
    assert fixture.repository.read_model.get_run(run_id).status == "completed"
    execution = fixture.repository.lease.get_run_execution(run_id)
    assert execution is not None
    assert [item.status for item in execution[1]] == ["expired", "completed"]
    assert (
        len(
            [
                event
                for event in fixture.repository.read_model.get_run_events(run_id)
                if event["type"] == "run.running"
            ]
        )
        == 1
    )
    fixture.database.dispose()


def test_crash_after_subject_invocation_fails_without_reinvocation_and_retry_is_new_run(
    tmp_path: Path,
) -> None:
    fixture = _runtime_fixture(tmp_path)
    kernel = build_runtime_kernel(fixture.repository, fixture.settings.artifacts_dir)
    run_id, job = kernel.coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=fixture.admission_id,
        idempotency_key="indeterminate-invocation",
    )
    leased_at = utc_now()
    claim_one = fixture.repository.lease.claim_next_job(
        worker_id="invoking-worker",
        lease_seconds=1,
        job_id=job.job_id,
        now=leased_at,
    )
    assert claim_one is not None
    claimed_job, attempt_one = claim_one
    contracts = fixture.repository.read_model.get_run_contracts(run_id)
    assert contracts is not None
    envelope, _ = kernel.coordinator._prepare(claimed_job, attempt_one, *contracts)
    fixture.repository.ledger.append_event(
        run_id=run_id,
        event_type="subject.invoked",
        payload={
            "runner": contracts[0].agent_inventory.runner_ref.name,
            "network": "disabled",
            "subject_envelope_digest": envelope.digest,
            "evaluation_guidance_digest": None,
        },
        operation_key="subject:invoked",
        lease=(
            job.job_id,
            attempt_one.attempt_id,
            attempt_one.worker_id,
            attempt_one.lease_generation,
        ),
    )
    claim_two = fixture.repository.lease.claim_next_job(
        worker_id="recovery-worker",
        lease_seconds=30,
        job_id=job.job_id,
        now=leased_at + timedelta(seconds=2),
    )
    assert claim_two is not None
    asyncio.run(kernel.coordinator.execute_attempt(*claim_two))
    assert fixture.repository.read_model.get_run(run_id).status == "failed"
    events = fixture.repository.read_model.get_run_events(run_id)
    assert sum(item["type"] == "subject.invoked" for item in events) == 1
    assert not any(item["type"] == "subject.responded" for item in events)

    with pytest.raises(ValueError, match="new AdmissionRecord"):
        kernel.coordinator.enqueue(
            run_spec_id=fixture.spec_id,
            admission_id=fixture.admission_id,
            idempotency_key="stale-admission-retry",
            retry_of=run_id,
        )

    new_admission = kernel.coordinator.admission_service.admit(contracts[0])
    new_admission_row = fixture.repository.catalog.save_admission_record(
        fixture.spec_id, new_admission
    )
    retry_run_id, retry_job = kernel.coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=new_admission_row.id,
        idempotency_key="explicit-retry",
        retry_of=run_id,
    )
    assert retry_run_id != run_id
    assert fixture.repository.read_model.get_run(retry_run_id).retry_of == run_id
    retry_claim = fixture.repository.lease.claim_next_job(
        worker_id="retry-worker", lease_seconds=30, job_id=retry_job.job_id
    )
    assert retry_claim is not None
    asyncio.run(kernel.coordinator.execute_attempt(*retry_claim))
    assert fixture.repository.read_model.get_run(retry_run_id).status == "completed"
    fixture.database.dispose()


def test_runner_exception_is_sanitized_and_adapter_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    fixture = _runtime_fixture(tmp_path)

    class RaisingRunner:
        name = "scripted-log-investigator-v1"

        async def execute(self, objective: str, context: str) -> object:
            del objective, context
            raise RuntimeError("credential=must-not-enter-ledger")

    catalog = RuntimeAdapterCatalog(
        subject=ScriptedLogInvestigatorAdapter(runner=RaisingRunner())  # type: ignore[arg-type]
    )
    coordinator = RunExecutionCoordinator(
        fixture.repository,
        ArtifactStore(fixture.settings.artifacts_dir),
        catalog,
    )
    run_id, job = coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=fixture.admission_id,
        idempotency_key="runner-exception",
    )
    claim = fixture.repository.lease.claim_next_job(
        worker_id="exception-worker", lease_seconds=30, job_id=job.job_id
    )
    assert claim is not None
    asyncio.run(coordinator.execute_attempt(*claim))
    assert fixture.repository.read_model.get_run(run_id).status == "failed"
    serialized_events = str(fixture.repository.read_model.get_run_events(run_id))
    assert "must-not-enter-ledger" not in serialized_events
    assert "Subject runner execution failed" in serialized_events
    failed_bundle = tmp_path / "failed-run.evidrun.zip"
    bundle_service = EvidenceBundleService(fixture.repository)
    bundle_service.export_run_v3(run_id, failed_bundle)
    assert bundle_service.verify(failed_bundle)["valid"] is True

    original = fixture.repository.read_model.get_run_spec(fixture.spec_id)
    binding = original.scenario.input_bindings[0]
    bad_source = binding.source.model_copy(update={"media_type": "application/json"})
    bad_binding = binding.model_copy(update={"source": bad_source})
    bad_scenario = original.scenario.model_copy(update={"input_bindings": (bad_binding,)})
    bad_spec = original.model_copy(update={"scenario": bad_scenario})
    rejected = build_runtime_kernel(
        fixture.repository, fixture.settings.artifacts_dir
    ).coordinator.admission_service.admit(bad_spec)
    assert rejected.decision == "rejected"
    assert any(
        item.category == "runtime"
        and item.subject_ref == "subject_input_media_type"
        and item.blocking
        for item in rejected.issues
    )

    bad_digest_source = binding.source.model_copy(update={"digest": "f" * 64})
    digest_binding = binding.model_copy(update={"source": bad_digest_source})
    digest_scenario = original.scenario.model_copy(update={"input_bindings": (digest_binding,)})
    digest_mount = original.workspace.mounts[0].model_copy(update={"source": bad_digest_source})
    digest_workspace = original.workspace.model_copy(update={"mounts": (digest_mount,)})
    digest_spec = original.model_copy(
        update={"scenario": digest_scenario, "workspace": digest_workspace}
    )
    digest_admission = build_runtime_kernel(
        fixture.repository, fixture.settings.artifacts_dir
    ).coordinator.admission_service.admit(digest_spec)
    assert digest_admission.decision == "rejected"
    assert any(item.subject_ref == "subject_input_artifact" for item in digest_admission.issues)
    fixture.database.dispose()


def test_artifact_removed_after_admission_fails_closed_and_rejects_job(
    tmp_path: Path,
) -> None:
    fixture = _runtime_fixture(tmp_path)
    kernel = build_runtime_kernel(fixture.repository, fixture.settings.artifacts_dir)
    spec = fixture.repository.read_model.get_run_spec(fixture.spec_id)
    ArtifactStore(fixture.settings.artifacts_dir).purge(
        spec.scenario.input_bindings[0].source.artifact_id
    )
    run_id, job = kernel.coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=fixture.admission_id,
        idempotency_key="artifact-disappeared",
    )
    worker = DurableRunWorker(
        fixture.repository,
        kernel.coordinator,
        worker_id="artifact-failure-worker",
    )
    assert asyncio.run(worker.process_once(job_id=job.job_id)) is True
    assert fixture.repository.read_model.get_run(run_id).status == "failed"
    execution = fixture.repository.lease.get_run_execution(run_id)
    assert execution is not None
    assert execution[0].status == "rejected"
    assert execution[1][0].status == "rejected"
    assert "Runtime execution could not be completed safely" in str(
        fixture.repository.read_model.get_run_events(run_id)[-1]
    )
    failed_bundle = tmp_path / "preparation-failure-v3.zip"
    bundle_service = EvidenceBundleService(fixture.repository)
    bundle_service.export_run_v3(run_id, failed_bundle)
    verification = bundle_service.verify(failed_bundle)
    assert verification["valid"] is True, json.dumps(verification, indent=2)
    assert verification["records"]["__subject_envelope_absence__"] is True
    fixture.database.dispose()


def test_recovery_with_exhausted_wall_budget_does_not_invoke_subject(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _runtime_fixture(tmp_path)
    kernel = build_runtime_kernel(fixture.repository, fixture.settings.artifacts_dir)
    run_id, job = kernel.coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=fixture.admission_id,
        idempotency_key="recovery-budget",
    )
    leased_at = utc_now()
    claim_one = fixture.repository.lease.claim_next_job(
        worker_id="budget-crash-worker",
        lease_seconds=1,
        job_id=job.job_id,
        now=leased_at,
    )
    assert claim_one is not None
    contracts = fixture.repository.read_model.get_run_contracts(run_id)
    assert contracts is not None
    kernel.coordinator._prepare(*claim_one, *contracts)
    prepared_events = fixture.repository.read_model.get_run_events(run_id)
    running = next(item for item in prepared_events if item["type"] == "run.running")
    started_at = coordinator_module.datetime.fromisoformat(str(running["occurred_at_utc"]))
    claim_two = fixture.repository.lease.claim_next_job(
        worker_id="budget-recovery-worker",
        lease_seconds=30,
        job_id=job.job_id,
        now=leased_at + timedelta(seconds=2),
    )
    assert claim_two is not None
    frozen_now = started_at.replace(tzinfo=UTC) + timedelta(seconds=10)
    monkeypatch.setattr(coordinator_module, "utc_now", lambda: frozen_now)
    monkeypatch.setattr(db_clock_module, "utc_now", lambda: frozen_now)
    asyncio.run(kernel.coordinator.execute_attempt(*claim_two))
    assert fixture.repository.read_model.get_run(run_id).status == "budget_exhausted"
    recovered_events = fixture.repository.read_model.get_run_events(run_id)
    assert not any(item["type"] == "subject.invoked" for item in recovered_events)
    bundle_path = tmp_path / "recovered-budget-exhausted-v3.zip"
    bundle_service = EvidenceBundleService(fixture.repository)
    bundle_service.export_run_v3(run_id, bundle_path)
    verification = bundle_service.verify(bundle_path)
    assert verification["valid"] is True, json.dumps(verification, indent=2)
    assert verification["records"][f"subject-envelopes/{run_id}.json"] is True
    fixture.database.dispose()


def test_repeating_prepare_response_evaluation_and_finish_is_idempotent(
    tmp_path: Path,
) -> None:
    fixture = _runtime_fixture(tmp_path)
    kernel = build_runtime_kernel(fixture.repository, fixture.settings.artifacts_dir)
    run_id, job = kernel.coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=fixture.admission_id,
        idempotency_key="repeat-phases",
    )
    claim = fixture.repository.lease.claim_next_job(
        worker_id="idempotency-worker", lease_seconds=30, job_id=job.job_id
    )
    assert claim is not None
    claimed_job, attempt = claim
    contracts = fixture.repository.read_model.get_run_contracts(run_id)
    assert contracts is not None
    envelope_one, inputs_one = kernel.coordinator._prepare(claimed_job, attempt, *contracts)
    envelope_two, inputs_two = kernel.coordinator._prepare(claimed_job, attempt, *contracts)
    assert envelope_one == envelope_two
    assert inputs_one == inputs_two
    lease = (
        job.job_id,
        attempt.attempt_id,
        attempt.worker_id,
        attempt.lease_generation,
    )
    kernel.coordinator.repository.ledger.append_event(
        run_id=run_id,
        event_type="subject.invoked",
        payload={
            "runner": contracts[0].agent_inventory.runner_ref.name,
            "network": "disabled",
            "subject_envelope_digest": envelope_one.digest,
            "evaluation_guidance_digest": None,
        },
        operation_key="subject:invoked",
        lease=lease,
    )
    result = asyncio.run(kernel.catalog.subject.execute(envelope_one, inputs_one))
    response_one = kernel.coordinator._persist_response(claimed_job, attempt, contracts[0], result)
    response_two = kernel.coordinator._persist_response(claimed_job, attempt, contracts[0], result)
    assert response_one.id == response_two.id
    outcome = kernel.catalog.evaluator.evaluate(
        run_id=run_id,
        spec=contracts[0],
        result=result,
        response_event_id=response_one.id,
        response_sequence=response_one.sequence,
        response_event_hash=response_one.event_hash,
    )
    kernel.coordinator._persist_evaluation(claimed_job, attempt, outcome)
    kernel.coordinator._persist_evaluation(claimed_job, attempt, outcome)
    kernel.coordinator._terminal(
        claimed_job,
        attempt,
        event_type="run.completed",
        goal_result=GoalStateTerminalResult(state="achieved"),
        cause="idempotent terminal",
    )
    kernel.coordinator._terminal(
        claimed_job,
        attempt,
        event_type="run.completed",
        goal_result=GoalStateTerminalResult(state="achieved"),
        cause="idempotent terminal",
    )
    event_types = [item["type"] for item in fixture.repository.read_model.get_run_events(run_id)]
    assert len(event_types) == len(set(event_types))
    assert len(fixture.repository.read_model.get_evaluation_records(run_id)) == 1
    execution = fixture.repository.lease.get_run_execution(run_id)
    assert execution is not None
    assert execution[0].status == "completed"
    fixture.database.dispose()


def test_prepare_transaction_rolls_back_all_facts_on_mid_commit_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _runtime_fixture(tmp_path)
    kernel = build_runtime_kernel(fixture.repository, fixture.settings.artifacts_dir)
    run_id, job = kernel.coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=fixture.admission_id,
        idempotency_key="prepare-rollback",
    )
    claim = fixture.repository.lease.claim_next_job(
        worker_id="prepare-rollback-worker", lease_seconds=30, job_id=job.job_id
    )
    assert claim is not None
    contracts = fixture.repository.read_model.get_run_contracts(run_id)
    assert contracts is not None
    original = preparation_module.append_event_once_in_session

    def fail_on_context(session: Any, **kwargs: Any) -> Any:
        if kwargs["event_type"] == "context.composed":
            raise RuntimeError("injected preparation transaction failure")
        return original(session, **kwargs)

    monkeypatch.setattr(
        preparation_module,
        "append_event_once_in_session",
        fail_on_context,
    )
    with pytest.raises(RuntimeError, match="injected preparation"):
        kernel.coordinator._prepare(*claim, *contracts)
    assert fixture.repository.read_model.get_run(run_id).status == "queued"
    rolled_back_events = fixture.repository.read_model.get_run_events(run_id)
    assert [item["type"] for item in rolled_back_events] == ["run.queued"]
    with pytest.raises(KeyError):
        fixture.repository.read_model.get_subject_envelope(run_id)
    dashboard_runs = fixture.repository.read_model.latest_dashboard()["runs"]
    dashboard_run = next(item for item in dashboard_runs if item["id"] == run_id)
    assert dashboard_run["context_snapshot"] is None
    fixture.database.dispose()


def test_evaluation_transaction_rolls_back_record_grade_and_event_together(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _runtime_fixture(tmp_path)
    kernel = build_runtime_kernel(fixture.repository, fixture.settings.artifacts_dir)
    run_id, job = kernel.coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=fixture.admission_id,
        idempotency_key="evaluation-rollback",
    )
    claim = fixture.repository.lease.claim_next_job(
        worker_id="evaluation-rollback-worker",
        lease_seconds=30,
        job_id=job.job_id,
    )
    assert claim is not None
    claimed_job, attempt = claim
    contracts = fixture.repository.read_model.get_run_contracts(run_id)
    assert contracts is not None
    envelope, inputs = kernel.coordinator._prepare(claimed_job, attempt, *contracts)
    lease = (
        job.job_id,
        attempt.attempt_id,
        attempt.worker_id,
        attempt.lease_generation,
    )
    fixture.repository.ledger.append_event(
        run_id=run_id,
        event_type="subject.invoked",
        payload={
            "runner": contracts[0].agent_inventory.runner_ref.name,
            "network": "disabled",
            "subject_envelope_digest": envelope.digest,
            "evaluation_guidance_digest": None,
        },
        operation_key="subject:invoked",
        lease=lease,
    )
    result = asyncio.run(kernel.catalog.subject.execute(envelope, inputs))
    response = kernel.coordinator._persist_response(claimed_job, attempt, contracts[0], result)
    outcome = kernel.catalog.evaluator.evaluate(
        run_id=run_id,
        spec=contracts[0],
        result=result,
        response_event_id=response.id,
        response_sequence=response.sequence,
        response_event_hash=response.event_hash,
    )
    original = evaluation_records_module.append_event_once_in_session

    def fail_on_evaluation_event(session: Any, **kwargs: Any) -> Any:
        if kwargs["event_type"] == "evaluation.completed":
            raise RuntimeError("injected evaluation transaction failure")
        return original(session, **kwargs)

    monkeypatch.setattr(
        evaluation_records_module,
        "append_event_once_in_session",
        fail_on_evaluation_event,
    )
    with pytest.raises(RuntimeError, match="injected evaluation"):
        kernel.coordinator._persist_evaluation(claimed_job, attempt, outcome)
    assert fixture.repository.read_model.get_evaluation_records(run_id) == []
    with pytest.raises(KeyError):
        fixture.repository.read_model.get_grade(run_id)
    evaluated_events = fixture.repository.read_model.get_run_events(run_id)
    assert not any(item["type"] == "evaluation.completed" for item in evaluated_events)
    fixture.database.dispose()
