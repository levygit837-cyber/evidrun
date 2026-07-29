"""Regenerate the admission oracle snapshot.

Run only when an admission behaviour change is intended and reviewed:

    uv run python -m tests.support.admission_oracle_snapshot
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from evidrun.infrastructure.artifacts.store import ArtifactStore, MemoryKeyProvider
from tests.support.admission_cases import build_admission_cases, build_catalogs
from tests.support.admission_specs import admission_fingerprint, oracle_profile
from tests.support.execution_trust import unpersisted_unverified_trust

SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "unit" / "admission_oracle.json"


def collect() -> dict[str, list[str]]:
    """Run every oracle case through the production admission path."""

    with tempfile.TemporaryDirectory() as directory:
        store = ArtifactStore(Path(directory) / "artifacts", MemoryKeyProvider())
        catalogs = build_catalogs(store, profile=oracle_profile())
        return {
            case.name: list(
                admission_fingerprint(
                    catalogs[case.catalog]
                    .admission_service()
                    .admit(case.spec, unpersisted_unverified_trust(case.spec))
                )
            )
            for case in build_admission_cases(store)
        }


def main() -> None:
    payload = json.dumps(collect(), ensure_ascii=False, indent=2, sort_keys=True)
    SNAPSHOT_PATH.write_text(f"{payload}\n", encoding="utf-8")
    print(f"wrote {SNAPSHOT_PATH.relative_to(Path.cwd())}")


if __name__ == "__main__":
    main()
