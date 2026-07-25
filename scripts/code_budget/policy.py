"""The declared budget: groups of globs, their limits, and the baseline ratchet."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Final, Literal, cast

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
DEFAULT_WARN_RATIO: Final = 0.8


@dataclass(frozen=True, slots=True)
class Group:
    """Grupo de globs com seus limites. Métrica ausente em `limits` = sem limite."""

    name: str
    patterns: tuple[str, ...]
    limits: Mapping[Metric, int]
    exempt: bool = False
    warn_at_ratio: float = DEFAULT_WARN_RATIO

    def matches(self, relative: str) -> bool:
        candidate = PurePosixPath(relative)
        return any(candidate.full_match(pattern) for pattern in self.patterns)

    def warn_threshold(self, metric: Metric) -> int | None:
        """The value at which a metric is close enough to its limit to be reported.

        Returns `None` when the group sets no limit for the metric, or when the
        threshold would equal the limit — a warning must fire strictly before the
        violation, never at the same time.
        """

        limit = self.limits.get(metric)
        if limit is None:
            return None
        threshold = int(limit * self.warn_at_ratio)
        return threshold if threshold < limit else None


@dataclass(frozen=True, slots=True)
class Policy:
    groups: tuple[Group, ...]
    baseline: Mapping[str, Mapping[Metric, int]]

    def group_for(self, relative: str) -> Group | None:
        for group in self.groups:
            if group.matches(relative):
                return group
        return None


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


def _as_ratio(value: object, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{where}: número esperado, recebido {value!r}")
    ratio = float(value)
    if not 0 < ratio < 1:
        raise ValueError(f"{where}: proporção deve estar entre 0 e 1, recebido {ratio}")
    return ratio


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
    raw_ratio = entry.get("warn_at_ratio")
    return Group(
        name=group_name,
        patterns=tuple(str(pattern) for pattern in patterns),
        limits=limits,
        exempt=bool(entry.get("exempt", False)),
        warn_at_ratio=(
            DEFAULT_WARN_RATIO
            if raw_ratio is None
            else _as_ratio(raw_ratio, f"{name}: {group_name}.warn_at_ratio")
        ),
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
