"""Debt machinery: the placeholder marker exception and its enumerator.

A placeholder is a real module at its real import path raising Owed --
the placeholder is the debt entry. Marker form rule v1 and the machinery
class are defined in docs/PLAN.md, Phase 2.
"""

import ast
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

ROOTS = ("src/sieve", "tests")

MODULE_QUALNAME = "<module>"


class Owed(Exception):
    """This scope is owed: present debt, announced structurally.

    Raised only in marker form rule v1 (docs/PLAN.md, Phase 2 gate,
    decision 4). Deliberately not an -Error name -- a marker is not a
    fault. Caught only by the debt machinery; catching it elsewhere is
    out of contract.
    """


class EnumerationError(Exception):
    """A file or Owed raise under an enumerated root that rule v1 cannot
    account for. Never a skip: a skipped file makes debt vanish while
    the mismatch test and the sentinel stay blind to it.
    """


@dataclass(frozen=True)
class Entry:
    """One marker, keyed by (path, qualname); reason is compared content."""

    path: str  # repo-relative POSIX path
    qualname: str  # dotted ClassDef/FunctionDef path, or MODULE_QUALNAME
    reason: str


def enumerate_markers(repo_root: Path, roots: Sequence[str] = ROOTS) -> list[Entry]:
    """Walk .py files under roots and return every rule-v1 marker, sorted.

    Static only: nothing under the roots is imported or executed.
    """
    repo_root = Path(repo_root)
    entries: list[Entry] = []
    for root in roots:
        root_dir = repo_root / root
        if not root_dir.is_dir():
            raise EnumerationError(f"enumerated root does not exist: {root}")
        for file in sorted(root_dir.rglob("*.py")):
            entries.extend(_scan_file(file, repo_root))
    seen: set[tuple[str, str]] = set()
    for entry in entries:
        key = (entry.path, entry.qualname)
        if key in seen:
            raise EnumerationError(
                f"duplicate marker key: {entry.path}::{entry.qualname}"
            )
        seen.add(key)
    return sorted(entries, key=lambda e: (e.path, e.qualname))


def _scan_file(file: Path, repo_root: Path) -> list[Entry]:
    rel = file.relative_to(repo_root).as_posix()
    try:
        source = file.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as err:
        raise EnumerationError(f"{rel}: unreadable, which is an error, not a skip: {err}") from err
    try:
        tree = ast.parse(source, filename=rel)
    except SyntaxError as err:
        raise EnumerationError(f"{rel}: unparseable, which is an error, not a skip: {err}") from err

    has_canonical, aliased = _owed_bindings(tree)

    entries: list[Entry] = []
    canonical_ids: set[int] = set()

    module_raise = _module_form_raise(tree)
    if module_raise is not None:
        # The module form's shape includes the canonical import.
        entries.append(Entry(rel, MODULE_QUALNAME, _reason(module_raise, True, rel, MODULE_QUALNAME)))
        canonical_ids.add(id(module_raise))

    for qualname, node in _callable_form_raises(tree.body, []):
        entries.append(Entry(rel, qualname, _reason(node, has_canonical, rel, qualname)))
        canonical_ids.add(id(node))

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Raise)
            and id(node) not in canonical_ids
            and _references_owed(node, aliased)
        ):
            raise EnumerationError(
                f"{rel}:{node.lineno}: Owed raised outside marker form rule v1"
            )

    return entries


def _owed_bindings(tree: ast.Module) -> tuple[bool, set[str]]:
    """The file's Owed bindings: (canonical import present, aliased names)."""
    has_canonical = False
    aliased: set[str] = set()
    for stmt in tree.body:
        if isinstance(stmt, ast.ImportFrom) and stmt.module == "sieve.debt" and stmt.level == 0:
            for alias in stmt.names:
                if alias.name == "Owed":
                    if alias.asname is None:
                        has_canonical = True
                    else:
                        aliased.add(alias.asname)
    return has_canonical, aliased


def _module_form_raise(tree: ast.Module) -> "ast.Raise | None":
    """Position (b): module body is exactly docstring + canonical import + raise."""
    body = _without_docstring(tree.body)
    if len(body) != 2:
        return None
    imp, last = body
    if not isinstance(last, ast.Raise) or not _references_owed(last, set()):
        return None
    if not (
        isinstance(imp, ast.ImportFrom)
        and imp.module == "sieve.debt"
        and imp.level == 0
        and [(a.name, a.asname) for a in imp.names] == [("Owed", None)]
    ):
        return None
    return last


def _callable_form_raises(body: Sequence[ast.stmt], stack: list[str]):
    """Position (a): the sole statement of a callable body after its docstring."""
    for stmt in body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qual = [*stack, stmt.name]
            inner = _without_docstring(stmt.body)
            if len(inner) == 1 and isinstance(inner[0], ast.Raise) and _references_owed(inner[0], set()):
                yield ".".join(qual), inner[0]
            else:
                yield from _callable_form_raises(stmt.body, qual)
        elif isinstance(stmt, ast.ClassDef):
            yield from _callable_form_raises(stmt.body, [*stack, stmt.name])


def _without_docstring(body: Sequence[ast.stmt]) -> list[ast.stmt]:
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return list(body[1:])
    return list(body)


def _references_owed(node: ast.Raise, aliased: set[str]) -> bool:
    """Statically visible reference to Owed; anything else is the adapter's job."""
    exc = node.exc
    if exc is None:
        return False
    target = exc.func if isinstance(exc, ast.Call) else exc
    if isinstance(target, ast.Name):
        return target.id == "Owed" or target.id in aliased
    if isinstance(target, ast.Attribute):
        return target.attr == "Owed"
    return False


def _reason(node: ast.Raise, has_canonical: bool, rel: str, qualname: str) -> str:
    """Validate a canonically positioned raise and extract its reason."""
    where = f"{rel}:{node.lineno}: {qualname}"
    if not has_canonical:
        raise EnumerationError(f"{where}: Owed raised without the canonical import")
    exc = node.exc
    if not (isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name) and exc.func.id == "Owed"):
        raise EnumerationError(f"{where}: Owed raised outside marker form rule v1")
    if node.cause is not None or exc.keywords or len(exc.args) != 1:
        raise EnumerationError(f"{where}: marker takes exactly one plain reason argument")
    arg = exc.args[0]
    if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value):
        raise EnumerationError(f"{where}: marker reason must be one non-empty static string literal")
    return arg.value
