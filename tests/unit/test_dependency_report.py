from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTER = ROOT / "scripts" / "check_dependency_report.py"


def commit_tracked(root: Path, files: dict[str, str], *, message: str) -> str:
    """Write, stage and commit `files`, returning the new commit SHA."""
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    if not (root / ".git").exists():
        subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
        for key, value in (("user.email", "test@example.com"), ("user.name", "Test")):
            subprocess.run(["git", "-C", str(root), "config", key, value], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "commit", "-q", "--no-verify", "-m", message],
        check=True,
    )
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def run_reporter(
    root: Path,
    *,
    output_format: str = "json",
    base_ref: str = "HEAD",
    extra: tuple[str, ...] = (),
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(REPORTER),
            "--root",
            str(root),
            "--format",
            output_format,
            "--base-ref",
            base_ref,
            *extra,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def report_of(root: Path, *, base_ref: str = "HEAD") -> dict[str, object]:
    result = run_reporter(root, base_ref=base_ref)
    assert result.returncode == 0, result.stderr
    document: dict[str, object] = json.loads(result.stdout)
    return document


def findings_with(document: dict[str, object], code: str) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = document["findings"]  # type: ignore[assignment]
    return [finding for finding in findings if finding["code"] == code]


def test_a_module_cycle_is_reported_with_its_members_sorted(tmp_path: Path) -> None:
    commit_tracked(
        tmp_path,
        {
            "src/evidrun/runs/alpha.py": "from evidrun.runs import beta\n",
            "src/evidrun/runs/beta.py": "from evidrun.runs import alpha\n",
        },
        message="cycle",
    )

    cycles = findings_with(report_of(tmp_path), "dependency.module_cycle")

    assert [finding["subjects"] for finding in cycles] == [
        ["evidrun.runs.alpha", "evidrun.runs.beta"]
    ]


def test_an_acyclic_graph_reports_no_cycle(tmp_path: Path) -> None:
    commit_tracked(
        tmp_path,
        {
            "src/evidrun/runs/alpha.py": "from evidrun.runs import beta\n",
            "src/evidrun/runs/beta.py": "value = 1\n",
        },
        message="acyclic",
    )

    assert findings_with(report_of(tmp_path), "dependency.module_cycle") == []


def test_the_same_checkout_produces_a_byte_identical_document(tmp_path: Path) -> None:
    commit_tracked(
        tmp_path,
        {
            "src/evidrun/runs/alpha.py": "from evidrun.runs import beta\n",
            "src/evidrun/runs/beta.py": "from evidrun.runs import alpha\n",
            "src/evidrun/contracts/base.py": "from evidrun.shared import types\n",
            "src/evidrun/shared/types.py": "value = 1\n",
        },
        message="determinism",
    )

    first = run_reporter(tmp_path)
    second = run_reporter(tmp_path)

    assert first.returncode == 0
    assert first.stdout == second.stdout


def test_findings_are_emitted_in_a_total_order_of_code_then_subjects(tmp_path: Path) -> None:
    """Reproducibility alone is not ordering: two runs of a shuffled writer also agree.

    Pinning the order is what lets a reader diff two reports, so the document must be
    sorted by `(code, subjects)` rather than by discovery.
    """
    commit_tracked(
        tmp_path,
        {
            "src/evidrun/runs/alpha.py": "from evidrun.runs import beta\n",
            "src/evidrun/runs/beta.py": "from evidrun.runs import alpha\n",
            "src/evidrun/runs/zeta.py": "from evidrun.runs import eta\n",
            "src/evidrun/runs/eta.py": "from evidrun.runs import zeta\n",
            "apps/web/src/main.tsx": "import './styles/index.css';\n",
        },
        message="ordering",
    )

    findings: list[dict[str, object]] = report_of(tmp_path)["findings"]  # type: ignore[assignment]
    keys = [(finding["code"], finding["subjects"]) for finding in findings]

    assert len(keys) > 1
    assert keys == sorted(keys)  # type: ignore[type-var]


def test_a_new_edge_leaves_the_unrelated_baseline_lines_untouched(
    tmp_path: Path,
) -> None:
    """A new edge must be additive: unrelated baseline lines keep their exact text.

    Counters and the drift section legitimately change. What must not change is any
    line describing an edge the branch did not touch, so a reviewer reads one addition
    instead of re-reading a reformatted report.
    """
    base = commit_tracked(
        tmp_path,
        {
            "src/evidrun/runs/alpha.py": "from evidrun.shared import types\n",
            "src/evidrun/runs/beta.py": "from evidrun.shared import types\n",
            "src/evidrun/runs/gamma.py": "from evidrun.shared import types\n",
            "src/evidrun/shared/types.py": "value = 1\n",
        },
        message="baseline",
    )
    before = run_reporter(tmp_path, output_format="text", base_ref=base).stdout
    commit_tracked(
        tmp_path,
        {
            "src/evidrun/runs/gamma.py": (
                "from evidrun.shared import types\nfrom evidrun.runs import alpha\n"
            )
        },
        message="one new edge",
    )

    after = run_reporter(tmp_path, output_format="text", base_ref=base).stdout

    assert "  + evidrun.runs.gamma -> evidrun.runs.alpha" in after.splitlines()
    removed = [
        line
        for line in before.splitlines()
        if line.strip() and line not in after.splitlines()
    ]
    # Counters, the drift header and the empty-section placeholder may all change.
    # No line describing an untouched edge may.
    volatile = ("=", "New edges", "No structural findings.")
    assert [line for line in removed if not any(mark in line for mark in volatile)] == []


def test_a_forbidden_edge_is_separated_from_allowed_and_suspicious(tmp_path: Path) -> None:
    """The three states partition the internal edges: every edge lands in exactly one."""
    commit_tracked(
        tmp_path,
        {
            "src/evidrun/contracts/bad.py": "from evidrun.infrastructure import database\n",
            "src/evidrun/infrastructure/database.py": "value = 1\n",
            "src/evidrun/contracts/fine.py": "from evidrun.shared import types\n",
            "src/evidrun/shared/types.py": "value = 1\n",
            "src/evidrun/runs/alpha.py": "from evidrun.runs import beta\n",
            "src/evidrun/runs/beta.py": "from evidrun.runs import alpha\n",
        },
        message="states",
    )

    document = report_of(tmp_path)

    assert document["forbidden_edges"] == [
        {"source": "evidrun.contracts.bad", "destination": "evidrun.infrastructure.database"}
    ]
    states: dict[str, int] = document["dependency_states"]  # type: ignore[assignment]
    assert states["forbidden"] == 1
    # The two edges of the cycle are suspicious, not forbidden: no rule names them.
    assert states["suspicious"] == 2
    assert states["allowed"] == 1
    assert (
        states["allowed"] + states["forbidden"] + states["suspicious"]
        == document["internal_edge_count"]
    )


def test_a_new_edge_is_named_without_restating_the_unchanged_baseline(tmp_path: Path) -> None:
    base = commit_tracked(
        tmp_path,
        {
            "src/evidrun/runs/alpha.py": "from evidrun.shared import types\n",
            "src/evidrun/runs/beta.py": "from evidrun.shared import types\n",
            "src/evidrun/shared/types.py": "value = 1\n",
        },
        message="baseline",
    )
    commit_tracked(
        tmp_path,
        {
            "src/evidrun/runs/beta.py": (
                "from evidrun.shared import types\nimport evidrun.runs.alpha\n"
            )
        },
        message="one new edge",
    )

    document = report_of(tmp_path, base_ref=base)

    drift: dict[str, object] = document["drift"]  # type: ignore[assignment]
    assert drift["computed"] is True
    assert drift["new_edges"] == [
        {"source": "evidrun.runs.beta", "destination": "evidrun.runs.alpha"}
    ]


def test_an_unchanged_checkout_reports_no_new_edge(tmp_path: Path) -> None:
    base = commit_tracked(
        tmp_path,
        {
            "src/evidrun/runs/alpha.py": "from evidrun.shared import types\n",
            "src/evidrun/shared/types.py": "value = 1\n",
        },
        message="baseline",
    )

    drift: dict[str, object] = report_of(tmp_path, base_ref=base)["drift"]  # type: ignore[assignment]

    assert drift["computed"] is True
    assert drift["new_edges"] == []


def test_an_unresolvable_base_ref_is_named_instead_of_reported_as_no_drift(
    tmp_path: Path,
) -> None:
    commit_tracked(
        tmp_path,
        {"src/evidrun/shared/types.py": "value = 1\n"},
        message="only commit",
    )

    document = report_of(tmp_path, base_ref="refs/heads/does-not-exist")

    drift: dict[str, object] = document["drift"]  # type: ignore[assignment]
    assert drift["computed"] is False
    assert drift["new_edges"] == []
    assert "cannot resolve a merge-base" in str(drift["reason"])


def test_no_finding_makes_the_report_exit_non_zero(tmp_path: Path) -> None:
    """The first phase must inform: a cycle, a forbidden edge and drift all coexist."""
    base = commit_tracked(
        tmp_path,
        {"src/evidrun/shared/types.py": "value = 1\n"},
        message="baseline",
    )
    commit_tracked(
        tmp_path,
        {
            "src/evidrun/runs/alpha.py": "from evidrun.runs import beta\n",
            "src/evidrun/runs/beta.py": "from evidrun.runs import alpha\n",
            "src/evidrun/contracts/bad.py": "from evidrun.infrastructure import database\n",
            "src/evidrun/infrastructure/database.py": "value = 1\n",
        },
        message="everything at once",
    )

    result = run_reporter(tmp_path, base_ref=base)
    document: dict[str, object] = json.loads(result.stdout)

    assert result.returncode == 0
    assert document["blocking"] is False
    assert findings_with(document, "dependency.module_cycle") != []
    assert document["forbidden_edges"] != []


def test_a_reexport_hub_counts_the_forwarded_surface_not_the_traffic(tmp_path: Path) -> None:
    exported = ", ".join(f"name_{index}" for index in range(20))
    definitions = "\n".join(f"name_{index} = {index}" for index in range(20))
    commit_tracked(
        tmp_path,
        {
            "src/evidrun/wide/__init__.py": f"from evidrun.wide.impl import {exported}\n",
            "src/evidrun/wide/impl.py": f"{definitions}\n",
            "src/evidrun/consumer.py": "from evidrun.wide import name_0\n",
        },
        message="hub",
    )

    hubs = findings_with(report_of(tmp_path), "dependency.reexport_hub")

    assert [finding["subjects"] for finding in hubs] == [["evidrun.wide"]]
    metrics: dict[str, int] = hubs[0]["metrics"]  # type: ignore[assignment]
    assert metrics["reexports"] == 20


def test_a_narrow_package_init_is_not_reported_as_a_hub(tmp_path: Path) -> None:
    commit_tracked(
        tmp_path,
        {
            "src/evidrun/narrow/__init__.py": "from evidrun.narrow.impl import only\n",
            "src/evidrun/narrow/impl.py": "only = 1\n",
        },
        message="narrow",
    )

    assert findings_with(report_of(tmp_path), "dependency.reexport_hub") == []


def test_external_packages_are_grouped_by_the_importing_slice(tmp_path: Path) -> None:
    commit_tracked(
        tmp_path,
        {
            "src/evidrun/entrypoints/api.py": "import fastapi\nimport json\n",
            "apps/web/src/main.tsx": "import React from 'react';\n",
        },
        message="externals",
    )

    externals = report_of(tmp_path)["external_dependencies"]

    assert externals == [
        {"slice": "evidrun.entrypoints", "package": "fastapi", "runtime": "python", "edges": 1},
        {"slice": "web/renderer", "package": "react", "runtime": "node", "edges": 1},
    ]


def test_a_json_out_path_receives_the_same_document_as_stdout(tmp_path: Path) -> None:
    commit_tracked(
        tmp_path,
        {"src/evidrun/shared/types.py": "value = 1\n"},
        message="artifact",
    )
    artifact = tmp_path / "reports" / "dependency-report.json"

    result = run_reporter(
        tmp_path,
        output_format="json",
        extra=("--json-out", str(artifact)),
    )

    assert result.returncode == 0
    assert artifact.read_text(encoding="utf-8") == result.stdout


def test_an_unparseable_source_is_a_config_error_not_a_finding(tmp_path: Path) -> None:
    commit_tracked(
        tmp_path,
        {"src/evidrun/broken.py": "def (\n"},
        message="broken",
    )

    result = run_reporter(tmp_path)

    assert result.returncode == 2
    assert "CONFIG ERROR" in result.stderr
