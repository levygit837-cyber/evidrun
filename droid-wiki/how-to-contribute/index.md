# How to contribute

This section explains how to work in the Evidrun codebase: where the source of truth lives, how a change moves from a branch to a merge, what the definition of done is, and how to debug when something fails closed. The rules here are enforced by review against `AGENTS.md` and by CI in `.github/workflows/ci.yml`.

## Read the docs before changing contracts or architecture

The repository is the normative source. Inside `docs/`, accepted ADRs and contracts are normative, architecture describes the current state, research is temporal, and roadmap is future intent. Before you touch a contract or an architectural boundary, read `docs/index.md` and the relevant ADR.

Three rules matter most:

- **Read `docs/index.md` first.** It links the charter, glossary, architecture, contract docs, and the accepted ADRs. Do not change a contract or a plane boundary without knowing which ADR governs it.
- **Successor ADRs, not rewrites.** An accepted ADR is never edited to change a decision. You write a new ADR that supersedes it, set `superseded_by` on the old one and `supersedes` on the new one, and leave the historical record intact. ADR 0013 superseding ADR 0012 is the worked example. See [background](../background/index.md).
- **Run results are not facts without references.** A claim about what a run did must point to a `run:`, `event:`, or `artifact:` reference. Do not write run outcomes into docs as prose. Reports are projections generated from evidence, never maintained by hand.

## Documentation is a checked artifact

Every file under `docs/` carries YAML frontmatter (`id`, `type`, `status`, `authority`, `implementation_refs`, `verification_refs`, and more). `scripts/validate_docs.py` validates that frontmatter, checks that `implementation_refs`/`verification_refs` point at paths that exist, rejects duplicate IDs, and regenerates `docs/_generated/manifest.json`. CI runs the validator and then `git diff --exit-code -- docs/_generated`, so a stale manifest fails the build. A `status` of `implemented` requires `implementation_refs`; `verified` also requires `verification_refs`. Docs are written in Brazilian Portuguese; IDs, routes, schemas, and filenames stay in stable ASCII English. See [tooling](tooling.md) for the validator and the other generators.

## The layering rules you cannot break

These are reviewed by hand, not caught by a linter, so they are easy to break by accident. They come straight from `AGENTS.md`:

- The Python domain never imports FastAPI, SQLAlchemy, OpenAI, Electron, or React.
- Electron Main manages lifecycle and desktop capabilities; it implements no domain logic.
- The renderer never imports `electron`, `node:*`, or native bindings.
- The Subject Agent never receives chats, hidden graders, or evidence outside the compiled `SubjectEnvelope`.
- The Lab Agent creates drafts; acceptance and external effects belong to the human.

The cross-cutting patterns that hold across the code (frozen contract models, canonical digests, fail-closed admission, generated types) are documented in [patterns and conventions](patterns-and-conventions.md).

## Definition of done

A change is done when the full verification suite passes locally and in CI. This is the mandatory suite from `AGENTS.md`:

```bash
uv run pytest
uv run ruff check .
uv run pyright
pnpm typecheck:web
pnpm typecheck:desktop
pnpm test
pnpm build
uv run python scripts/validate_docs.py
```

`pnpm test` includes `check:contracts`, which regenerates the JSON Schemas and the TypeScript contract types and diffs them against what is committed. If you changed a contract, regenerate and commit the output first. The `CRL-CTX-002` benchmark must stay offline and deterministic; a change that makes it need the network or produce a different result is a regression. See [development workflow](development-workflow.md) for the branch-to-merge cycle, [testing](testing.md) for what each suite covers, and [debugging](debugging.md) for reading fail-closed rejections.

## Where to start

| You want to | Start at |
| --- | --- |
| Understand the code conventions | [patterns and conventions](patterns-and-conventions.md) |
| Follow the branch-to-merge cycle | [development workflow](development-workflow.md) |
| Know what the tests cover | [testing](testing.md) |
| Troubleshoot a fail-closed rejection | [debugging](debugging.md) |
| Understand the generators and CI | [tooling](tooling.md) |
| Understand why a decision was made | [background](../background/index.md) |
