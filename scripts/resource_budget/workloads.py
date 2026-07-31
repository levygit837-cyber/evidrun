"""Real workloads executed in isolated processes by the resource checker."""

from __future__ import annotations

import argparse
import importlib
import json
import resource
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Any


def _peak_rss_kib() -> int:
    peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return peak // 1024 if sys.platform == "darwin" else peak


def _startup_import(_: Path) -> dict[str, float | int]:
    started = perf_counter()
    importlib.import_module("evidrun.entrypoints.cli.app")

    return {
        "duration_ms": (perf_counter() - started) * 1000,
        "peak_rss_kib": _peak_rss_kib(),
    }


def _open_demo(root: Path, data_dir: Path) -> tuple[Any, Any, dict[str, Any]]:
    from evidrun.infrastructure.database import Database, Repository
    from evidrun.runs import EvidrunService
    from evidrun.settings import Settings

    settings = Settings.load(data_dir)
    settings.ensure_directories()
    database = Database(settings.database_path)
    database.create_all()
    repository = Repository(database)
    result = EvidrunService(repository).bootstrap_demo(root / "benchmarks")
    return database, repository, result


def _crl_ctx_002(root: Path) -> dict[str, float | int]:
    with TemporaryDirectory(prefix="evidrun-resource-crl-") as temporary:
        started = perf_counter()
        database, repository, _ = _open_demo(root, Path(temporary))
        try:
            dashboard = repository.read_model.latest_dashboard()
            return {
                "duration_ms": (perf_counter() - started) * 1000,
                "peak_rss_kib": _peak_rss_kib(),
                "run_count": int(dashboard["summary"]["runs"]),
                "comparison_count": int(dashboard["summary"]["comparisons"]),
                "event_count": int(dashboard["summary"]["events"]),
            }
        finally:
            database.dispose()


def _run_bundle_export_verify(root: Path) -> dict[str, float | int]:
    from evidrun.evidence.bundle import EvidenceBundleService

    with TemporaryDirectory(prefix="evidrun-resource-bundle-") as temporary:
        data_dir = Path(temporary)
        database, repository, result = _open_demo(root, data_dir)
        try:
            bundle = data_dir / "run.evidrun.zip"
            service = EvidenceBundleService(repository)
            started = perf_counter()
            _, version = service.export_run(result["baseline_run_id"], bundle)
            verification = service.verify(bundle)
            duration_ms = (perf_counter() - started) * 1000
            import zipfile

            with zipfile.ZipFile(bundle) as archive:
                bundle_files = len(archive.namelist())
            return {
                "duration_ms": duration_ms,
                "peak_rss_kib": _peak_rss_kib(),
                "bundle_bytes": bundle.stat().st_size,
                "bundle_files": bundle_files,
                "bundle_schema_version": int(version),
                "verification_valid": int(bool(verification["valid"])),
            }
        finally:
            database.dispose()


WORKLOADS = {
    "startup_import": _startup_import,
    "crl_ctx_002": _crl_ctx_002,
    "run_bundle_export_verify": _run_bundle_export_verify,
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workload", choices=tuple(WORKLOADS), required=True)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(WORKLOADS[args.workload](args.root.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
