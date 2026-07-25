"""Apply the budget and the ratchet, and warn before a file reaches its limit.

A finding is either a violation, which fails the gate, or a warning, which does
not. The distinction is deliberate: a warning that breaks CI becomes noise someone
silences, so headroom is reported without changing the exit code.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

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


@dataclass(frozen=True, slots=True)
class Finding:
    path: str
    metric: Metric
    measured: int
    limit: int | None
    kind: FindingKind
    message: str
    severity: Severity = "violation"

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
                Finding(
                    path=measurement.path,
                    metric="file_lines",
                    measured=measurement.metrics["file_lines"],
                    limit=None,
                    kind="syntax",
                    message=f"não foi possível parsear: {measurement.syntax_error}",
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


def _stale_entries(
    policy: Policy, measurements: Sequence[Measurement]
) -> list[Finding]:
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


def _check_metric(
    group: Group,
    recorded: Mapping[Metric, int],
    measurement: Measurement,
    metric: Metric,
) -> Finding | None:
    allowed = recorded.get(metric)
    value = measurement.metrics.get(metric)
    if value is None:
        return None if allowed is None else _stale_metric(measurement, metric, allowed)
    budget = group.limits.get(metric)
    if allowed is None:
        if budget is not None and value > budget:
            return _over_budget(group, measurement, metric, value, budget)
        return _headroom(group, measurement, metric, value)
    if budget is not None and value <= budget:
        return _baseline_slack(group, measurement, metric, value, budget)
    if value > allowed:
        return _baseline_growth(measurement, metric, value, allowed)
    return None


def _where(measurement: Measurement, metric: Metric) -> str:
    detail = measurement.details.get(metric)
    return f" ({detail})" if detail else ""


def _stale_metric(measurement: Measurement, metric: Metric, allowed: int) -> Finding:
    return Finding(
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


def _over_budget(
    group: Group, measurement: Measurement, metric: Metric, value: int, budget: int
) -> Finding:
    return Finding(
        path=measurement.path,
        metric=metric,
        measured=value,
        limit=budget,
        kind="budget",
        message=(
            f"{LABELS[metric]} é {value}{_where(measurement, metric)}, acima do "
            f"orçamento {budget} do grupo '{group.name}'"
        ),
    )


def _baseline_slack(
    group: Group, measurement: Measurement, metric: Metric, value: int, budget: int
) -> Finding:
    return Finding(
        path=measurement.path,
        metric=metric,
        measured=value,
        limit=budget,
        kind="baseline_slack",
        message=(
            f"{LABELS[metric]} caiu para {value}, dentro do orçamento {budget} do grupo "
            f"'{group.name}': remova a entrada de baseline de {CONFIG_NAME} "
            "(o ratchet só aperta, nunca afrouxa)"
        ),
    )


def _baseline_growth(
    measurement: Measurement, metric: Metric, value: int, allowed: int
) -> Finding:
    return Finding(
        path=measurement.path,
        metric=metric,
        measured=value,
        limit=allowed,
        kind="baseline_growth",
        message=(
            f"{LABELS[metric]} cresceu de {allowed} (baseline) para {value}"
            f"{_where(measurement, metric)}: arquivo de baseline pode encolher, "
            "nunca crescer"
        ),
    )


def _headroom(
    group: Group, measurement: Measurement, metric: Metric, value: int
) -> Finding | None:
    """Warn once a metric passes the group's warn ratio but still fits its budget."""

    threshold = group.warn_threshold(metric)
    if threshold is None or value <= threshold:
        return None
    budget = group.limits[metric]
    return Finding(
        path=measurement.path,
        metric=metric,
        measured=value,
        limit=budget,
        kind="headroom",
        severity="warning",
        message=(
            f"{LABELS[metric]} é {value}{_where(measurement, metric)}, "
            f"{budget - value} de folga para o orçamento {budget} do grupo "
            f"'{group.name}'"
        ),
    )
