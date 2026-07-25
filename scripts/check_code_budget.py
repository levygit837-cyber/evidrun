"""Gate de orçamento estrutural dos arquivos versionados.

Mede três métricas por arquivo rastreado pelo git e compara com o orçamento do
grupo de globs a que o arquivo pertence:

- `file_lines`: linhas do arquivo;
- `function_lines`: maior função ou método (só Python, via `ast`);
- `public_methods`: maior número de métodos públicos de uma classe (só Python).

Arquivos que já violavam a política quando o gate foi ligado ficam na tabela
`[baseline]` de `code-budget.toml`. O baseline é um ratchet: uma métrica listada
pode encolher, nunca crescer, e quando volta para dentro do orçamento normal o
gate exige a remoção da entrada.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
import tomllib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Final, Literal, cast

ROOT: Final = Path(__file__).resolve().parents[1]
CONFIG_NAME: Final = "code-budget.toml"
BASELINE_HEADER: Final = "[baseline]"

Metric = Literal["file_lines", "function_lines", "public_methods"]
METRICS: Final[tuple[Metric, ...]] = ("file_lines", "function_lines", "public_methods")
LABELS: Final[Mapping[Metric, str]] = {
    "file_lines": "linhas do arquivo",
    "function_lines": "linhas da maior função",
    "public_methods": "métodos públicos na maior classe",
}
GROUP_KEYS: Final[Mapping[Metric, str]] = {
    "file_lines": "max_file_lines",
    "function_lines": "max_function_lines",
    "public_methods": "max_public_methods",
}

ViolationKind = Literal["budget", "baseline_growth", "baseline_slack", "stale_baseline", "syntax"]

FunctionDef = ast.FunctionDef | ast.AsyncFunctionDef
NESTING = ast.If | ast.Try | ast.With | ast.For | ast.While


@dataclass(frozen=True, slots=True)
class Group:
    """Grupo de globs com seus limites. Métrica ausente em `limits` = sem limite."""

    name: str
    patterns: tuple[str, ...]
    limits: Mapping[Metric, int]
    exempt: bool = False

    def matches(self, relative: str) -> bool:
        candidate = PurePosixPath(relative)
        return any(candidate.full_match(pattern) for pattern in self.patterns)


@dataclass(frozen=True, slots=True)
class Policy:
    groups: tuple[Group, ...]
    baseline: Mapping[str, Mapping[Metric, int]]

    def group_for(self, relative: str) -> Group | None:
        """Primeiro grupo declarado cujo glob casa; `None` quando nenhum casa."""
        for group in self.groups:
            if group.matches(relative):
                return group
        return None


@dataclass(frozen=True, slots=True)
class Measurement:
    """Métricas de um arquivo. Chave ausente = métrica não aplicável ao arquivo."""

    path: str
    metrics: Mapping[Metric, int]
    details: Mapping[Metric, str]
    syntax_error: str | None = None


@dataclass(frozen=True, slots=True)
class Violation:
    path: str
    metric: Metric
    measured: int
    limit: int | None
    kind: ViolationKind
    message: str

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "metric": self.metric,
            "measured": self.measured,
            "limit": self.limit,
            "kind": self.kind,
            "message": self.message,
        }


def _as_int(value: object, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{where}: inteiro esperado, recebido {value!r}")
    return value


def _as_table(value: object, where: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{where}: tabela esperada, recebido {type(value).__name__}")
    return cast("dict[str, object]", value)


def _as_list(value: object, where: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"{where}: lista esperada, recebido {type(value).__name__}")
    return cast("list[object]", value)


def load_policy(config_path: Path) -> Policy:
    """Lê `code-budget.toml`. Falha alto quando a política está malformada."""
    name = config_path.name
    raw = _as_table(tomllib.loads(config_path.read_text(encoding="utf-8")), name)
    raw_groups = _as_list(raw.get("groups"), f"{name}: [[groups]]")
    if not raw_groups:
        raise ValueError(f"{name}: precisa de pelo menos um [[groups]]")
    groups = tuple(
        _load_group(_as_table(entry, f"{name}: [[groups]]"), name) for entry in raw_groups
    )
    return Policy(groups=groups, baseline=_load_baseline(raw.get("baseline"), name))


def _load_group(entry: Mapping[str, object], name: str) -> Group:
    group_name = str(entry.get("name", ""))
    patterns = _as_list(entry.get("patterns"), f"{name}: {group_name or '<sem nome>'}.patterns")
    if not group_name or not patterns:
        raise ValueError(f"{name}: grupo sem 'name' ou 'patterns'")
    limits: dict[Metric, int] = {}
    for metric, key in GROUP_KEYS.items():
        raw_limit = entry.get(key)
        if raw_limit is not None:
            limits[metric] = _as_int(raw_limit, f"{name}: {group_name}.{key}")
    return Group(
        name=group_name,
        patterns=tuple(str(pattern) for pattern in patterns),
        limits=limits,
        exempt=bool(entry.get("exempt", False)),
    )


def _load_baseline(raw: object, name: str) -> dict[str, dict[Metric, int]]:
    if raw is None:
        return {}
    baseline: dict[str, dict[Metric, int]] = {}
    for path, raw_entry in _as_table(raw, f"{name}: [baseline]").items():
        where = f"{name}: baseline de {path}"
        entry = _as_table(raw_entry, where)
        unknown = set(entry) - set(METRICS)
        if unknown:
            raise ValueError(f"{where} tem métrica desconhecida: {', '.join(sorted(unknown))}")
        recorded: dict[Metric, int] = {}
        for metric in METRICS:
            if metric in entry:
                recorded[metric] = _as_int(entry[metric], f"{where}.{metric}")
        baseline[path] = recorded
    return baseline


def tracked_files(root: Path) -> list[str]:
    """Arquivos versionados, na ordem do git, sem walk do filesystem."""
    completed = subprocess.run(
        ("git", "ls-files", "-z"), cwd=root, check=True, capture_output=True
    )
    return [entry for entry in completed.stdout.decode("utf-8").split("\0") if entry]


def measure_file(root: Path, relative: str) -> Measurement:
    """Mede um arquivo. Métricas de função e classe existem só para Python."""
    text = (root / relative).read_text(encoding="utf-8")
    metrics: dict[Metric, int] = {"file_lines": len(text.splitlines())}
    if not relative.endswith(".py"):
        return Measurement(path=relative, metrics=metrics, details={})
    try:
        tree = ast.parse(text, filename=relative)
    except SyntaxError as exc:
        return Measurement(path=relative, metrics=metrics, details={}, syntax_error=str(exc))
    details: dict[Metric, str] = {}
    scans: tuple[tuple[Metric, tuple[str | None, int]], ...] = (
        ("function_lines", _longest_function(tree)),
        ("public_methods", _largest_class(tree)),
    )
    for metric, (name, value) in scans:
        metrics[metric] = value
        if name is not None:
            details[metric] = name
    return Measurement(path=relative, metrics=metrics, details=details)


def _longest_function(tree: ast.Module) -> tuple[str | None, int]:
    winner: str | None = None
    longest = 0
    for node, scope in _walk_scopes(tree.body, ()):
        if isinstance(node, FunctionDef):
            span = (node.end_lineno or node.lineno) - node.lineno + 1
            if span > longest:
                longest, winner = span, ".".join((*scope, node.name))
    return winner, longest


def _largest_class(tree: ast.Module) -> tuple[str | None, int]:
    winner: str | None = None
    largest = 0
    for node, scope in _walk_scopes(tree.body, ()):
        if not isinstance(node, ast.ClassDef):
            continue
        public = sum(
            1
            for child in node.body
            if isinstance(child, FunctionDef) and not child.name.startswith("_")
        )
        if public > largest:
            largest, winner = public, ".".join((*scope, node.name))
    return winner, largest


def _walk_scopes(
    body: Sequence[ast.stmt], scope: tuple[str, ...]
) -> Iterable[tuple[ast.stmt, tuple[str, ...]]]:
    """Percorre defs de função e classe mantendo o nome qualificado do escopo."""
    for node in body:
        if isinstance(node, FunctionDef | ast.ClassDef):
            yield node, scope
            yield from _walk_scopes(node.body, (*scope, node.name))
        elif isinstance(node, NESTING):
            yield from _walk_scopes(node.body, scope)


def measure_all(root: Path, policy: Policy, files: Iterable[str]) -> list[Measurement]:
    """Mede só os arquivos que caem em algum grupo com orçamento."""
    measurements: list[Measurement] = []
    for relative in files:
        group = policy.group_for(relative)
        if group is None or group.exempt or not (root / relative).is_file():
            continue
        measurements.append(measure_file(root, relative))
    return measurements


def check(policy: Policy, measurements: Sequence[Measurement]) -> list[Violation]:
    """Aplica orçamento e ratchet. Lista vazia significa gate verde."""
    violations: list[Violation] = []
    for measurement in measurements:
        group = policy.group_for(measurement.path)
        if group is None or group.exempt:
            continue
        recorded = policy.baseline.get(measurement.path, {})
        if measurement.syntax_error is not None:
            violations.append(
                Violation(
                    path=measurement.path,
                    metric="file_lines",
                    measured=measurement.metrics["file_lines"],
                    limit=None,
                    kind="syntax",
                    message=f"não foi possível parsear: {measurement.syntax_error}",
                )
            )
        for metric in METRICS:
            violation = _check_metric(group, recorded, measurement, metric)
            if violation is not None:
                violations.append(violation)
    measured = {measurement.path for measurement in measurements}
    violations.extend(
        Violation(
            path=path,
            metric="file_lines",
            measured=0,
            limit=None,
            kind="stale_baseline",
            message=(
                "entrada de baseline sem arquivo medido correspondente; "
                f"remova a entrada de {CONFIG_NAME}"
            ),
        )
        for path in sorted(set(policy.baseline) - measured)
    )
    return violations


def _check_metric(
    group: Group, recorded: Mapping[Metric, int], measurement: Measurement, metric: Metric
) -> Violation | None:
    allowed = recorded.get(metric)
    value = measurement.metrics.get(metric)
    if value is None:
        if allowed is None:
            return None
        return Violation(
            path=measurement.path,
            metric=metric,
            measured=0,
            limit=allowed,
            kind="stale_baseline",
            message=(
                f"baseline registra {metric} para um arquivo que não expõe essa métrica; "
                f"remova a chave de {CONFIG_NAME}"
            ),
        )
    budget = group.limits.get(metric)
    label = LABELS[metric]
    detail = measurement.details.get(metric)
    where = f" ({detail})" if detail else ""
    if allowed is None:
        if budget is None or value <= budget:
            return None
        return Violation(
            path=measurement.path,
            metric=metric,
            measured=value,
            limit=budget,
            kind="budget",
            message=(
                f"{label} é {value}{where}, acima do orçamento {budget} "
                f"do grupo '{group.name}'"
            ),
        )
    if budget is not None and value <= budget:
        return Violation(
            path=measurement.path,
            metric=metric,
            measured=value,
            limit=budget,
            kind="baseline_slack",
            message=(
                f"{label} caiu para {value}, dentro do orçamento {budget} do grupo "
                f"'{group.name}': remova a entrada de baseline de {CONFIG_NAME} "
                "(o ratchet só aperta, nunca afrouxa)"
            ),
        )
    if value > allowed:
        return Violation(
            path=measurement.path,
            metric=metric,
            measured=value,
            limit=allowed,
            kind="baseline_growth",
            message=(
                f"{label} cresceu de {allowed} (baseline) para {value}{where}: "
                "arquivo de baseline pode encolher, nunca crescer"
            ),
        )
    return None


def compute_baseline(
    policy: Policy, measurements: Sequence[Measurement]
) -> dict[str, dict[Metric, int]]:
    """Baseline mínimo: só as métricas que hoje estouram o orçamento do grupo."""
    baseline: dict[str, dict[Metric, int]] = {}
    for measurement in measurements:
        group = policy.group_for(measurement.path)
        if group is None or group.exempt:
            continue
        recorded: dict[Metric, int] = {}
        for metric in METRICS:
            value = measurement.metrics.get(metric)
            budget = group.limits.get(metric)
            if value is not None and budget is not None and value > budget:
                recorded[metric] = value
        if recorded:
            baseline[measurement.path] = recorded
    return baseline


def render_baseline(config_text: str, baseline: Mapping[str, Mapping[Metric, int]]) -> str:
    """Reescreve o bloco `[baseline]` preservando tudo que vem antes dele."""
    lines = config_text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == BASELINE_HEADER:
            head = lines[:index]
            break
    else:
        raise ValueError(f"linha '{BASELINE_HEADER}' não encontrada na configuração")
    while head and not head[-1].strip():
        head.pop()
    rendered = [*head, "", BASELINE_HEADER]
    for path in sorted(baseline):
        rendered.append("")
        rendered.append(f"[baseline.{json.dumps(path, ensure_ascii=False)}]")
        rendered.extend(
            f"{metric} = {baseline[path][metric]}" for metric in METRICS if metric in baseline[path]
        )
    return "\n".join(rendered) + "\n"


def _update_baseline(
    config_path: Path, policy: Policy, measurements: Sequence[Measurement]
) -> tuple[Mapping[str, Mapping[Metric, int]], dict[str, list[str]]]:
    baseline = compute_baseline(policy, measurements)
    previous = dict(policy.baseline)
    config_path.write_text(
        render_baseline(config_path.read_text(encoding="utf-8"), baseline), encoding="utf-8"
    )
    shared = set(baseline) & set(previous)
    return baseline, {
        "adicionados": sorted(set(baseline) - set(previous)),
        "removidos": sorted(set(previous) - set(baseline)),
        "alterados": sorted(path for path in shared if baseline[path] != previous[path]),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_code_budget",
        description="Verifica o orçamento de tamanho de arquivo, função e classe.",
    )
    parser.add_argument("--root", type=Path, default=ROOT, help="raiz do repositório")
    parser.add_argument(
        "--config", type=Path, default=None, help=f"caminho de {CONFIG_NAME} (default: na raiz)"
    )
    parser.add_argument("--json", action="store_true", help="saída de máquina em JSON")
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="regrava o baseline a partir do estado atual (uso humano deliberado, nunca em CI)",
    )
    args = parser.parse_args(argv)
    root: Path = Path(args.root).resolve()
    config_path: Path = Path(args.config) if args.config is not None else root / CONFIG_NAME
    policy = load_policy(config_path)
    measurements = measure_all(root, policy, tracked_files(root))

    if args.update_baseline:
        baseline, changes = _update_baseline(config_path, policy, measurements)
        if args.json:
            print(
                json.dumps(
                    {"baseline_files": len(baseline)} | changes, ensure_ascii=False, indent=2
                )
            )
            return 0
        print(f"Baseline regravado em {config_path.name}: {len(baseline)} arquivos")
        for label, paths in changes.items():
            if paths:
                print(f"  {label}: {', '.join(paths)}")
        return 0

    violations = check(policy, measurements)
    if args.json:
        print(
            json.dumps(
                {
                    "ok": not violations,
                    "checked_files": len(measurements),
                    "baseline_files": len(policy.baseline),
                    "violations": [violation.as_dict() for violation in violations],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1 if violations else 0
    for violation in violations:
        limit = "sem limite" if violation.limit is None else str(violation.limit)
        print(
            f"VIOLAÇÃO {violation.path}: {violation.metric}={violation.measured} "
            f"(limite {limit}) — {violation.message}",
            file=sys.stderr,
        )
    print(
        f"Orçamento estrutural: {len(measurements)} arquivos medidos, "
        f"{len(policy.baseline)} no baseline, {len(violations)} violações",
        file=sys.stderr if violations else sys.stdout,
    )
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
