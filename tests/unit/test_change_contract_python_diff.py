from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from change_contract.python_diff import (  # noqa: E402
    compare_migration_surface,
    compare_python_surface,
)
from change_contract.schema_diff import Compatibility, ContractSurface  # noqa: E402


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
