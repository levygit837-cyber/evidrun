from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]

# `scripts/` não é pacote instalado: a CLI ganha esse diretório em `sys.path[0]` por
# ser executada como arquivo, e o teste, que roda de outra raiz, precisa colocá-lo lá.
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import check_code_budget  # noqa: E402
import code_budget as budget  # noqa: E402

POLICY = """
[[groups]]
name = "exempt"
exempt = true
patterns = ["apps/web/src/generated/**", "**/*.lock"]

[[groups]]
name = "tests"
patterns = ["tests/**/*.py"]
max_file_lines = 800

[[groups]]
name = "source"
patterns = ["src/**/*.py", "apps/**/*.tsx"]
max_file_lines = 500
max_function_lines = 120
max_public_methods = 25

[baseline]
"""


def run_check(root: Path, baseline: Mapping[str, Mapping[str, int]] | None = None) -> list[Any]:
    """Findings de violação, que é o que decide o gate."""

    return budget.violations(_findings(root, baseline))


def run_warnings(root: Path) -> list[Any]:
    return budget.warnings(_findings(root))


def _findings(root: Path, baseline: Mapping[str, Mapping[str, int]] | None = None) -> list[Any]:
    config = root / "code-budget.toml"
    if baseline is not None:
        config.write_text(
            budget.render_baseline(config.read_text(encoding="utf-8"), baseline), encoding="utf-8"
        )
    policy = budget.load_policy(config)
    tracked = sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file())
    measurements = budget.measure_all(root, policy, tracked)
    return budget.check(policy, measurements)


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "code-budget.toml").write_text(POLICY, encoding="utf-8")
    return tmp_path


@pytest.fixture
def git_workspace(workspace: Path) -> Path:
    """Workspace com repo git de verdade: o gate mede via `git ls-files`."""

    for command in (("git", "init", "-q"), ("git", "config", "commit.gpgsign", "false")):
        subprocess.run(command, cwd=workspace, check=True, capture_output=True)
    return workspace


def track(root: Path) -> None:
    subprocess.run(("git", "add", "-A"), cwd=root, check=True, capture_output=True)


def run_cli(root: Path) -> dict[str, Any]:
    """Roda `main` como o CI roda, e devolve o JSON mais o exit code observado."""

    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        exit_code = check_code_budget.main(
            ["--root", str(root), "--config", str(root / "code-budget.toml"), "--json"]
        )
    return {"exit_code": exit_code, **json.loads(stream.getvalue())}



def write_file(root: Path, relative: str, body: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def python_module(lines: int) -> str:
    return "".join(f"VALUE_{index} = {index}\n" for index in range(lines))


def python_function(body_lines: int) -> str:
    body = "".join(f"    step_{index} = {index}\n" for index in range(body_lines))
    return f"def work() -> None:\n{body}"


def python_class(public: int, private: int = 0) -> str:
    methods = "".join(f"    def action_{index}(self) -> None: ...\n" for index in range(public))
    methods += "".join(f"    def _hidden_{index}(self) -> None: ...\n" for index in range(private))
    return f"class Service:\n{methods}"


def test_file_within_budget_passes(workspace: Path) -> None:
    write_file(workspace, "src/evidrun/small.py", python_module(120))
    assert run_check(workspace) == []


def test_file_above_budget_fails(workspace: Path) -> None:
    write_file(workspace, "src/evidrun/big.py", python_module(501))
    (violation,) = run_check(workspace)
    assert violation.path == "src/evidrun/big.py"
    assert violation.metric == "file_lines"
    assert violation.measured == 501
    assert violation.limit == 500
    assert violation.kind == "budget"


def test_baseline_entry_at_recorded_value_passes(workspace: Path) -> None:
    write_file(workspace, "src/evidrun/big.py", python_module(700))
    baseline = {"src/evidrun/big.py": {"file_lines": 700}}
    assert run_check(workspace, baseline) == []


def test_baseline_entry_that_grew_fails(workspace: Path) -> None:
    write_file(workspace, "src/evidrun/big.py", python_module(701))
    baseline = {"src/evidrun/big.py": {"file_lines": 700}}
    (violation,) = run_check(workspace, baseline)
    assert violation.kind == "baseline_growth"
    assert violation.measured == 701
    assert violation.limit == 700
    assert "cresceu" in violation.message


def test_baseline_entry_that_shrank_below_budget_demands_removal(workspace: Path) -> None:
    write_file(workspace, "src/evidrun/big.py", python_module(400))
    baseline = {"src/evidrun/big.py": {"file_lines": 700}}
    (violation,) = run_check(workspace, baseline)
    assert violation.kind == "baseline_slack"
    assert violation.measured == 400
    assert violation.limit == 500
    assert "remova a entrada de baseline" in violation.message


def test_baseline_entry_shrinking_inside_baseline_still_passes(workspace: Path) -> None:
    write_file(workspace, "src/evidrun/big.py", python_module(600))
    baseline = {"src/evidrun/big.py": {"file_lines": 700}}
    assert run_check(workspace, baseline) == []


def test_exempt_glob_never_fails(workspace: Path) -> None:
    write_file(workspace, "apps/web/src/generated/contracts.tsx", "x\n" * 4000)
    write_file(workspace, "pnpm-lock.lock", "y\n" * 9000)
    assert run_check(workspace) == []


def test_long_function_in_short_file_fails(workspace: Path) -> None:
    write_file(workspace, "src/evidrun/hot.py", python_function(130))
    (violation,) = run_check(workspace)
    assert violation.metric == "function_lines"
    assert violation.measured == 131
    assert violation.limit == 120
    assert violation.kind == "budget"


def test_tests_group_has_no_function_or_method_limits(workspace: Path) -> None:
    write_file(workspace, "tests/unit/test_long.py", python_function(400))
    assert run_check(workspace) == []


def test_tests_group_file_budget_is_enforced(workspace: Path) -> None:
    write_file(workspace, "tests/unit/test_huge.py", python_module(801))
    (violation,) = run_check(workspace)
    assert violation.metric == "file_lines"
    assert violation.limit == 800


def test_public_methods_ignores_private_members(workspace: Path) -> None:
    write_file(workspace, "src/evidrun/wide.py", python_class(public=25, private=40))
    assert run_check(workspace) == []
    write_file(workspace, "src/evidrun/wide.py", python_class(public=26))
    (violation,) = run_check(workspace)
    assert violation.metric == "public_methods"
    assert violation.measured == 26
    assert violation.limit == 25


def test_stale_baseline_entry_for_missing_file_fails(workspace: Path) -> None:
    write_file(workspace, "src/evidrun/small.py", python_module(10))
    baseline = {"src/evidrun/gone.py": {"file_lines": 900}}
    (violation,) = run_check(workspace, baseline)
    assert violation.kind == "stale_baseline"
    assert violation.path == "src/evidrun/gone.py"


def test_typescript_files_are_measured_by_lines_only(workspace: Path) -> None:
    write_file(workspace, "apps/web/src/Page.tsx", "const x = 1;\n" * 501)
    (violation,) = run_check(workspace)
    assert violation.metric == "file_lines"
    measurement = budget.measure_file(workspace, "apps/web/src/Page.tsx")
    assert "function_lines" not in measurement.metrics
    assert "public_methods" not in measurement.metrics


def test_longest_function_reports_nested_method_name(workspace: Path) -> None:
    write_file(
        workspace,
        "src/evidrun/nested.py",
        "class Outer:\n    def method(self) -> None:\n" + "        x = 1\n" * 200,
    )
    measurement = budget.measure_file(workspace, "src/evidrun/nested.py")
    assert measurement.details["function_lines"] == "Outer.method"


def test_compute_baseline_records_only_overflowing_metrics(workspace: Path) -> None:
    write_file(workspace, "src/evidrun/big.py", python_module(600))
    write_file(workspace, "src/evidrun/small.py", python_module(10))
    policy = budget.load_policy(workspace / "code-budget.toml")
    measurements = [
        budget.measure_file(workspace, "src/evidrun/big.py"),
        budget.measure_file(workspace, "src/evidrun/small.py"),
    ]
    assert budget.compute_baseline(policy, measurements) == {
        "src/evidrun/big.py": {"file_lines": 600}
    }


def test_render_baseline_round_trips_through_load_policy(workspace: Path) -> None:
    config = workspace / "code-budget.toml"
    baseline = {
        "src/evidrun/b.py": {"file_lines": 900, "function_lines": 200},
        "src/evidrun/a.py": {"public_methods": 40},
    }
    config.write_text(
        budget.render_baseline(config.read_text(encoding="utf-8"), baseline), encoding="utf-8"
    )
    reloaded = budget.load_policy(config)
    assert reloaded.baseline == baseline
    assert [group.name for group in reloaded.groups] == ["exempt", "tests", "source"]


def test_render_baseline_keeps_groups_when_the_header_is_mentioned_in_prose() -> None:
    """O `[baseline]` citado em comentário não é o início do bloco.

    O `code-budget.toml` do repositório documenta o ratchet no cabeçalho, então o corte
    tem de ser por linha inteira: por substring, regravar o baseline apagaria os grupos.
    """

    original = (ROOT / "code-budget.toml").read_text(encoding="utf-8")
    assert "[baseline]" in original.split("[[groups]]")[0], "cabeçalho perdeu a menção em prosa"
    rendered = budget.render_baseline(original, {"src/evidrun/a.py": {"file_lines": 900}})
    assert rendered.count("[[groups]]") == original.count("[[groups]]")
    assert rendered.count("[baseline]") == original.count("[baseline]")


def test_render_baseline_without_the_bare_header_is_rejected() -> None:
    """Sem a linha nua não há onde cortar, e anexar um segundo bloco gera TOML inválido."""

    with pytest.raises(ValueError, match="não encontrada"):
        budget.render_baseline(
            '[baseline."src/evidrun/x.py"]\nfile_lines = 900\n',
            {"src/evidrun/x.py": {"file_lines": 900}},
        )


def test_unparseable_python_is_reported_as_violation(workspace: Path) -> None:
    write_file(workspace, "src/evidrun/broken.py", "def oops(:\n")
    (violation,) = run_check(workspace)
    assert violation.kind == "syntax"


def test_unknown_baseline_metric_is_rejected(workspace: Path) -> None:
    config = workspace / "code-budget.toml"
    config.write_text(
        POLICY + '\n[baseline."src/evidrun/a.py"]\nmax_lines = 10\n', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="métrica desconhecida"):
        budget.load_policy(config)


def test_file_near_budget_warns_without_failing(workspace: Path) -> None:
    write_file(workspace, "src/evidrun/close.py", python_module(460))
    assert run_check(workspace) == []
    (warning,) = run_warnings(workspace)
    assert warning.kind == "headroom"
    assert warning.severity == "warning"
    assert warning.measured == 460
    assert warning.limit == 500
    assert "40 de folga" in warning.message


def test_file_exactly_at_the_warn_threshold_stays_silent(workspace: Path) -> None:
    """400 = int(500 * 0.8). O limiar em si não avisa; a linha seguinte avisa."""

    write_file(workspace, "src/evidrun/small.py", python_module(400))
    assert run_warnings(workspace) == []
    write_file(workspace, "src/evidrun/small.py", python_module(401))
    assert [finding.measured for finding in run_warnings(workspace)] == [401]


def test_file_exactly_at_the_budget_warns_with_no_slack(workspace: Path) -> None:
    """O último valor que cabe é aviso, não violação, e anuncia folga zero."""

    write_file(workspace, "src/evidrun/edge.py", python_module(500))
    assert run_check(workspace) == []
    (warning,) = run_warnings(workspace)
    assert warning.measured == 500
    assert "0 de folga" in warning.message


def test_first_line_over_the_budget_is_a_violation_and_not_a_warning(workspace: Path) -> None:
    write_file(workspace, "src/evidrun/big.py", python_module(501))
    (violation,) = run_check(workspace)
    assert violation.kind == "budget"
    assert violation.severity == "violation"
    assert run_warnings(workspace) == []


def test_headroom_kind_is_always_a_warning() -> None:
    """`severity` é derivada de `kind`: não há como declarar um `headroom` que falhe."""

    finding = budget.Finding(
        path="src/evidrun/a.py",
        metric="file_lines",
        measured=460,
        limit=500,
        kind="headroom",
        message="",
    )
    assert finding.severity == "warning"
    assert budget.violations([finding]) == []
    assert finding.as_dict()["severity"] == "warning"


def test_baseline_file_is_not_warned_about(workspace: Path) -> None:
    write_file(workspace, "src/evidrun/big.py", python_module(700))
    assert budget.warnings(_findings(workspace, {"src/evidrun/big.py": {"file_lines": 700}})) == []


def test_group_can_set_its_own_warn_ratio(workspace: Path) -> None:
    config = workspace / "code-budget.toml"
    config.write_text(POLICY.replace('name = "source"', 'name = "source"\nwarn_at_ratio = 0.5'))
    write_file(workspace, "src/evidrun/half.py", python_module(260))
    assert [finding.measured for finding in run_warnings(workspace)] == [260]


def test_warn_ratio_outside_the_open_unit_interval_is_rejected(workspace: Path) -> None:
    config = workspace / "code-budget.toml"
    config.write_text(POLICY.replace('name = "source"', 'name = "source"\nwarn_at_ratio = 1.0'))
    with pytest.raises(ValueError, match="entre 0 e 1"):
        budget.load_policy(config)


def test_warning_alone_keeps_the_exit_code_green(git_workspace: Path) -> None:
    """O contrato do ticket é o exit code, e só `main` decide isso."""

    write_file(git_workspace, "src/evidrun/close.py", python_module(460))
    track(git_workspace)
    report = run_cli(git_workspace)
    assert report["exit_code"] == 0
    assert report["ok"] is True
    assert [item["measured"] for item in report["warnings"]] == [460]
    assert report["violations"] == []


def test_violation_still_fails_even_when_warnings_exist(git_workspace: Path) -> None:
    write_file(git_workspace, "src/evidrun/close.py", python_module(460))
    write_file(git_workspace, "src/evidrun/big.py", python_module(501))
    track(git_workspace)
    report = run_cli(git_workspace)
    assert report["exit_code"] == 1
    assert report["ok"] is False
    assert [item["path"] for item in report["violations"]] == ["src/evidrun/big.py"]


def test_untracked_file_is_measured_by_neither_level(git_workspace: Path) -> None:
    """A medição parte de `git ls-files`: fora do índice, não há aviso nem violação."""

    write_file(git_workspace, "src/evidrun/big.py", python_module(900))
    report = run_cli(git_workspace)
    assert report["exit_code"] == 0
    assert report["checked_files"] == 0
    track(git_workspace)
    assert run_cli(git_workspace)["exit_code"] == 1



def test_repository_policy_and_baseline_hold_together() -> None:
    policy = budget.load_policy(ROOT / "code-budget.toml")
    assert {group.name for group in policy.groups} == {"exempt", "tests", "source"}
    for path, entry in policy.baseline.items():
        assert entry, f"{path} tem entrada de baseline vazia"
        group = policy.group_for(path)
        assert group is not None and not group.exempt
        for metric, value in entry.items():
            limit = group.limits.get(metric)
            assert limit is not None, f"{path}: {metric} não tem orçamento no grupo {group.name}"
            assert value > limit, f"{path}: {metric} no baseline já cabe no orçamento"
