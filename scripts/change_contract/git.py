"""Git inspection for a change contract, including a dirty worktree."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class GitError(RuntimeError):
    pass


class ChangeSource(StrEnum):
    COMMITTED = "committed"
    WORKTREE = "worktree"


@dataclass(frozen=True)
class GitChange:
    path: str
    status: str
    old_path: str | None
    sources: tuple[ChangeSource, ...]

    @property
    def affected_paths(self) -> tuple[str, ...]:
        return (self.path,) if self.old_path is None else (self.old_path, self.path)


@dataclass(frozen=True)
class AddedLine:
    path: str
    line: int
    content: str


@dataclass(frozen=True)
class GitSnapshot:
    root: Path
    base_ref: str
    merge_base: str
    head: str
    branch: str | None
    changes: tuple[GitChange, ...]
    untracked: tuple[str, ...]
    added_lines: tuple[AddedLine, ...]
    normative_documents: tuple[str, ...]

    @property
    def changed_paths(self) -> tuple[str, ...]:
        return tuple(sorted({path for change in self.changes for path in change.affected_paths}))


def inspect_repository(root: Path, base_ref: str) -> GitSnapshot:
    """Inspect committed and tracked worktree changes from the true merge-base."""

    repository_root = Path(_git_text(root, "rev-parse", "--show-toplevel")).resolve()
    merge_base = _git_text(repository_root, "merge-base", base_ref, "HEAD")
    head = _git_text(repository_root, "rev-parse", "HEAD")
    branch = _git_text(repository_root, "branch", "--show-current") or None
    committed = _name_status(
        _git_bytes(
            repository_root,
            "diff",
            "--name-status",
            "-z",
            "--find-renames",
            merge_base,
            "HEAD",
        ),
        ChangeSource.COMMITTED,
    )
    worktree = _name_status(
        _git_bytes(
            repository_root,
            "diff",
            "--name-status",
            "-z",
            "--find-renames",
            "HEAD",
        ),
        ChangeSource.WORKTREE,
    )
    changes = _combine_changes((*committed, *worktree))
    untracked = tuple(
        sorted(
            item.decode("utf-8", errors="surrogateescape")
            for item in _git_bytes(
                repository_root, "ls-files", "--others", "--exclude-standard", "-z"
            ).split(b"\0")
            if item
        )
    )
    added_lines = _added_lines(
        repository_root,
        ((merge_base, "HEAD"), ("HEAD",)),
    )
    return GitSnapshot(
        root=repository_root,
        base_ref=base_ref,
        merge_base=merge_base,
        head=head,
        branch=branch,
        changes=changes,
        untracked=untracked,
        added_lines=added_lines,
        normative_documents=_normative_documents(repository_root, merge_base, changes),
    )


def resolve_commit(root: Path, revision: str) -> str | None:
    """Resolve a revision to a full SHA, or None when the repository does not know it."""

    result = subprocess.run(
        ("git", "rev-parse", "--verify", f"{revision}^{{commit}}"),
        cwd=root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", errors="replace").strip() or None


def paths_changed_since(root: Path, commit: str, head: str) -> tuple[str, ...]:
    """Paths that differ between `commit` and `head`, including the dirty worktree.

    Used to decide whether a recorded CI run still covers the candidate commit: if a
    delivered file changed afterwards, the suite ran against different code.
    """

    if commit == head:
        changed = _name_status(
            _git_bytes(root, "diff", "--name-status", "-z", "--find-renames", "HEAD"),
            ChangeSource.WORKTREE,
        )
    else:
        changed = _combine_changes(
            (
                *_name_status(
                    _git_bytes(
                        root, "diff", "--name-status", "-z", "--find-renames", commit, head
                    ),
                    ChangeSource.COMMITTED,
                ),
                *_name_status(
                    _git_bytes(root, "diff", "--name-status", "-z", "--find-renames", "HEAD"),
                    ChangeSource.WORKTREE,
                ),
            )
        )
    return tuple(sorted({path for item in changed for path in item.affected_paths}))


def _git_text(root: Path, *args: str) -> str:
    return _git_bytes(root, *args).decode("utf-8", errors="replace").strip()


def _git_bytes(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ("git", *args),
        cwd=root,
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitError(f"git {' '.join(args)} falhou: {error}")
    return result.stdout


def _name_status(output: bytes, source: ChangeSource) -> tuple[GitChange, ...]:
    fields = output.split(b"\0")
    changes: list[GitChange] = []
    index = 0
    while index < len(fields) and fields[index]:
        status = fields[index].decode("ascii", errors="replace")
        index += 1
        if index >= len(fields):
            raise GitError("saida truncada de git diff --name-status")
        first = fields[index].decode("utf-8", errors="surrogateescape")
        index += 1
        if status.startswith(("R", "C")):
            if index >= len(fields):
                raise GitError("rename/copy truncado em git diff --name-status")
            second = fields[index].decode("utf-8", errors="surrogateescape")
            index += 1
            changes.append(GitChange(second, status[0], first, (source,)))
        else:
            changes.append(GitChange(first, status[:1], None, (source,)))
    return tuple(changes)


def _combine_changes(changes: tuple[GitChange, ...]) -> tuple[GitChange, ...]:
    combined: dict[tuple[str, str | None], GitChange] = {}
    for change in changes:
        key = (change.path, change.old_path)
        previous = combined.get(key)
        if previous is None:
            combined[key] = change
            continue
        sources = tuple(sorted({*previous.sources, *change.sources}))
        combined[key] = GitChange(change.path, change.status, change.old_path, sources)
    return tuple(sorted(combined.values(), key=lambda item: (item.path, item.old_path or "")))


def _added_lines(root: Path, ranges: tuple[tuple[str, ...], ...]) -> tuple[AddedLine, ...]:
    additions: dict[tuple[str, int, str], AddedLine] = {}
    for diff_range in ranges:
        patch = _git_text(
            root,
            "diff",
            "--no-ext-diff",
            "--no-color",
            "--unified=0",
            *diff_range,
            "--",
        )
        for addition in _parse_added_lines(patch):
            additions[(addition.path, addition.line, addition.content)] = addition
    return tuple(sorted(additions.values(), key=lambda item: (item.path, item.line, item.content)))


def _parse_added_lines(patch: str) -> tuple[AddedLine, ...]:
    path: str | None = None
    next_line: int | None = None
    additions: list[AddedLine] = []
    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
            continue
        if line.startswith("+++ /dev/null"):
            path = None
            continue
        if line.startswith("@@"):
            match = re.search(r"\+(\d+)(?:,\d+)?", line)
            next_line = int(match.group(1)) if match else None
            continue
        if next_line is None:
            continue
        if line.startswith("+") and not line.startswith("+++"):
            if path is not None:
                additions.append(AddedLine(path, next_line, line[1:]))
            next_line += 1
        elif line.startswith(" "):
            next_line += 1
        elif line.startswith("-"):
            continue
        else:
            next_line = None
    return tuple(additions)


def _normative_documents(
    root: Path, merge_base: str, changes: tuple[GitChange, ...]
) -> tuple[str, ...]:
    candidates = {
        path
        for change in changes
        for path in change.affected_paths
        if path.startswith("docs/") and path.endswith(".md")
    }
    normative: set[str] = set()
    for path in candidates:
        current_path = root / path
        current = (
            current_path.read_text(encoding="utf-8", errors="replace")
            if current_path.is_file()
            else None
        )
        baseline = _git_optional_text(root, "show", f"{merge_base}:{path}")
        if any(_document_authority(text) == "normative" for text in (current, baseline)):
            normative.add(path)
    return tuple(sorted(normative))


def _git_optional_text(root: Path, *args: str) -> str | None:
    result = subprocess.run(("git", *args), cwd=root, check=False, capture_output=True)
    if result.returncode != 0:
        return None
    return result.stdout.decode("utf-8", errors="replace")


def _document_authority(text: str | None) -> str | None:
    if text is None or not text.startswith("---\n"):
        return None
    for line in text.splitlines()[1:]:
        if line == "---":
            return None
        key, separator, value = line.partition(":")
        if separator and key.strip() == "authority":
            return value.strip()
    return None
