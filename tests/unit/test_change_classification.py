from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from change_contract import (  # noqa: E402
    ContractError,
    check_contract,
    inspect_repository,
    load_contract,
)
from change_contract.repository_diff import detect_repository_contract_diffs  # noqa: E402
from change_contract.schema_diff import Compatibility, ContractSurface  # noqa: E402


def git(root: Path, *args: str) -> str:
    result = subprocess.run(("git", *args), cwd=root, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def write(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def commit_all(root: Path, message: str) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-qm", message)


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "fixture@example.invalid")
    git(tmp_path, "config", "user.name", "Fixture")
    write(
        tmp_path,
        "schemas/generated/contracts/example.json",
        '{"type":"object","properties":{"id":{"type":"string"}},"required":["id"]}\n',
    )
    write(
        tmp_path,
        "src/evidrun/contracts/runtime/events.py",
        "class EventPayload(BaseModel):\n    event_id: str\n",
    )
    write(
        tmp_path,
        "src/evidrun/entrypoints/cli/app.py",
        '@app.command("inspect")\ndef inspect(run: str) -> None:\n    pass\n',
    )
    write(
        tmp_path,
        "src/evidrun/contracts/__init__.py",
        'from .events import EventPayload\n__all__ = ["EventPayload"]\n',
    )
    write(
        tmp_path,
        "src/evidrun/infrastructure/database/models.py",
        "class RunRow(Base):\n    id: Mapped[str] = mapped_column(nullable=False)\n",
    )
    write(tmp_path, "tests/compat/test_old_bundle.py", "def test_old_bundle():\n    pass\n")
    write(
        tmp_path,
        "src/evidrun/public.py",
        'from .contracts import EventPayload\n__all__ = ["EventPayload"]\n',
    )
    commit_all(tmp_path, "baseline")
    git(tmp_path, "switch", "-qc", "feat/issue-53-fixture")
    return tmp_path


def contract_text(
    *,
    classification: str,
    persisted: str,
    normative: str = "none",
    breaking: str = "",
    focused_test: str = "uv run pytest tests/compat/test_old_bundle.py",
) -> str:
    return f'''
schema_version = "1"
change_id = "GH-53"
issue = 53
title = "Fixture"
classification = "{classification}"
base_ref = "main"
branch_pattern = "feat/issue-53-*"
expected_outcome = "Diff contratual verificavel."
confirmed_facts = ["Baseline criada."]
stop_conditions = ["Comparacao incerta."]

[impact]
capability = "none"
persisted_contract = "{persisted}"
normative = "{normative}"
notes = []

[scope]
expected = ["schemas/**", "changes/**"]
forbidden = []
preexisting = []

[preserve]
interfaces = []
errors = []
invariants = ["Falha fechada."]

[verification]
focused = ["{focused_test}"]
full_gates = ["uv run pytest"]
{breaking}
'''


def breaking_text(
    *,
    successors: str = "[]",
    previous_test: str = "uv run pytest tests/compat/test_old_bundle.py",
) -> str:
    return f"""
[breaking]
justification = "Remocao necessaria e explicitamente aprovada."
strategy = "expand-contract"
versioning = "Bundle v5 preserva leitura de v4 durante a migracao."
adr_successors = {successors}
previous_artifact_tests = ["{previous_test}"]
"""


def test_breaking_requires_complete_migration_and_previous_artifact_test(
    repository: Path,
) -> None:
    path = repository / "changes/53.toml"
    write(
        repository,
        "changes/53.toml",
        contract_text(classification="breaking", persisted="breaking"),
    )
    with pytest.raises(ContractError, match=r"\[breaking\] e obrigatorio"):
        load_contract(path)

    write(
        repository,
        "changes/53.toml",
        contract_text(
            classification="breaking",
            persisted="breaking",
            breaking=breaking_text(),
        ),
    )
    contract = load_contract(path)
    assert contract.breaking_plan is not None
    assert contract.breaking_plan.strategy.value == "expand-contract"


def test_normative_breaking_requires_an_adr_successor(repository: Path) -> None:
    path = repository / "changes/53.toml"
    write(
        repository,
        "changes/53.toml",
        contract_text(
            classification="breaking",
            persisted="breaking",
            normative="breaking",
            breaking=breaking_text(),
        ),
    )
    with pytest.raises(ContractError, match="adr_successors e obrigatorio"):
        load_contract(path)

    write(
        repository,
        "changes/53.toml",
        contract_text(
            classification="breaking",
            persisted="breaking",
            normative="breaking",
            breaking=breaking_text(successors='["docs/adr/0099-successor.md"]'),
        ),
    )
    assert load_contract(path).breaking_plan is not None


def test_feature_with_removed_schema_fails_closed_and_reports_the_diff(
    repository: Path,
) -> None:
    write(
        repository,
        "changes/53.toml",
        contract_text(classification="feature", persisted="changed"),
    )
    write(
        repository,
        "schemas/generated/contracts/example.json",
        '{"type":"object","properties":{},"required":[]}\n',
    )
    git(repository, "add", "changes/53.toml", "schemas")

    report = check_contract(
        load_contract(repository / "changes/53.toml"),
        inspect_repository(repository, "main"),
    )

    assert "classification.breaking_mismatch" in {item.code for item in report.blockers}
    assert "impact.persisted_breaking_mismatch" in {item.code for item in report.blockers}
    assert report.contract_diffs[0].changes[0].kind == "property-removed"
    assert report.as_dict()["contract_diffs"][0]["changes"][0]["pointer"] == "/properties/id"


def test_declared_breaking_schema_with_plan_is_consistent(repository: Path) -> None:
    write(
        repository,
        "changes/53.toml",
        contract_text(
            classification="breaking",
            persisted="breaking",
            breaking=breaking_text(),
        ),
    )
    write(
        repository,
        "schemas/generated/contracts/example.json",
        '{"type":"object","properties":{},"required":[]}\n',
    )
    git(repository, "add", "changes/53.toml", "schemas")

    report = check_contract(
        load_contract(repository / "changes/53.toml"),
        inspect_repository(repository, "main"),
    )

    codes = {item.code for item in report.blockers}
    assert "classification.breaking_mismatch" not in codes
    assert "impact.persisted_breaking_mismatch" not in codes


def test_breaking_evidence_must_exist_in_candidate(repository: Path) -> None:
    missing_test = "uv run pytest tests/compat/test_missing_bundle.py"
    write(
        repository,
        "changes/53.toml",
        contract_text(
            classification="breaking",
            persisted="breaking",
            normative="breaking",
            focused_test=missing_test,
            breaking=breaking_text(
                successors='["docs/adr/0099-missing.md"]',
                previous_test=missing_test,
            ),
        ),
    )
    git(repository, "add", "changes/53.toml")

    report = check_contract(
        load_contract(repository / "changes/53.toml"),
        inspect_repository(repository, "main"),
    )

    assert {
        "breaking.adr_successor_missing",
        "breaking.previous_artifact_test_missing",
    }.issubset({item.code for item in report.blockers})


def test_docs_only_cannot_modify_another_change_contract(repository: Path) -> None:
    write(
        repository,
        "changes/53.toml",
        contract_text(classification="docs-only", persisted="none"),
    )
    write(repository, "changes/52.toml", "# historical contract\n")
    git(repository, "add", "changes")

    report = check_contract(
        load_contract(repository / "changes/53.toml"),
        inspect_repository(repository, "main"),
    )

    blocker = next(
        item for item in report.blockers if item.code == "classification.docs_only_code"
    )
    assert blocker.paths == ("changes/52.toml",)


def test_repository_routes_event_model_cli_and_export_surfaces(repository: Path) -> None:
    write(
        repository,
        "src/evidrun/contracts/runtime/events.py",
        "class EventPayload(BaseModel):\n    event_id: int\n",
    )
    write(
        repository,
        "src/evidrun/entrypoints/cli/app.py",
        '@app.command("inspect")\ndef inspect(run_id: str) -> None:\n    pass\n',
    )
    write(repository, "src/evidrun/contracts/__init__.py", "__all__: list[str] = []\n")
    write(
        repository,
        "src/evidrun/infrastructure/database/models.py",
        (
            "class RunRow(Base):\n"
            "    id: Mapped[str] = mapped_column(nullable=False)\n"
            "    tenant: Mapped[str] = mapped_column(nullable=False)\n"
        ),
    )
    git(repository, "add", "src")

    reports = detect_repository_contract_diffs(inspect_repository(repository, "main"))

    assert {report.surface for report in reports} == {
        ContractSurface.CLI,
        ContractSurface.EVENT,
        ContractSurface.EXPORT,
        ContractSurface.PERSISTED_MODEL,
    }


def test_repository_routes_explicit_exports_outside_init_modules(repository: Path) -> None:
    write(
        repository,
        "src/evidrun/public.py",
        'from .contracts import OtherPayload\n__all__ = ["OtherPayload"]\n',
    )
    git(repository, "add", "src/evidrun/public.py")

    reports = detect_repository_contract_diffs(inspect_repository(repository, "main"))

    export = next(report for report in reports if report.path == "src/evidrun/public.py")
    assert export.surface is ContractSurface.EXPORT
    assert [(item.kind, item.pointer) for item in export.changes] == [
        ("export-removed", "/symbols/EventPayload"),
        ("export-added", "/symbols/OtherPayload"),
    ]

    write(repository, "src/evidrun/public.py", "from .contracts import OtherPayload\n")
    git(repository, "add", "src/evidrun/public.py")
    transition = detect_repository_contract_diffs(inspect_repository(repository, "main"))
    export = next(report for report in transition if report.path == "src/evidrun/public.py")
    assert [(item.kind, item.compatibility) for item in export.changes] == [
        ("explicit-exports-changed", Compatibility.BREAKING)
    ]
