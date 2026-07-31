from __future__ import annotations

import hashlib
import re
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from .model import Finding, SourceLine
from .policy import Policy


@dataclass(frozen=True)
class Rule:
    id: str
    pattern: re.Pattern[str]


RULES = (
    Rule("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    Rule("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    Rule("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    Rule("openai-api-key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b")),
    Rule("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    Rule("slack-token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{20,}\b")),
    Rule(
        "authorization-bearer",
        re.compile(r"(?i)\bBearer[ \t]+[A-Za-z0-9._~+/=-]{24,}\b"),
    ),
)


def tracked_paths(root: Path) -> tuple[Path, ...]:
    completed = subprocess.run(
        ("git", "ls-files", "-z"),
        cwd=root,
        capture_output=True,
        check=True,
    )
    return tuple(root / item for item in completed.stdout.decode("utf-8").split("\0") if item)


def scan_paths(root: Path, paths: Iterable[Path], policy: Policy) -> tuple[Finding, ...]:
    lines: list[SourceLine] = []
    for path in paths:
        absolute = path if path.is_absolute() else root / path
        content = (
            str(absolute.readlink()).encode("utf-8", errors="surrogateescape")
            if absolute.is_symlink()
            else absolute.read_bytes()
        )
        # Secret signatures are ASCII. Surrogate escape preserves invalid bytes without
        # classifying them as word characters, so binary prefixes cannot suppress a
        # token boundary and non-UTF-8 files never become a silent scanner bypass.
        text = content.decode("utf-8", errors="surrogateescape")
        relative = (
            (absolute.parent.resolve() / absolute.name)
            .relative_to(root.resolve())
            .as_posix()
        )
        lines.extend(
            SourceLine(path=relative, line=number, content=line)
            for number, line in enumerate(text.splitlines(), start=1)
        )
    return scan_lines(lines, policy)


def scan_lines(lines: Iterable[SourceLine], policy: Policy) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    for source in lines:
        for rule in RULES:
            for match in rule.pattern.finditer(source.content):
                finding = Finding(
                    rule=rule.id,
                    path=source.path,
                    line=source.line,
                    column=match.start() + 1,
                    match_sha256=hashlib.sha256(match.group().encode("utf-8")).hexdigest(),
                )
                if not policy.permits(finding):
                    findings.append(finding)
    return tuple(findings)
