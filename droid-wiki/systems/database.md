# Database

`src/evidrun/infrastructure/database/` is the persistence layer. It is the one place the domain's contracts are written to and read from SQLite, and it is where the Run state machine and the hash-chained event ledger are enforced. Everything here is an adapter behind the domain; the contracts themselves never import SQLAlchemy.

## Directory layout

| File | Purpose |
| --- | --- |
| `src/evidrun/infrastructure/database/engine.py` | `Database` — the SQLite/WAL engine, session factory, and additive schema guards. |
| `src/evidrun/infrastructure/database/models.py` | SQLAlchemy row models (`Base` and the `*Row` tables). |
| `src/evidrun/infrastructure/database/repository.py` | `Repository` — all reads and writes, plus the state machine and event chaining. |
| `src/evidrun/infrastructure/database/__init__.py` | Re-exports `Database` and `Repository`. |

Alembic migrations live at the repository root in `alembic/` (with `alembic.ini`) and `migrations/`; `Database.create_all` additionally applies small additive column guards so a pre-contract local database stays readable before a migration is run.

## Database engine

`Database` opens a `sqlite+pysqlite` engine and configures every connection with WAL journaling, foreign keys on, a 5-second busy timeout, and `synchronous=FULL`:

```python
cursor.execute("PRAGMA journal_mode=WAL")
cursor.execute("PRAGMA foreign_keys=ON")
cursor.execute("PRAGMA busy_timeout=5000")
cursor.execute("PRAGMA synchronous=FULL")
```

WAL lets readers proceed while a writer holds the log, which suits the local-first single-process model. `create_all` imports `evidrun.authority.models` first so the human-authority tables register, then creates all tables and runs the additive guards (`_ensure_additive_run_contract_columns` adds the `run_spec_id`/`admission_id` columns; `_ensure_additive_contract_revision_status` adds the revision `status` column).

## Row models

`models.py` defines the tables: workspaces, projects, contract revisions and decisions, run specs, admission records, experiment revisions, runs, run events, context snapshots, grades, checkpoint records, evaluation records, comparisons, and chat sessions/messages. Notable constraints: contract revisions are unique per `(contract_type, logical_id, revision)`, run events are unique per `(run_id, sequence)`, run-spec and admission digests are indexed, and checkpoint boundaries are unique per `(run_id, definition_id, up_to_event_sequence)`. `RunRow.run_spec_id` and `admission_id` are nullable to accommodate the legacy contract mode; a Run with them set is `study_v1`, otherwise `legacy_v1`.

## Contracts: save, decide, import

`save_contract_revision` writes a draft or proposed revision, re-checking immutability (an existing key with different content is rejected) and monotonicity (the revision number must be exactly the prior max plus one). It never accepts a revision directly.

`decide_contract_revision` records an acceptance/rejection/supersession. A `verified_human` authority is verified through the injected `HumanAttestationVerifier`; a `repository_fixture` authority is refused here and only allowed through the legacy import path. `_persist_contract_decision` enforces the decision rules: only an accepted revision can be superseded, a conflicting decision is rejected, and the revision row's status is advanced to the decision.

`import_legacy_contract_package` is the sole path that accepts repository-fixture authorities. It checks the package covers exactly the expected CRL-CTX-002 contract identities and digests, then saves each revision and persists each decision with the package's fixture digest. This is how the offline benchmark gets accepted contracts without a human in the loop.

`contract_registry` rebuilds an `InMemoryContractRegistry` from stored rows, re-parsing each revision, re-checking its stored digest, and replaying each decision through the verifier — so the compiler always works against verified, accepted contracts.

## RunSpecs and admissions

`save_run_spec` stores the canonical spec JSON keyed by digest (deduplicating on digest). `save_admission_record` does deep consistency checks before persisting: the admission's run-spec digest must match the stored spec, and the resolved inventory must match the RunSpec's requirements exactly — same requirement ref, runner, provider, one resolved capability per requirement, no permission escalation, no authority-constraint substitution, and, for resolved capabilities, exact interface and context-ref agreement. A malformed admission cannot be stored against a spec it does not fit.

## The Run state machine

`RunRow.status` is an operational cache, not the source of truth — the event ledger is normative. Two rules keep them consistent:

- `update_run` only accepts `output` and `context_hash`. It cannot change `status`. There is no direct status setter.
- `append_event` is the only thing that advances status, and it does so in the same transaction that writes the event.

`_event_transition` encodes the legal transitions:

| Event | From | To |
| --- | --- | --- |
| `run.queued` | (first event, status `queued`) | (no change) |
| `run.preparing` | `queued` | `preparing` |
| `run.running` | `preparing` | `running` |
| `run.evaluating` | `running` | `evaluating` |
| `run.completed` | `evaluating` | `completed` |
| `run.failed` / `run.cancelled` / `run.budget_exhausted` / `run.guardrail_stopped` | any non-terminal | that terminal state |
| `run.paused` / `run.resumed` | `running` / `paused` | `paused` / `running` (reserved) |

`run.queued` must be the first event; nothing may be appended after a terminal state. Lifecycle payload `from_status` and terminal `status` fields must agree with the actual current and target status, or the append is rejected.

## append_event and chaining

`append_event` is the heart of the ledger. Before writing it:

- rejects human actor types (only `system`, `subject`, `evaluator`, `tool`, `skill`, `observer` are allowed — no event can claim human authority);
- rejects reserved event types (`UNSUPPORTED_RUNTIME_EVENT_TYPES`);
- normalizes the payload through `normalize_event_payload`;
- checks the event is valid for the current status via `EVENT_ALLOWED_RUN_STATUSES`;
- pairs subject invocations and responses, and forbids evaluation before a response;
- for `evaluation.completed`, requires the exact persisted `EvaluationRecord` (matching digest and gate status) and forbids a duplicate completion;
- for `run.queued`, `context.composed`, `subject.responded`, and terminal events, cross-checks the payload against the stored RunSpec, snapshot, capture policy, and evaluation coverage (including `EvaluationValidator` gate/stage rules and required human adjudication).

It then computes the sequence, builds the event envelope, sets `event_hash = sha256_json(envelope)` with `prev_event_hash` pointing at the last event, appends the row, and (if the transition yields a new status) advances `run.status` and stamps `completed_at` on terminal events — all in one commit. This is the chain the [evidence](evidence.md) verifier independently recomputes.

## Evaluation and checkpoint persistence

`save_evaluation_record` verifies human attestations, validates the boundary against the ledger, runs `EvaluationValidator.validate`, checks the stage trigger matches the boundary event/checkpoint, confirms every evidence ref stays within the authorized boundary sequence, enforces the human relation and adjudication rules, checks hard-gate visibility, and forbids a second record from the same source type per stage (one adjudication per stage). `save_checkpoint_record` similarly validates the boundary, definition digest, validators, trigger, and capture spec, and refuses deterministic replayability. Both are append-only and deduplicate on their digest.

## Reads and the human-attestation hook

`latest_dashboard` returns the aggregate view the API and CLI render — workspaces, projects, experiments, runs (with grade and snapshot), comparisons, chats, and summary counts. `get_run_contracts`, `get_run_record`, `get_evaluation_records`, `get_checkpoint_records`, and `get_run_events` feed the evidence exporter, re-checking every stored digest on the way out.

The `Repository` takes a `HumanAttestationVerifier` in its constructor, defaulting to `UnavailableHumanAttestationVerifier`. Every human decision or evaluation write routes through it, so a repository built without a trusted verifier fails closed on any human-authority write. See [authority](authority.md).

## Integration points

- [contracts](contracts/index.md) supplies every model this layer serializes and re-verifies.
- [run execution](run-execution.md) drives the writes; [evidence](evidence.md) drives the reads.
- Alembic (`alembic/`, `migrations/`) owns durable schema evolution; `create_all` guards only cover additive local-database drift.

## Entry points for modification

- Schema changes belong in an Alembic migration; the additive guards in `engine.py` are a stopgap, not a migration system.
- New event validation rules go in `append_event`; keep them consistent with the [evidence](evidence.md) verifier, which re-checks the same invariants.
- Never add a direct status setter — the ledger must remain the only way status advances.
