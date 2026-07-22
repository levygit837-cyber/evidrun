from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from evidrun.experiments import ExperimentManifest

ROOT = Path(__file__).resolve().parents[2]


def load_manifest() -> dict[str, object]:
    return yaml.safe_load((ROOT / "benchmarks/experiments/crl-ctx-002-demo.yaml").read_text())


def test_manifest_is_controlled_and_has_stable_digest() -> None:
    first = ExperimentManifest.model_validate(load_manifest())
    second = ExperimentManifest.model_validate(load_manifest())
    assert first.validity == "controlled"
    assert first.digest == second.digest


def test_confounder_marks_experiment_exploratory() -> None:
    payload = load_manifest()
    payload["variants"][1]["confounders"] = ["model"]  # type: ignore[index]
    manifest = ExperimentManifest.model_validate(payload)
    assert manifest.validity == "exploratory"


def test_unknown_context_policy_is_rejected() -> None:
    payload = load_manifest()
    payload["variants"][1]["context_policy"] = "missing"  # type: ignore[index]
    with pytest.raises(ValidationError):
        ExperimentManifest.model_validate(payload)

