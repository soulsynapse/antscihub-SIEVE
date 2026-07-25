"""Report markdown voice violations across the repository.

[INTENT] This is a report, not a rewrite or a gate by default. The corpus is
not expected to be clean on arrival, so the script surfaces findings for a
human or another agent to work through and only fails when asked to gate the
main body.

[ASSUMPTION] The word lists are intentionally small and explicit. A broader
NLP classifier would be harder to trust in a repo-wide hygiene check, and the
goal here is to catch the obvious prose drift that the handoff named, not to
infer style from context.

Stdlib only.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOC_ROOT = ROOT / "docs"
LLM_WIKI = DOC_ROOT / "06-ops" / "LLM-wiki"
ROOT_MARKDOWN = ("AGENTS.md", "NOTES.md", "README.md", "SIEVE-HANDOFF.md")

TAG_NAMES = ("STABLE", "ASSUMPTION", "INTENT", "STALE WHEN", "OPEN QUESTION")
TAG_PATTERN = re.compile(r"\[(?:STABLE|ASSUMPTION|INTENT|STALE WHEN|OPEN QUESTION)\]")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(\S.*)$")
FENCE_PATTERN = re.compile(r"^\s*(```|~~~)")
INDENTED_CODE_PATTERN = re.compile(r"^(?: {4,}|\t)")
TABLE_DELIMITER_PATTERN = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*$")
INLINE_CODE_PATTERN = re.compile(r"`[^`\n]*`")
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^)\n]+)\)")
BARE_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
ABSOLUTE_TERMS = (
    "must not",
    "without exception",
    "no exception",
    "guaranteed",
    "guarantees",
    "guarantee",
    "ensures",
    "ensure",
    "cannot",
    "impossible",
    "always",
    "never",
    "every",
    "must",
    "all",
    "any",
)
ABSOLUTE_PATTERN = re.compile(
    r"\b(?:" + "|".join(re.escape(term) for term in ABSOLUTE_TERMS) + r")\b",
    re.IGNORECASE,
)
RUNTIME_PATTERN = re.compile(
    r"\b(?:decode|decoder|cache|worker|subprocess|thread|latency|executor|frame|gpu|import|imports|memory|process|render|ms|budget)\b",
    re.IGNORECASE,
)
IMPERATIVE_OPENERS = {
    "use",
    "do",
    "don't",
    "ensure",
    "avoid",
    "prefer",
    "run",
    "add",
    "keep",
    "treat",
    "make",
    "write",
    "register",
    "mark",
    "store",
    "provide",
    "separate",
    "retain",
    "implement",
    "create",
    "remove",
    "call",
    "set",
    "put",
    "follow",
    "apply",
    "check",
    "verify",
    "note",
    "consider",
    "remember",
}
TAG_TEXT = {tag: f"[{tag}]" for tag in TAG_NAMES}


@dataclass(slots=True)
class HeadingNode:
    level: int
    title: str
    line: int
    parent: int | None
    children: list[int] = field(default_factory=list)
    direct_tag: bool = False


@dataclass(slots=True)
class ProseLine:
    file_path: Path
    line: int
    raw_text: str
    visible_text: str
    section_id: int
    section_special: bool


@dataclass(slots=True)
class Paragraph:
    file_path: Path
    start_line: int
    raw_lines: list[str]
    visible_text: str
    section_id: int
    section_special: bool
    has_tag: bool


@dataclass(slots=True)
class Finding:
    file_path: Path
    line: int
    check: str
    token: str
    text: str


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _resolve_target(path_text: str) -> Path:
    path = Path(path_text)
    return path if path.is_absolute() else ROOT / path


def _is_target_file(path: Path, strict: bool) -> bool:
    if not path.is_file() or path.suffix.lower() != ".md":
        return False
    if any(parent == LLM_WIKI for parent in path.parents):
        return False
    if not strict:
        return True
    if path.name in ROOT_MARKDOWN:
        return True
    return any(parent == DOC_ROOT for parent in path.parents)


def _discover_files(paths: list[Path] | None) -> list[Path]:
    files: set[Path] = set()
    if paths:
        for path in paths:
            if path.is_dir():
                for candidate in path.rglob("*.md"):
                    if _is_target_file(candidate, strict=False):
                        files.add(candidate)
            elif _is_target_file(path, strict=False):
                files.add(path)
        return sorted(files, key=_display_path)

    for candidate in DOC_ROOT.rglob("*.md"):
        if _is_target_file(candidate, strict=True):
            files.add(candidate)
    for name in ROOT_MARKDOWN:
        candidate = ROOT / name
        if _is_target_file(candidate, strict=True):
            files.add(candidate)
    return sorted(files, key=_display_path)


def _clean_visible_text(text: str) -> str:
    text = INLINE_CODE_PATTERN.sub(" ", text)
    text = MARKDOWN_LINK_PATTERN.sub(r"\1", text)
    text = BARE_URL_PATTERN.sub(" ", text)
    return text


def _strip_leading_tags(text: str) -> str:
    remaining = text.lstrip()
    while True:
        match = re.match(
            r"^\[(?:STABLE|ASSUMPTION|INTENT|STALE WHEN|OPEN QUESTION)\]\s*",
            remaining,
        )
        if match is None:
            return remaining
        remaining = remaining[match.end() :].lstrip()


def _has_tag(text: str) -> bool:
    return bool(TAG_PATTERN.search(text))


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


DECISION_LEVEL = 2


def _normalize_title(text: str) -> str:
    return _collapse_whitespace(text).lower()


def _current_section_special(file_path: Path, stack: list[int], nodes: list[HeadingNode]) -> bool:
    if not any(part == "05-adr" for part in file_path.parts):
        return False
    for node_id in reversed(stack):
        if node_id == 0:
            continue
        node = nodes[node_id]
        if node.level == DECISION_LEVEL and _normalize_title(node.title) in {
            "decision",
            "consequences",
        }:
            return True
    return False


def _paragraph_text(lines: list[str]) -> str:
    return _collapse_whitespace(" ".join(lines))


def _scan_file(  # noqa: PLR0912, PLR0915
    file_path: Path,
) -> tuple[list[ProseLine], list[Paragraph], list[HeadingNode], list[str]]:
    nodes = [HeadingNode(level=0, title="ROOT", line=0, parent=None)]
    stack = [0]
    prose_lines: list[ProseLine] = []
    paragraphs: list[Paragraph] = []
    errors: list[str] = []

    in_frontmatter = False
    frontmatter_done = False
    in_fence = False
    fence_marker = ""
    paragraph_raw_lines: list[str] = []
    paragraph_visible_lines: list[str] = []
    paragraph_start = 0
    paragraph_section = 0
    paragraph_special = False
    paragraph_has_tag = False

    def flush_paragraph() -> None:
        nonlocal paragraph_raw_lines, paragraph_visible_lines, paragraph_start, paragraph_section
        nonlocal paragraph_special, paragraph_has_tag
        if not paragraph_raw_lines:
            return
        paragraphs.append(
            Paragraph(
                file_path=file_path,
                start_line=paragraph_start,
                raw_lines=paragraph_raw_lines[:],
                visible_text=_paragraph_text(paragraph_visible_lines),
                section_id=paragraph_section,
                section_special=paragraph_special,
                has_tag=paragraph_has_tag,
            )
        )
        paragraph_raw_lines = []
        paragraph_visible_lines = []
        paragraph_start = 0
        paragraph_section = 0
        paragraph_special = False
        paragraph_has_tag = False

    try:
        lines = file_path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        errors.append(f"{_display_path(file_path)}: {exc}")
        return [], paragraphs, nodes, errors

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()

        if not frontmatter_done and line_number == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
                frontmatter_done = True
            continue

        if in_fence:
            if stripped.startswith(fence_marker):
                in_fence = False
                fence_marker = ""
            continue

        if FENCE_PATTERN.match(line):
            flush_paragraph()
            in_fence = True
            match = FENCE_PATTERN.match(line)
            fence_marker = match.group(1) if match is not None else "```"
            continue

        if INDENTED_CODE_PATTERN.match(line):
            flush_paragraph()
            continue

        if not stripped:
            flush_paragraph()
            continue

        if TABLE_DELIMITER_PATTERN.match(line):
            flush_paragraph()
            continue

        heading_match = HEADING_PATTERN.match(line)
        if heading_match is not None:
            flush_paragraph()
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            while len(stack) > 1 and nodes[stack[-1]].level >= level:
                stack.pop()
            parent = stack[-1]
            nodes.append(HeadingNode(level=level, title=title, line=line_number, parent=parent))
            new_id = len(nodes) - 1
            nodes[parent].children.append(new_id)
            stack.append(new_id)
            if _has_tag(_clean_visible_text(line)):
                nodes[new_id].direct_tag = True
            section_id = new_id
            prose_lines.append(
                ProseLine(
                    file_path=file_path,
                    line=line_number,
                    raw_text=line,
                    visible_text=_clean_visible_text(line),
                    section_id=section_id,
                    section_special=_current_section_special(file_path, stack, nodes),
                )
            )
            continue

        visible_line = _clean_visible_text(line)
        section_id = stack[-1]
        section_special = _current_section_special(file_path, stack, nodes)
        prose_lines.append(
            ProseLine(
                file_path=file_path,
                line=line_number,
                raw_text=line,
                visible_text=visible_line,
                section_id=section_id,
                section_special=section_special,
            )
        )

        if not paragraph_raw_lines:
            paragraph_start = line_number
            paragraph_section = section_id
            paragraph_special = section_special
        paragraph_raw_lines.append(line)
        paragraph_visible_lines.append(visible_line)
        paragraph_has_tag = paragraph_has_tag or _has_tag(visible_line)

    flush_paragraph()
    return prose_lines, paragraphs, nodes, errors


def _subtree_has_tag(node_id: int, nodes: list[HeadingNode], memo: dict[int, bool]) -> bool:
    cached = memo.get(node_id)
    if cached is not None:
        return cached
    node = nodes[node_id]
    result = node.direct_tag or any(
        _subtree_has_tag(child_id, nodes, memo) for child_id in node.children
    )
    memo[node_id] = result
    return result


def _check_absolute_line(visible_line: str) -> list[str]:
    return [match.group(0).lower() for match in ABSOLUTE_PATTERN.finditer(visible_line)]


def _sentence_candidates(visible_line: str) -> list[str]:
    text = _strip_leading_tags(visible_line)
    bullet = re.match(r"^(?:[-*]|\d+\.)\s+(.*)$", text)
    if bullet is not None:
        text = bullet.group(1)
    return [candidate for candidate in re.split(r"(?<=[.!?])\s+", text) if candidate]


def _check_imperative_line(visible_line: str) -> list[str]:
    openers: list[str] = []
    for sentence in _sentence_candidates(visible_line):
        stripped = _strip_leading_tags(sentence).lstrip()
        if not stripped:
            continue
        words = re.findall(r"[A-Za-z][A-Za-z'\-]*", stripped)
        if not words:
            continue
        first = words[0].lower()
        if first == "do" and len(words) > 1 and words[1].lower() == "not":
            openers.append("Do not")
        elif first == "never":
            openers.append("Never")
        elif first in IMPERATIVE_OPENERS:
            openers.append(words[0])
    return openers


def _runtime_snippet(text: str) -> str:
    return _collapse_whitespace(text)[:100]


def _scan_findings(
    prose_lines: list[ProseLine],
    paragraphs: list[Paragraph],
    nodes: list[HeadingNode],
) -> tuple[list[Finding], list[Finding], dict[str, int], int, int]:
    memo: dict[int, bool] = {}
    main_findings: list[Finding] = []
    adr_findings: list[Finding] = []
    counts: dict[str, int] = defaultdict(int)
    main_total = 0
    adr_total = 0

    for line in prose_lines:
        target = adr_findings if line.section_special else main_findings
        for token in _check_absolute_line(line.visible_text):
            target.append(
                Finding(
                    file_path=line.file_path,
                    line=line.line,
                    check="absolute",
                    token=token,
                    text=line.raw_text,
                )
            )
            counts["absolute"] += 1
            if line.section_special:
                adr_total += 1
            else:
                main_total += 1
        for token in _check_imperative_line(line.visible_text):
            target.append(
                Finding(
                    file_path=line.file_path,
                    line=line.line,
                    check="imperative",
                    token=token,
                    text=line.raw_text,
                )
            )
            counts["imperative"] += 1
            if line.section_special:
                adr_total += 1
            else:
                main_total += 1

    for paragraph in paragraphs:
        section_has_tag = _subtree_has_tag(paragraph.section_id, nodes, memo)
        if (
            not paragraph.has_tag
            and not section_has_tag
            and RUNTIME_PATTERN.search(paragraph.visible_text)
        ):
            target = adr_findings if paragraph.section_special else main_findings
            target.append(
                Finding(
                    file_path=paragraph.file_path,
                    line=paragraph.start_line,
                    check="runtime",
                    token="runtime",
                    text=_runtime_snippet(paragraph.visible_text),
                )
            )
            counts["runtime"] += 1
            if paragraph.section_special:
                adr_total += 1
            else:
                main_total += 1

    return main_findings, adr_findings, dict(counts), main_total, adr_total


def _group_findings(findings: list[Finding]) -> dict[str, dict[str, list[Finding]]]:
    grouped: dict[str, dict[str, list[Finding]]] = defaultdict(lambda: defaultdict(list))
    for finding in findings:
        grouped[_display_path(finding.file_path)][finding.check].append(finding)
    return grouped


def _render_finding(finding: Finding) -> str:
    return f"  line {finding.line:<4}  [{finding.check}]   {finding.token:<12} | {finding.text}"


def _render_section(title: str, findings: list[Finding], empty_message: str) -> list[str]:
    lines = [title, ""]
    if not findings:
        lines.append(empty_message)
        return lines

    grouped = _group_findings(findings)
    for file_path in sorted(grouped):
        lines.append(f"### {file_path}")
        for check in ("absolute", "imperative", "runtime"):
            entries = sorted(grouped[file_path].get(check, []), key=_finding_sort_key)
            if not entries:
                continue
            lines.append(f"#### {check}")
            lines.extend(_render_finding(entry) for entry in entries)
            lines.append("")
        if lines and lines[-1] == "":
            lines.pop()
        lines.append("")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _finding_sort_key(finding: Finding) -> tuple[int, str, str]:
    return finding.line, finding.token, finding.text


def _render_markdown(
    main_findings: list[Finding],
    adr_findings: list[Finding],
    counts: dict[str, int],
    main_total: int,
    adr_total: int,
) -> str:
    lines = [
        "# Documentation voice",
        "",
        (
            "Descriptive voice violations in prose. The checker skips code "
            "blocks, inline code, link targets, bare URLs, and table delimiter "
            "rows."
        ),
        "",
    ]
    lines.extend(
        _render_section("## Main body", main_findings, "Nothing flagged in the main body.")
    )
    lines.append("")
    if adr_findings:
        lines.extend(
            _render_section(
                "## ADR Decision and Consequences sections (genre question unresolved)",
                adr_findings,
                "Nothing flagged in the ADR Decision and Consequences sections.",
            )
        )
        lines.append("")
    lines.extend(
        [
            "## Summary",
            "",
            f"- absolute: {counts.get('absolute', 0)}",
            f"- imperative: {counts.get('imperative', 0)}",
            f"- runtime: {counts.get('runtime', 0)}",
            f"- main body total: {main_total}",
            f"- ADR total: {adr_total}",
            f"- total: {sum(counts.values())}",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_json(  # noqa: PLR0913, PLR0917
    main_findings: list[Finding],
    adr_findings: list[Finding],
    counts: dict[str, int],
    main_total: int,
    adr_total: int,
    parse_errors: list[str],
) -> str:
    def serialize(finding: Finding) -> dict[str, Any]:
        return {
            "file": _display_path(finding.file_path),
            "line": finding.line,
            "check": finding.check,
            "token": finding.token,
            "text": finding.text,
        }

    payload: dict[str, Any] = {
        "schema_version": 1,
        "counts": {
            "absolute": counts.get("absolute", 0),
            "imperative": counts.get("imperative", 0),
            "runtime": counts.get("runtime", 0),
            "main_total": main_total,
            "adr_total": adr_total,
            "total": sum(counts.values()),
        },
        "findings": {
            "main": [serialize(finding) for finding in main_findings],
            "adr": [serialize(finding) for finding in adr_findings],
        },
        "parse_errors": parse_errors,
    }
    return json.dumps(payload, indent=2)


def _gate_exit(main_total: int, parse_errors: list[str]) -> int:
    if parse_errors:
        return 1
    return 1 if main_total else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    parser.add_argument(
        "--gate",
        action="store_true",
        help="exit 1 when the main body has findings",
    )
    parser.add_argument(
        "--path",
        action="append",
        type=Path,
        help="limit the scan to one or more files or directories",
    )
    args = parser.parse_args(argv)

    paths = [_resolve_target(str(path)) for path in args.path] if args.path else None
    main_findings: list[Finding] = []
    adr_findings: list[Finding] = []
    parse_errors: list[str] = []
    counts: dict[str, int] = defaultdict(int)
    main_total = 0
    adr_total = 0

    for file_path in _discover_files(paths):
        prose_lines, paragraphs, nodes, errors = _scan_file(file_path)
        parse_errors.extend(errors)
        if errors:
            continue
        file_main, file_adr, file_counts, file_main_total, file_adr_total = _scan_findings(
            prose_lines,
            paragraphs,
            nodes,
        )
        main_findings.extend(file_main)
        adr_findings.extend(file_adr)
        main_total += file_main_total
        adr_total += file_adr_total
        for key, value in file_counts.items():
            counts[key] += value

    if args.json:
        report = _render_json(
            main_findings,
            adr_findings,
            dict(counts),
            main_total,
            adr_total,
            parse_errors,
        )
    else:
        report = _render_markdown(main_findings, adr_findings, dict(counts), main_total, adr_total)

    # The corpus is full of en dashes and arrows, and a Windows console defaults
    # to cp1252, which raises on the first one. Reconfiguring the stream is
    # narrower than sanitizing the report: the findings quote source lines, so
    # mangling them here would misreport what the document says.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(report)

    for error in parse_errors:
        print(f"error: could not parse {error}", file=sys.stderr)

    if args.gate:
        return _gate_exit(main_total, parse_errors)
    return 1 if parse_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
