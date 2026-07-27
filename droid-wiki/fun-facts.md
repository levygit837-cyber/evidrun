# Fun facts

A few things about Evidrun that stood out while measuring the repository. Each
one was checked against the tree or `git` before it went on this page.

## The name packs in the mission

"Evidrun" reads as evidence plus run, which is exactly what the system produces:
auditable evidence about agent runs. The reference benchmark carries the fuller
name in its code, `CRL-CTX-002`, where CRL stands for Context Reliability Lab.
The scaffold lives under `benchmarks/scenarios/crl-ctx-002/` and has been in the
tree since the first commit.

## A bilingual codebase

The domain vocabulary is largely Portuguese while the code identifiers are
English. The agent instructions in `AGENTS.md` and much of the CLI help text are
written in Portuguese, but the classes, functions, and modules under
`src/evidrun/` read in English (`AdmissionRecord`, `SubjectEnvelope`,
`HumanAttestationRecord`). It is an unusual and consistent split: prose in one
language, code in another.

## One file carries a sixth of the Python

`src/evidrun/infrastructure/database/repository.py` is 1,742 lines, the largest
source file in the project by a wide margin. That single file holds about 16% of
all Python lines under `src/`. Nothing is broken about it, but it is the obvious
first candidate if anyone goes looking for a module to split.

## Zero TODO, FIXME, or HACK markers

A search across `src/` and `apps/` for `TODO`, `FIXME`, and `HACK` in Python,
TypeScript, and TSX files returns nothing. For a two-day-old project this is
plausible rather than surprising, and it may not last, but right now the code
carries no self-flagged debt markers at all.

## The missing ADR

The architecture decision records in `docs/adr/` run `0001` through `0013` and
then skip straight to `0015`. There is no `0014`. Whether the slot was reserved
and abandoned or simply skipped is not something the history settles, but the gap
is a genuine, visible artifact in the decision log.

For how these pieces fit together, see [architecture](overview/architecture.md)
and the [overview](overview/index.md).
