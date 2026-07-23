from __future__ import annotations

from pathlib import Path

import pytest

from evidrun.contracts import (
    CheckpointRecord,
    ContractRef,
    ContractType,
    semantic_model_dump,
)
from evidrun.contracts.authoring import (
    CheckpointCaptureSpec,
    CheckpointDefinition,
    CheckpointPolicySpec,
    ManualCheckpointTrigger,
)
from evidrun.contracts.legacy import capability_ref
from evidrun.contracts.runtime import CheckpointValidation
from evidrun.infrastructure.database import Repository
from evidrun.runs import EvidrunService
from evidrun.shared.types import new_id, sha256_bytes, sha256_json, utc_now

ROOT = Path(__file__).resolve().parents[2]


def test_checkpoint_record_is_anchored_to_the_exact_run_ledger(
    repository: Repository,
) -> None:
    result = EvidrunService(repository).bootstrap_demo(ROOT / "benchmarks")
    source_run = repository.get_run(result["baseline_run_id"])
    assert source_run.run_spec_id is not None
    spec = repository.get_run_spec(source_run.run_spec_id)

    validator_ref = capability_ref("evidrun.checkpoint", "integrity")
    policy = CheckpointPolicySpec(
        definitions=(
            CheckpointDefinition(
                id="requirements-frozen",
                label="Requirements frozen",
                order=1,
                trigger=ManualCheckpointTrigger(),
                validator_refs=(validator_ref,),
                capture=CheckpointCaptureSpec(context_snapshot=True),
            ),
        )
    )
    policy_ref = ContractRef(
        contract_type=ContractType.CHECKPOINT_POLICY,
        logical_id="checkpoint-test-policy",
        revision=1,
        digest="d" * 64,
    )
    checkpoint_spec = spec.model_copy(
        update={
            "variant_id": "checkpoint-test",
            "checkpoint_policy_ref": policy_ref,
            "checkpoint_policy": policy,
        }
    )
    spec_row = repository.save_run_spec(checkpoint_spec)
    admission = EvidrunService(repository).admission_service.admit(checkpoint_spec)
    admission_row = repository.save_admission_record(spec_row.id, admission)
    run = repository.create_run(
        experiment_revision_id=source_run.experiment_revision_id,
        variant_id="checkpoint-test",
        runner=checkpoint_spec.agent_inventory.subject_id,
        objective=checkpoint_spec.goal.instruction,
        run_spec_id=spec_row.id,
        admission_id=admission_row.id,
    )
    boundary = repository.append_event(
        run_id=run.id,
        event_type="run.queued",
        payload={
            "run_id": run.id,
            "variant_id": run.variant_id,
            "run_spec_digest": checkpoint_spec.digest,
            "admission_digest": admission.digest,
        },
    )
    snapshot_content = "authorized checkpoint context"
    snapshot = repository.save_snapshot(
        run.id,
        {
            "policy_id": "checkpoint-test",
            "strategy": "full",
            "max_chars": len(snapshot_content),
            "source_chars": len(snapshot_content),
            "selected_chars": len(snapshot_content),
            "selected_content": snapshot_content,
            "omitted": [],
            "content_hash": sha256_bytes(snapshot_content.encode()),
        },
    )
    record = CheckpointRecord(
        checkpoint_id=new_id("checkpoint"),
        run_id=run.id,
        policy_ref=policy_ref,
        definition_id="requirements-frozen",
        definition_digest=sha256_json(semantic_model_dump(policy.definitions[0])),
        up_to_event_sequence=boundary.sequence,
        event_hash=boundary.event_hash,
        context_snapshot_refs=(snapshot.id,),
        validations=(
            CheckpointValidation(
                validator_ref=validator_ref,
                passed=True,
                rationale="The immutable requirements are present.",
            ),
        ),
        replayability="partial",
        replayability_limitations=("Private model state is unavailable.",),
        created_at_utc=utc_now(),
    )
    saved = repository.save_checkpoint_record(record)
    assert saved.checkpoint_hash == record.checkpoint_hash
    assert repository.get_checkpoint_records(run.id)[0] == record

    tampered = record.model_copy(
        update={"checkpoint_id": new_id("checkpoint"), "event_hash": "e" * 64}
    )
    with pytest.raises(ValueError, match="boundary"):
        repository.save_checkpoint_record(tampered)

    missing_capture = record.model_copy(
        update={
            "checkpoint_id": new_id("checkpoint"),
            "context_snapshot_refs": (),
        }
    )
    with pytest.raises(ValueError, match="capture does not match"):
        repository.save_checkpoint_record(missing_capture)

    substituted_validator = record.model_copy(
        update={
            "checkpoint_id": new_id("checkpoint"),
            "validations": (
                CheckpointValidation(
                    validator_ref=capability_ref("evidrun.checkpoint", "substituted"),
                    passed=True,
                    rationale="A validator not authorized by the definition.",
                ),
            ),
        }
    )
    with pytest.raises(ValueError, match="definition validators"):
        repository.save_checkpoint_record(substituted_validator)

    replay_overclaim = record.model_copy(
        update={
            "checkpoint_id": new_id("checkpoint"),
            "replayability": "deterministic",
            "replayability_limitations": (),
        }
    )
    with pytest.raises(ValueError, match="replayability is unsupported"):
        repository.save_checkpoint_record(replay_overclaim)
