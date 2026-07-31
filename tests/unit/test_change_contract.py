from __future__ import annotations

import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import check_change_contract  # noqa: E402
from change_contract import (  # noqa: E402
    ContractError,
    check_contract,
    inspect_repository,
    load_contract,
)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ("git", *args), cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def commit_all(root: Path, message: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-qm", message)
    return git(root, "rev-parse", "HEAD")


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    git(tmp_path, "config", "user.name", "Fixture")
    git(tmp_path, "config", "commit.gpgsign", "false")
    write(tmp_path, "src/base.py", "BASE = 1\n")
    commit_all(tmp_path, "base")
    git(tmp_path, "switch", "-qc", "feat/issue-123-contract")
    return tmp_path


def contract_text(
    *,
    classification: str = "feature",
    expected: tuple[str, ...] = ("src/task/**", "tests/**"),
    forbidden: tuple[str, ...] = ("src/forbidden/**",),
    preexisting: tuple[str, ...] = (),
    capability: str = "none",
    persisted: str = "none",
    normative: str = "none",
    question: str = "",
    oracle: str = "",
    generated: str = "",
) -> str:
    return f'''
schema_version = "1"
change_id = "GH-123"
issue = 123
title = "Fixture"
classification = "{classification}"
base_ref = "main"
branch_pattern = "feat/issue-123-*"
expected_outcome = "Resultado observavel da fixture."
confirmed_facts = ["Base confirmada."]
stop_conditions = ["Mudanca normativa nao planejada."]

[impact]
capability = "{capability}"
persisted_contract = "{persisted}"
normative = "{normative}"
notes = []

[scope]
expected = {json.dumps(expected)}
forbidden = {json.dumps(forbidden)}
preexisting = {json.dumps(preexisting)}
{generated}

[preserve]
interfaces = []
errors = []
invariants = ["Falha fechada permanece."]

[verification]
focused = ["uv run pytest tests/unit/test_fixture.py"]
full_gates = ["uv run pytest"]
{question}
{oracle}
'''


def load_fixture(root: Path, body: str) -> object:
    path = root / "changes/123.toml"
    write(root, "changes/123.toml", body)
    return load_contract(path)


@pytest.mark.parametrize(
    "classification",
    [
        "behavior-compatible",
        "feature",
        "breaking",
        "docs-only",
        "generated",
    ],
)
def test_contract_supports_development_classifications(
    repository: Path, classification: str
) -> None:
    contract = load_fixture(repository, contract_text(classification=classification))
    assert contract.classification.value == classification


def test_refactor_requires_oracle_and_zero_semantic_impact(repository: Path) -> None:
    with pytest.raises(ContractError, match="refactor exige"):
        load_fixture(repository, contract_text(classification="refactor"))
    oracle = '''
[oracle]
kind = "equivalence"
command = "uv run pytest tests/unit/test_fixture.py"
evidence = ["tests/characterization.py"]
preserves = ["capability", "persisted-contract", "fail-closed"]
'''
    contract = load_fixture(
        repository, contract_text(classification="refactor", oracle=oracle)
    )
    assert contract.oracle is not None
    assert contract.oracle.kind == "equivalence"
    with pytest.raises(ContractError, match="impactos"):
        load_fixture(
            repository,
            contract_text(
                classification="refactor", capability="additive", oracle=oracle
            ),
        )

    incomplete = oracle.replace(
        '["capability", "persisted-contract", "fail-closed"]', '["capability"]'
    )
    with pytest.raises(ContractError, match=r"oracle\.preserves"):
        load_fixture(
            repository, contract_text(classification="refactor", oracle=incomplete)
        )
    command_not_focused = oracle.replace("tests/unit/test_fixture.py", "tests/other.py", 1)
    with pytest.raises(ContractError, match=r"verification\.focused"):
        load_fixture(
            repository,
            contract_text(classification="refactor", oracle=command_not_focused),
        )


def test_open_semantic_question_blocks_readiness(repository: Path) -> None:
    question = '''
[[questions]]
text = "Qual codigo observavel deve vencer?"
affects_semantics = true
status = "open"
'''
    contract = load_fixture(repository, contract_text(question=question))
    report = check_contract(contract, inspect_repository(repository, "main"))
    assert [item.code for item in report.blockers] == ["planning.semantic_question_open"]


def test_unplanned_path_warns_but_forbidden_path_blocks(repository: Path) -> None:
    contract = load_fixture(repository, contract_text())
    write(repository, "src/discovered/new.py", "VALUE = 1\n")
    git(repository, "add", "src/discovered/new.py")
    report = check_contract(contract, inspect_repository(repository, "main"))
    assert "scope.unplanned_path" in {item.code for item in report.warnings}
    assert not report.blockers
    write(repository, "src/forbidden/bad.py", "VALUE = 2\n")
    git(repository, "add", "src/forbidden/bad.py")
    blocked = check_contract(contract, inspect_repository(repository, "main"))
    assert "scope.forbidden_path" in {item.code for item in blocked.blockers}


def test_expansion_with_rationale_plans_discovered_path(repository: Path) -> None:
    expansion = '''
[[scope.expansions]]
patterns = ["src/discovered/**"]
rationale = "O adapter real vive nessa arvore."
'''
    body = contract_text().replace("\n[scope]\n", "\n[scope]\n").replace(
        "\n[preserve]\n", f"\n{expansion}\n[preserve]\n"
    )
    contract = load_fixture(repository, body)
    write(repository, "src/discovered/new.py", "VALUE = 1\n")
    git(repository, "add", "src/discovered/new.py")
    report = check_contract(contract, inspect_repository(repository, "main"))
    assert "scope.unplanned_path" not in {item.code for item in report.warnings}


def test_normative_and_persisted_changes_require_declared_impact(repository: Path) -> None:
    contract = load_fixture(
        repository,
        contract_text(expected=("docs/**", "schemas/**", "changes/**")),
    )
    write(
        repository,
        "docs/architecture/rule.md",
        "---\nauthority: normative\n---\n\nRegra.\n",
    )
    write(repository, "schemas/generated/api.json", "{}\n")
    git(repository, "add", "docs", "schemas")
    report = check_contract(contract, inspect_repository(repository, "main"))
    assert {item.code for item in report.blockers} == {
        "impact.normative_undeclared",
        "impact.persisted_contract_undeclared",
    }


def test_deleted_normative_document_is_detected_from_baseline(repository: Path) -> None:
    write(
        repository,
        "docs/security/deleted.md",
        "---\nauthority: normative\n---\n\nRegra anterior.\n",
    )
    commit_all(repository, "normative baseline")
    contract = load_fixture(repository, contract_text(expected=("docs/**",)))
    git(repository, "rm", "docs/security/deleted.md")
    report = check_contract(contract, inspect_repository(repository, "HEAD"))
    assert "impact.normative_undeclared" in {item.code for item in report.blockers}


def test_preexisting_never_bypasses_protected_path_rules(repository: Path) -> None:
    write(repository, "src/forbidden/user.py", "VALUE = 1\n")
    commit_all(repository, "preexisting protected file")
    contract = load_fixture(
        repository,
        contract_text(preexisting=("src/forbidden/user.py",)),
    )
    write(repository, "src/forbidden/user.py", "VALUE = 2\n")
    report = check_contract(contract, inspect_repository(repository, "main"))
    assert report.excluded_preexisting == ("src/forbidden/user.py",)
    assert "scope.forbidden_path" in {item.code for item in report.blockers}


def test_refactor_cannot_touch_persisted_contract_source(repository: Path) -> None:
    oracle = '''
[oracle]
kind = "characterization"
command = "uv run pytest tests/unit/test_fixture.py"
evidence = ["tests/unit/test_fixture.py"]
preserves = ["capability", "persisted-contract", "fail-closed"]
'''
    contract = load_fixture(
        repository,
        contract_text(
            classification="refactor",
            expected=("src/evidrun/contracts/**",),
            oracle=oracle,
        ),
    )
    write(repository, "src/evidrun/contracts/model.py", "VALUE = 1\n")
    git(repository, "add", "src/evidrun/contracts/model.py")
    report = check_contract(contract, inspect_repository(repository, "main"))
    assert "impact.persisted_contract_undeclared" in {
        item.code for item in report.blockers
    }


def test_generated_change_checks_declared_source(repository: Path) -> None:
    generated = '''
[[scope.generated]]
patterns = ["generated/**"]
source_patterns = ["source/**"]
'''
    contract = load_fixture(
        repository,
        contract_text(expected=("source/**", "changes/**"), generated=generated),
    )
    write(repository, "generated/output.json", "{}\n")
    git(repository, "add", "generated/output.json")
    missing = check_contract(contract, inspect_repository(repository, "main"))
    assert "generated.source_missing" in {item.code for item in missing.warnings}
    write(repository, "source/model.py", "MODEL = 1\n")
    git(repository, "add", "source/model.py")
    complete = check_contract(contract, inspect_repository(repository, "main"))
    assert "generated.source_missing" not in {item.code for item in complete.warnings}


def test_rename_and_deletion_are_observed_from_merge_base(repository: Path) -> None:
    write(repository, "src/task/old.py", "VALUE = 1\n")
    write(repository, "src/task/delete.py", "VALUE = 2\n")
    commit_all(repository, "tracked inputs")
    git(repository, "mv", "src/task/old.py", "src/task/new.py")
    git(repository, "rm", "src/task/delete.py")
    snapshot = inspect_repository(repository, "main")
    assert any(
        change.status == "R"
        and change.old_path == "src/task/old.py"
        and change.path == "src/task/new.py"
        for change in snapshot.changes
    )
    assert any(
        change.status == "D" and change.path == "src/task/delete.py"
        for change in snapshot.changes
    )
    contract = load_fixture(
        repository,
        contract_text(expected=("src/task/new.py", "src/task/delete.py")),
    )
    report = check_contract(contract, snapshot)
    unplanned = next(item for item in report.warnings if item.code == "scope.unplanned_path")
    assert unplanned.paths == ("src/task/old.py",)


def test_true_merge_base_excludes_changes_that_only_advanced_base(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    git(tmp_path, "config", "user.name", "Fixture")
    write(tmp_path, "base.txt", "base\n")
    common = commit_all(tmp_path, "common")
    git(tmp_path, "branch", "feature")
    write(tmp_path, "main-only.txt", "main\n")
    commit_all(tmp_path, "advance main")
    git(tmp_path, "switch", "-q", "feature")
    write(tmp_path, "feature-only.txt", "feature\n")
    commit_all(tmp_path, "feature")
    snapshot = inspect_repository(tmp_path, "main")
    assert snapshot.merge_base == common
    assert snapshot.changed_paths == ("feature-only.txt",)


def test_preexisting_and_untracked_are_not_counted_as_delivery(repository: Path) -> None:
    write(repository, "notes/user.txt", "before\n")
    write(repository, "src/task/owned.py", "before\n")
    commit_all(repository, "tracked files")
    contract = load_fixture(
        repository,
        contract_text(preexisting=("notes/user.txt",), expected=("src/task/**",)),
    )
    write(repository, "notes/user.txt", "user concurrent change\n")
    write(repository, "src/task/owned.py", "agent change\n")
    write(repository, "src/task/untracked.py", "not delivery\n")
    report = check_contract(contract, inspect_repository(repository, "main"))
    assert "notes/user.txt" not in report.delivery_paths
    assert report.excluded_preexisting == ("notes/user.txt",)
    assert "src/task/owned.py" in report.delivery_paths
    assert "src/task/untracked.py" not in report.delivery_paths
    assert "src/task/untracked.py" in report.untracked


def test_secret_blocker_never_contains_secret_value(repository: Path) -> None:
    contract = load_fixture(repository, contract_text(expected=("src/task/**",)))
    synthetic = "ghp_" + "A" * 30
    write(repository, "src/task/credential.py", f'TOKEN = "{synthetic}"\n')
    git(repository, "add", "src/task/credential.py")
    report = check_contract(contract, inspect_repository(repository, "main"))
    finding = next(item for item in report.blockers if item.code == "security.secret_detected")
    assert synthetic not in finding.message
    assert synthetic not in json.dumps(report.as_dict())


def test_cli_json_uses_exit_codes_for_warning_blocker_and_configuration(
    repository: Path,
) -> None:
    contract_path = repository / "changes/123.toml"
    write(repository, "changes/123.toml", contract_text())
    write(repository, "outside.txt", "warning\n")
    git(repository, "add", "changes/123.toml", "outside.txt")
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        warning_exit = check_change_contract.main(
            [
                "--root",
                str(repository),
                "--contract",
                str(contract_path),
                "--format",
                "json",
            ]
        )
    assert warning_exit == 0
    assert json.loads(stream.getvalue())["summary"]["warnings"] >= 1
    assert check_change_contract.main(
        ["--root", str(repository), "--contract", str(contract_path), "--strict-warnings"]
    ) == 1
    write(repository, "changes/bad.toml", "not = [valid")
    assert check_change_contract.main(
        ["--root", str(repository), "--contract", "changes/bad.toml"]
    ) == 2
    write(repository, "secret-scan.toml", 'schema_version = "unknown"\n')
    assert check_change_contract.main(
        ["--root", str(repository), "--contract", str(contract_path)]
    ) == 2


def test_cli_discovers_the_single_contract_in_delivery(repository: Path) -> None:
    write(repository, "changes/123.toml", contract_text(expected=("src/task/**",)))
    write(repository, "src/task/owned.py", "VALUE = 1\n")
    git(repository, "add", "changes/123.toml", "src/task/owned.py")
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        exit_code = check_change_contract.main(
            [
                "--root",
                str(repository),
                "--discover",
                "--base-ref",
                "main",
                "--format",
                "json",
            ]
        )
    payload = json.loads(stream.getvalue())
    assert exit_code == 0
    assert payload["contract"]["change_id"] == "GH-123"
    assert payload["summary"]["blockers"] == 0


def test_cli_missing_contract_warns_without_blocking_discovery(repository: Path) -> None:
    write(repository, "src/task/owned.py", "VALUE = 1\n")
    git(repository, "add", "src/task/owned.py")
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        exit_code = check_change_contract.main(
            [
                "--root",
                str(repository),
                "--discover",
                "--base-ref",
                "main",
                "--format",
                "json",
            ]
        )
    payload = json.loads(stream.getvalue())
    assert exit_code == 0
    assert payload["contract"] is None
    assert [item["code"] for item in payload["diagnostics"]] == [
        "planning.contract_missing"
    ]
