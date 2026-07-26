from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

Report = Callable[[Path, str, str, str], None]


def validate_relations(documents: dict[str, tuple[Path, dict[str, Any]]], report: Report) -> None:
    for relative, (path, metadata) in documents.items():
        successor = metadata.get("superseded_by")
        if successor:
            record = documents.get(str(successor))
            if record is None:
                report(
                    path, "supersession-missing", f"successor does not exist: {successor}", "error"
                )
            elif relative not in (record[1].get("supersedes") or []):
                report(
                    path,
                    "supersession-mismatch",
                    f"{successor} does not supersede {relative}",
                    "error",
                )
        for predecessor in metadata.get("supersedes") or []:
            record = documents.get(str(predecessor))
            if record is None:
                report(
                    path,
                    "supersession-missing",
                    f"predecessor does not exist: {predecessor}",
                    "error",
                )
            elif record[1].get("superseded_by") != relative:
                report(
                    path,
                    "supersession-mismatch",
                    f"{predecessor} does not point to successor {relative}",
                    "error",
                )
