# Features

Features are capabilities that span more than one system. Where the [systems](../systems/index.md) pages describe a single module (contracts, run execution, evidence, authority) and the [primitives](../primitives/index.md) pages describe a single domain object, the pages here follow a workflow from end to end and name every part it touches.

Each feature page states what it does, how it works with a diagram, which systems and primitives are involved, the current limits (what compiles but is not executable), and the entry points in code.

## The cross-cutting capabilities

- [Study to Run lifecycle](study-to-run-lifecycle.md) — the canonical path from an accepted revision through compilation, admission, run execution, the event ledger, evaluation, and comparison. This is the flow the whole project is organized around.
- [Deterministic benchmark](deterministic-benchmark.md) — how `CRL-CTX-002` bootstraps from a legacy manifest and runs two context-policy variants fully offline, and what that proves and does not prove.
- [Human authority](human-authority.md) — the verifiable-human-authority policy: agents never claim to be human, human authority needs a verified attestation, and without a trusted adapter the surfaces fail closed.
- [Evidence bundles](evidence-bundles.md) — exporting a comparison as an auditable, verifiable archive, and what verification re-checks.

## How these relate

The lifecycle is the spine. The benchmark is the one path through that spine the runtime can execute today. Human authority guards the acceptance step at the top of the lifecycle and the evaluation records near the bottom. Evidence bundles package the output of a completed lifecycle for a third party to verify. Read the lifecycle first; the other three make more sense against it.
