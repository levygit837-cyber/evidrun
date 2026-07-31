"""Change-contract checker with a small interface over Git and policy details."""

from .checker import CheckReport, Diagnostic, Severity, check_contract, secret_diagnostics
from .git import ChangeSource, GitError, GitSnapshot, inspect_repository
from .model import ChangeContract, ContractError, load_contract

__all__ = [
    "ChangeContract",
    "ChangeSource",
    "CheckReport",
    "ContractError",
    "Diagnostic",
    "GitError",
    "GitSnapshot",
    "Severity",
    "check_contract",
    "inspect_repository",
    "load_contract",
    "secret_diagnostics",
]
