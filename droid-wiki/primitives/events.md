# Events

A Run event is an append-only observation of execution. The events for one Run form a hash-chained ledger that is the normative record of what happened — `RunRow.status` is only an operational cache derived from it. Events are typed, phase-gated, and tamper-evident.

## The concept

Each event is written with a fixed envelope. `sequence` is monotonic within a Run, `event_hash` covers the envelope without itself, and `prev_event_hash` links the event to its predecessor. Because every event commits to the previous hash, changing any earlier event breaks every later hash, so the chain is tamper-evident. A retry creates a new Run; earlier events never change.

Each registered event type maps to a closed Pydantic payload model, validated before the event enters the ledger. An unregistered type is rejected. Beyond shape, the repository validates semantics: the event's type must be legal for the Run's current phase, lifecycle transitions must be legal, subject invocations and responses must be paired, and terminal events close the Run.

## The envelope

The Run Event v1 envelope (`docs/contracts/run-event.md`):

```text
event_id, schema_version, run_id, sequence, type, occurred_at_utc,
actor_type, actor_id, classification, payload, correlation_id,
causation_id, prev_event_hash, event_hash
```

## The canonical event types

The executable path emits, in order:

| Type | Valid phase | Payload notes |
| --- | --- | --- |
| `run.queued` | queued | Carries the run-spec and admission digests; checked against stored contracts. Must be first; may not reappear. |
| `run.preparing` | queued → preparing | Lifecycle transition. |
| `context.composed` | preparing | Snapshot id, policy id, strategy, char counts, omission flag, content hash. |
| `run.running` | preparing → running | Lifecycle transition. |
| `subject.invoked` | running | Runner, network mode, subject envelope digest, optional guidance digest. |
| `subject.responded` | running | `output_digest` and the applied capture mode; shape enforced per mode. |
| `run.evaluating` | running → evaluating | Requires a prior response. |
| `evaluation.completed` | evaluating | Must point at the exact persisted `EvaluationRecord`, same run, digest, and gate; no duplicate conclusion. |
| `run.completed` | evaluating → completed | Requires the records and stage coverage the evaluation plan demands. |

Terminal alternatives to `run.completed`: `run.budget_exhausted` (wall timeout, with a `not_assessable` goal result) and `run.failed`. All terminal events close the Run; nothing may follow.

## Reserved types

`UNSUPPORTED_RUNTIME_EVENT_TYPES` is the reserved set the active runtime refuses to append until its coordinator exists: `run.paused`, `run.resumed`, `capability.offered`, every tool and skill lifecycle event, `checkpoint.validation_failed`, and every `progress.*` event. A registered schema does not mean an authorized factual event — the payload catalog defines these shapes for the future, but the repository and the bundle verifier both reject them today.

## Invariants

- **Monotonic, chained.** `sequence` increments by one; `prev_event_hash` equals the previous event's hash; the recomputed `sha256_json` of the envelope equals the stored `event_hash`.
- **First and terminal.** The first event is `run.queued`; `run.queued` may not reappear; no event may follow a terminal event.
- **Phase-gated.** A type is valid only in the run statuses its `EVENT_ALLOWED_RUN_STATUSES` entry permits (for example `subject.responded` only while `running`, `evaluation.completed` only while `evaluating`).
- **Paired subject turns.** Each `subject.responded` requires exactly one prior unanswered `subject.invoked`; a new invocation requires the previous turn to have ended; the Run cannot enter evaluation before the first response.
- **Exact payload shape.** `normalize_event_payload(event_type, payload)` validates against the type's model and returns the canonical dump; the repository calls it on every append and the [evidence](../systems/evidence.md) verifier calls it on every stored event. `subject.responded` capture shape must match the RunSpec's capture mode exactly.
- **Status written atomically.** The repository advances `RunRow.status` in the same transaction that appends each lifecycle event; `update_run` does not accept a direct status change.

## Where it appears in code

| File | Role |
| --- | --- |
| `src/evidrun/contracts/runtime.py` | Event payload models, `EVENT_PAYLOAD_MODELS`, `EVENT_ALLOWED_RUN_STATUSES`, `UNSUPPORTED_RUNTIME_EVENT_TYPES`, `normalize_event_payload`. |
| `src/evidrun/infrastructure/database/repository.py` | `append_event` — the state machine, phase gate, hash chaining, and semantic checks. |
| `src/evidrun/runs/service.py` | `_execute_spec` — emits the canonical sequence. |
| `docs/contracts/run-event.md`, `docs/contracts/run-event-payloads-v1.md` | The normative envelope and payload catalog. |

## Cross-links

- [Run execution](../systems/run-execution.md) — the exact sequence and the timeout/failure branches.
- [Database](../systems/database.md) — how events are written and the status column advanced.
- [Runtime records](../systems/contracts/runtime.md) — every payload model.
- [Evidence bundles](../features/evidence-bundles.md) — how the chain is re-verified independently.
