"""One file, one docstring, one secret -- and a queue of the files that are not there yet.

The convention this checks: a module says, once and at the top, what design
decision it hides -- Parnas' secret, stated so that changing that decision does
not propagate past this file. Nothing else in the file carries prose. If the
secret cannot be stated inside the budget, the file holds more than one secret
and is a split candidate, so the word cap and the split trigger are the same
test rather than two rules that can disagree.

The cap is on *docstring plus comment* words together, not on docstrings alone.
Measured 2026-08-04, `src/` held 97,244 words of docstring and 30,433 of comment
at 11 words per comment line, which is prose blocks rather than trailing notes.
A docstring-only cap would move the banned paragraphs into `#` blocks above the
same functions, improve every number here, and change nothing.

`ASSESSED` is the ledger and the definition of done: a file is finished when a
human-readable statement of its secret appears there, which is a thing the
mechanical checks below cannot verify and a reader can. Passing the checks is
necessary and not sufficient -- a 40-line module with no docstrings at all
passes every assertion here while nobody has yet asked what it is for. This
follows `bench/budgets.py:WITHOUT_PRODUCER` and `doc_drift.UNSTAMPED`: the honest
gap lives in a list in the tool, not in a document that can drift from it.
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

#: A secret that needs more than this many words is more than one secret. 250 sits
#: under the 310-word mean of the 105 module docstrings measured on 2026-08-04, so
#: it bites the top quartile rather than every file, and it is a budget on the
#: statement rather than on the file: a long argument about *why* belongs in the
#: rationale that owns the decision, not at the top of the module that obeys it.
DOCSTRING_WORDS = 250

#: Docstring plus comments. The 150-word gap above `DOCSTRING_WORDS` is what a
#: file gets for the notes that survive the convention -- a rejected alternative,
#: a version bump log, a failure mode that leaves no trace. It exists so the
#: comment channel has a ceiling; without one, this whole tool measures a
#: relocation.
FILE_PROSE_WORDS = 400

#: The three modules CLAUDE.md designates as interface contracts, where the
#: protocol genuinely *is* prose and a reader arrives at a symbol by hovering it
#: rather than by reading the file top-down. These keep per-symbol docstrings and
#: get a larger budget. Adding a fourth is a decision, not a convenience: every
#: entry here is a file that opted out of the rule the other 102 obey.
CONTRACT_MODULES = frozenset(
    {
        "sieve/core/filter_base.py",
        "sieve/core/pipeline_model.py",
        "sieve/pipeline/cache_key.py",
    }
)

CONTRACT_DOCSTRING_WORDS = 600
CONTRACT_FILE_PROSE_WORDS = 900

#: Comment pragmas are instructions to a tool, not prose, and counting them would
#: charge a file for satisfying its own linter.
PRAGMA_PREFIXES = ("noqa", "type:", "ruff:", "pyright:", "isort:", "fmt:", "!")

#: path -> the secret it owns, in one line. Written by whoever assessed the file.
#: This is the ledger: a file is done when it is here, and `--next` hands out the
#: files that are not. A filter's overflow goes to the `.md` beside it (guardrail
#: 3 already puts one there), which is why `filters/*.py` gets no special budget.
ASSESSED: dict[str, str] = {}

#: path -> slug of the `docs/todo/` item proposing the split. A file lands here
#: when its prose cannot reach the budget without losing something underivable,
#: which is the evidence that it holds more than one secret. It is not a pass:
#: the file is unfinished and parked, and the count of this dict is the backlog
#: the convention discovered.
PENDING_SPLIT: dict[str, str] = {}


@dataclass(frozen=True)
class Measurement:
    """What one module carries, in the units the budgets are denominated in."""

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
        # `#:` is a Sphinx-style attribute comment and carries prose like any other;
        # only the colon is punctuation, so it is stripped before the pragma test.
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


def violations(m: Measurement) -> list[str]:
    """Every way this file is not yet at the convention, in the order to fix them."""
    is_contract = m.path in CONTRACT_MODULES
    doc_cap = CONTRACT_DOCSTRING_WORDS if is_contract else DOCSTRING_WORDS
    prose_cap = CONTRACT_FILE_PROSE_WORDS if is_contract else FILE_PROSE_WORDS

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
    """Unassessed files, worst first: the biggest files carry the most restated
    architecture and are where the split proposals are, which is what a reviewer
    learns most from seeing early."""
    pending = [m for m, _ in rows if m.path not in ASSESSED and m.path not in PENDING_SPLIT]
    return sorted(pending, key=lambda m: -m.prose_words)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=SRC)
    parser.add_argument("--next", action="store_true", help="print the next file to assess")
    parser.add_argument("--progress", action="store_true", help="print assessed+parked / total")
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
        if not pending:
            print("QUEUE-EMPTY")
            return 0
        m = pending[0]
        print(m.path)
        return 0

    if args.progress:
        print(len(ASSESSED) + len(PENDING_SPLIT))
        return 0

    if args.gate:
        broken = [(m, v) for m, v in rows if m.path in ASSESSED and v]
        for m, vs in broken:
            for v in vs:
                print(f"{m.path}: {v}", file=sys.stderr)
        if broken:
            print(
                f"\n{len(broken)} assessed file(s) regressed past the convention.",
                file=sys.stderr,
            )
            return 1
        print(f"{len(ASSESSED)} assessed file(s) still at the convention.")
        return 0

    total_prose = sum(m.prose_words for m, _ in rows)
    print(
        f"{len(rows)} modules, {total_prose} words of prose, "
        f"{len(ASSESSED)} assessed, {len(PENDING_SPLIT)} parked for a split, "
        f"{len(pending)} to go"
    )
    print()
    print(f"{'file':<48}{'lines':>6}{'doc':>6}{'sym':>5}{'cmt':>6}{'prose':>7}")
    for m in pending:
        print(
            f"{m.path:<48}{m.lines:>6}{m.module_docstring_words:>6}"
            f"{m.symbol_docstrings:>5}{m.comment_words:>6}{m.prose_words:>7}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
