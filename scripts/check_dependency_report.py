"""Report dependencies, cycles and drift without blocking a merge.

Exit codes are deliberately narrow for this first phase:

* `0` — the report was produced, whatever it found. Issue #51 requires the first phase
  to inform, so no finding and no candidate threshold changes this.
* `2` — the report could not be produced: unreadable source, unusable repository. That
  is a broken tool, not a finding, and it must not be silent.

There is no exit code `1`: reserving it would invite a later change to make a finding
blocking by accident. Promoting any threshold is a separate, deliberate decision.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path

from check_import_directions import ImportException, evaluate, load_exceptions
from dependency_report import (
    build_report,
    edge_drift,
    json_document,
    text_document,
    write_json,
)
from dependency_report.graph_metrics import partition_edges
from dependency_report.vocabulary import ReportError
from import_graph import ImportGraph, WorktreeSource, build_graph

EXIT_OK = 0
EXIT_CONFIG_ERROR = 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Report dependencies, cycles and drift")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument(
        "--base-ref",
        default="origin/main",
        help="revision to diff new edges against; default origin/main",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="also write the JSON document to this path, for CI artifacts",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        graph = build_graph(root, WorktreeSource(root))
        forbidden = _forbidden_edges(graph, load_exceptions(root))
        internal_edges, _, _ = partition_edges(graph)
        drift = edge_drift(root, args.base_ref, internal_edges)
        report = build_report(graph, forbidden, drift)
    except (
        OSError,
        subprocess.CalledProcessError,
        SyntaxError,
        tomllib.TOMLDecodeError,
        ValueError,
        ReportError,
    ) as exc:
        print(f"CONFIG ERROR: {exc}", file=sys.stderr)
        return EXIT_CONFIG_ERROR
    document = json_document(report) if args.format == "json" else text_document(report)
    sys.stdout.write(document)
    if args.json_out is not None:
        write_json(args.json_out, report)
    return EXIT_OK


def _forbidden_edges(
    graph: ImportGraph, exceptions: tuple[ImportException, ...]
) -> tuple[tuple[str, str], ...]:
    """The gate's verdict, keyed by module so it partitions the internal edges.

    `Violation.source` is a file path, while the report keys internal edges by module.
    Translating here keeps the gate as the single authority on what is forbidden and
    still lets `allowed`, `forbidden` and `suspicious` be counted in one unit.

    Exceptions are applied exactly as the gate applies them: an edge an exception
    covers no longer fails the gate, so calling it forbidden here would be a second,
    divergent notion of forbidden.
    """
    module_by_path = {edge.source_path: edge.source_module for edge in graph.edges}
    return tuple(
        sorted(
            {
                (module_by_path.get(violation.source, violation.source), violation.destination)
                for violation in evaluate(graph.edges)
                if not any(exception.matches(violation) for exception in exceptions)
            }
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
