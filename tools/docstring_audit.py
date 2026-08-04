"""One file, one docstring, one secret -- and the queue of files not yet there.

A module says once, at the top, which design decision it hides, so that changing
that decision changes this file and stops. If the secret does not fit the budget
the file holds more than one, so the cap and the split trigger are one test
rather than two rules that can disagree.

The cap counts docstring and comment words together. On 2026-08-04 `src/` held
97,244 words of docstring against 30,433 of comment at 11 words per comment line
-- prose blocks, not trailing notes -- so a docstring-only cap would have moved
the banned paragraphs into `#` blocks and changed nothing.

`ASSESSED` and `FLAGGED` are the ledger and both mean somebody read the file.
Flagged is the answer "not mechanically": more than one secret, or prose the
budget would destroy. It leaves the queue exactly as a pass does, because a
queue that keeps handing the file back until somebody bulldozes it punishes the
correct call. Passing the checks below is necessary and not sufficient -- a
40-line module with no docstrings satisfies every assertion here while nobody
has yet asked what it is for -- so the ledger holds a sentence a reader can
judge, as `bench/budgets.py:WITHOUT_PRODUCER` does.

Order is largest job first, reversed 2026-08-04 after 22 files had passed
without a single flag. Smallest-first defers every file that could plausibly
hide two secrets to the tail, which leaves the flag path — the one that writes
a `docs/todo/` proposal and runs the co-change check — unexercised until it
fires in an unattended batch at the end. Contexts are fresh per file, so
ordering buys no accumulated skill either way; what largest-first buys is the
hard case arriving while somebody is still watching. The cost, accepted: the
first runs are the ones most likely to flag, so early flags read as the rule's
opening output rather than as considered exceptions.
"""

from __future__ import annotations

import argparse
import ast
import io
import sys
import tokenize
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"

#: 250 sits under the 310-word mean of the 105 module docstrings measured
#: 2026-08-04, so it bites the top quartile rather than every file.
DOCSTRING_WORDS = 250

#: The gap above DOCSTRING_WORDS is what survives for decisions and bump logs.
FILE_PROSE_WORDS = 400

#: CLAUDE.md designates these three as interface contracts, where the protocol
#: genuinely is prose and a reader arrives by hovering a symbol rather than by
#: reading the file. A fourth entry is a decision, not a convenience.
CONTRACT_MODULES = frozenset(
    {
        "sieve/core/filter_base.py",
        "sieve/core/pipeline_model.py",
        "sieve/pipeline/cache_key.py",
    }
)
CONTRACT_DOCSTRING_WORDS = 600
CONTRACT_FILE_PROSE_WORDS = 900

PRAGMA_PREFIXES = ("noqa", "type:", "ruff:", "pyright:", "isort:", "fmt:", "!")

#: path -> the secret it owns, in one line.
ASSESSED: dict[str, str] = {
    "sieve/__init__.py": "the runtime __version__ string CLI/GUI report, apart from pyproject.toml",
    "sieve/decode/__init__.py": "decode/ is the only package allowed to import cv2 directly",
    "sieve/gui/__init__.py": "Qt stays in sieve.gui; it reaches the rest only via public APIs",
    "sieve/gui/__main__.py": "python -m sieve.gui delegates to gui.app.main, keeping its exit code",
    "sieve/pipeline/__init__.py": (
        "pipeline/ is Qt-free by contract; CLI, GUI, and cluster batch jobs execute through it"
    ),
    "sieve/backend/__init__.py": "which kernel runs and what to call the machine that ran it, never a kernel itself",
    "sieve/bench/__init__.py": "budgets are checkable headlessly, so CLI and GUI runs are held to the same numbers",
    "sieve/storage/__init__.py": "storage/ knows a file format and an array, never a cache key, replicate, or project",
    "sieve/cli/__init__.py": "commands own no arithmetic — parsing, one run-only decision, and printing, nothing execute doesn't already do",
    "sieve/detect/__init__.py": "detection takes a resolved DetectorSettings and a series, never a Project or the GUI's mutable tuning state, so both front ends compute it the same way",
    "sieve/core/__init__.py": "core/ is pure logic: nothing here imports a layer above it, Qt, Zarr, or subprocess, machine-checked by .importlinter",
    "sieve/decode/identity.py": "a cache key over decoded content must include who decoded it, since decoders can disagree on pixel values for the same input",
    "sieve/gui/app.py": "the one place that mutates process-wide state before any window exists, and resolves which video a launch opens",
    "sieve/backend/identity.py": "a cache key must say which backend produced a frame, since backends can disagree in the low bits, unless the filter declared backend_agnostic",
    "sieve/gui/block_spin.py": "0 is a mode (auto), not a smaller size, so stepping down stops at 1 before it can cross into auto",
    "sieve/cli/materialize_cmd.py": "materialize is one headless command that derives its format from the graph and writes+registers a single replicate's crop atomically",
    "sieve/gui/param_form.py": "one widget per params-model field, bounds read from the field's own constraints, so a filter's settings surface exists the moment the filter does with no per-filter GUI code",
    "sieve/cli/app.py": "the exhaustive, hand-registered assembly of subcommands into one Typer app, with the real-process entry point kept separate from the callback so installing the stderr filter never displaces a test's fd-2 capture",
    "sieve/gui/history_dialog.py": "the two facts (action, how long ago) that make a snapshot identifiable to the person who caused it, and that restoring is the window's job, not the dialog's",
    "sieve/cli/sweep_cmd.py": "the sweep reproduces the luma finding's hand-run protocol across a machine axis, and refuses rather than measures unpinned when the platform won't grant affinity",
    "sieve/gui/preferences_dialog.py": "the pane applies every change immediately and has no Cancel, because the setting's only value is seeing its effect on the video while the pane is open",
    "sieve/gui/editing_sources.py": "editing state is a set keyed by claimant source, not a bool or counter, so two overlapping typing controls can't strand or prematurely release the keyboard shortcuts",
    "sieve/filters/motion_history.py": "decay and neighbourhood coupling are one stateful kernel, not two composed nodes, because coupling must apply inside the feedback path to the previous state before it decays",
}

#: path -> why it was not edited, ending in the docs/todo/ slug if one was written.
FLAGGED: dict[str, str] = {
    "sieve/core/filter_base.py": (
        "already a contract module (600/900) and still 4,649 words of prose against 900 — "
        "one secret, 25 dense per-method asymmetry docstrings the budget would delete rather "
        "than compress — filter-base-contract-budget"
    ),
    "sieve/gui/filter_tab.py": (
        "six decisions (composite refresh state machine, the two-tier drag discipline repeated "
        "per control, document-vs-local knob routing, the wizard session lifecycle, the crop "
        "boundary card, structure-edit macros), not one — filter-tab-many-secrets"
    ),
    "sieve/gui/document.py": (
        "one secret (ReplicateSet plus undo history, GUI-side), but 67 symbol docstrings and "
        "5,793 words of prose against a 400 cap, each one a non-obvious per-method reason the "
        "budget would delete rather than compress — document-docstring-budget"
    ),
    "sieve/core/pipeline_model.py": (
        "already a contract module (600/900) and still 6,214 words of prose against 900 — "
        "plausibly four bundled secrets (graph identity, replicate inheritance, crop artifact "
        "provenance, document lifecycle), not one — pipeline-model-prose-budget"
    ),
    "sieve/gui/preview_runner.py": (
        "one secret (a PreviewSession run on its own thread, revision-current, "
        "cache warm across renders), but 39 symbol docstrings and 4,283 words of "
        "prose against a 400 cap, each one a non-obvious per-method reason the "
        "budget would delete rather than compress — preview-runner-docstring-budget"
    ),
    "sieve/gui/main_window.py": (
        "one secret (the window as composition root, holding the session-only "
        "identity the document excludes and wiring player/document/preview/probe "
        "together), but 33 symbol docstrings and 3,570 words of prose against a "
        "400 cap, each one a non-obvious per-method ordering or shutdown hazard "
        "the budget would delete rather than compress — main-window-docstring-budget"
    ),
    "sieve/pipeline/dag.py": (
        "one secret (Pipeline resolved into an ordered, validated Dag the "
        "executor and cache key walk without re-deriving order), but 22 symbol "
        "docstrings and 3,147 words of prose against a 400 cap, each one a "
        "non-obvious per-method rejection ordering or cache-fold reason the "
        "budget would delete rather than compress — dag-docstring-budget"
    ),
    "sieve/pipeline/preview.py": (
        "one secret (PreviewSession takes the graph fresh per render and "
        "relies on cache_key's keying, which excludes span and window, for "
        "incremental re-render with no invalidation logic here), but 17 "
        "symbol docstrings and 2,463 words of prose against a 400 cap, each "
        "one a non-obvious layering or failure-mode reason the budget would "
        "delete rather than compress — preview-docstring-budget"
    ),
}


@dataclass(frozen=True)
class Measurement:
    path: str
    lines: int
    module_docstring_words: int
    has_module_docstring: bool
    symbol_docstrings: int
    symbol_docstring_words: int
    comment_words: int

    @property
    def prose_words(self) -> int:
        return self.module_docstring_words + self.symbol_docstring_words + self.comment_words


def iter_modules(root: Path) -> Iterator[Path]:
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" not in path.parts:
            yield path


def measure(path: Path, root: Path) -> Measurement:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)

    module_doc = ast.get_docstring(tree, clean=False)
    symbol_docstrings = 0
    symbol_words = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Module):
            continue
        if not isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        doc = ast.get_docstring(node, clean=False)
        if doc is not None:
            symbol_docstrings += 1
            symbol_words += len(doc.split())

    comment_words = 0
    for token in tokenize.generate_tokens(io.StringIO(text).readline):
        if token.type != tokenize.COMMENT:
            continue
        # `#:` carries prose like any other comment; only the colon is punctuation.
        body = token.string.lstrip("#").lstrip(":").strip()
        if body.startswith(PRAGMA_PREFIXES):
            continue
        comment_words += len(body.split())

    return Measurement(
        path=path.relative_to(root).as_posix(),
        lines=len(text.splitlines()),
        module_docstring_words=len(module_doc.split()) if module_doc else 0,
        has_module_docstring=module_doc is not None,
        symbol_docstrings=symbol_docstrings,
        symbol_docstring_words=symbol_words,
        comment_words=comment_words,
    )


def caps(path: str) -> tuple[int, int]:
    if path in CONTRACT_MODULES:
        return CONTRACT_DOCSTRING_WORDS, CONTRACT_FILE_PROSE_WORDS
    return DOCSTRING_WORDS, FILE_PROSE_WORDS


def excess(m: Measurement) -> int:
    return max(0, m.prose_words - caps(m.path)[1])


def violations(m: Measurement) -> list[str]:
    is_contract = m.path in CONTRACT_MODULES
    doc_cap, prose_cap = caps(m.path)

    out: list[str] = []
    if not m.has_module_docstring:
        out.append("no module docstring: the file's secret is unstated")
    if m.module_docstring_words > doc_cap:
        out.append(
            f"module docstring is {m.module_docstring_words} words, cap {doc_cap} "
            "-- compress it, or the file holds more than one secret"
        )
    if m.symbol_docstrings and not is_contract:
        out.append(
            f"{m.symbol_docstrings} class/function docstrings "
            f"({m.symbol_docstring_words} words): fold what is underivable into the "
            "module docstring, delete the rest"
        )
    if m.prose_words > prose_cap:
        out.append(f"{m.prose_words} words of prose (docstring + comments), cap {prose_cap}")
    return out


def audit(root: Path) -> list[tuple[Measurement, list[str]]]:
    return [(m, violations(m)) for m in (measure(p, root) for p in iter_modules(root))]


def queue(rows: list[tuple[Measurement, list[str]]]) -> list[Measurement]:
    pending = [m for m, _ in rows if m.path not in ASSESSED and m.path not in FLAGGED]
    return sorted(pending, key=lambda m: (-excess(m), -m.symbol_docstrings, -m.lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=SRC)
    parser.add_argument("--next", action="store_true", help="print the next file to assess")
    parser.add_argument(
        "--progress", action="store_true", help="print how many files have left the queue"
    )
    parser.add_argument(
        "--gate",
        action="store_true",
        help="fail if any ASSESSED file violates the convention (regression guard)",
    )
    args = parser.parse_args()

    root: Path = args.root
    rows = audit(root)
    pending = queue(rows)

    if args.next:
        print(pending[0].path if pending else "QUEUE-EMPTY")
        return 0

    if args.progress:
        print(len(ASSESSED) + len(FLAGGED))
        return 0

    if args.gate:
        broken = [(m, v) for m, v in rows if m.path in ASSESSED and v]
        for m, vs in broken:
            for v in vs:
                print(f"{m.path}: {v}", file=sys.stderr)
        if broken:
            print(f"\n{len(broken)} assessed file(s) regressed.", file=sys.stderr)
            return 1
        print(f"{len(ASSESSED)} assessed file(s) still at the convention.")
        return 0

    total_prose = sum(m.prose_words for m, _ in rows)
    print(
        f"{len(rows)} modules, {total_prose} words of prose, "
        f"{len(ASSESSED)} assessed, {len(FLAGGED)} flagged, {len(pending)} to go"
    )
    print()
    print(f"{'file':<48}{'lines':>6}{'doc':>6}{'sym':>5}{'cmt':>6}{'prose':>7}{'over':>7}")
    for m in pending:
        print(
            f"{m.path:<48}{m.lines:>6}{m.module_docstring_words:>6}"
            f"{m.symbol_docstrings:>5}{m.comment_words:>6}{m.prose_words:>7}{excess(m):>7}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
