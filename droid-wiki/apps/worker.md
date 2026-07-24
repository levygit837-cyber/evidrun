# Worker

The local worker is a placeholder process. Today it prints a notice and idles. The durable, lease-based async worker is a future milestone; in the current revision the deterministic execution spine runs inside the local coordinator, not here.

Defined in `src/evidrun/entrypoints/worker/app.py` (about 22 lines).

## Directory layout

```
src/evidrun/entrypoints/worker/
  __init__.py   # docstring only: "Local worker entrypoint."
  app.py        # main(): prints a reserved-worker notice, then sleeps in a loop
```

## What it actually does

`main()` builds a Rich `Console`, prints that the durable worker is reserved and that the deterministic spine runs in the local coordinator, then loops on `time.sleep(5)` until interrupted. On `KeyboardInterrupt` it prints a shutdown line and exits. There is no lease acquisition, no queue polling, no domain call, and no repository access.

```python
console.print(
    "[yellow]Worker durável reservado.[/yellow] "
    "A espinha determinística executa no coordinator local nesta revisão."
)
```

## Why it is thin

Run execution in this revision is deterministic and in-process: the coordinator drives the scripted subject runner and the single grader stage synchronously. There is no durable async execution model yet, so there is nothing for a separate worker to lease. When durable execution lands, this entrypoint is where lease acquisition and worker-side run processing would live. Until then, treat it as reserved.

## Integration points

- None wired today. It does not construct `Settings`, `Database`, or `Repository`.
- The execution path that will eventually feed a worker is the coordinator described in [run execution](../systems/run-execution.md).

## Entry points for modification

- When durable execution is designed, add lease and run-processing logic in `src/evidrun/entrypoints/worker/app.py`, reaching the domain through the same `Repository`/`EvidrunService` seam the [CLI](cli/index.md) and [API](api.md) use. Keep the domain-boundary rule: no FastAPI, SQLAlchemy, OpenAI, Electron, or React imports leaking into the domain.

## Key source files

| Path | Role |
| --- | --- |
| `src/evidrun/entrypoints/worker/app.py` | The placeholder worker process |
| `src/evidrun/entrypoints/worker/__init__.py` | Package docstring |

See [architecture](../overview/architecture.md) for where the worker sits in the execution plane.
