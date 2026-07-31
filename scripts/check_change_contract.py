#!/usr/bin/env python3
"""Check a planned change against the real Git diff."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

from change_contract import (
    ContractError,
    Diagnostic,
    GitError,
    GitSnapshot,
    Severity,
    check_contract,
    inspect_repository,
    load_contract,
    secret_diagnostics,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--base-ref", help="Override do base_ref para CI ou branches empilhadas")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help=(
            "Promove warnings a exit 1; desligado por padrao para nao bloquear "
            "descoberta legitima"
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.contract is not None and args.discover:
        return _configuration_error(args.format, "use --contract ou --discover, nao ambos")
    root = args.root.resolve()
    try:
        if args.contract is not None:
            contract_path = args.contract
            if not contract_path.is_absolute():
                contract_path = root / contract_path
            contract = load_contract(contract_path)
            snapshot = inspect_repository(root, args.base_ref or contract.base_ref)
            report = check_contract(contract, snapshot)
            _print(report.as_dict(), args.format)
            if report.blockers or (args.strict_warnings and report.warnings):
                return 1
            return 0
        return _discover(root, args.base_ref or "origin/main", args.format, args.strict_warnings)
    except (ContractError, GitError) as error:
        details = list(error.errors) if isinstance(error, ContractError) else [str(error)]
        return _configuration_error(args.format, *details)


def _discover(root: Path, base_ref: str, output_format: str, strict: bool) -> int:
    snapshot = inspect_repository(root, base_ref)
    candidates = tuple(
        path
        for path in snapshot.changed_paths
        if path.startswith("changes/") and path.endswith(".toml") and (root / path).is_file()
    )
    if len(candidates) > 1:
        return _configuration_error(
            output_format,
            "mais de um contrato ativo no diff; preserve uma issue por branch/worktree: "
            + ", ".join(candidates),
        )
    if not candidates:
        diagnostics: list[Diagnostic] = list(secret_diagnostics(snapshot.added_lines))
        delivery = tuple(path for path in snapshot.changed_paths if not path.startswith("changes/"))
        if delivery:
            diagnostics.append(
                Diagnostic(
                    code="planning.contract_missing",
                    severity=Severity.WARNING,
                    message="O diff possui entrega sem contrato de mudanca novo ou alterado.",
                    paths=delivery,
                    remediation="Crie changes/<issue>.toml a partir do template antes do handoff.",
                )
            )
        payload = _discovery_payload(snapshot, tuple(diagnostics))
        _print(payload, output_format)
        blockers = any(item.severity is Severity.BLOCKER for item in diagnostics)
        warnings = any(item.severity is Severity.WARNING for item in diagnostics)
        return 1 if blockers or (strict and warnings) else 0
    contract = load_contract(root / candidates[0])
    if contract.base_ref != base_ref:
        snapshot = inspect_repository(root, base_ref)
    report = check_contract(contract, snapshot)
    _print(report.as_dict(), output_format)
    if report.blockers or (strict and report.warnings):
        return 1
    return 0


def _discovery_payload(
    snapshot: GitSnapshot, diagnostics: tuple[Diagnostic, ...]
) -> dict[str, Any]:
    blockers = sum(item.severity is Severity.BLOCKER for item in diagnostics)
    warnings = sum(item.severity is Severity.WARNING for item in diagnostics)
    return {
        "schema_version": "1",
        "contract": None,
        "git": {
            "base_ref": snapshot.base_ref,
            "merge_base": snapshot.merge_base,
            "head": snapshot.head,
            "branch": snapshot.branch,
        },
        "delivery_paths": list(snapshot.changed_paths),
        "untracked_not_delivery": list(snapshot.untracked),
        "summary": {
            "blockers": blockers,
            "warnings": warnings,
            "diagnostics": len(diagnostics),
        },
        "diagnostics": [item.as_dict() for item in diagnostics],
    }


def _configuration_error(output_format: str, *messages: str) -> int:
    payload = {
        "schema_version": "1",
        "configuration_errors": list(messages),
    }
    _print(payload, output_format)
    return 2


def _print(payload: dict[str, Any], output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return
    errors = payload.get("configuration_errors")
    if isinstance(errors, list):
        for error in cast(list[object], errors):
            print(f"ERRO configuracao: {error}")
        return
    contract = payload.get("contract")
    identity = "sem contrato" if contract is None else contract["change_id"]
    summary = payload["summary"]
    print(
        f"Contrato de mudanca {identity}: {summary['blockers']} blockers, "
        f"{summary['warnings']} warnings"
    )
    for item in payload["diagnostics"]:
        paths = f" ({', '.join(item['paths'])})" if item["paths"] else ""
        print(f"{item['severity'].upper()} {item['code']}: {item['message']}{paths}")
        if item["remediation"]:
            print(f"  proxima acao: {item['remediation']}")


if __name__ == "__main__":
    sys.exit(main())
