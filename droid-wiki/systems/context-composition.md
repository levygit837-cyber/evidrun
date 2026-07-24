# Context composition

`src/evidrun/contexts/engine.py` holds `ContextComposer`, the small deterministic component that applies a context policy to source text and produces a hashed snapshot. Context is the independent variable of the CRL-CTX-002 benchmark: the baseline and candidate runs differ only in how much of the same log the Subject can see.

## Purpose

The composer answers one question: given a block of source text and a policy, what does the Subject actually get, and what is the content hash of that selection? It also diffs two snapshots so a comparison can report what changed.

## Key source files

| File | Role |
| --- | --- |
| `src/evidrun/contexts/engine.py` | `ContextComposer.compose` and `ContextComposer.diff`. |
| `src/evidrun/contexts/__init__.py` | Re-exports `ContextComposer`. |
| `src/evidrun/experiments/models.py` | `ContextPolicySpec` (`id`, `strategy`, `max_chars`). |

## ContextPolicySpec

A context policy is a frozen model with three fields: an `id`, a `strategy` of `head`, `tail`, or `full`, and a positive `max_chars`. It rides along on the RunSpec (`RunSpec.context_policy`) and on the run blueprint and variant overrides, so different variants can apply different policies to the same scenario input.

## Strategies

`compose(source, policy)` selects a substring based on the strategy and character budget:

- `full`, or any source at or under `max_chars`: the whole source is selected, nothing omitted.
- `head`: the first `max_chars` characters are kept; the tail is recorded as omitted.
- `tail`: the last `max_chars` characters are kept; the head is recorded as omitted.

The omitted region is recorded as a start/end range so the diff can show exactly what was dropped. In CRL-CTX-002, the `ROOT_CAUSE=` marker sits near the end of the log, so a `head` policy that truncates before it starves the Subject while a `tail` (or `full`) policy preserves it — that difference is the whole experiment.

## Snapshots and content hashing

`compose` returns a plan dict with the policy id, strategy, char budget, source and selected char counts, the selected content, and the omitted ranges. It then sets a `content_hash` over a stable subset:

```python
plan["content_hash"] = sha256_json(
    {
        "policy_id": policy.id,
        "selected_content": selected,
        "omitted": omitted,
    }
)
```

Hashing only the policy id, the selected content, and the omission ranges means the hash identifies exactly what the Subject saw, independent of incidental counts. The [run executor](run-execution.md) persists this plan through `Repository.save_snapshot` and records the same fields in the `context.composed` event; the repository re-checks the snapshot against the event and against the RunSpec's policy before accepting the event.

## Diffing

`diff(baseline, candidate)` compares two snapshot dicts and returns a structured summary: the before/after strategy, the before/after selected char counts, whether the root-cause marker appeared only in the candidate, and both omission lists.

```python
"added_root_cause": (
    "ROOT_CAUSE=" not in baseline_text and "ROOT_CAUSE=" in candidate_text
),
```

This is the payload that `bootstrap_demo` embeds in the comparison report, making the causal difference between the two runs explicit.

## Integration points

- [run execution](run-execution.md) calls `compose` before invoking the Subject and `diff` when building the comparison.
- [database](database.md) stores snapshots and validates the `context.composed` event against both the stored snapshot and the RunSpec policy.
- The composed content hash flows into `RunRow.context_hash` and the event ledger.

## Entry points for modification

- New selection strategies go in `compose`; keep `content_hash` covering only what the Subject actually receives so identity stays stable.
- The composer is intentionally pure and synchronous — it holds no state and does no I/O, which keeps the benchmark deterministic and offline.
