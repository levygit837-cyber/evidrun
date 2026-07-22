from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class Classification(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"


class EvidenceMode(StrEnum):
    PROSPECTIVE_CONTROLLED = "prospective_controlled"
    COUNTERFACTUAL_REPLAY = "counterfactual_replay"
    RETROSPECTIVE_OBSERVATIONAL = "retrospective_observational"


def new_id(prefix: str) -> str:
    """Return a sortable UUIDv7 identifier with a human-readable prefix."""
    return f"{prefix}_{uuid.uuid7()}"


def utc_now() -> datetime:
    return datetime.now(UTC)


def canonical_json(value: Any) -> str:
    """Stable JSON representation used by revision and event digests."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

