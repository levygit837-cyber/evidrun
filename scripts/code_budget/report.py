"""Apply the budget and the ratchet, and warn before a file reaches its limit.

A finding is either a violation, which fails the gate, or a warning, which does
not. The distinction is deliberate: a warning that breaks CI becomes noise someone
silences, so headroom is reported without changing the exit code.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, Literal

from code_budget.measure import Measurement
from code_budget.policy import (
    CONFIG_NAME,
    LABELS,
    METRICS,
    Group,
    Metric,
    Policy,
)

Severity = Literal["violation", "warning"]
FindingKind = Literal[
    "budget",
    "baseline_growth",
    "baseline_slack",
    "stale_baseline",
    "syntax",
    "headroom",
]

WARNING_KINDS: Final[frozenset[FindingKind]] = frozenset({"headroom"})


@dataclass(frozen=True, slots=True)
class Finding:
    path: str
    metric: Metric
    measured: int
    limit: int | None
    kind: FindingKind
    message: str

    @property
    def severity(self) -> Severity:
        """Derivada do kind, nunca declarada: um kind não pode mudar de gravidade."""

        return "warning" if self.kind in WARNING_KINDS else "violation"

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "metric": self.metric,
            "measured": self.measured,
            "limit": self.limit,
            "kind": self.kind,
            "message": self.message,
            "severity": self.severity,
        }


def check(policy: Policy, measurements: Sequence[Measurement]) -> list[Finding]:
    """Aplica orçamento e ratchet. Sem violação significa gate verde."""

    findings: list[Finding] = []
    for measurement in measurements:
        group = policy.group_for(measurement.path)
        if group is None or group.exempt:
            continue
        recorded = policy.baseline.get(measurement.path, {})
        if measurement.syntax_error is not None:
            findings.append(
                _finding(
                    measurement,
                    "file_lines",
                    "syntax",
                    measurement.metrics["file_lines"],
                    None,
                    f"não foi possível parsear: {measurement.syntax_error}",
                )
            )
        for metric in METRICS:
            finding = _check_metric(group, recorded, measurement, metric)
            if finding is not None:
                findings.append(finding)
    findings.extend(_stale_entries(policy, measurements))
    return findings


def violations(findings: Sequence[Finding]) -> list[Finding]:
    return [item for item in findings if item.severity == "violation"]


def warnings(findings: Sequence[Finding]) -> list[Finding]:
    return [item for item in findings if item.severity == "warning"]


def _finding(
    measurement: Measurement,
    metric: Metric,
    kind: FindingKind,
    measured: int,
    limit: int | None,
    message: str,
) -> Finding:
    return Finding(
        path=measurement.path,
        metric=metric,
        measured=measured,
        limit=limit,
        kind=kind,
        message=message,
    )


def _stale_entries(policy: Policy, measurements: Sequence[Measurement]) -> list[Finding]:
    measured = {measurement.path for measurement in measurements}
    return [
        Finding(
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
    ]


def _described(measurement: Measurement, metric: Metric, value: int) -> str:
    """`<rótulo> é <valor> (<onde>)`, o prefixo comum das mensagens de tamanho."""

    detail = measurement.details.get(metric)
    return f"{LABELS[metric]} é {value}{f' ({detail})' if detail else ''}"


def _check_metric(
    group: Group,
    recorded: Mapping[Metric, int],
    measurement: Measurement,
    metric: Metric,
) -> Finding | None:
    allowed = recorded.get(metric)
    value = measurement.metrics.get(metric)
    if value is None:
        if allowed is None:
            return None
        return _finding(
            measurement,
            metric,
            "stale_baseline",
            0,
            allowed,
            f"baseline registra {metric} para um arquivo que não expõe essa métrica; "
            f"remova a chave de {CONFIG_NAME}",
        )
    budget = group.limits.get(metric)
    if allowed is None:
        if budget is not None and value > budget:
            return _finding(
                measurement,
                metric,
                "budget",
                value,
                budget,
                f"{_described(measurement, metric, value)}, acima do orçamento {budget} "
                f"do grupo '{group.name}'",
            )
        return _headroom(group, measurement, metric, value)
    if budget is not None and value <= budget:
        return _finding(
            measurement,
            metric,
            "baseline_slack",
            value,
            budget,
            f"{LABELS[metric]} caiu para {value}, dentro do orçamento {budget} do grupo "
            f"'{group.name}': remova a entrada de baseline de {CONFIG_NAME} "
            "(o ratchet só aperta, nunca afrouxa)",
        )
    if value > allowed:
        detail = measurement.details.get(metric)
        return _finding(
            measurement,
            metric,
            "baseline_growth",
            value,
            allowed,
            f"{LABELS[metric]} cresceu de {allowed} (baseline) para {value}"
            f"{f' ({detail})' if detail else ''}: "
            "arquivo de baseline pode encolher, nunca crescer",
        )
    return None


def _headroom(
    group: Group, measurement: Measurement, metric: Metric, value: int
) -> Finding | None:
    """Avisa quando a métrica passa do ratio do grupo mas ainda cabe no orçamento."""

    threshold = group.warn_threshold(metric)
    if threshold is None or value <= threshold:
        return None
    budget = group.limits[metric]
    return _finding(
        measurement,
        metric,
        "headroom",
        value,
        budget,
        f"{_described(measurement, metric, value)}, {budget - value} de folga para o "
        f"orçamento {budget} do grupo '{group.name}'",
    )
