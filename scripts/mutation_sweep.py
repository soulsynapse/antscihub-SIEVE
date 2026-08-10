"""Mutation sweeps over one file: unique anchors, byte-exact restore, a green bounded baseline.

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

The four above all print SURVIVED for a mutant the tests kill — the direction that
convicts correct work. The fifth lie runs the other way and is worse: KILLED is read
off any non-zero exit, so a command that is red before any mutation — a broken
import, a crash, a mistyped path that collects nothing — prints a clean sweep over
mutants it never judged, and a clean sweep is what closes an item
(`docs/findings/loop/2026.08.08-a-crashing-test-command-is-indistinguishable-from-a-killed-mutant.md`).
So the sweep now runs the command once on the original bytes first and refuses,
showing the command's own output, unless that baseline is green. A baseline cannot
reach the deterministic member of that class — a mutant that leaves the subject
unparseable is red on the mutated bytes only — so the mutated bytes are compiled
and the mutant refused rather than scored.

The baseline is also the sweep's clock. The test command after `--` should be the
narrowest command the subject's own tests constitute — a mutant only a distant test
kills is a coverage gap the narrow oracle exposes and a broad one hides — so a
baseline that does not finish inside the oracle budget is refused as too broad
rather than swept; `--oracle-budget` raises it for a deliberately broad run. Each
mutant then runs under a timeout derived from the green baseline, and a mutant that
stops the command terminating is KILLED: it broke the program.

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
import signal
import subprocess
import sys
import tempfile
import time
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

#: How long the baseline may take before the oracle is refused as too broad. The
#: figure is set so a sweep of a handful of mutants — baseline plus one timed run
#: each — fits inside a single foreground command in the loop's harness, which is
#: what makes "backgrounded, then killed at turn end, mutant left in the tree"
#: structurally impossible rather than a convention an agent must remember.
ORACLE_BUDGET_SECONDS = 60.0

#: Floor for the per-mutant timeout, so a sub-second baseline does not convict a
#: mutant on scheduler jitter.
MUTANT_TIMEOUT_FLOOR_SECONDS = 30.0


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


def refuse_unparseable(subject: Path, mutant: Mutant, mutated: bytes) -> None:
    """A mutant the compiler rejects was never applied, so nothing it exits with is a verdict.

    The one member of the false-KILLED class that carries no probability: every oracle
    imports its subject, an unparseable one raises before a single test runs, and KILLED
    is read off the non-zero exit. `parse_mutant` strips the separator's padding and not
    the anchor's indentation, so a replacement quoting an indented line arrives one space
    short and the two verdicts are a space apart with nothing in the output saying which
    you got
    (`docs/findings/loop/2026.08.08-a-crashing-test-command-is-indistinguishable-from-a-killed-mutant.md`).
    """
    try:
        compile(mutated, str(subject), "exec")
    except SyntaxError as error:
        raise SweepError(
            f"the mutant leaves {subject.name} unparseable, so it was never applied and no "
            f"exit code from it is a verdict: {mutant.label!r} — {type(error).__name__}: "
            f"{error.msg} (line {error.lineno}) — check the replacement's own indentation, "
            f"which the separator's padding eats one space of"
        ) from None


def purge_bytecode(repo: Path = REPO) -> None:
    for root in PURGE_ROOTS:
        folder = repo / root
        if not folder.is_dir():
            continue
        for cache in folder.rglob("__pycache__"):
            shutil.rmtree(cache, ignore_errors=True)


def _tail(finished: subprocess.CompletedProcess[bytes], lines: int = 20) -> str:
    """The end of both streams, enough to say why without a by-hand re-run."""
    streams = []
    for name, raw in (("stdout", finished.stdout), ("stderr", finished.stderr)):
        text = raw.decode("utf-8", errors="replace").strip()
        if text:
            kept = text.splitlines()[-lines:]
            streams.append(f"--- {name} ---\n" + "\n".join(kept))
    return "\n".join(streams) if streams else "(the command printed nothing)"


def _terminate_tree(process: subprocess.Popen[bytes]) -> None:
    """Kill the command and everything it started, not just the command.

    `Popen.kill()` reaches the direct child alone, and the oracle passed after `--`
    is `uv run pytest`: uv spawns the interpreter, so killing uv leaves pytest
    running with the mutant still patched into the tree.
    """
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True, check=False
        )
    else:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    process.kill()


def _run_bounded(
    command: list[str], cwd: Path, env: dict[str, str], timeout: float
) -> subprocess.CompletedProcess[bytes]:
    """`subprocess.run` whose timeout bounds the call rather than only the child.

    Two departures from `run(capture_output=True, timeout=...)`, answering different
    things. Killing the process tree is what bounds the call: `run` kills the direct
    child and then blocks in `communicate()` until every inherited copy of the pipe
    closes, and `uv run pytest` holds one — 40.1s of wall clock under a 3s timeout
    (`docs/findings/loop/2026.08.08-a-subprocess-timeout-does-not-bound-a-command-whose-grandchild-holds-the-pipe.md`).
    The redirection buys capacity rather than promptness: `Popen.wait` waits on the
    process handle and returns on time whatever the streams are, but nothing here
    drains a pipe, so under `PIPE` an oracle whose output outgrows the buffer blocks
    in its own `write`, never exits, and is timed out and scored KILLED
    (`docs/findings/loop/2026.08.10-a-two-part-fix-is-reported-as-two-kills-and-the-half-that-carries-it-is-the-other-one.md`).
    """
    detach = {} if os.name == "nt" else {"start_new_session": True}
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as scratch:
        out_path, err_path = Path(scratch) / "out", Path(scratch) / "err"
        with out_path.open("wb") as out, err_path.open("wb") as err:
            process = subprocess.Popen(command, cwd=cwd, env=env, stdout=out, stderr=err, **detach)
            try:
                returncode = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                _terminate_tree(process)
                process.wait()
                raise
        return subprocess.CompletedProcess(
            command, returncode, out_path.read_bytes(), err_path.read_bytes()
        )


def run_sweep(
    subject: Path,
    mutants: list[Mutant],
    command: list[str],
    repo: Path = REPO,
    oracle_budget: float = ORACLE_BUDGET_SECONDS,
    mutant_timeout: float | None = None,
) -> list[tuple[Mutant, bool]]:
    """Each mutant applied alone against `command`; True in a row means killed.

    The command runs once on the original bytes first, under `oracle_budget` as a
    hard timeout, and the sweep refuses unless that baseline is green: a command
    that is red, crashes, or never finishes on unmutated code would print KILLED
    for every mutant it never judged. Each mutant then runs under `mutant_timeout`
    (derived from the baseline's own elapsed time when not given), and a timeout
    is a kill — the mutant stopped the program terminating. A mutant whose bytes do
    not compile is refused before it is written, since the baseline cannot see it.

    The original bytes are restored after every mutant, inside a `finally`, and
    re-read afterwards to prove the restore happened — a sweep that cannot lose
    the work under test is the entire reason this file exists.
    """
    original = subject.read_bytes()
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    purge_bytecode(repo)
    started = time.monotonic()
    try:
        baseline = _run_bounded(command, repo, env, oracle_budget)
    except subprocess.TimeoutExpired:
        raise SweepError(
            f"the test command did not finish inside the {oracle_budget:g}s oracle budget — "
            f"narrow it to the tests that hold this subject, or raise --oracle-budget "
            f"for a deliberately broad sweep"
        ) from None
    elapsed = time.monotonic() - started
    if baseline.returncode != 0:
        raise SweepError(
            f"the test command exits {baseline.returncode} before any mutation, so KILLED "
            f"would mean nothing — its output:\n{_tail(baseline)}"
        )
    timeout = (
        mutant_timeout
        if mutant_timeout is not None
        else max(MUTANT_TIMEOUT_FLOOR_SECONDS, 2.0 * elapsed + 1.0)
    )
    results: list[tuple[Mutant, bool]] = []
    for mutant in mutants:
        mutated = apply_mutant(original, mutant)
        refuse_unparseable(subject, mutant, mutated)
        try:
            subject.write_bytes(mutated)
            purge_bytecode(repo)
            try:
                finished = _run_bounded(command, repo, env, timeout)
                results.append((mutant, finished.returncode != 0))
            except subprocess.TimeoutExpired:
                results.append((mutant, True))
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
    parser.add_argument(
        "--oracle-budget",
        type=float,
        default=ORACLE_BUDGET_SECONDS,
        metavar="SECONDS",
        help="how long the green baseline may take before the oracle is refused as too broad",
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
        results = run_sweep(subject, mutants, command, repo, oracle_budget=args.oracle_budget)
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
