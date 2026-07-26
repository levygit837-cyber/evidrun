"""Structural budget gate: policy, measurement, findings, and the baseline ratchet.

The facade exports what the CLI and its test consume. Modules inside the package
import from each other directly, so nothing here is a pass-through for internal use.
"""

from code_budget.baseline import compute_baseline, render_baseline, update_baseline
from code_budget.measure import measure_all, measure_file, tracked_files
from code_budget.policy import CONFIG_NAME, Policy, load_policy
from code_budget.report import Finding, check, violations, warnings

__all__ = [
    "CONFIG_NAME",
    "Finding",
    "Policy",
    "check",
    "compute_baseline",
    "load_policy",
    "measure_all",
    "measure_file",
    "render_baseline",
    "tracked_files",
    "update_baseline",
    "violations",
    "warnings",
]
