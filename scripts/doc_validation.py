from __future__ import annotations

import ast
import re
import subprocess
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from doc_claims import ClaimResult, evaluate_claims, load_claims
from doc_relations import validate_relations

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
MARKDOWN_LINK = re.compile(r"\[[^]]*]\(([^)]+)\)")
REFERENCE_LINK = re.compile(r"(?m)^[ \t]{0,3}\[[^]]+]:[ \t]*(?:<([^>\n]+)>|(\S+))")
SOURCE_SCHEME = re.compile(r"^[a-z][a-z-]+:")


@dataclass(frozen=True, order=True)
class Diagnostic:
    severity: str
    code: str
    document: str
    message: str


@dataclass(frozen=True)
class ValidationResult:
    diagnostics: tuple[Diagnostic, ...]
    entries: tuple[dict[str, Any], ...]
    claim_results: tuple[ClaimResult, ...]

    @property
    def has_errors(self) -> bool:
        return any(item.severity == "error" for item in self.diagnostics)


Report = Callable[[Path, str, str, str], None]


def metadata_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def checkout_date(root: Path) -> date | None:
    completed = subprocess.run(
        ["git", "show", "-s", "--format=%cs", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return metadata_date(completed.stdout.strip())


def python_symbols(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    symbols: set[str] = set()

    def add_target(target: ast.expr) -> None:
        if isinstance(target, ast.Name):
            symbols.add(target.id)
        elif isinstance(target, ast.Tuple | ast.List):
            for element in target.elts:
                add_target(element)

    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            symbols.add(node.name)
        elif isinstance(node, ast.Import):
            symbols.update(alias.asname or alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            symbols.update(alias.asname or alias.name for alias in node.names if alias.name != "*")
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                add_target(target)
        elif isinstance(node, ast.AnnAssign):
            add_target(node.target)
    return symbols


def parse_frontmatter(path: Path, *, root: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{path.relative_to(root)} has no frontmatter")
    _, raw, _body = text.split("---", 2)
    value = yaml.safe_load(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(root)} has invalid frontmatter")
    return value


def validate_document(
    root: Path,
    path: Path,
    generated_refs: set[Path],
    evaluation_date: date | None,
    ids: dict[str, Path],
    report: Report,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    try:
        metadata = parse_frontmatter(path, root=root)
    except ValueError as exc:
        report(path, "frontmatter", str(exc), "error")
        return None
    missing = REQUIRED - metadata.keys()
    if missing:
        report(path, "frontmatter-missing", f"missing: {', '.join(sorted(missing))}", "error")
    doc_id = str(metadata.get("id", ""))
    if doc_id in ids:
        report(path, "duplicate-id", f"duplicate id {doc_id}: {ids[doc_id]} and {path}", "error")
    ids[doc_id] = path
    status, authority, volatility = (
        metadata.get("status"),
        metadata.get("authority"),
        metadata.get("volatility"),
    )
    validate_classification(path, status, authority, volatility, report)
    validate_dates(path, metadata, evaluation_date, report)
    validate_references(root, path, metadata, generated_refs, report)
    validate_links(path, report)
    entry = {
        "id": doc_id,
        "path": str(path.relative_to(root)),
        "type": metadata.get("type"),
        "title": metadata.get("title"),
        "status": status,
        "authority": authority,
        "volatility": volatility,
        "owner": metadata.get("owner"),
        "updated_at": str(metadata.get("updated_at")),
        "review_due": str(metadata.get("review_due")) if metadata.get("review_due") else None,
    }
    return metadata, entry


def validate_classification(
    path: Path, status: object, authority: object, volatility: object, report: Report
) -> None:
    if status not in STATUSES:
        report(path, "invalid-status", "has invalid status", "error")
    if authority not in AUTHORITIES:
        report(path, "invalid-authority", "has invalid authority", "error")
    if volatility not in VOLATILITIES:
        report(path, "invalid-volatility", "has invalid volatility", "error")
    if authority in SNAPSHOT_AUTHORITIES and volatility != "snapshot":
        report(
            path,
            "invalid-volatility",
            f"{authority} authority requires snapshot volatility",
            "error",
        )
    if authority == "normative" and volatility in {"snapshot", "generated"}:
        report(
            path,
            "invalid-volatility",
            f"normative authority cannot use {volatility} volatility",
            "error",
        )
    if authority == "incubation" and status in {"implemented", "verified"}:
        report(
            path, "invalid-status", f"incubation authority cannot claim {status} status", "error"
        )


def validate_dates(
    path: Path, metadata: dict[str, Any], today: date | None, report: Report
) -> None:
    created, updated = (
        metadata_date(metadata.get("created_at")),
        metadata_date(metadata.get("updated_at")),
    )
    template = "templates" in path.parts and {
        metadata.get("created_at"),
        metadata.get("updated_at"),
    } == {"YYYY-MM-DD"}
    if (created is None or updated is None) and not template:
        report(path, "invalid-date", "created_at and updated_at must be ISO dates", "error")
    elif created and updated and created > updated:
        report(path, "invalid-date-order", "created_at must not be after updated_at", "error")
    due = metadata_date(metadata.get("review_due")) if metadata.get("review_due") else None
    if metadata.get("review_due") and due is None:
        report(path, "invalid-date", "review_due must be an ISO date", "error")
    elif due and today is not None and due < today:
        report(path, "review-overdue", f"review_due {due} is before {today}", "warning")


def validate_references(
    root: Path, path: Path, metadata: dict[str, Any], generated: set[Path], report: Report
) -> None:
    status = metadata.get("status")
    for source in metadata.get("sources") or []:
        source_text = str(source)
        if not SOURCE_SCHEME.match(source_text) and not (root / source_text).exists():
            report(path, "missing-source", f"source does not resolve: {source}", "error")
    if status in {"implemented", "verified"} and not metadata.get("implementation_refs"):
        report(
            path,
            "missing-implementation-ref",
            "is implemented without implementation_refs",
            "error",
        )
    if status == "verified" and not metadata.get("verification_refs"):
        report(path, "missing-verification-ref", "is verified without verification_refs", "error")
    for key in ("implementation_refs", "verification_refs"):
        for reference in metadata.get(key) or []:
            path_text, separator, symbol = str(reference).partition("#")
            target = root / path_text
            if target in generated:
                continue
            if not target.exists():
                report(path, "missing-reference", f"references missing {reference}", "error")
            elif separator and (target.suffix != ".py" or symbol not in python_symbols(target)):
                report(
                    path,
                    "missing-reference-symbol",
                    f"reference symbol does not resolve: {reference}",
                    "error",
                )


def validate_links(path: Path, report: Report) -> None:
    text = path.read_text(encoding="utf-8")
    targets = MARKDOWN_LINK.findall(text)
    targets.extend(left or right for left, right in REFERENCE_LINK.findall(text))
    for target in targets:
        clean = target.split("#", 1)[0].split("?", 1)[0]
        if (
            clean
            and not clean.startswith(("http://", "https://", "mailto:"))
            and not (path.parent / clean).resolve().exists()
        ):
            report(path, "broken-link", f"relative link does not resolve: {target}", "error")


def validate_repository(root: Path, *, today: date | None = None) -> ValidationResult:
    diagnostics: list[Diagnostic] = []
    entries: list[dict[str, Any]] = []
    documents: dict[str, tuple[Path, dict[str, Any]]] = {}
    ids: dict[str, Path] = {}

    def report(path: Path, code: str, message: str, severity: str) -> None:
        diagnostics.append(Diagnostic(severity, code, str(path.relative_to(root)), message))

    if today is None:
        today = checkout_date(root)
    generated = {root / "docs/_generated/manifest.json", root / "docs/_generated/claims.json"}
    paths = sorted(p for p in (root / "docs").rglob("*.md") if "_generated" not in p.parts)
    for path in paths:
        result = validate_document(root, path, generated, today, ids, report)
        if result:
            metadata, entry = result
            documents[str(path.relative_to(root))] = (path, metadata)
            entries.append(entry)
    validate_relations(documents, report)
    try:
        claims = evaluate_claims(root, load_claims(root))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as exc:
        report(root / "docs/claims.toml", "claim-registry", str(exc), "error")
        claims = ()
    for result in claims:
        if result.severity:
            code = "claim-failed" if result.status == "failed" else "claim-not-verifiable"
            report(root / result.claim.document, code, result.message, result.severity)
    return ValidationResult(tuple(sorted(diagnostics)), tuple(entries), claims)
