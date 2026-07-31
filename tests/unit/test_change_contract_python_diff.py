from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from change_contract.migration_diff import compare_migration_surface  # noqa: E402
from change_contract.python_diff import compare_python_surface  # noqa: E402
from change_contract.schema_diff import (  # noqa: E402
    Compatibility,
    ContractSurface,
    SchemaDiffError,
)


def test_event_description_and_message_body_are_not_contract_changes() -> None:
    baseline = """
class FailurePayload(BaseModel):
    code: str
    message: str = Field(description="Old wording")

def render() -> str:
    return "Old runtime message"
"""
    candidate = baseline.replace("Old wording", "Translated wording").replace(
        "Old runtime message", "Translated runtime message"
    )

    report = compare_python_surface(
        baseline,
        candidate,
        path="src/evidrun/contracts/runtime/events.py",
        surface=ContractSurface.EVENT,
    )

    assert report.changes == ()


def test_event_required_field_and_type_change_are_breaking() -> None:
    baseline = """
class EventPayload(BaseModel):
    event_id: str
"""
    candidate = """
class EventPayload(BaseModel):
    event_id: int
    correlation_id: str
    note: str | None = None
"""

    report = compare_python_surface(
        baseline,
        candidate,
        path="src/evidrun/contracts/runtime/events.py",
        surface=ContractSurface.EVENT,
    )

    assert [(item.kind, item.compatibility, item.pointer) for item in report.changes] == [
        ("required-field-added", Compatibility.BREAKING, "/symbols/EventPayload.correlation_id"),
        ("field-added", Compatibility.ADDITIVE, "/symbols/EventPayload.note"),
        ("field-changed", Compatibility.BREAKING, "/symbols/EventPayload.event_id"),
    ]


def test_pydantic_field_constraints_do_not_make_a_required_field_optional() -> None:
    baseline = "class EventPayload(BaseModel):\n    event_id: str\n"
    candidate = (
        "class EventPayload(BaseModel):\n"
        "    event_id: str\n"
        "    count: int = Field(ge=0)\n"
        "    note: str = Field(default=\"\", max_length=20)\n"
    )

    report = compare_python_surface(
        baseline,
        candidate,
        path="src/evidrun/contracts/runtime/events.py",
        surface=ContractSurface.EVENT,
    )

    assert [(item.kind, item.compatibility) for item in report.changes] == [
        ("required-field-added", Compatibility.BREAKING),
        ("field-added", Compatibility.ADDITIVE),
    ]


def test_persisted_model_distinguishes_nullable_and_required_columns() -> None:
    baseline = """
class RunRow(Base):
    id: Mapped[str] = mapped_column(String, primary_key=True)
"""
    candidate = """
class RunRow(Base):
    id: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str | None] = mapped_column(String, nullable=True)
    tenant_id: Mapped[str] = mapped_column(String, nullable=False)
"""

    report = compare_python_surface(
        baseline,
        candidate,
        path="src/evidrun/infrastructure/database/models.py",
        surface=ContractSurface.PERSISTED_MODEL,
    )

    assert [(item.kind, item.compatibility) for item in report.changes] == [
        ("field-added", Compatibility.ADDITIVE),
        ("required-field-added", Compatibility.BREAKING),
    ]


def test_cli_help_is_ignored_but_flags_and_commands_are_contractual() -> None:
    baseline = """
@app.command("inspect")
def inspect(run_id: Annotated[str, typer.Option("--run", help="Old help")]) -> None:
    console.print("Old message")
"""
    wording_only = baseline.replace("Old help", "New help").replace("Old message", "New message")
    changed = """
@app.command("inspect")
def inspect(run_id: Annotated[str, typer.Option("--run-id", help="New help")]) -> None:
    console.print("New message")

@app.command("export")
def export() -> None:
    pass
"""

    assert (
        compare_python_surface(
            baseline,
            wording_only,
            path="src/evidrun/entrypoints/cli/app.py",
            surface=ContractSurface.CLI,
        ).changes
        == ()
    )
    report = compare_python_surface(
        baseline,
        changed,
        path="src/evidrun/entrypoints/cli/app.py",
        surface=ContractSurface.CLI,
    )
    assert [(item.kind, item.compatibility) for item in report.changes] == [
        ("command-added", Compatibility.ADDITIVE),
        ("command-changed", Compatibility.BREAKING),
    ]


def test_cli_keyword_command_name_is_contractual_and_dynamic_name_fails_closed() -> None:
    baseline = '@app.command(name="inspect")\ndef run() -> None:\n    pass\n'
    candidate = '@app.command(name="check")\ndef run() -> None:\n    pass\n'

    report = compare_python_surface(
        baseline,
        candidate,
        path="src/evidrun/entrypoints/cli/app.py",
        surface=ContractSurface.CLI,
    )

    assert [(item.kind, item.pointer) for item in report.changes] == [
        ("command-removed", "/symbols/inspect"),
        ("command-added", "/symbols/check"),
    ]
    with pytest.raises(SchemaDiffError, match="nome de comando Typer"):
        compare_python_surface(
            "@app.command(name=COMMAND_NAME)\ndef run():\n    pass\n",
            candidate,
            path="src/evidrun/entrypoints/cli/app.py",
            surface=ContractSurface.CLI,
        )


def test_explicit_exports_are_compared_without_import_order_noise() -> None:
    baseline = 'from .api import A, B\n__all__ = ["A", "B"]\n'
    reordered = 'from .api import B, A\n__all__ = ["B", "A"]\n'
    changed = 'from .api import A, C\n__all__ = ["A", "C"]\n'

    assert (
        compare_python_surface(
            baseline,
            reordered,
            path="src/evidrun/contracts/__init__.py",
            surface=ContractSurface.EXPORT,
        ).changes
        == ()
    )
    report = compare_python_surface(
        baseline,
        changed,
        path="src/evidrun/contracts/__init__.py",
        surface=ContractSurface.EXPORT,
    )
    assert [(item.kind, item.pointer) for item in report.changes] == [
        ("export-removed", "/symbols/B"),
        ("export-added", "/symbols/C"),
    ]


def test_dynamic_explicit_exports_fail_closed() -> None:
    with pytest.raises(SchemaDiffError, match="lista ou tupla literal"):
        compare_python_surface(
            "NAMES = [\"A\"]\n__all__ = NAMES\n",
            "NAMES = [\"B\"]\n__all__ = NAMES\n",
            path="src/evidrun/public.py",
            surface=ContractSurface.EXPORT,
        )


def test_augmented_or_reassigned_exports_fail_closed() -> None:
    baseline = '__all__ = ["A"]\n__all__ += ["B"]\n'
    candidate = '__all__ = ["A"]\n__all__ += ["C"]\n'

    with pytest.raises(SchemaDiffError, match="unica atribuicao literal"):
        compare_python_surface(
            baseline,
            candidate,
            path="src/evidrun/public.py",
            surface=ContractSurface.EXPORT,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        '__all__.append("B")',
        '__all__.extend(["B"])',
        '__all__[0] = "B"',
    ],
)
def test_mutated_exports_fail_closed(mutation: str) -> None:
    source = f'__all__ = ["A"]\n{mutation}\n'

    with pytest.raises(SchemaDiffError, match="unica atribuicao literal"):
        compare_python_surface(
            source,
            source,
            path="src/evidrun/public.py",
            surface=ContractSurface.EXPORT,
        )


def test_migration_reads_upgrade_and_distinguishes_add_from_drop() -> None:
    baseline = "def upgrade():\n    pass\n\ndef downgrade():\n    pass\n"
    additive = """
def upgrade():
    op.add_column("runs", sa.Column("label", sa.String(), nullable=True))

def downgrade():
    op.drop_column("runs", "label")
"""
    breaking = additive.replace(
        'op.add_column("runs", sa.Column("label", sa.String(), nullable=True))',
        'op.drop_column("runs", "legacy")',
    )

    additive_report = compare_migration_surface(baseline, additive, path="alembic/1.py")
    breaking_report = compare_migration_surface(baseline, breaking, path="alembic/1.py")

    assert additive_report.changes[0].compatibility is Compatibility.ADDITIVE
    assert breaking_report.changes[0].compatibility is Compatibility.BREAKING


def test_migration_required_column_and_restrictive_constraints_are_breaking() -> None:
    baseline = "def upgrade():\n    pass\n"
    candidate = """
def upgrade():
    op.add_column("runs", sa.Column("tenant", sa.String(), nullable=False))
    op.create_check_constraint("ck_runs", "runs", "length(tenant) > 0")
    op.create_foreign_key("fk_runs", "runs", "tenants", ["tenant"], ["id"])
    op.create_unique_constraint("uq_runs", "runs", ["tenant"])
    op.create_index("ix_runs_tenant", "runs", ["tenant"], unique=True)
    op.add_column("runs", sa.Column("sequence", sa.Integer(), primary_key=True))
"""

    report = compare_migration_surface(baseline, candidate, path="alembic/2.py")

    assert len(report.changes) == 6
    assert all(
        item.compatibility is Compatibility.BREAKING for item in report.changes
    )


def test_migration_batch_operations_are_detected() -> None:
    baseline = "def upgrade():\n    pass\n"
    candidate = """
def upgrade():
    with op.batch_alter_table("runs") as batch:
        batch.drop_column("legacy")
"""

    report = compare_migration_surface(baseline, candidate, path="alembic/3.py")

    assert [(item.kind, item.compatibility, item.pointer) for item in report.changes] == [
        (
            "migration-operation-added",
            Compatibility.BREAKING,
            "/upgrade/drop_column",
        )
    ]

    additive = """
def upgrade():
    with op.batch_alter_table("runs") as batch:
        batch.add_column(sa.Column("note", sa.String(), nullable=True))
"""
    additive_report = compare_migration_surface(baseline, additive, path="alembic/3.py")
    assert additive_report.changes[0].compatibility is Compatibility.ADDITIVE


@pytest.mark.parametrize(
    "column",
    [
        'sa.Column("tenant", sa.String(), nullable=IS_NULLABLE)',
        'sa.Column("tenant", sa.String(), primary_key=IS_PRIMARY)',
        'sa.Column("tenant", sa.String(), nullable=False, server_default=None)',
    ],
)
def test_migration_uncertain_column_arguments_fail_closed(column: str) -> None:
    baseline = "def upgrade():\n    pass\n"
    candidate = f'def upgrade():\n    op.add_column("runs", {column})\n'

    report = compare_migration_surface(baseline, candidate, path="alembic/4.py")

    assert report.changes[0].compatibility is Compatibility.BREAKING


def test_migration_required_column_with_literal_server_default_is_additive() -> None:
    baseline = "def upgrade():\n    pass\n"
    candidate = """
def upgrade():
    op.add_column(
        "runs",
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'queued'")),
    )
"""

    report = compare_migration_surface(baseline, candidate, path="alembic/5.py")

    assert report.changes[0].compatibility is Compatibility.ADDITIVE


@pytest.mark.parametrize(
    "default",
    [
        "sa.FetchedValue()",
        'sa.text("NULL")',
        'sa.text("coalesce(NULL, NULL)")',
    ],
)
def test_migration_non_materializing_server_defaults_are_breaking(default: str) -> None:
    baseline = "def upgrade():\n    pass\n"
    candidate = (
        "def upgrade():\n"
        '    op.add_column("runs", '
        f'sa.Column("status", sa.String(), nullable=False, server_default={default}))\n'
    )

    report = compare_migration_surface(baseline, candidate, path="alembic/6.py")

    assert report.changes[0].compatibility is Compatibility.BREAKING
