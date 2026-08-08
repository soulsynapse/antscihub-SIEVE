"""Mutation sweeps over one file: unique anchors, byte-exact restore, no stale bytecode.

Every review that hand-built this harness re-hit the same four lies, each one printing
SURVIVED for a mutant the tests in fact kill — the direction that convicts correct work.
This module is those findings as code, so a sweep is one command instead of a rebuilt
scratch script:

- An anchor must occur exactly once in the file, or the replacement lands somewhere the
  reviewer did not mean — a first-occurrence replace of a call token once hit the module
  docstring eleven lines above the call
  (`docs/findings/loop/2026.08.07-a-mutant-anchored-on-a-token-that-also-appears-in-prose-reports-a-false-survivor.md`).
- Anchors written with `\\n` are matched against the file's own line endings: the tree is
  CRLF on disk, so a literal match would find nothing.
- `__pycache__` is purged and `PYTHONDONTWRITEBYTECODE` set for every run: CPython
  invalidates on `(int(mtime), size)`, so a same-size edit inside one wall-clock second
  runs against stale bytecode and never executes at all
  (`docs/findings/loop/2026.08.07-a-same-size-mutant-is-masked-by-the-bytecode-cache-and-reports-a-false-survivor.md`).
- The subject is restored by writing back its original *bytes*, never text — `write_text`
  retranslates newlines and leaves the tree modified in a way `git diff` will not show
  (`docs/findings/loop/2026.08.07-a-mutation-harness-restores-the-bytes-and-not-the-line-endings.md`)
  — and never by `git checkout --`, which restores to HEAD and deletes uncommitted work
  (`docs/findings/loop/2026.08.07-git-checkout-restores-a-sweep-onto-the-commit-and-deletes-the-work-under-test.md`).

KILLED means the test command failed under the mutant, which is the good outcome.
Exit is 0 only when every mutant was killed; a survivor or a refused anchor is 1.

    uv run python scripts/mutation_sweep.py --file src/sieve/tools/crop.py \\
        --mutant "left + width ==> left - width" \\
        --mutant "raise ValidationError ==> pass  # " \\
        -- uv run pytest -q tests/unit/test_crop.py
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: Splits a `--mutant` into anchor and replacement. Three characters that are
#: not a Python operator sequence, so an anchor quoting real code never
#: contains the separator by accident.
SEPARATOR = "==>"

#: Roots whose stale bytecode could mask a mutant. `tests` is included because
#: a mutant in a test helper is a legal subject.
PURGE_ROOTS = ("src", "scripts", "tests")


class SweepError(ValueError):
    """A mutant that cannot be applied as written."""


@dataclass(frozen=True)
class Mutant:
    anchor: str
    replacement: str

    @property
    def label(self) -> str:
        flat = " ".join(self.anchor.split())
        return flat if len(flat) <= 60 else flat[:57] + "..."


def parse_mutant(raw: str) -> Mutant:
    # The spaced form first, so `A ==> B` means A and B rather than `A ` and
    # ` B` — an anchor's own indentation still counts, only the separator's
    # padding does not.
    anchor, sep, replacement = raw.partition(f" {SEPARATOR} ")
    if not sep:
        anchor, sep, replacement = raw.partition(SEPARATOR)
    if not sep:
        raise SweepError(f"no {SEPARATOR!r} in {raw!r} — a mutant is 'anchor {SEPARATOR} text'")
    if not anchor.strip():
        raise SweepError(f"empty anchor in {raw!r}")
    if anchor == replacement:
        raise SweepError(f"{raw!r} replaces the anchor with itself and can only survive")
    return Mutant(anchor=anchor, replacement=replacement)


def _match_eol(text: str, data: bytes) -> bytes:
    """`text` as bytes in the file's own line endings.

    Adapted, not assumed: the anchor is written by a reader of `git show` or an
    editor pane, both of which speak `\\n`, while the file on disk may be CRLF.
    """
    raw = text.encode("utf-8")
    if b"\r\n" in data and b"\r" not in raw:
        raw = raw.replace(b"\n", b"\r\n")
    return raw


def apply_mutant(data: bytes, mutant: Mutant) -> bytes:
    anchor = _match_eol(mutant.anchor, data)
    hits = data.count(anchor)
    if hits == 0:
        raise SweepError(
            f"anchor not found: {mutant.label!r} — check spelling against the bytes on disk"
        )
    if hits > 1:
        raise SweepError(
            f"anchor occurs {hits} times: {mutant.label!r} — anchor on a string that "
            f"occurs once, or the replacement lands where you did not mean"
        )
    return data.replace(anchor, _match_eol(mutant.replacement, data))


def purge_bytecode(repo: Path = REPO) -> None:
    for root in PURGE_ROOTS:
        folder = repo / root
        if not folder.is_dir():
            continue
        for cache in folder.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)


def run_sweep(
    subject: Path, mutants: list[Mutant], command: list[str], repo: Path = REPO
) -> list[tuple[Mutant, bool]]:
    """Each mutant applied alone against `command`; True in a row means killed.

    The original bytes are restored after every mutant, inside a `finally`, and
    re-read afterwards to prove the restore happened — a sweep that cannot lose
    the work under test is the entire reason this file exists.
    """
    original = subject.read_bytes()
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    results: list[tuple[Mutant, bool]] = []
    for mutant in mutants:
        mutated = apply_mutant(original, mutant)
        try:
            subject.write_bytes(mutated)
            purge_bytecode(repo)
            finished = subprocess.run(command, cwd=repo, env=env, capture_output=True, check=False)
            results.append((mutant, finished.returncode != 0))
        finally:
            subject.write_bytes(original)
    purge_bytecode(repo)
    if subject.read_bytes() != original:
        raise SweepError(f"{subject} did not restore byte-exact — do not commit this tree")
    return results


def main(argv: list[str] | None = None, repo: Path = REPO) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--" not in argv:
        print("mutation_sweep: no test command after `--`", file=sys.stderr)
        return 2
    split = argv.index("--")
    command = argv[split + 1 :]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, help="the module under mutation")
    parser.add_argument(
        "--mutant",
        action="append",
        required=True,
        metavar=f"'ANCHOR {SEPARATOR} REPLACEMENT'",
        help="applied alone, once each; the anchor must occur exactly once in the file",
    )
    args = parser.parse_args(argv[:split])
    if not command:
        print("mutation_sweep: the test command after `--` is empty", file=sys.stderr)
        return 2

    subject = (repo / args.file) if not Path(args.file).is_absolute() else Path(args.file)
    if not subject.is_file():
        print(f"mutation_sweep: no such file: {args.file}", file=sys.stderr)
        return 2

    try:
        mutants = [parse_mutant(raw) for raw in args.mutant]
        results = run_sweep(subject, mutants, command, repo)
    except SweepError as error:
        print(f"mutation_sweep: {error}", file=sys.stderr)
        return 1

    survived = 0
    for mutant, killed in results:
        print(f"{'KILLED  ' if killed else 'SURVIVED'}  {mutant.label}")
        survived += 0 if killed else 1
    print(f"mutation_sweep: {len(results) - survived} killed, {survived} survived")
    return 1 if survived else 0


if __name__ == "__main__":
    raise SystemExit(main())
