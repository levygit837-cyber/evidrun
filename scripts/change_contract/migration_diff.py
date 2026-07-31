"""Semantic compatibility projection for Alembic upgrade operations."""

from __future__ import annotations

import ast
from dataclasses import dataclass

from .schema_diff import (
    Compatibility,
    ContractChange,
    ContractDiffReport,
    ContractSurface,
    SchemaDiffError,
)


@dataclass(frozen=True)
class _MigrationOperation:
    name: str
    call: ast.Call


def compare_migration_surface(
    baseline: str,
    candidate: str,
    *,
    path: str,
) -> ContractDiffReport:
    """Compare Alembic upgrade operations, including batch-alter aliases."""

    before = _migration_operations(baseline, path, "baseline")
    after = _migration_operations(candidate, path, "candidate")
    changes: list[ContractChange] = []
    for signature in sorted(before.keys() - after.keys()):
        operation = before[signature]
        changes.append(
            ContractChange(
                "migration-operation-removed",
                Compatibility.BREAKING,
                f"/upgrade/{operation.name}",
                f"A operacao de migration {operation.name!r} foi removida.",
            )
        )
    for signature in sorted(after.keys() - before.keys()):
        operation = after[signature]
        changes.append(
            ContractChange(
                "migration-operation-added",
                _operation_compatibility(operation),
                f"/upgrade/{operation.name}",
                f"A operacao de migration {operation.name!r} foi adicionada.",
            )
        )
    return ContractDiffReport(path, ContractSurface.PERSISTED_MODEL, tuple(changes))


def _migration_operations(
    source: str,
    path: str,
    side: str,
) -> dict[str, _MigrationOperation]:
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as error:
        raise SchemaDiffError(f"{path} {side} nao e Python valido: {error.msg}") from error
    upgrade = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            and node.name == "upgrade"
        ),
        None,
    )
    if upgrade is None:
        return {}
    receivers = {"op", *_batch_aliases(upgrade)}
    operations: dict[str, _MigrationOperation] = {}
    for node in ast.walk(upgrade):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in receivers
            and node.func.attr != "batch_alter_table"
        ):
            operations[ast.dump(node, include_attributes=False)] = _MigrationOperation(
                node.func.attr,
                node,
            )
    return operations


def _batch_aliases(upgrade: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    aliases: set[str] = set()
    for node in ast.walk(upgrade):
        if not isinstance(node, ast.withitem) or not isinstance(node.optional_vars, ast.Name):
            continue
        context = node.context_expr
        if (
            isinstance(context, ast.Call)
            and isinstance(context.func, ast.Attribute)
            and isinstance(context.func.value, ast.Name)
            and context.func.value.id == "op"
            and context.func.attr == "batch_alter_table"
        ):
            aliases.add(node.optional_vars.id)
    return aliases


def _operation_compatibility(operation: _MigrationOperation) -> Compatibility:
    if operation.name in {"create_table"}:
        return Compatibility.ADDITIVE
    if operation.name == "add_column":
        return _add_column_compatibility(operation.call)
    if operation.name == "create_index":
        return _create_index_compatibility(operation.call)
    return Compatibility.BREAKING


def _add_column_compatibility(call: ast.Call) -> Compatibility:
    column = _keyword(call, "column")
    if column is None and call.args:
        column = call.args[1] if len(call.args) > 1 else call.args[0]
    if not isinstance(column, ast.Call) or not _call_named(column, "Column"):
        return Compatibility.BREAKING
    nullable_node = _keyword(column, "nullable")
    primary_key_node = _keyword(column, "primary_key")
    primary_key = _literal_bool(primary_key_node)
    if primary_key_node is not None and primary_key is not False:
        return Compatibility.BREAKING
    if nullable_node is None:
        return Compatibility.ADDITIVE
    nullable = _literal_bool(nullable_node)
    if nullable is True:
        return Compatibility.ADDITIVE
    if nullable is False and _materializable_default(_keyword(column, "server_default")):
        return Compatibility.ADDITIVE
    return Compatibility.BREAKING


def _create_index_compatibility(call: ast.Call) -> Compatibility:
    unique = call.args[4] if len(call.args) > 4 else _keyword(call, "unique")
    if unique is None:
        return Compatibility.ADDITIVE
    return (
        Compatibility.BREAKING
        if _literal_bool(unique) is not False
        else Compatibility.ADDITIVE
    )


def _keyword(call: ast.Call, name: str) -> ast.expr | None:
    return next(
        (keyword.value for keyword in call.keywords if keyword.arg == name),
        None,
    )


def _call_named(call: ast.Call, name: str | set[str]) -> bool:
    names = {name} if isinstance(name, str) else name
    return (isinstance(call.func, ast.Name) and call.func.id in names) or (
        isinstance(call.func, ast.Attribute) and call.func.attr in names
    )


def _literal_bool(node: ast.expr | None) -> bool | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, bool) else None


def _materializable_default(node: ast.expr | None) -> bool:
    if isinstance(node, ast.Constant):
        return node.value is not None
    if not isinstance(node, ast.Call) or not _call_named(node, "text"):
        return False
    if len(node.args) != 1 or node.keywords:
        return False
    value = node.args[0]
    if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
        return False
    expression = value.value.strip()
    if not expression or expression.upper() == "NULL":
        return False
    if expression.upper() in {"TRUE", "FALSE"}:
        return True
    if expression[:1] == expression[-1:] and expression.startswith(("'", '"')):
        return len(expression) >= 2
    try:
        float(expression)
    except ValueError:
        return False
    return True
