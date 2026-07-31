"""Offline, value-safe secret scanning for tracked repository text."""

from .model import Finding, SourceLine
from .policy import Policy, PolicyError, load_policy
from .scanner import scan_lines, scan_paths, tracked_paths

__all__ = [
    "Finding",
    "Policy",
    "PolicyError",
    "SourceLine",
    "load_policy",
    "scan_lines",
    "scan_paths",
    "tracked_paths",
]
