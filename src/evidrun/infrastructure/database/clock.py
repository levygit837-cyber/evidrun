"""The one clock every persistence aggregate reads.

Aggregates call `clock.utc_now()` through this module instead of importing
`utc_now` directly, which keeps the layer at a single patchable seam. Before the
decomposition that seam existed by accident: one `Repository` class held one
import, so freezing it froze every timestamp the layer wrote. Ten per-module
imports would let a clock freeze reach some write paths and miss others, mixing
frozen and wall-clock instants inside one hash-chained transaction.

This changes where the read comes from, never how often it happens: each event
still reads the clock once and reuses that instant for both the envelope digest
and the stored row.
"""

from __future__ import annotations

from datetime import datetime

from evidrun.shared.types import utc_now as _utc_now

__all__ = ["utc_now"]


def utc_now() -> datetime:
    return _utc_now()
