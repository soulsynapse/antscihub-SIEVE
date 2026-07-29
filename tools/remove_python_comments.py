from __future__ import annotations

import argparse
import ast
import io
import subprocess
import sys
import tokenize
from collections.abc import Iterable, Sequence
from pathlib import Path


EXCLUDED_DIRECTORIES = {
    ".git",
    ".mypy_cache",
    ".pyright",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
}


def _line_offsets(source: str) -> list[int]:
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def remove_comments(source: str) -> tuple[str, int]:
    offsets = _line_offsets(source)
    spans: list[tuple[int, int]] = []

    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.COMMENT:
            continue
        start = offsets[token.start[0] - 1] + token.start[1]
        end = offsets[token.end[0] - 1] + token.end[1]
        line_start = offsets[token.start[0] - 1]
        prefix = source[line_start:start]

        if prefix.isspace() or not prefix:
            start = line_start
        else:
            while start > line_start and source[start - 1] in " \t":
                start -= 1
        spans.append((start, end))

    result = source
    for start, end in reversed(spans):
        result = result[:start] + result[end:]
    return result, len(spans)


def remove_docstrings(source: str) -> tuple[str, int]:
    tree = ast.parse(source)
    offsets = _line_offsets(source)
    lines = source.splitlines(keepends=True)
    spans: list[tuple[int, int, bool, str]] = []
    owners = (
        ast.Module,
        ast.ClassDef,
        ast.FunctionDef,
        ast.AsyncFunctionDef,
    )

    for owner in ast.walk(tree):
        if not isinstance(owner, owners) or not owner.body:
            continue
        statement = owner.body[0]
        if (
            not isinstance(statement, ast.Expr)
            or not isinstance(statement.value, ast.Constant)
            or not isinstance(statement.value.value, str)
        ):
            continue
        if statement.end_lineno is None or statement.end_col_offset is None:
            raise ValueError("Python AST did not provide a complete docstring span")
        start_line = statement.lineno - 1
        end_line = statement.end_lineno - 1
        start_column = len(
            lines[start_line].encode("utf-8")[: statement.col_offset].decode("utf-8")
        )
        end_column = len(
            lines[end_line].encode("utf-8")[: statement.end_col_offset].decode("utf-8")
        )
        start = offsets[start_line] + start_column
        end = offsets[end_line] + end_column
        line_start = offsets[start_line]
        prefix = source[line_start:start]
        indent = prefix if prefix.isspace() else ""
        if indent:
            start = line_start
        spans.append((start, end, len(owner.body) == 1, indent))

    result = source
    for start, end, needs_pass, indent in sorted(spans, reverse=True):
        newlines = "".join(
            character for character in result[start:end] if character in "\r\n"
        )
        replacement = (f"{indent}pass" if needs_pass else "") + newlines
        result = result[:start] + replacement + result[end:]
    return result, len(spans)


def clean_blank_lines(source: str) -> str:
    if not source.strip():
        return ""
    cleaned: list[str] = []
    for line in source.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        ending = line[len(content) :]
        cleaned.append(ending if content and content.isspace() else line)
    result = "".join(cleaned)
    if source.endswith("\r\n"):
        final_ending = "\r\n"
    elif source.endswith("\n"):
        final_ending = "\n"
    elif source.endswith("\r"):
        final_ending = "\r"
    else:
        final_ending = ""
    return result.rstrip(" \t\r\n") + final_ending


def _read_source(path: Path) -> tuple[str, str]:
    with path.open("rb") as stream:
        encoding, _ = tokenize.detect_encoding(stream.readline)
        stream.seek(0)
        return stream.read().decode(encoding), encoding


def _tracked_python_files(root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--", "*.py"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return [
        root / name
        for name in result.stdout.splitlines()
        if name and (root / name).is_file()
    ]


def _directory_python_files(path: Path) -> Iterable[Path]:
    for candidate in path.rglob("*.py"):
        if not any(part in EXCLUDED_DIRECTORIES for part in candidate.parts):
            yield candidate


def _resolve_targets(targets: Sequence[str]) -> list[Path]:
    if not targets:
        root_result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
        return _tracked_python_files(Path(root_result.stdout.strip()))

    files: set[Path] = set()
    for raw_target in targets:
        target = Path(raw_target)
        if target.is_dir():
            files.update(_directory_python_files(target))
        elif target.suffix == ".py":
            files.add(target)
        else:
            raise ValueError(f"not a Python file or directory: {target}")
    return sorted(files)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Remove Python comment tokens while preserving strings, docstrings, "
            "line endings, and source encoding."
        )
    )
    parser.add_argument(
        "targets",
        nargs="*",
        help="Python files or directories; defaults to Git-tracked Python files",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="rewrite files in place; without this flag, only report changes",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit with status 1 if any target contains comments",
    )
    parser.add_argument(
        "--docstrings",
        action="store_true",
        help="also remove module, class, function, and method docstrings",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        targets = _resolve_targets(args.targets)
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    changed_files = 0
    removed_comments = 0
    removed_docstrings = 0
    for path in targets:
        try:
            source, encoding = _read_source(path)
            updated, comment_count = remove_comments(source)
            docstring_count = 0
            if args.docstrings:
                updated, docstring_count = remove_docstrings(updated)
            updated = clean_blank_lines(updated)
            if updated == source:
                continue
            compile(updated, str(path), "exec")
            changed_files += 1
            removed_comments += comment_count
            removed_docstrings += docstring_count
            action = "updated" if args.write else "would update"
            details = [f"{comment_count} comments"]
            if args.docstrings:
                details.append(f"{docstring_count} docstrings")
            print(f"{action}: {path} ({', '.join(details)})")
            if args.write:
                path.write_bytes(updated.encode(encoding))
        except (OSError, SyntaxError, UnicodeError, tokenize.TokenError) as error:
            print(f"error: {path}: {error}", file=sys.stderr)
            return 2

    action = "Removed" if args.write else "Found"
    summary = f"{removed_comments} comments"
    if args.docstrings:
        summary += f" and {removed_docstrings} docstrings"
    print(f"{action} {summary} in {changed_files} files.")
    if args.check and changed_files:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
