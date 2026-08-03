"""Debt machinery: the placeholder marker exception and its enumerator.

A placeholder is a real module at its real import path raising Owed --
the placeholder is the debt entry; any other tracked text file states one
debt with a column-0 ``Owed:`` line. Marker form rule v2 and the
machinery class are defined in docs/par/0002-debt-is-derived-from-the-tree.md.
"""

import ast
import re
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

SENTINEL_ROOT = "tests/_sentinel"

LEDGER_NAME = "DEBT-AUTO.txt"

# Named boundaries, not leniencies (PAR-0002, "The universal surface"):
# the sentinel is a liveness proof, the ledger is machinery output, and
# the frozen tier states no live debt -- a frozen enumeration error could
# never be edited away.
EXCLUDED = (SENTINEL_ROOT, LEDGER_NAME, "docs/archive")

MODULE_QUALNAME = "<module>"
FILE_QUALNAME = "<file>"

# Every line boundary str.splitlines() honors, except LF. A reason containing
# any of these would put non-LF bytes in the ledger and break parse as
# serialize's inverse.
_NON_LF_BOUNDARIES = ''.join(
    map(chr, (0x0D, 0x0B, 0x0C, 0x1C, 0x1D, 0x1E, 0x85, 0x2028, 0x2029))
)

FORMAT_VERSION = 2
MARKER_RULE = "v2"

# The statement stamp: UTC, second resolution, one canonical fixed-width
# spelling. It is the entry's identity -- it survives relocation and
# rewording -- and the minimum priority signal carried on the line.
STAMP_FORMAT = "%Y%m%dT%H%M%SZ"
REPO_EPOCH = "20260801T000000Z"
_FUTURE_SLACK = timedelta(days=1)
_STAMPED_REASON = re.compile(r"(\d{8}T\d{6}Z): (.+)", re.DOTALL)
_TEXT_MARKER = re.compile(r"Owed: (\d{8}T\d{6}Z): (.+)")

_HEADER = (
    "# SIEVE automatic ledger. Generated; never hand-edit.\n"
    "# Regenerate: python -m sieve.debt write\n"
    f"format-version: {FORMAT_VERSION}\n"
    f"marker-rule: {MARKER_RULE}\n"
)


class Owed(Exception):
    """This scope is owed: present debt, announced structurally.

    Raised only in marker form rule v2 (PAR-0002). Deliberately not an
    -Error name -- a marker is not a fault. Caught only by the debt
    machinery; catching it elsewhere is out of contract.
    """


class EnumerationError(Exception):
    """A file or Owed marker under the enumerated surface that rule v2
    cannot account for. Never a skip: a skipped file makes debt vanish
    while the mismatch test and the sentinel stay blind to it.
    """


@dataclass(frozen=True)
class Entry:
    """One marker: keyed by (path, qualname), identified by its stamp."""

    path: str  # repo-relative POSIX path
    qualname: str  # dotted qualname, MODULE_QUALNAME, or FILE_QUALNAME
    stamp: str  # UTC statement stamp, the entry's identity
    reason: str  # compared content, stamp-stripped


def enumerate_markers(
    repo_root: Path,
    roots: "Sequence[str] | None" = None,
    excluded: Sequence[str] = EXCLUDED,
) -> list[Entry]:
    """Return every rule-v2 marker under the surface, sorted by location.

    With roots=None the universe is the git index -- tracked plus
    untracked-not-ignored, so a marker is visible to regen before its
    first commit. Explicit roots walk the filesystem instead, so the
    machinery's own tests run against fixture trees. Static only:
    nothing under the surface is imported or executed.
    """
    repo_root = Path(repo_root)
    if roots is None:
        files = _git_universe(repo_root)
    else:
        files = []
        for root in roots:
            root_dir = repo_root / root
            if not root_dir.is_dir():
                raise EnumerationError(f"enumerated root does not exist: {root}")
            files.extend(
                p.relative_to(repo_root).as_posix()
                for p in sorted(root_dir.rglob("*"))
                if p.is_file()
            )
    entries: list[Entry] = []
    for rel in sorted(files):
        if any(rel == p or rel.startswith(p + "/") for p in excluded):
            continue
        if not (repo_root / rel).is_file():
            # Named boundary: the surface is regular files. Git can list
            # symlinks, junctions, and gitlinks; none of them is a text.
            continue
        if rel.endswith(".py"):
            entries.extend(_scan_python(repo_root / rel, rel))
        else:
            entries.extend(_scan_text(repo_root / rel, rel))
    seen: set[tuple[str, str]] = set()
    stamps: dict[str, str] = {}
    for entry in entries:
        key = (entry.path, entry.qualname)
        if key in seen:
            raise EnumerationError(
                f"duplicate marker key: {entry.path}::{entry.qualname}"
            )
        seen.add(key)
        holder = stamps.setdefault(entry.stamp, f"{entry.path}::{entry.qualname}")
        if holder != f"{entry.path}::{entry.qualname}":
            raise EnumerationError(
                f"duplicate stamp {entry.stamp}: {holder} and "
                f"{entry.path}::{entry.qualname} -- one stamp is the grain "
                "of one debt's history"
            )
    return sorted(entries, key=lambda e: (e.path, e.qualname))


def serialize(entries: Sequence[Entry]) -> bytes:
    """The automatic ledger's canonical bytes: format-version 2.

    Column 0 is a key line (`path :: qualname :: stamp`); four-space
    indentation is reason content, so a multiline reason needs no
    escaping. Additive-only evolution; nothing derivable beyond the
    entries themselves.
    """
    parts = [_HEADER]
    if entries:
        parts.append("\n")
        for entry in sorted(entries, key=lambda e: (e.path, e.qualname)):
            parts.append(f"{entry.path} :: {entry.qualname} :: {entry.stamp}\n")
            for line in entry.reason.split("\n"):
                parts.append(f"    {line}\n")
    return "".join(parts).encode("utf-8")


def parse(data: bytes) -> list[Entry]:
    """Inverse of serialize, for entry-level diff reporting on mismatch."""
    lines = data.decode("utf-8").splitlines()
    # Entries begin after the blank line that ends the header; a header-only
    # ledger has no blank line. Header lines can never parse as entries,
    # whatever future (additive) header fields contain.
    body: list[str] = []
    for i, line in enumerate(lines):
        if line == "":
            body = lines[i + 1 :]
            break
    entries: list[Entry] = []
    key: "tuple[str, str, str] | None" = None
    reason_lines: list[str] = []
    for line in body:
        if line.startswith("    "):
            reason_lines.append(line[4:])
        elif line.count(" :: ") == 2:
            if key is not None:
                entries.append(Entry(*key, "\n".join(reason_lines)))
            path, qualname, stamp = line.split(" :: ")
            key = (path, qualname, stamp)
            reason_lines = []
    if key is not None:
        entries.append(Entry(*key, "\n".join(reason_lines)))
    return entries


def entry_diff(old: Sequence[Entry], new: Sequence[Entry]) -> str:
    """Entry-level diff joined on the stamp: added / removed / changed /
    moved, sorted by location.

    This is the mismatch test's failure output: it keeps "stale ledger",
    "unintended debt change", and "relocation" distinguishable at the
    point of failure. A location losing one stamp and gaining another is
    flagged as identity churn rather than read silently as a discharge
    plus a new debt.
    """
    old_by = {e.stamp: e for e in old}
    new_by = {e.stamp: e for e in new}
    keyed: list[tuple[tuple[str, str], int, str]] = []
    removed: dict[tuple[str, str], Entry] = {}
    added: dict[tuple[str, str], Entry] = {}
    for stamp in old_by.keys() | new_by.keys():
        o, n = old_by.get(stamp), new_by.get(stamp)
        if n is None:
            removed[(o.path, o.qualname)] = o
            keyed.append(((o.path, o.qualname), 0, f"removed: {o.path} :: {o.qualname} :: {stamp}"))
        elif o is None:
            added[(n.path, n.qualname)] = n
            keyed.append(((n.path, n.qualname), 0, f"added:   {n.path} :: {n.qualname} :: {stamp}"))
        else:
            if (o.path, o.qualname) != (n.path, n.qualname):
                keyed.append((
                    (n.path, n.qualname), 1,
                    f"moved:   {o.path} :: {o.qualname} -> {n.path} :: {n.qualname} [{stamp}]",
                ))
            if o.reason != n.reason:
                keyed.append(((n.path, n.qualname), 2, f"changed: {n.path} :: {n.qualname} :: {stamp}"))
    for loc in sorted(removed.keys() & added.keys()):
        keyed.append((
            loc, 3,
            f"rekeyed? {loc[0]} :: {loc[1]} ({removed[loc].stamp} -> "
            f"{added[loc].stamp}): same scope, new stamp -- identity churn, "
            "not discharge-plus-new?",
        ))
    return "\n".join(line for _, _, line in sorted(keyed))


def stamp_landings(repo_root: Path) -> "dict[str, datetime]":
    """First-ledger-appearance time per stamp, from git history.

    The audit's other half lives at enumeration (form, epoch, future,
    duplicates); this is the history-dependent half -- a stamp cannot
    postdate its own landing -- and it is computed on call, never stored
    (PAR-0002, "The line, and the history").
    """
    head = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--verify", "HEAD"],
        capture_output=True,
    )
    if head.returncode != 0:
        # A repo with no commits has no landings; that is empty history,
        # not an unavailable instrument.
        return {}
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "log", "--reverse",
         "--format=commit-time %cI", "-p", "--", LEDGER_NAME],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise EnumerationError(
            f"git history unavailable for {LEDGER_NAME}: "
            + proc.stderr.decode("utf-8", errors="replace").strip()
        )
    landings: dict[str, datetime] = {}
    current: "datetime | None" = None
    for line in proc.stdout.decode("utf-8", errors="replace").splitlines():
        if line.startswith("commit-time "):
            current = datetime.fromisoformat(line.removeprefix("commit-time "))
        elif line.startswith("+") and current is not None and line.count(" :: ") == 2:
            stamp = line.split(" :: ")[-1]
            if _STAMPED_REASON.fullmatch(stamp + ": x") and stamp not in landings:
                landings[stamp] = current
    return landings


def parse_stamp(stamp: str) -> datetime:
    """The stamp's instant, timezone-aware UTC. Raises ValueError off-form."""
    return datetime.strptime(stamp, STAMP_FORMAT).replace(tzinfo=timezone.utc)


def main(argv: Sequence[str]) -> int:
    """The one-command write mode; the mismatch test is the only check."""
    if len(argv) not in (1, 2) or argv[0] != "write":
        print("usage: python -m sieve.debt write [repo_root]", file=sys.stderr)
        return 2
    repo_root = Path(argv[1]) if len(argv) == 2 else Path.cwd()
    entries = enumerate_markers(repo_root)
    ledger = repo_root / LEDGER_NAME
    ledger.write_bytes(serialize(entries))
    print(f"{ledger}: {len(entries)} entries (marker rule {MARKER_RULE})")
    return 0


def _git_universe(repo_root: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files", "--cached", "--others",
         "--exclude-standard"],
        capture_output=True,
    )
    if proc.returncode != 0:
        raise EnumerationError(
            "the enumeration universe is the git index and git could not "
            "provide it: " + proc.stderr.decode("utf-8", errors="replace").strip()
        )
    return proc.stdout.decode("utf-8").splitlines()


def _split_stamped(value: str, where: str) -> tuple[str, str]:
    m = _STAMPED_REASON.fullmatch(value)
    if m is None:
        raise EnumerationError(
            f"{where}: marker reason must open with its UTC statement stamp "
            "('YYYYMMDDTHHMMSSZ: ')"
        )
    stamp, reason = m.group(1), m.group(2)
    try:
        instant = parse_stamp(stamp)
    except ValueError as err:
        raise EnumerationError(f"{where}: nonsense stamp {stamp}: {err}") from err
    if instant < parse_stamp(REPO_EPOCH):
        raise EnumerationError(
            f"{where}: stamp {stamp} predates the repo epoch {REPO_EPOCH}"
        )
    if instant > datetime.now(timezone.utc) + _FUTURE_SLACK:
        raise EnumerationError(f"{where}: stamp {stamp} is in the future")
    return stamp, reason


def _scan_text(file: Path, rel: str) -> list[Entry]:
    try:
        raw = file.read_bytes()
    except OSError as err:
        raise EnumerationError(
            f"{rel}: unreadable, which is an error, not a skip: {err}"
        ) from err
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        # A named boundary, not a leniency: files that do not decode as
        # UTF-8 are outside the text surface (PAR-0002).
        return []
    entries: list[Entry] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.startswith("Owed:"):
            continue
        where = f"{rel}:{lineno}: {FILE_QUALNAME}"
        m = _TEXT_MARKER.fullmatch(line)
        if m is None:
            raise EnumerationError(
                f"{where}: column-0 'Owed:' line outside marker form rule v2"
            )
        stamp, reason = _split_stamped(f"{m.group(1)}: {m.group(2)}", where)
        entries.append(Entry(rel, FILE_QUALNAME, stamp, reason))
    return entries


def _scan_python(file: Path, rel: str) -> list[Entry]:
    try:
        source = file.read_bytes()
    except OSError as err:
        raise EnumerationError(f"{rel}: unreadable, which is an error, not a skip: {err}") from err
    try:
        # Bytes, not str: ast.parse then applies the interpreter's own
        # BOM and PEP 263 encoding rules, so "parseable" means exactly
        # "the pinned interpreter can import it".
        tree = ast.parse(source, filename=rel)
    except (SyntaxError, ValueError) as err:
        raise EnumerationError(f"{rel}: unparseable, which is an error, not a skip: {err}") from err

    has_canonical, aliased = _owed_bindings(tree)

    entries: list[Entry] = []
    canonical_ids: set[int] = set()

    module_raise = _module_form_raise(tree)
    if module_raise is not None:
        # The module form's shape includes the canonical import.
        entries.append(_entry(module_raise, True, rel, MODULE_QUALNAME))
        canonical_ids.add(id(module_raise))

    for qualname, node in _callable_form_raises(tree.body, []):
        entries.append(_entry(node, has_canonical, rel, qualname))
        canonical_ids.add(id(node))

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Raise)
            and id(node) not in canonical_ids
            and _references_owed(node, aliased)
        ):
            raise EnumerationError(
                f"{rel}:{node.lineno}: Owed raised outside marker form rule v2"
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


def _entry(node: ast.Raise, has_canonical: bool, rel: str, qualname: str) -> Entry:
    """Validate a canonically positioned raise and build its entry."""
    where = f"{rel}:{node.lineno}: {qualname}"
    if not has_canonical:
        raise EnumerationError(f"{where}: Owed raised without the canonical import")
    exc = node.exc
    if not (isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name) and exc.func.id == "Owed"):
        raise EnumerationError(f"{where}: Owed raised outside marker form rule v2")
    if node.cause is not None or exc.keywords or len(exc.args) != 1:
        raise EnumerationError(f"{where}: marker takes exactly one plain reason argument")
    arg = exc.args[0]
    if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value):
        raise EnumerationError(f"{where}: marker reason must be one non-empty static string literal")
    if any(ch in arg.value for ch in _NON_LF_BOUNDARIES):
        raise EnumerationError(f"{where}: marker reason may contain no line boundary other than LF")
    stamp, reason = _split_stamped(arg.value, where)
    return Entry(rel, qualname, stamp, reason)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
