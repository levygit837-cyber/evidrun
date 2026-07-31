from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .model import Finding


class PolicyError(ValueError):
    """The scanner policy cannot be evaluated safely."""


@dataclass(frozen=True)
class AllowEntry:
    rule: str
    path: str
    line: int
    match_sha256: str
    reason: str

    def matches(self, finding: Finding) -> bool:
        return (
            self.rule == finding.rule
            and self.path == finding.path
            and self.line == finding.line
            and self.match_sha256 == finding.match_sha256
        )


@dataclass(frozen=True)
class Policy:
    allow: tuple[AllowEntry, ...] = ()

    def permits(self, finding: Finding) -> bool:
        return any(entry.matches(finding) for entry in self.allow)


def load_policy(path: Path) -> Policy:
    try:
        raw = cast(dict[str, object], tomllib.loads(path.read_text(encoding="utf-8")))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise PolicyError(f"cannot load scanner policy: {type(error).__name__}") from error
    if raw.get("schema_version") != "1":
        raise PolicyError("scanner policy requires schema_version=1")
    entries = raw.get("allow", [])
    if not isinstance(entries, list):
        raise PolicyError("scanner policy allow must be an array")
    parsed: list[AllowEntry] = []
    for index, value in enumerate(cast(list[object], entries), start=1):
        if not isinstance(value, dict):
            raise PolicyError(f"scanner policy allow entry {index} must be a table")
        parsed.append(_parse_entry(cast(dict[object, object], value), index))
    return Policy(tuple(parsed))


def _parse_entry(raw: dict[object, object], index: int) -> AllowEntry:
    expected = {"rule", "path", "line", "match_sha256", "reason"}
    if set(raw) != expected:
        raise PolicyError(f"scanner policy allow entry {index} has invalid fields")
    rule = _text(raw, "rule", index)
    path = _text(raw, "path", index)
    reason = _text(raw, "reason", index)
    line = raw["line"]
    digest = _text(raw, "match_sha256", index)
    if not isinstance(line, int) or isinstance(line, bool) or line < 1:
        raise PolicyError(f"scanner policy allow entry {index} line must be positive")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise PolicyError(f"scanner policy allow entry {index} digest must be sha256 hex")
    return AllowEntry(rule=rule, path=path, line=line, match_sha256=digest, reason=reason)


def _text(raw: dict[object, object], name: str, index: int) -> str:
    value = raw[name]
    if not isinstance(value, str) or not value.strip():
        raise PolicyError(f"scanner policy allow entry {index} {name} must be text")
    return value
