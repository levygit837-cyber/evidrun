# Lore

The history of Evidrun is short and easy to tell honestly: five commits across
two days in July 2026, all from one author. This page reconstructs that timeline
from `git log` rather than from memory. Dates come from commit author
timestamps.

## Eras

### Foundation, Jul 22 2026

The repository opened at 18:24 on Jul 22 2026 with
`feat: initialize Evidrun context reliability lab` (`0fc6ef3`), a single large
commit of 136 files. That first commit already laid down the modular monolith
shape: a Python domain core under `src/evidrun/`, desktop and web apps under
`apps/`, the `CRL-CTX-002` benchmark scaffold under `benchmarks/`, and the ADR
and contract documentation trees under `docs/`.

About three hours later, at 21:29, `feat: add default provider and preserve run
concepts` (`f0c27ed`) settled the default provider decision and kept the early
run vocabulary intact. This era is the skeleton: the folders and boundaries that
everything after it fills in.

### Contract discovery and foundation, Jul 22-23 2026

At 22:51 on Jul 22, `Document scenario-oriented Run contract discovery` (`#1`,
`bee188d`) was a documentation-first step. It wrote down how a Run contract
should be discovered from scenarios before the code committed to a shape, and it
also fixed CI setup ordering along the way.

The next morning, at 11:02 on Jul 23, that research turned into
`Add auditable Study and Run contract foundation` (`#2`, `71f5841`), the largest
change in the repo's life at 86 files and tens of thousands of inserted lines.
This is where immutable Study/Run contracts, fail-closed admission, audited
evaluation and checkpoint records, and Evidence Bundle v2 verification landed,
along with the generated schemas that back them.

### Human authority, Jul 23 2026

The most recent commit, at 14:27 on Jul 23,
`feat(authority): verifiable human authority per ADR 0010` (`#3`, `1010879`),
added the isolated `src/evidrun/authority/` package: enrollment, a local
software authenticator, single-use intent-bound challenges, attestation
verification, and revocation. It is opt-in and fail-closed by default. This is
the newest layer, and it shows: `authority` is already the single most-touched
source subsystem despite being the last to arrive.

## Longest-standing code

Because the project is only two days old, the oldest surviving code is simply
the initial commit's code, still largely present. Files that have lived in the
tree since `0fc6ef3` on Jul 22 include the domain entrypoints
(`src/evidrun/entrypoints/api/app.py`, `src/evidrun/entrypoints/cli/app.py`),
the evidence and persistence core (`src/evidrun/evidence/bundle.py`,
`src/evidrun/infrastructure/database/repository.py`,
`src/evidrun/infrastructure/database/models.py`), and the desktop shell under
`apps/desktop/src/main/`. `AGENTS.md`, `README.md`, and the CI workflow also
date to that first commit.

## Growth trajectory

The arc is legible in five steps: initialize the lab, fix the default provider
and run concepts, document contract discovery, build the auditable Study/Run
foundation, then add verifiable human authority. It reads as documentation-led
development. The scenario-discovery commit wrote the intent down before the
foundation commit implemented it, and the authority commit followed its ADR
rather than preceding it.

One observable artifact worth noting: the ADR sequence runs `0001` through
`0013` and then jumps to `0015`, skipping `0014`. There is no `0014` file in
`docs/adr/`. It is hard to say from the history alone whether a decision was
reserved and dropped or the number was simply passed over; either way, the gap
is a real thing you can see in the tree.

For the concepts these eras produced, see [architecture](overview/architecture.md)
and the [overview](overview/index.md).
