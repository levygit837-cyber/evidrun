"""AST-based contract diffs for events, persistence, CLI and Python exports."""

from __future__ import annotations

import ast
import copy
from dataclasses import dataclass

from .schema_diff import (
    Compatibility,
    ContractChange,
    ContractDiffReport,
    ContractSurface,
    SchemaDiffError,
)

_IGNORED_CALL_KEYWORDS = {"description", "examples", "help", "title"}
_IGNORED_CLASS_NAMES = {"model_config"}
_HTTPLESS_COMMAND_DECORATORS = {"command", "callback"}


@dataclass(frozen=True)
class _Declaration:
    kind: str
    name: str
    owner: str | None
    signature: str
    optional: bool = True

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.kind, self.owner or "", self.name)

    @property
    def qualified_name(self) -> str:
        return f"{self.owner}.{self.name}" if self.owner else self.name


def compare_python_surface(
    baseline: str,
    candidate: str,
    *,
    path: str,
    surface: ContractSurface,
) -> ContractDiffReport:
    """Compare declarations that callers, stored data or event consumers observe."""

    if surface not in {
        ContractSurface.PERSISTED_MODEL,
        ContractSurface.EVENT,
        ContractSurface.CLI,
        ContractSurface.EXPORT,
    }:
        raise SchemaDiffError(f"superficie Python nao suportada: {surface.value}")
    before = _snapshot(baseline, path, surface, "baseline")
    after = _snapshot(candidate, path, surface, "candidate")
    changes = _compare_declarations(before, after)
    return ContractDiffReport(path, surface, changes)


def compare_migration_surface(
    baseline: str,
    candidate: str,
    *,
    path: str,
) -> ContractDiffReport:
    """Compare Alembic `upgrade` operations without treating `downgrade` as delivery."""

    before = _migration_operations(baseline, path, "baseline")
    after = _migration_operations(candidate, path, "candidate")
    changes: list[ContractChange] = []
    for signature in sorted(before.keys() - after.keys()):
        operation = before[signature]
        changes.append(
            ContractChange(
                "migration-operation-removed",
                Compatibility.BREAKING,
                f"/upgrade/{operation}",
                f"A operacao de migration {operation!r} foi removida.",
            )
        )
    additive_operations = {
        "add_column",
        "create_check_constraint",
        "create_foreign_key",
        "create_index",
        "create_table",
        "create_unique_constraint",
    }
    for signature in sorted(after.keys() - before.keys()):
        operation = after[signature]
        compatibility = (
            Compatibility.ADDITIVE if operation in additive_operations else Compatibility.BREAKING
        )
        changes.append(
            ContractChange(
                "migration-operation-added",
                compatibility,
                f"/upgrade/{operation}",
                f"A operacao de migration {operation!r} foi adicionada.",
            )
        )
    return ContractDiffReport(path, ContractSurface.PERSISTED_MODEL, tuple(changes))


def declares_explicit_exports(source: str, *, path: str) -> bool:
    """Return whether a Python module assigns __all__ at module scope."""

    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as error:
        raise SchemaDiffError(f"{path} nao e Python valido: {error.msg}") from error
    return any(_all_value(node) is not None for node in tree.body)


def _snapshot(
    source: str,
    path: str,
    surface: ContractSurface,
    side: str,
) -> dict[tuple[str, str, str], _Declaration]:
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as error:
        raise SchemaDiffError(f"{path} {side} nao e Python valido: {error.msg}") from error
    declarations: list[_Declaration] = []
    if surface is ContractSurface.CLI:
        declarations.extend(_cli_declarations(tree))
    elif surface is ContractSurface.EXPORT:
        declarations.extend(_export_declarations(tree))
    else:
        declarations.extend(_model_declarations(tree, surface))
    return {item.key: item for item in declarations}


def _migration_operations(source: str, path: str, side: str) -> dict[str, str]:
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as error:
        raise SchemaDiffError(f"{path} {side} nao e Python valido: {error.msg}") from error
    operations: dict[str, str] = {}
    upgrade = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name == "upgrade"
        ),
        None,
    )
    if upgrade is None:
        return operations
    for node in ast.walk(upgrade):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "op"
        ):
            operations[_fingerprint(node)] = node.func.attr
    return operations


def _model_declarations(tree: ast.Module, surface: ContractSurface) -> tuple[_Declaration, ...]:
    declarations: list[_Declaration] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
            declarations.append(_Declaration("class", node.name, None, _class_signature(node)))
            declarations.extend(_class_fields(node, surface))
        elif surface is ContractSurface.EVENT:
            declarations.extend(_module_contract_assignments(node))
    return tuple(declarations)


def _class_fields(node: ast.ClassDef, surface: ContractSurface) -> tuple[_Declaration, ...]:
    fields: list[_Declaration] = []
    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            name = item.target.id
            if _include_field(name, surface):
                fields.append(
                    _Declaration(
                        "field",
                        name,
                        node.name,
                        _annotated_field_signature(item),
                        _field_is_optional(item),
                    )
                )
        elif isinstance(item, ast.Assign) and len(item.targets) == 1:
            target = item.targets[0]
            if isinstance(target, ast.Name) and _include_field(target.id, surface):
                fields.append(
                    _Declaration(
                        "field",
                        target.id,
                        node.name,
                        _fingerprint(item.value),
                        True,
                    )
                )
    return tuple(fields)


def _module_contract_assignments(node: ast.stmt) -> tuple[_Declaration, ...]:
    if (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and not node.target.id.startswith("_")
        and node.target.id != "model_config"
    ):
        return (
            _Declaration(
                "symbol",
                node.target.id,
                None,
                _annotated_field_signature(node),
            ),
        )
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target = node.targets[0]
        if isinstance(target, ast.Name) and not target.id.startswith("_"):
            return (_Declaration("symbol", target.id, None, _fingerprint(node.value)),)
    return ()


def _cli_declarations(tree: ast.Module) -> tuple[_Declaration, ...]:
    declarations: list[_Declaration] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            command = _command_name(node)
            if command is not None:
                declarations.append(
                    _Declaration("command", command, None, _function_signature(node))
                )
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            subcommand = _subcommand_declaration(node.value)
            if subcommand is not None:
                declarations.append(subcommand)
    return tuple(declarations)


def _command_name(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    for decorator in node.decorator_list:
        call = decorator if isinstance(decorator, ast.Call) else None
        target = call.func if call is not None else decorator
        if not isinstance(target, ast.Attribute) or target.attr not in _HTTPLESS_COMMAND_DECORATORS:
            continue
        if target.attr == "callback":
            return "<callback>"
        if call is not None and call.args:
            explicit = call.args[0]
            if isinstance(explicit, ast.Constant) and isinstance(explicit.value, str):
                return explicit.value
        return node.name.replace("_", "-")
    return None


def _subcommand_declaration(call: ast.Call) -> _Declaration | None:
    if not isinstance(call.func, ast.Attribute) or call.func.attr != "add_typer":
        return None
    name = next(
        (
            keyword.value.value
            for keyword in call.keywords
            if keyword.arg == "name"
            and isinstance(keyword.value, ast.Constant)
            and isinstance(keyword.value.value, str)
        ),
        None,
    )
    if name is None:
        return None
    return _Declaration("command-group", name, None, _fingerprint(call))


def _export_declarations(tree: ast.Module) -> tuple[_Declaration, ...]:
    explicit = _explicit_all(tree)
    if explicit is not None:
        return tuple(_Declaration("export", name, None, name) for name in sorted(explicit))
    exports: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom):
            exports.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, ast.Import):
            exports.update(alias.asname or alias.name.partition(".")[0] for alias in node.names)
    return tuple(
        _Declaration("export", name, None, name)
        for name in sorted(name for name in exports if not name.startswith("_"))
    )


def _explicit_all(tree: ast.Module) -> tuple[str, ...] | None:
    for node in tree.body:
        value = _all_value(node)
        if value is not None and not isinstance(value, ast.List | ast.Tuple):
            raise SchemaDiffError("__all__ deve ser uma lista ou tupla literal")
        if isinstance(value, ast.List | ast.Tuple):
            names = tuple(
                item.value
                for item in value.elts
                if isinstance(item, ast.Constant) and isinstance(item.value, str)
            )
            if len(names) != len(value.elts):
                raise SchemaDiffError("__all__ deve conter apenas nomes literais")
            return names
    return None


def _all_value(node: ast.stmt) -> ast.expr | None:
    if isinstance(node, ast.Assign) and any(
        isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
    ):
        return node.value
    if (
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "__all__"
    ):
        return node.value
    return None


def _compare_declarations(
    before: dict[tuple[str, str, str], _Declaration],
    after: dict[tuple[str, str, str], _Declaration],
) -> tuple[ContractChange, ...]:
    changes: list[ContractChange] = []
    removed_classes = {
        item.name for key, item in before.items() if item.kind == "class" and key not in after
    }
    added_classes = {
        item.name for key, item in after.items() if item.kind == "class" and key not in before
    }
    for key in sorted(before.keys() - after.keys()):
        item = before[key]
        if item.owner in removed_classes:
            continue
        changes.append(_removed(item))
    for key in sorted(after.keys() - before.keys()):
        item = after[key]
        if item.owner in added_classes:
            continue
        changes.append(_added(item))
    for key in sorted(before.keys() & after.keys()):
        old = before[key]
        new = after[key]
        if old.signature != new.signature:
            changes.append(
                ContractChange(
                    f"{new.kind}-changed",
                    Compatibility.BREAKING,
                    _pointer(new),
                    f"A declaracao {new.qualified_name!r} mudou.",
                )
            )
    return tuple(changes)


def _removed(item: _Declaration) -> ContractChange:
    return ContractChange(
        f"{item.kind}-removed",
        Compatibility.BREAKING,
        _pointer(item),
        f"A declaracao {item.qualified_name!r} foi removida.",
    )


def _added(item: _Declaration) -> ContractChange:
    compatibility = Compatibility.ADDITIVE if item.optional else Compatibility.BREAKING
    return ContractChange(
        f"{item.kind}-added" if item.optional else f"required-{item.kind}-added",
        compatibility,
        _pointer(item),
        f"A declaracao {item.qualified_name!r} foi adicionada.",
    )


def _class_signature(node: ast.ClassDef) -> str:
    bases = ",".join(_fingerprint(base) for base in node.bases)
    return f"bases={bases}"


def _annotated_field_signature(node: ast.AnnAssign) -> str:
    value = _fingerprint(node.value) if node.value is not None else "<required>"
    return f"annotation={_fingerprint(node.annotation)};default={value}"


def _function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    returns = _fingerprint(node.returns) if node.returns is not None else ""
    return f"args={_fingerprint(node.args)};returns={returns}"


def _field_is_optional(node: ast.AnnAssign) -> bool:
    if node.value is not None:
        if isinstance(node.value, ast.Call) and _call_named(node.value, "Field"):
            keywords = {
                item.arg: item.value for item in node.value.keywords if item.arg is not None
            }
            default = node.value.args[0] if node.value.args else keywords.get("default")
            if "default_factory" in keywords:
                return True
            return default is not None and not (
                isinstance(default, ast.Constant) and default.value is Ellipsis
            )
        if isinstance(node.value, ast.Call) and _call_named(node.value, "mapped_column"):
            keywords = {
                item.arg: item.value for item in node.value.keywords if item.arg is not None
            }
            if _literal_bool(keywords.get("nullable")) is True:
                return True
            if {
                "default",
                "server_default",
            }.intersection(keywords):
                return True
            return _annotation_allows_none(node.annotation)
        return True
    return _annotation_allows_none(node.annotation)


def _annotation_allows_none(node: ast.expr) -> bool:
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _annotation_allows_none(node.left) or _annotation_allows_none(node.right)
    return (isinstance(node, ast.Constant) and node.value is None) or (
        isinstance(node, ast.Name) and node.id in {"None", "NoneType"}
    )


def _include_field(name: str, surface: ContractSurface) -> bool:
    if name in _IGNORED_CLASS_NAMES:
        return False
    if surface is ContractSurface.PERSISTED_MODEL:
        return not name.startswith("_") or name in {"__tablename__", "__table_args__"}
    return not name.startswith("_")


def _call_named(node: ast.Call, name: str) -> bool:
    return (isinstance(node.func, ast.Name) and node.func.id == name) or (
        isinstance(node.func, ast.Attribute) and node.func.attr == name
    )


def _literal_bool(node: ast.expr | None) -> bool | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, bool) else None


def _pointer(item: _Declaration) -> str:
    name = item.qualified_name.replace("~", "~0").replace("/", "~1")
    return f"/symbols/{name}"


def _fingerprint(node: ast.AST | None) -> str:
    if node is None:
        return ""
    normalized = _StripDescriptions().visit(copy.deepcopy(node))
    ast.fix_missing_locations(normalized)
    return ast.dump(normalized, annotate_fields=True, include_attributes=False)


class _StripDescriptions(ast.NodeTransformer):
    def visit_Call(self, node: ast.Call) -> ast.AST:
        updated = self.generic_visit(node)
        assert isinstance(updated, ast.Call)
        updated.keywords = [
            keyword for keyword in updated.keywords if keyword.arg not in _IGNORED_CALL_KEYWORDS
        ]
        return updated
