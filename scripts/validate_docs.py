from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
GENERATED = DOCS / "_generated" / "manifest.json"
REQUIRED = {
    "id",
    "type",
    "title",
    "status",
    "authority",
    "owner",
    "created_at",
    "updated_at",
    "applies_to",
    "sources",
    "supersedes",
    "superseded_by",
    "implementation_refs",
    "verification_refs",
}
STATUSES = {
    "draft",
    "proposed",
    "accepted",
    "implemented",
    "verified",
    "deprecated",
    "superseded",
    "rejected",
}


def parse_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path.relative_to(ROOT)} has no frontmatter")
    _, raw, _body = text.split("---", 2)
    value = yaml.safe_load(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} has invalid frontmatter")
    return value


def main() -> int:
    errors: list[str] = []
    entries: list[dict[str, Any]] = []
    ids: dict[str, Path] = {}
    paths = sorted(path for path in DOCS.rglob("*.md") if "_generated" not in path.parts)
    for path in paths:
        try:
            metadata = parse_frontmatter(path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        missing = REQUIRED - metadata.keys()
        if missing:
            errors.append(f"{path.relative_to(ROOT)} missing: {', '.join(sorted(missing))}")
        doc_id = str(metadata.get("id", ""))
        if doc_id in ids:
            errors.append(f"duplicate id {doc_id}: {ids[doc_id]} and {path}")
        ids[doc_id] = path
        if metadata.get("status") not in STATUSES:
            errors.append(f"{path.relative_to(ROOT)} has invalid status")
        if metadata.get("status") in {"implemented", "verified"} and not metadata.get(
            "implementation_refs"
        ):
            errors.append(f"{path.relative_to(ROOT)} is implemented without implementation_refs")
        if metadata.get("status") == "verified" and not metadata.get("verification_refs"):
            errors.append(f"{path.relative_to(ROOT)} is verified without verification_refs")
        for key in ("implementation_refs", "verification_refs"):
            for reference in metadata.get(key) or []:
                reference_path = ROOT / str(reference)
                if reference_path == GENERATED:
                    continue
                if not reference_path.exists():
                    errors.append(f"{path.relative_to(ROOT)} references missing {reference}")
        entries.append(
            {
                "id": doc_id,
                "path": str(path.relative_to(ROOT)),
                "type": metadata.get("type"),
                "title": metadata.get("title"),
                "status": metadata.get("status"),
                "authority": metadata.get("authority"),
                "owner": metadata.get("owner"),
                "updated_at": str(metadata.get("updated_at")),
                "review_due": str(metadata.get("review_due"))
                if metadata.get("review_due")
                else None,
            }
        )
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    GENERATED.parent.mkdir(parents=True, exist_ok=True)
    GENERATED.write_text(
        json.dumps({"schema_version": "1", "documents": entries}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"Validated {len(entries)} documents; generated {GENERATED.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
