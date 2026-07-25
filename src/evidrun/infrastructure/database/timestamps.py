from __future__ import annotations

from datetime import UTC, datetime

__all__ = ["aware_utc", "naive_utc"]


def aware_utc(value: datetime) -> datetime:
    """Read a stored timestamp back as an aware UTC instant."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def naive_utc(value: datetime) -> datetime:
    """Normalize an instant to the naive UTC shape SQLite columns compare against."""
    return value.astimezone(UTC).replace(tzinfo=None) if value.tzinfo else value
