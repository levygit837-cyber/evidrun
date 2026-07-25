"""Recompute and rewrite the `[baseline]` ratchet.

The minimum baseline records only what currently exceeds its group budget, so
regenerating never invents slack for a file that already fits.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from code_budget.measure import Measurement
from code_budget.policy import (
    BASELINE_HEADER,
    METRICS,
    Metric,
    Policy,
)


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
            budget = group.limits.get(metric)
            value = measurement.metrics.get(metric)
            if budget is not None and value is not None and value > budget:
                recorded[metric] = value
        if recorded:
            baseline[measurement.path] = recorded
    return baseline


def render_baseline(config_text: str, baseline: Mapping[str, Mapping[Metric, int]]) -> str:
    """Reescreve o bloco `[baseline]` preservando tudo que vem antes dele.

    O corte é por linha, não por substring: o cabeçalho de comentário do próprio
    `code-budget.toml` menciona `[baseline]` em prosa, e um `partition` cru cortava ali,
    apagando todos os `[[groups]]` do arquivo.
    """

    head: list[str] = []
    for line in config_text.splitlines():
        if line.strip() == BASELINE_HEADER:
            break
        head.append(line)
    rendered = ["\n".join(head).rstrip("\n"), "", BASELINE_HEADER]
    for path in sorted(baseline):
        rendered.extend(("", f'[baseline."{path}"]'))
        rendered.extend(
            f"{metric} = {baseline[path][metric]}"
            for metric in METRICS
            if metric in baseline[path]
        )
    return "\n".join(rendered) + "\n"


def update_baseline(
    config_path: Path, policy: Policy, measurements: Sequence[Measurement]
) -> tuple[Mapping[str, Mapping[Metric, int]], dict[str, list[str]]]:
    """Rewrite the file and report which entries appeared, changed, or vanished."""

    baseline = compute_baseline(policy, measurements)
    config_path.write_text(
        render_baseline(config_path.read_text(encoding="utf-8"), baseline),
        encoding="utf-8",
    )
    previous = policy.baseline
    return baseline, {
        "adicionados": sorted(set(baseline) - set(previous)),
        "removidos": sorted(set(previous) - set(baseline)),
        "alterados": sorted(
            path
            for path in set(baseline) & set(previous)
            if dict(baseline[path]) != dict(previous[path])
        ),
    }
