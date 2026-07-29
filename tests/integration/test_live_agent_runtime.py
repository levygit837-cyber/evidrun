from __future__ import annotations

import asyncio
import hashlib
import json
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

import evidrun.runs.coordinator.attempt as attempt_module
from evidrun.contracts import ExtensionRef
from evidrun.contracts.authoring.evaluation import AggregationSpec, BlindingPolicy
from evidrun.evidence.bundle import EvidenceBundleService
from evidrun.infrastructure.artifacts.store import (
    ArtifactStore,
    MemoryKeyProvider,
)
from evidrun.infrastructure.database import Database, Repository
from evidrun.providers import ProviderProfile
from evidrun.runs import DurableRunWorker
from evidrun.runs.adapters import (
    ArtifactInputMaterializer,
    ResponsesReadAgentAdapter,
    RuntimeAdapterCatalog,
)
from evidrun.runs.coordinator import RunExecutionCoordinator
from evidrun.settings import Settings
from evidrun.shared.types import Classification, utc_now
from tests.support.execution_trust import (
    prepare_registered_study,
    unpersisted_unverified_trust,
)
from tests.support.human_attestation import (
    TestHumanAttestationVerifier,
    accepted_decision,
)
from tests.support.live_read_study import (
    build_live_read_study,
    fresh_incident_memo,
)


class SequencedProvider:
    def __init__(self, responses: list[Mapping[str, Any]]) -> None:
        self.responses = responses
        self.requests: list[Mapping[str, Any]] = []

    async def invoke(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("provider received an unexpected extra invocation")
        return self.responses.pop(0)


@dataclass
class LiveFixture:
    settings: Settings
    database: Database
    repository: Repository
    artifact_store: ArtifactStore
    key_provider: MemoryKeyProvider
    catalog: RuntimeAdapterCatalog
    coordinator: RunExecutionCoordinator
    provider: SequencedProvider
    spec_id: str
    admission_id: str
    expected: str


def _profile() -> ProviderProfile:
    return ProviderProfile(
        id="test-responses-local",
        display_name="Fake Responses provider",
        api="openai_responses",
        base_url="http://127.0.0.1:9/v1",
        model="fake-read-agent-v1",
        reasoning_effort="max",
        local_only=True,
        credential_service="tests.evidrun.providers",
    )


def _function_call_response(
    *, call_id: str = "call_read_1", input_id: str = "incident-memo"
) -> Mapping[str, Any]:
    return {
        "id": "resp_tool_1",
        "status": "completed",
        "output": [
            {
                "type": "function_call",
                "id": "fc_1",
                "call_id": call_id,
                "name": "read_text",
                "arguments": json.dumps({"input_id": input_id, "start_line": 1, "max_lines": 80}),
                "status": "completed",
            }
        ],
        "usage": {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
    }


def _terminal_response(expected: str) -> Mapping[str, Any]:
    return {
        "id": "resp_final_1",
        "status": "completed",
        "output_text": json.dumps(
            {
                "answer": expected,
                "evidence": [{"input_id": "incident-memo", "line": 36}],
            },
            separators=(",", ":"),
        ),
        "usage": {"input_tokens": 300, "output_tokens": 40, "total_tokens": 340},
    }


def _terminal_document_response(document: object) -> Mapping[str, Any]:
    return {
        "id": "resp_final_custom",
        "status": "completed",
        "output_text": json.dumps(document, separators=(",", ":")),
    }


def _fixture(
    tmp_path: Path,
    responses: list[Mapping[str, Any]],
    *,
    expected: str = "THERMAL_RELAY_TEST_NONCE_71",
) -> LiveFixture:
    settings = Settings.load(tmp_path)
    settings.ensure_directories()
    database = Database(settings.database_path)
    database.create_all()
    repository = Repository(database, TestHumanAttestationVerifier())
    workspace = repository.catalog.create_workspace("Live agent workspace")
    project = repository.catalog.create_project(workspace.id, "Live agent project")
    key_provider = MemoryKeyProvider()
    artifact_store = ArtifactStore(settings.artifacts_dir, key_provider)
    source = artifact_store.put_ref(
        fresh_incident_memo(expected).encode("utf-8"),
        project_id=project.id,
        media_type="text/plain",
        classification=Classification.INTERNAL,
    )
    revisions, study = build_live_read_study(
        project_id=project.id,
        source=source,
        expected=expected,
        profile=_profile(),
    )
    for revision in revisions:
        repository.registry.save_contract_revision(revision, status="proposed")
        repository.registry.decide_contract_revision(accepted_decision(revision))
    spec, trust, spec_id = prepare_registered_study(repository, study)
    provider = SequencedProvider(responses)
    real_subject = ResponsesReadAgentAdapter(
        provider,
        _profile(),
        credential_available=True,
    )
    catalog = RuntimeAdapterCatalog(
        real_subject=real_subject,
        materializer=ArtifactInputMaterializer(artifact_store),
    )
    coordinator = RunExecutionCoordinator(repository, artifact_store, catalog)
    admission = coordinator.admission_service.admit(spec, trust)
    assert admission.decision == "admitted", admission.model_dump(mode="json")
    admission_row = repository.catalog.save_admission_record(spec_id, admission)
    return LiveFixture(
        settings=settings,
        database=database,
        repository=repository,
        artifact_store=artifact_store,
        key_provider=key_provider,
        catalog=catalog,
        coordinator=coordinator,
        provider=provider,
        spec_id=spec_id,
        admission_id=admission_row.id,
        expected=expected,
    )


def test_real_agent_adapter_traces_tool_and_completes_grounded_run(
    tmp_path: Path,
) -> None:
    expected = "THERMAL_RELAY_TEST_NONCE_71"
    fixture = _fixture(
        tmp_path,
        [_function_call_response(), _terminal_response(expected)],
        expected=expected,
    )
    run_id, job = fixture.coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=fixture.admission_id,
        idempotency_key="fake-live-success",
    )
    worker = DurableRunWorker(
        fixture.repository,
        fixture.coordinator,
        worker_id="fake-live-worker",
        lease_seconds=30,
        heartbeat_seconds=5,
    )
    assert asyncio.run(worker.process_once(job_id=job.job_id)) is True

    assert fixture.repository.read_model.get_run(run_id).status == "completed"
    events = fixture.repository.read_model.get_run_events(run_id)
    assert [event["type"] for event in events] == [
        "run.queued",
        "run.preparing",
        "context.composed",
        "capability.offered",
        "run.running",
        "subject.invoked",
        "tool.called",
        "tool.completed",
        "subject.responded",
        "run.evaluating",
        "evaluation.completed",
        "run.completed",
    ]
    invoked = next(event for event in events if event["type"] == "subject.invoked")
    assert invoked["payload"]["provider_model"] == "fake-read-agent-v1"
    responded = next(event for event in events if event["type"] == "subject.responded")
    assert "output" not in responded["payload"]
    assert responded["payload"]["output_ref"]["classification"] == "sensitive"
    assert {item["key"]: item["value"] for item in responded["payload"]["metadata"]}[
        "transport_max_output_tokens"
    ] == 768
    assert responded["payload"]["evidence"] == [
        f"artifact:{responded['payload']['output_ref']['artifact_id']}"
    ]
    evaluation = fixture.repository.read_model.get_evaluation_records(run_id)[0]
    assert evaluation.gate_status == "passed"
    assert evaluation.dimension_values[0].value is True
    assert fixture.provider.requests[0]["tool_choice"] == "auto"
    assert "previous_response_id" not in fixture.provider.requests[1]
    continuation = fixture.provider.requests[1]["input"]
    assert isinstance(continuation, list)
    assert [item["type"] for item in continuation[1:]] == [
        "function_call",
        "function_call_output",
    ]
    bundle_path = tmp_path / "live-agent-run-v4.zip"
    bundle_service = EvidenceBundleService(fixture.repository)
    bundle_service.export_run_v4(run_id, bundle_path)
    verification = bundle_service.verify(bundle_path)
    assert verification["valid"] is True, verification

    for label, event_type, mutate in (
        (
            "provider",
            "subject.invoked",
            lambda payload: payload.update({"provider_model": "forged-provider-model"}),
        ),
        (
            "capability",
            "capability.offered",
            lambda payload: payload["capability_ref"].update({"name": "forged-read-tool"}),
        ),
    ):
        with zipfile.ZipFile(bundle_path) as archive:
            files = {name: archive.read(name) for name in archive.namelist()}
        event_name = next(name for name in files if name.startswith("events/"))
        event_documents = [json.loads(line) for line in files[event_name].splitlines() if line]
        target_event = next(item for item in event_documents if item["type"] == event_type)
        mutate(target_event["payload"])
        files[event_name] = (
            "\n".join(
                json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                for item in event_documents
            )
            + "\n"
        ).encode()
        checksums = json.loads(files["checksums.json"])
        checksums["files"][event_name] = hashlib.sha256(files[event_name]).hexdigest()
        files["checksums.json"] = (
            json.dumps(checksums, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode()
        tampered_path = tmp_path / f"live-agent-{label}-tampered.zip"
        with zipfile.ZipFile(tampered_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, content in files.items():
                archive.writestr(name, content)
        tampered = bundle_service.verify(tampered_path)
        assert tampered["valid"] is False
        assert tampered["records"]["__runtime_admission_binding__"] is False

    with zipfile.ZipFile(bundle_path) as archive:
        manifest = json.loads(archive.read("artifact-manifest.json"))
    assert {entry["role"] for entry in manifest["entries"]} >= {
        "scenario_input",
        "subject_input_materialized",
        "tool_arguments",
        "tool_result",
        "run_output",
    }
    fixture.database.dispose()


def test_out_of_envelope_tool_request_is_denied_and_scores_false(
    tmp_path: Path,
) -> None:
    expected = "THERMAL_RELAY_TEST_NONCE_72"
    fixture = _fixture(
        tmp_path,
        [
            _function_call_response(input_id="not-authorized"),
            _terminal_response(expected),
        ],
        expected=expected,
    )
    run_id, job = fixture.coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=fixture.admission_id,
        idempotency_key="fake-live-denied",
    )
    worker = DurableRunWorker(
        fixture.repository,
        fixture.coordinator,
        worker_id="fake-live-denied-worker",
        lease_seconds=30,
        heartbeat_seconds=5,
    )
    assert asyncio.run(worker.process_once(job_id=job.job_id)) is True

    assert fixture.repository.read_model.get_run(run_id).status == "completed"
    events = fixture.repository.read_model.get_run_events(run_id)
    assert "tool.called" in [event["type"] for event in events]
    assert "tool.denied" in [event["type"] for event in events]
    assert "tool.completed" not in [event["type"] for event in events]
    evaluation = fixture.repository.read_model.get_evaluation_records(run_id)[0]
    assert evaluation.gate_status == "failed"
    assert evaluation.dimension_values[0].value is False
    assert events[-1]["payload"]["goal_result"]["state"] == "not_achieved"
    fixture.database.dispose()


def test_encrypted_response_recovers_after_sqlite_restart_without_reinvocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = "THERMAL_RELAY_TEST_NONCE_73"
    fixture = _fixture(
        tmp_path,
        [_function_call_response(), _terminal_response(expected)],
        expected=expected,
    )
    run_id, job = fixture.coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=fixture.admission_id,
        idempotency_key="fake-live-response-recovery",
    )
    leased_at = utc_now()
    claim_one = fixture.repository.lease.claim_next_job(
        worker_id="crash-after-response",
        lease_seconds=1,
        job_id=job.job_id,
        now=leased_at,
    )
    assert claim_one is not None

    def crash_before_evaluation(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError("simulated crash after durable Subject response")

    monkeypatch.setattr(
        attempt_module,
        "persist_evaluation",
        crash_before_evaluation,
    )
    with pytest.raises(RuntimeError, match="simulated crash"):
        asyncio.run(fixture.coordinator.execute_attempt(*claim_one))
    crashed_events = fixture.repository.read_model.get_run_events(run_id)
    assert any(event["type"] == "subject.responded" for event in crashed_events)
    assert not fixture.provider.responses
    fixture.database.dispose()

    reopened_database = Database(fixture.settings.database_path)
    reopened_database.create_all()
    reopened_repository = Repository(reopened_database)
    reopened_store = ArtifactStore(
        fixture.settings.artifacts_dir,
        fixture.key_provider,
    )
    provider_that_must_not_run = SequencedProvider([])
    reopened_catalog = RuntimeAdapterCatalog(
        real_subject=ResponsesReadAgentAdapter(
            provider_that_must_not_run,
            _profile(),
            credential_available=True,
        ),
        materializer=ArtifactInputMaterializer(reopened_store),
    )
    reopened_coordinator = RunExecutionCoordinator(
        reopened_repository,
        reopened_store,
        reopened_catalog,
    )
    claim_two = reopened_repository.lease.claim_next_job(
        worker_id="recover-response",
        lease_seconds=30,
        job_id=job.job_id,
        now=leased_at + timedelta(seconds=2),
    )
    assert claim_two is not None
    asyncio.run(reopened_coordinator.execute_attempt(*claim_two))

    assert reopened_repository.read_model.get_run(run_id).status == "completed"
    assert provider_that_must_not_run.requests == []
    assert reopened_repository.read_model.get_evaluation_records(run_id)[0].gate_status == "passed"
    execution = reopened_repository.lease.get_run_execution(run_id)
    assert execution is not None
    assert [attempt.status for attempt in execution[1]] == ["expired", "completed"]
    reopened_database.dispose()


def test_live_spec_variations_reject_without_enqueuing(tmp_path: Path) -> None:
    expected = "THERMAL_RELAY_TEST_NONCE_74"
    fixture = _fixture(tmp_path, [], expected=expected)
    spec = fixture.repository.read_model.get_run_spec(fixture.spec_id)
    source = spec.scenario.input_bindings[0].source
    extra_evaluator_input = spec.scenario.input_bindings[0].model_copy(
        update={
            "id": "evaluator-only-extra",
            "visibility": "evaluator",
            "mount_name": None,
        }
    )
    variants = (
        spec.model_copy(
            update={
                "workspace": spec.workspace.model_copy(
                    update={
                        "network_policy": spec.workspace.network_policy.model_copy(
                            update={"mode": "disabled"}
                        )
                    }
                )
            }
        ),
        spec.model_copy(
            update={"budgets": spec.budgets.model_copy(update={"max_tool_calls": None})}
        ),
        spec.model_copy(
            update={
                "capture_policy": spec.capture_policy.model_copy(
                    update={"default_mode": "redacted", "raw_sensitive": "disabled"}
                )
            }
        ),
        spec.model_copy(
            update={
                "scenario": spec.scenario.model_copy(
                    update={
                        "input_bindings": (
                            *spec.scenario.input_bindings,
                            extra_evaluator_input,
                        )
                    }
                )
            }
        ),
        spec.model_copy(
            update={
                "evaluation_plan": spec.evaluation_plan.model_copy(
                    update={
                        "disclosure": spec.evaluation_plan.disclosure.model_copy(
                            update={"hidden_input_refs": (source,)}
                        )
                    }
                )
            }
        ),
        spec.model_copy(
            update={
                "evaluation_plan": spec.evaluation_plan.model_copy(
                    update={"blinding_policy": BlindingPolicy(hidden_fields=("subject.output",))}
                )
            }
        ),
        spec.model_copy(
            update={
                "evaluation_plan": spec.evaluation_plan.model_copy(
                    update={
                        "aggregation": AggregationSpec(
                            projector_ref=spec.evaluation_plan.stages[0].evaluator_ref
                        )
                    }
                )
            }
        ),
        spec.model_copy(
            update={
                "extensions": (
                    ExtensionRef(
                        namespace="tests.live",
                        slot="unexecuted-extension",
                        schema_ref=source,
                        schema_version="1",
                        payload_ref=source,
                        digest=source.digest,
                        classification=source.classification,
                    ),
                )
            }
        ),
    )
    for variant in variants:
        admission = fixture.coordinator.admission_service.admit(variant, unpersisted_unverified_trust(variant))
        assert admission.decision == "rejected"
        assert admission.issues
    assert fixture.repository.read_model.latest_dashboard()["runs"] == []
    fixture.database.dispose()


def test_tool_call_budget_exhaustion_is_an_explicit_terminal(
    tmp_path: Path,
) -> None:
    expected = "THERMAL_RELAY_TEST_NONCE_75"
    fixture = _fixture(
        tmp_path,
        [
            _function_call_response(call_id="invalid_1", input_id="outside-1"),
            _function_call_response(call_id="invalid_2", input_id="outside-2"),
            _function_call_response(call_id="over_budget", input_id="outside-3"),
        ],
        expected=expected,
    )
    run_id, job = fixture.coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=fixture.admission_id,
        idempotency_key="fake-live-tool-budget",
    )
    worker = DurableRunWorker(
        fixture.repository,
        fixture.coordinator,
        worker_id="fake-live-budget-worker",
        lease_seconds=30,
        heartbeat_seconds=5,
    )
    assert asyncio.run(worker.process_once(job_id=job.job_id)) is True

    assert fixture.repository.read_model.get_run(run_id).status == "budget_exhausted"
    events = fixture.repository.read_model.get_run_events(run_id)
    assert [event["type"] for event in events].count("tool.called") == 3
    assert [event["type"] for event in events].count("tool.denied") == 3
    assert events[-1]["type"] == "run.budget_exhausted"
    assert events[-1]["payload"]["goal_result"]["state"] == "not_assessable"
    assert fixture.repository.read_model.get_evaluation_records(run_id) == []
    fixture.database.dispose()


@pytest.mark.parametrize(
    "document",
    [
        {
            "answer": "THERMAL_RELAY_TEST_NONCE_76",
            "evidence": [{"input_id": "incident-memo", "line": 33}],
        },
        {
            "answer": "THERMAL_RELAY_TEST_NONCE_76",
            "evidence": [{"input_id": "incident-memo", "line": 36}],
            "extra": "rubric-bypass-attempt",
        },
        {
            "answer": "CACHE_STAMPEDE_R2",
            "evidence": [{"input_id": "incident-memo", "line": 31}],
        },
    ],
)
def test_strict_grader_rejects_ungrounded_or_shape_bypass_attempts(
    tmp_path: Path,
    document: object,
) -> None:
    expected = "THERMAL_RELAY_TEST_NONCE_76"
    fixture = _fixture(
        tmp_path,
        [_function_call_response(), _terminal_document_response(document)],
        expected=expected,
    )
    run_id, job = fixture.coordinator.enqueue(
        run_spec_id=fixture.spec_id,
        admission_id=fixture.admission_id,
        idempotency_key=f"grader-bypass-{hash(json.dumps(document, sort_keys=True))}",
    )
    worker = DurableRunWorker(
        fixture.repository,
        fixture.coordinator,
        worker_id="fake-live-grader-worker",
        lease_seconds=30,
        heartbeat_seconds=5,
    )
    assert asyncio.run(worker.process_once(job_id=job.job_id)) is True
    assert fixture.repository.read_model.get_run(run_id).status == "completed"
    assert fixture.repository.read_model.get_evaluation_records(run_id)[0].gate_status == "failed"
    assert (
        fixture.repository.read_model.get_run_events(run_id)[-1]["payload"]["goal_result"]["state"]
        == "not_achieved"
    )
    fixture.database.dispose()
