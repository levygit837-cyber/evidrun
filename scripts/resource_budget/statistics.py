"""Robust statistics for any repeated warning-only observation."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

MINIMUM_CONCLUSIVE_SAMPLES = 3


@dataclass(frozen=True)
class SampleEvaluation:
    value: float
    relative_spread: float
    status: str
    threshold: float


def evaluate_samples(
    samples: tuple[float, ...],
    *,
    baseline: float,
    warning_ratio: float,
    noise_spread_ratio: float | None,
) -> SampleEvaluation:
    """Classify a repeated observation using the median and the relative spread.

    The median resists an isolated outlier, so it stays the reported value.

    Dispersion is measured as `(max - min) / median` rather than by a median absolute
    deviation. MAD has no resolution at the sample sizes this repository configures:
    with three samples the deviations from the median are `[b-a, 0, c-b]`, whose median
    is `min(b-a, c-b)`, so one tight pair pins MAD near zero no matter how far the
    third sample lies. Measured on the real python profile, `crl_ctx_002.duration_ms`
    reported relative MAD `0.0000` against a true spread of `0.0531`, and a synthetic
    `(100, 101, 1000)` scored `0.0099` — a tenfold outlier called stable.

    Relative spread is deliberately the pessimistic choice: it reacts to the single
    worst sample. For a warning-only signal that is the safer direction, because the
    consequence of over-reporting noise is `inconclusive`, never a failed build.

    `noise_spread_ratio = None` disables the guard, for a quantity that is exact rather
    than sampled. A byte count read once is measured, not estimated; calling it
    inconclusive would withhold a fact the checker actually holds.
    """

    if not samples:
        raise ValueError("at least one sample is required")
    value = float(median(samples))
    relative_spread = (max(samples) - min(samples)) / value if value else 0.0
    threshold = baseline * warning_ratio
    if noise_spread_ratio is not None and (
        len(samples) < MINIMUM_CONCLUSIVE_SAMPLES or relative_spread > noise_spread_ratio
    ):
        status = "inconclusive"
    elif value > threshold:
        status = "regression"
    else:
        status = "ok"
    return SampleEvaluation(
        value=value,
        relative_spread=relative_spread,
        status=status,
        threshold=threshold,
    )
