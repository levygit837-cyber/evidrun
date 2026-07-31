"""Change-contract checker with a small interface over Git and policy details."""

from .breaking import BreakingPlan, MigrationStrategy
from .checker import CheckReport, check_contract, secret_diagnostics
from .diagnostics import Diagnostic, Severity
from .git import ChangeSource, GitError, GitSnapshot, inspect_repository
from .merge_gate import (
    MERGE_LAYER_ORDER,
    CiCoverage,
    EvidenceKind,
    LayerConclusion,
    MergeGate,
    MergeLayer,
    ReviewDepth,
    merge_gate_diagnostics,
    required_review_depth,
)
from .model import ChangeContract, load_contract
from .vocabulary import ChangeClassification, ContractError, ImpactLevel

__all__ = [
    "MERGE_LAYER_ORDER",
    "BreakingPlan",
    "ChangeClassification",
    "ChangeContract",
    "ChangeSource",
    "CheckReport",
    "CiCoverage",
    "ContractError",
    "Diagnostic",
    "EvidenceKind",
    "GitError",
    "GitSnapshot",
    "ImpactLevel",
    "LayerConclusion",
    "MergeGate",
    "MergeLayer",
    "MigrationStrategy",
    "ReviewDepth",
    "Severity",
    "check_contract",
    "inspect_repository",
    "load_contract",
    "merge_gate_diagnostics",
    "required_review_depth",
    "secret_diagnostics",
]
