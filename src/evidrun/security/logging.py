"""Structured operational logging with a closed field allowlist.

Values reach the standard logging backend only after both the field name and its value
shape are accepted. Exception messages, args and tracebacks are never serialized.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Mapping
from typing import Final, Literal

type Classification = Literal["public", "internal"]
type LogValue = str | int | bool

REDACTED: Final = "<redacted>"
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:@-]{0,127}")
_EVENT_CODE = re.compile(r"[a-z][a-z0-9_.-]{2,127}")

LOG_FIELD_POLICY: Final[Mapping[str, Classification]] = {
    "event_code": "public",
    "correlation_id": "internal",
    "error_code": "public",
    "error_type": "public",
    "provider_id": "internal",
    "status_code": "public",
    "worker_id": "internal",
    "process": "public",
    "exit_code": "public",
    "signal": "public",
    "bundle_version": "public",
    "artifact_ref": "internal",
    "contract_type": "public",
    "operation": "public",
}

_INTEGER_FIELDS = frozenset({"status_code", "exit_code"})
_BOOLEAN_FIELDS: frozenset[str] = frozenset()


def safe_log_document(
    event_code: str,
    *,
    correlation_id: str | None = None,
    error_code: str | None = None,
    error: BaseException | None = None,
    fields: Mapping[str, object] | None = None,
) -> dict[str, LogValue]:
    """Build the complete document that may cross the logging boundary."""

    document: dict[str, LogValue] = {
        "event_code": _safe_text(event_code, event=True),
    }
    if correlation_id is not None:
        document["correlation_id"] = _safe_text(correlation_id)
    if error_code is not None:
        document["error_code"] = _safe_text(error_code)
    if error is not None:
        document["error_type"] = _safe_text(type(error).__name__)
    for name, value in (fields or {}).items():
        if name not in LOG_FIELD_POLICY or name in document:
            continue
        document[name] = _safe_value(name, value)
    return document


def emit_secure_log(
    logger: logging.Logger,
    level: int,
    event_code: str,
    *,
    correlation_id: str | None = None,
    error_code: str | None = None,
    error: BaseException | None = None,
    fields: Mapping[str, object] | None = None,
) -> None:
    """Emit one deterministic JSON record without exception text or traceback."""

    # Alembic's logging fileConfig disables loggers imported before a migration. Security
    # events must remain observable after that operational reconfiguration.
    logger.disabled = False
    document = safe_log_document(
        event_code,
        correlation_id=correlation_id,
        error_code=error_code,
        error=error,
        fields=fields,
    )
    logger.log(level, json.dumps(document, sort_keys=True, separators=(",", ":")))


def _safe_value(name: str, value: object) -> LogValue:
    if name in _INTEGER_FIELDS:
        return value if isinstance(value, int) and not isinstance(value, bool) else REDACTED
    if name in _BOOLEAN_FIELDS:
        return value if isinstance(value, bool) else REDACTED
    return _safe_text(value) if isinstance(value, str) else REDACTED


def _safe_text(value: str, *, event: bool = False) -> str:
    pattern = _EVENT_CODE if event else _IDENTIFIER
    return value if pattern.fullmatch(value) else REDACTED
