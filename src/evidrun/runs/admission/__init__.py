"""The concrete admission layer: what the resolved adapter pair can execute."""

from evidrun.runs.admission.catalog_checks import (
    SpecSupport,
    check_evaluator_resolution,
    check_shared_spec,
    issue,
)
from evidrun.runs.admission.real_checks import RealSubjectContract, check_real_spec
from evidrun.runs.admission.scripted_checks import check_scripted_spec

__all__ = [
    "RealSubjectContract",
    "SpecSupport",
    "check_evaluator_resolution",
    "check_real_spec",
    "check_scripted_spec",
    "check_shared_spec",
    "issue",
]
