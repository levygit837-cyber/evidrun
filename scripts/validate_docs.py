from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {
    "id",
    "type",
    "title",
    "status",
    "authority",
    "volatility",
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
AUTHORITIES = {
    "normative",
    "informative",
    "non-normative",
    "planning",
    "incubation",
    "research",
}
VOLATILITIES = {"timeless", "current", "snapshot", "generated"}
SNAPSHOT_AUTHORITIES = {"planning", "incubation", "research"}


def parse_frontmatter(path: Path, *, root: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path.relative_to(root)} has no frontmatter")
    _, raw, _body = text.split("---", 2)
    value = yaml.safe_load(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(root)} has invalid frontmatter")
    return value


def validate_docs(root: Path) -> int:
    docs = root / "docs"
    generated = docs / "_generated" / "manifest.json"
    errors: list[str] = []
    entries: list[dict[str, Any]] = []
    ids: dict[str, Path] = {}
    paths = sorted(path for path in docs.rglob("*.md") if "_generated" not in path.parts)
    for path in paths:
        try:
            metadata = parse_frontmatter(path, root=root)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        missing = REQUIRED - metadata.keys()
        if missing:
            errors.append(f"{path.relative_to(root)} missing: {', '.join(sorted(missing))}")
        doc_id = str(metadata.get("id", ""))
        if doc_id in ids:
            errors.append(f"duplicate id {doc_id}: {ids[doc_id]} and {path}")
        ids[doc_id] = path
        if metadata.get("status") not in STATUSES:
            errors.append(f"{path.relative_to(root)} has invalid status")
        authority = metadata.get("authority")
        if authority not in AUTHORITIES:
            errors.append(f"{path.relative_to(root)} has invalid authority")
        volatility = metadata.get("volatility")
        if metadata.get("volatility") not in VOLATILITIES:
            errors.append(f"{path.relative_to(root)} has invalid volatility")
        if authority in SNAPSHOT_AUTHORITIES and volatility != "snapshot":
            errors.append(
                f"{path.relative_to(root)} {authority} authority requires snapshot volatility"
            )
        if authority == "normative" and volatility == "snapshot":
            errors.append(
                f"{path.relative_to(root)} normative authority cannot use snapshot volatility"
            )
        if authority == "normative" and volatility == "generated":
            errors.append(
                f"{path.relative_to(root)} normative authority cannot use generated volatility"
            )
        if authority == "incubation" and metadata.get("status") in {"implemented", "verified"}:
            errors.append(
                f"{path.relative_to(root)} incubation authority cannot claim "
                f"{metadata.get('status')} status"
            )
        if metadata.get("status") in {"implemented", "verified"} and not metadata.get(
            "implementation_refs"
        ):
            errors.append(f"{path.relative_to(root)} is implemented without implementation_refs")
        if metadata.get("status") == "verified" and not metadata.get("verification_refs"):
            errors.append(f"{path.relative_to(root)} is verified without verification_refs")
        for key in ("implementation_refs", "verification_refs"):
            for reference in metadata.get(key) or []:
                reference_path = root / str(reference)
                if reference_path == generated:
                    continue
                if not reference_path.exists():
                    errors.append(f"{path.relative_to(root)} references missing {reference}")
        entries.append(
            {
                "id": doc_id,
                "path": str(path.relative_to(root)),
                "type": metadata.get("type"),
                "title": metadata.get("title"),
                "status": metadata.get("status"),
                "authority": metadata.get("authority"),
                "volatility": metadata.get("volatility"),
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
    generated.parent.mkdir(parents=True, exist_ok=True)
    generated.write_text(
        json.dumps({"schema_version": "1", "documents": entries}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(f"Validated {len(entries)} documents; generated {generated.relative_to(root)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Evidrun documentation metadata")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    return validate_docs(args.root.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
