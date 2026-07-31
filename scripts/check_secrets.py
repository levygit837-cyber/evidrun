#!/usr/bin/env python3
"""Scan repository text for high-confidence secrets without printing matched values."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from secret_scan import PolicyError, load_policy, scan_paths, tracked_paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path("secret-scan.toml"))
    parser.add_argument("--path", action="append", type=Path, default=[])
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    config = args.config if args.config.is_absolute() else root / args.config
    try:
        policy = load_policy(config)
        paths = tuple(args.path) if args.path else tracked_paths(root)
        findings = scan_paths(root, paths, policy)
    except (PolicyError, subprocess.SubprocessError, ValueError) as error:
        print(
            f"secret scan configuration error: {type(error).__name__}",
            file=sys.stderr,
        )
        return 2
    if args.format == "json":
        print(
            json.dumps(
                {
                    "files": len(paths),
                    "findings": [
                        {
                            "code": "security.secret_detected",
                            "rule": finding.rule,
                            "path": finding.path,
                            "line": finding.line,
                            "column": finding.column,
                        }
                        for finding in findings
                    ],
                },
                sort_keys=True,
            )
        )
    elif findings:
        for finding in findings:
            print(
                "security.secret_detected "
                f"rule={finding.rule} location={finding.location()}",
                file=sys.stderr,
            )
    else:
        print(f"secret scan: {len(paths)} file(s), 0 finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
