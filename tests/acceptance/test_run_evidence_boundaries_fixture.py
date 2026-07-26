from __future__ import annotations

import asyncio
from pathlib import Path

from evidrun.contracts import EvaluationRecord, RunRecord, RunSpec, SubjectEnvelope
from evidrun.contracts.compiler import StudyCompiler
from evidrun.infrastructure.artifacts.store import ArtifactStore
from evidrun.infrastructure.database import Database, Repository
from evidrun.runs import build_runtime_kernel
from evidrun.runs.worker import DurableRunWorker
from evidrun.settings import Settings
from evidrun.shared.types import Classification, sha256_bytes
from tests.support.human_attestation import (
    TestHumanAttestationVerifier,
    accepted_decision,
)
from tests.support.runtime_study import build_runtime_study

ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "benchmarks" / "fixtures" / "run-evidence-boundaries"
LAB_INTENT = "Validar uma Run duravel sem o pacote de benchmark legado."
HIDDEN_EXPECTED = "SEARCH_INDEX_LAG"


def _event_reference(
    reference: str,
    events_by_id: dict[str, str],
) -> str:
    if not reference.startswith("event:"):
        return reference
    event_id = reference.removeprefix("event:")
    return f"event:{events_by_id[event_id]}"


def _render_expected_run(
    *,
    spec: RunSpec,
    run_record: RunRecord,
    admission_decision: str,
    envelope: SubjectEnvelope,
    events: list[dict[str, object]],
    evaluation: EvaluationRecord,
) -> str:
    terminal = events[-1]
    terminal_payload = terminal["payload"]
    assert isinstance(terminal_payload, dict)
    goal_result = terminal_payload["goal_result"]
    assert isinstance(goal_result, dict)
    events_by_id = {str(item["event_id"]): str(item["type"]) for item in events}
    evidence = tuple(
        _event_reference(item.ref, events_by_id)
        for dimension in evaluation.dimension_values
        for item in dimension.evidence_refs
    )
    input_binding = envelope.inputs[0]

    return f"""# Run esperada — fronteiras mínimas de evidência

> Projeção humana determinística de uma fixture de teste. Não é contrato, evento canônico nem
> resultado de produção.

## Identidade canônica

- RunRecord: presente e ligado aos digests exatos de RunSpec e AdmissionRecord.
- Scenario: `{run_record.scenario_ref.logical_id}@{run_record.scenario_ref.revision}`.
- Variant: `{run_record.variant_id}`; repetição: `{run_record.repetition_index}`.
- AdmissionRecord: `{admission_decision}` antes da criação da Run.

## Visão entregue ao Subject

- Goal: {envelope.goal.instruction}
- Input: `{input_binding.id}` (`{input_binding.source.media_type}`,
  `{input_binding.source.classification.value}`), somente por ArtifactRef.
- Rede: `{spec.workspace.network_policy.mode}`; efeitos externos:
  `{spec.workspace.external_effect_policy.mode}`.

## Evidência canônica da execução

- Ledger: `{" → ".join(str(item["type"]) for item in events)}`.
- Terminal: `{terminal["type"]}`; Goal: `{goal_result["state"]}`.
- EvaluationRecord: `{evaluation.stage_id}` / `{evaluation.source_type}` /
  `{evaluation.gate_status}`.
- Âncoras de evidência: `{", ".join(evidence)}`.

## Omitido por desenho

- Provider, tools, skills, checkpoints, findings, fork, judge e revisão humana.
- Study intent, hipótese, oracle oculto, conteúdo bruto do Artifact e output de outra Run.

## Limite da afirmação

Esta fixture verifica separação e rastreabilidade das evidências no caminho offline atual. Ela não
mede capacidade de LLM, não demonstra estabilidade estatística e não promove os candidatos do
discovery a schema ou API.
"""


def test_minimal_run_fixture_preserves_evidence_boundaries(tmp_path: Path) -> None:
    source_path = FIXTURE_ROOT / "incident.log"
    expected_path = FIXTURE_ROOT / "expected-run.md"
    source = source_path.read_bytes()

    settings = Settings.load(tmp_path)
    settings.ensure_directories()
    database = Database(settings.database_path)
    database.create_all()
    repository = Repository(database, TestHumanAttestationVerifier())
    workspace = repository.catalog.create_workspace("Fixture workspace")
    project = repository.catalog.create_project(workspace.id, "Run evidence boundaries")
    source_ref = ArtifactStore(settings.artifacts_dir).put_ref(
        source,
        project_id=project.id,
        media_type="text/plain",
        classification=Classification.INTERNAL,
    )
    assert source_ref.digest == sha256_bytes(source)
    revisions, study = build_runtime_study(project_id=project.id, source=source_ref)
    assert study.payload.intent.purpose == LAB_INTENT
    for revision in revisions:
        repository.registry.save_contract_revision(revision, status="proposed")
        repository.registry.decide_contract_revision(accepted_decision(revision))

    specs = StudyCompiler(repository.registry.contract_registry(project.id)).compile(study)
    assert len(specs) == 1
    spec = specs[0]
    spec_row = repository.catalog.save_run_spec(spec)
    kernel = build_runtime_kernel(repository, settings.artifacts_dir)
    admission = kernel.coordinator.admission_service.admit(spec)
    assert admission.decision == "admitted"
    admission_row = repository.catalog.save_admission_record(spec_row.id, admission)
    run_id, job = kernel.coordinator.enqueue(
        run_spec_id=spec_row.id,
        admission_id=admission_row.id,
        idempotency_key="run-evidence-boundaries-v1",
    )
    worker = DurableRunWorker(
        repository,
        kernel.coordinator,
        worker_id="run-evidence-boundaries-worker",
    )
    assert asyncio.run(worker.process_once(job_id=job.job_id)) is True

    run_record = repository.read_model.get_run_record(run_id)
    assert run_record is not None
    assert run_record.run_id == run_id
    assert run_record.run_spec_id == spec_row.id
    assert run_record.admission_id == admission_row.id
    assert run_record.run_spec_digest == spec.digest
    assert run_record.admission_digest == admission.digest
    envelope = repository.read_model.get_subject_envelope(run_id).envelope
    events = repository.read_model.get_run_events(run_id)
    evaluations = repository.read_model.get_evaluation_records(run_id)
    assert len(evaluations) == 1
    evaluation = evaluations[0]

    assert [item["type"] for item in events] == [
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
    assert events[-1]["payload"]["goal_result"] == {
        "goal_mode": "goal_state",
        "state": "achieved",
    }
    assert evaluation.gate_status == "passed"
    assert repository.read_model.get_checkpoint_records(run_id) == []
    assert evaluation.boundary.up_to_event_sequence == events[5]["sequence"]
    assert evaluation.boundary.event_hash == events[5]["event_hash"]
    assert envelope.inputs[0].source.digest == source_ref.digest

    assert spec.agent_inventory.provider_profile_id is None
    assert spec.agent_inventory.capability_requirements == ()
    assert spec.agent_inventory.runtime_requirements == ()
    assert admission.resolved_inventory.provider_profile_id is None
    assert admission.resolved_inventory.capabilities == ()
    assert spec.checkpoint_policy is None
    assert spec.progress_artifact_policy is None
    assert spec.extensions == ()

    envelope_json = envelope.model_dump_json()
    assert HIDDEN_EXPECTED in spec.evaluation_plan.model_dump_json()
    assert HIDDEN_EXPECTED not in envelope_json
    assert LAB_INTENT not in envelope_json
    assert source.decode("utf-8") not in envelope_json

    rendered = _render_expected_run(
        spec=spec,
        run_record=run_record,
        admission_decision=admission.decision,
        envelope=envelope,
        events=events,
        evaluation=evaluation,
    )
    assert HIDDEN_EXPECTED not in rendered
    assert LAB_INTENT not in rendered
    assert source.decode("utf-8") not in rendered
    assert rendered == expected_path.read_text()
    database.dispose()
