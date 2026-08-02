"""The dispersion rule on its own, without spawning the checker.

Split from `test_resource_budget.py` when that file crossed the budget warning at
660/800 lines. These cases call `evaluate_samples` directly: they are about how a
repeated observation is classified, not about how the CLI reports it.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from resource_budget.statistics import evaluate_samples  # noqa: E402


def test_noisy_repeated_measurement_is_inconclusive_instead_of_a_regression() -> None:
    result = evaluate_samples(
        (100.0, 140.0, 160.0, 200.0, 240.0),
        baseline=80.0,
        warning_ratio=1.5,
        noise_spread_ratio=0.20,
    )

    assert result.value == 160.0
    assert result.relative_spread == 0.875
    assert result.status == "inconclusive"


def test_a_single_outlier_cannot_be_reported_as_a_stable_measurement() -> None:
    """Relative spread exists because a median absolute deviation was blind here.

    With three samples the deviations from the median are `[b-a, 0, c-b]`, so their
    median is `min(b-a, c-b)`: one tight pair reported MAD 0.0099 for a tenfold
    outlier. Measured on the real python profile, `crl_ctx_002.duration_ms` scored
    relative MAD 0.0000 against a true spread of 0.0531.
    """
    result = evaluate_samples(
        (100.0, 101.0, 1000.0),
        baseline=100.0,
        warning_ratio=2.0,
        noise_spread_ratio=0.60,
    )

    assert result.value == 101.0
    assert result.relative_spread > 0.60
    assert result.status == "inconclusive"


def test_a_tight_repeated_measurement_stays_conclusive() -> None:
    """The noise guard must not swallow every sample: a stable one still concludes."""
    result = evaluate_samples(
        (100.0, 101.0, 102.0),
        baseline=100.0,
        warning_ratio=2.0,
        noise_spread_ratio=0.60,
    )

    assert result.status == "ok"
    assert result.relative_spread < 0.05


def test_a_single_observation_is_reported_rather_than_called_inconclusive() -> None:
    """One sample is measured, not estimated, so the guard must not withhold it.

    A `repetitions = 1` inventory has no dispersion to judge. Reporting it as
    `inconclusive` would hide a fact the checker holds.
    """
    result = evaluate_samples(
        (500.0,),
        baseline=100.0,
        warning_ratio=2.0,
        noise_spread_ratio=0.60,
    )

    assert result.relative_spread == 0.0
    assert result.status == "regression"


def test_a_repeated_byte_count_is_guarded_like_any_other_sample() -> None:
    """Sampling decides the guard, not classification.

    `run_bundle.bundle_bytes` is a `runtime_artifact` repeated three times and it does
    vary run to run: 19227 -> 19237 on one checkout, the measurement behind #120's
    Latente 7. Keying the guard on classification excluded exactly the metric that was
    proven noisy, so a dispersed byte count has to be able to reach `inconclusive`.
    """
    result = evaluate_samples(
        (19227.0, 19237.0, 40000.0),
        baseline=25000.0,
        warning_ratio=2.0,
        noise_spread_ratio=0.60,
    )

    assert result.value == 19237.0
    assert result.relative_spread > 0.60
    assert result.status == "inconclusive"
