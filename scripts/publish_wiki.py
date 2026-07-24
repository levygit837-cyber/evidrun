#!/usr/bin/env python3
"""Convert the hierarchical droid-wiki/ tree into a flat GitHub Wiki checkout.

The GitHub Wiki is a flat git repository. This script flattens nested paths
using "--" as a separator (matching `droid wiki-upload --upload-to github`),
rewrites internal markdown links to the flattened page names, promotes
overview/index.md to Home.md, and generates a _Sidebar.md from .wiki-meta.json.

No LLM or network access is required: this only moves and rewrites files.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

LINK_RE = re.compile(r"(!?\[[^\]]*\])\(([^)]+)\)")


def page_name(rel_path: str) -> str:
    """Map a droid-wiki relative path (posix, with .md) to a wiki page name."""
    rel = rel_path.replace("\\", "/")
    if rel == "overview/index.md":
        return "Home"
    if rel.endswith("/index.md"):
        rel = rel[: -len("/index.md")]
    else:
        rel = rel[: -len(".md")] if rel.endswith(".md") else rel
    return rel.replace("/", "--")


def wiki_filename(name: str) -> str:
    return f"{name}.md"


def build_page_map(source: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for md in source.rglob("*.md"):
        rel = md.relative_to(source).as_posix()
        mapping[rel] = page_name(rel)
    return mapping


def rewrite_links(
    text: str,
    current_rel: str,
    page_map: dict[str, str],
    repo_blob_base: str | None,
) -> str:
    current_dir = Path(current_rel).parent

    def replace(match: re.Match[str]) -> str:
        label, target = match.group(1), match.group(2)
        if label.startswith("!"):
            return match.group(0)  # leave images untouched
        raw = target.strip()
        if raw.startswith(("http://", "https://", "mailto:", "#")):
            return match.group(0)
        anchor = ""
        if "#" in raw:
            raw, anchor = raw.split("#", 1)
            anchor = "#" + anchor
        if not raw.endswith(".md"):
            return match.group(0)
        # Resolve the link relative to the current page, tracking segments that
        # escape the wiki root (those point at the main repository).
        parts: list[str] = [p for p in current_dir.parts if p not in (".", "")]
        escape = 0
        for part in Path(raw).parts:
            if part == ".":
                continue
            if part == "..":
                if parts:
                    parts.pop()
                else:
                    escape += 1
            else:
                parts.append(part)
        norm = "/".join(parts)
        if escape == 0 and norm in page_map:
            return f"{label}({page_map[norm]}{anchor})"
        # A single escape lands on the repo root, since droid-wiki/ sits there.
        if escape == 1 and repo_blob_base and norm:
            return f"{label}({repo_blob_base.rstrip('/')}/{norm})"
        return match.group(0)

    return LINK_RE.sub(replace, text)


def load_titles(source: Path, page_map: dict[str, str]) -> dict[str, str]:
    titles: dict[str, str] = {}
    for rel in page_map:
        first_heading = ""
        for line in (source / rel).read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                first_heading = line[2:].strip()
                break
        titles[rel] = first_heading or page_map[rel]
    return titles


def build_sidebar(source: Path, page_map: dict[str, str], titles: dict[str, str]) -> str:
    meta_path = source / ".wiki-meta.json"
    order: list[str]
    if meta_path.exists():
        order = json.loads(meta_path.read_text(encoding="utf-8")).get("pageOrder", [])
    else:
        order = sorted(page_map)
    seen: set[str] = set()
    lines = ["# Evidrun Wiki", ""]
    for rel in order:
        if rel not in page_map:
            continue
        seen.add(rel)
        depth = 0 if "/" not in rel else 1
        indent = "  " * depth
        lines.append(f"{indent}- [{titles.get(rel, page_map[rel])}]({page_map[rel]})")
    for rel in sorted(page_map):
        if rel not in seen:
            lines.append(f"- [{titles.get(rel, page_map[rel])}]({page_map[rel]})")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="droid-wiki")
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--repo-blob-base",
        default=None,
        help="Base URL for links into the main repo, e.g. "
        "https://github.com/owner/repo/blob/main",
    )
    args = parser.parse_args()

    source = Path(args.source).resolve()
    output = Path(args.output).resolve()
    if not source.is_dir():
        raise SystemExit(f"source wiki directory not found: {source}")

    page_map = build_page_map(source)
    if not page_map:
        raise SystemExit(f"no markdown pages found under {source}")
    titles = load_titles(source, page_map)

    # Clear previously generated wiki pages (keep .git and other VCS metadata).
    for item in output.iterdir():
        if item.name == ".git":
            continue
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    for rel, name in page_map.items():
        text = (source / rel).read_text(encoding="utf-8")
        text = rewrite_links(text, rel, page_map, args.repo_blob_base)
        (output / wiki_filename(name)).write_text(text, encoding="utf-8")

    (output / "_Sidebar.md").write_text(
        build_sidebar(source, page_map, titles), encoding="utf-8"
    )
    print(f"Wrote {len(page_map)} page(s) + _Sidebar.md to {output}")


if __name__ == "__main__":
    main()
