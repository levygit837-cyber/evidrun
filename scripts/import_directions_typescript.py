from __future__ import annotations

import re
from pathlib import Path

TYPESCRIPT_SOURCE_SUFFIXES = (".ts", ".tsx", ".mjs", ".mts", ".cts")
TYPESCRIPT_FROM_IMPORT = re.compile(
    r"^[ \t]*(?:import|export)[ \t]+(?:type[ \t]+)?"
    r"(?:(?!;)[\s\S])*?\bfrom[ \t\r\n]*[\"']([^\"']+)[\"']",
    re.MULTILINE,
)
TYPESCRIPT_SIDE_EFFECT_IMPORT = re.compile(
    r"^[ \t]*import[ \t]*[\"']([^\"']+)[\"']",
    re.MULTILINE,
)
TYPESCRIPT_STATIC_REQUIRE = re.compile(
    r"^[ \t]*(?:"
    r"import[ \t]+[A-Za-z_$][\w$]*[ \t]*="
    r"|(?:const|let|var)[ \t]+[^;\n=]+?[ \t]*="
    r")[ \t]*require[ \t]*\([ \t]*[\"']([^\"']+)[\"'][ \t]*\)",
    re.MULTILINE,
)

JsxTag = tuple[str, int, int, bool, bool]


def resolve_typescript_path(specifier: str, source: Path, root: Path, tracked: set[str]) -> str:
    if not specifier.startswith("."):
        return specifier
    base = (source.parent / specifier).resolve()
    candidates = [
        base,
        *[base.with_suffix(suffix) for suffix in TYPESCRIPT_SOURCE_SUFFIXES],
        *[(base / f"index{suffix}") for suffix in TYPESCRIPT_SOURCE_SUFFIXES],
    ]
    for candidate in candidates:
        try:
            relative = str(candidate.relative_to(root))
        except ValueError:
            continue
        if relative in tracked:
            return relative
    return specifier


def _mask_comments_and_templates(text: str) -> str:
    masked = list(text)
    index = 0
    quote: str | None = None
    continued_string = False
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if quote is not None:
            if (quote == "`" or continued_string) and char not in {"\n", quote}:
                masked[index] = " "
            if char == "\\":
                if following == "\n" and quote != "`":
                    continued_string = True
                if (
                    (quote == "`" or continued_string)
                    and index + 1 < len(text)
                    and following != "\n"
                ):
                    masked[index + 1] = " "
                index += 2
                continue
            if char == quote:
                quote = None
                continued_string = False
            index += 1
            continue
        if char in {'"', "'", "`"}:
            quote = char
            if char == "`":
                masked[index] = " "
            index += 1
            continue
        if char == "/" and following == "/":
            while index < len(text) and text[index] != "\n":
                masked[index] = " "
                index += 1
            continue
        if char == "/" and following == "*":
            masked[index] = masked[index + 1] = " "
            index += 2
            while index < len(text):
                if text[index : index + 2] == "*/":
                    masked[index] = masked[index + 1] = " "
                    index += 2
                    break
                if text[index] != "\n":
                    masked[index] = " "
                index += 1
            continue
        index += 1
    return "".join(masked)


def _jsx_tag_at(text: str, start: int) -> JsxTag | None:
    index = start + 1
    closing = index < len(text) and text[index] == "/"
    if closing:
        index += 1
    if index < len(text) and text[index] == ">":
        return ("", start, index + 1, closing, False)
    if index >= len(text) or not text[index].isalpha():
        return None
    name_start = index
    while index < len(text) and (text[index].isalnum() or text[index] in "._:-"):
        index += 1
    name = text[name_start:index]
    quote: str | None = None
    while index < len(text):
        char = text[index]
        if quote is not None:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in {'"', "'"}:
            quote = char
        elif char == ">":
            self_closing = not closing and text[start:index].rstrip().endswith("/")
            return (name, start, index + 1, closing, self_closing)
        index += 1
    return None


def _jsx_tags(text: str) -> tuple[JsxTag, ...]:
    tags: list[JsxTag] = []
    index = 0
    quote: str | None = None
    while index < len(text):
        char = text[index]
        if quote is not None:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
            index += 1
            continue
        if char in {'"', "'"}:
            quote = char
            index += 1
            continue
        if char == "<":
            tag = _jsx_tag_at(text, index)
            if tag is not None:
                tags.append(tag)
                index = tag[2]
                continue
        index += 1
    return tuple(tags)


def _jsx_content_ranges(text: str) -> tuple[tuple[int, int], ...]:
    stack: list[JsxTag] = []
    ranges: list[tuple[int, int]] = []
    for tag in _jsx_tags(text):
        name, start, _, closing, self_closing = tag
        if self_closing:
            continue
        if not closing:
            stack.append(tag)
            continue
        match_index = next(
            (index for index in range(len(stack) - 1, -1, -1) if stack[index][0] == name),
            None,
        )
        if match_index is not None:
            opening = stack.pop(match_index)
            ranges.append((opening[2], start))
    return tuple(ranges)


def _mask_jsx_text(text: str) -> str:
    masked = list(text)
    for start, end in _jsx_content_ranges(text):
        brace_depth = 0
        quote: str | None = None
        index = start
        while index < end:
            char = text[index]
            if brace_depth:
                if quote is not None:
                    if char == "\\":
                        index += 2
                        continue
                    if char == quote:
                        quote = None
                elif char in {'"', "'", "`"}:
                    quote = char
                elif char == "{":
                    brace_depth += 1
                elif char == "}":
                    brace_depth -= 1
            elif char == "{":
                brace_depth = 1
            elif char != "\n":
                masked[index] = " "
            index += 1
    return "".join(masked)


def typescript_imports(text: str) -> tuple[str, ...]:
    source = _mask_jsx_text(_mask_comments_and_templates(text))
    matches = [
        (match.start(), match.group(1))
        for pattern in (
            TYPESCRIPT_FROM_IMPORT,
            TYPESCRIPT_SIDE_EFFECT_IMPORT,
            TYPESCRIPT_STATIC_REQUIRE,
        )
        for match in pattern.finditer(source)
    ]
    return tuple(specifier for _, specifier in sorted(matches))
