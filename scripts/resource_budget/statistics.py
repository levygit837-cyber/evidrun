"""Robust statistics for noisy duration and memory observations."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median


@dataclass(frozen=True)
class SampleEvaluation:
    value: float
    relative_mad: float
    status: str
    threshold: float


def evaluate_samples(
    samples: tuple[float, ...],
    *,
    baseline: float,
    warning_ratio: float,
    noise_mad_ratio: float,
) -> SampleEvaluation:
    """Classify a repeated observation using median and relative MAD.

    Median resists isolated outliers. The median absolute deviation then tells a
    reviewer when the whole sample is too dispersed to call a regression.
    """

    if not samples:
        raise ValueError("at least one sample is required")
    value = float(median(samples))
    absolute_deviations = tuple(abs(sample - value) for sample in samples)
    relative_mad = float(median(absolute_deviations)) / value if value else 0.0
    threshold = baseline * warning_ratio
    if len(samples) < 3 or relative_mad > noise_mad_ratio:
        status = "inconclusive"
    elif value > threshold:
        status = "regression"
    else:
        status = "ok"
    return SampleEvaluation(
        value=value,
        relative_mad=relative_mad,
        status=status,
        threshold=threshold,
    )
