from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceLine:
    path: str
    line: int
    content: str


@dataclass(frozen=True)
class Finding:
    rule: str
    path: str
    line: int
    column: int
    match_sha256: str

    def location(self) -> str:
        return f"{self.path}:{self.line}:{self.column}"
