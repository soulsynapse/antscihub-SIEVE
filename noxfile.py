"""Nox sessions.

Sessions run inside the already-synced project environment rather than building
their own virtualenvs — there is one environment for this project and `uv sync`
owns it. Invoke as `uv run nox -s checks`.
"""

from collections.abc import Callable, Sequence

import nox

nox.options.default_venv_backend = "none"
nox.options.sessions = ["checks"]


@nox.session
def lint(session: nox.Session) -> None:
    """Ruff lint and format gate."""
    session.run("ruff", "check", ".")
    session.run("ruff", "format", "--check", ".")


@nox.session
def typecheck(session: nox.Session) -> None:
    """Static type checking."""
    session.run("pyright")


@nox.session
def imports(session: nox.Session) -> None:
    """Layer boundary contracts (.importlinter)."""
    session.run("lint-imports", env={"PYTHONIOENCODING": "utf-8"})


@nox.session
def docs(session: nox.Session) -> None:
    """Regenerate the doc indexes and `.state.md`, and count what has drifted.

    One line, not the report: this session is run for the indexes, after every
    completed item, and forty lines of standing drift advice printed on each of
    those runs is read once and skipped thereafter — it also buries the verdict
    of whatever was piped after it. The report itself is `nox -s drift`.

    Run *before* `checks`, not after: the gate tests these files for staleness,
    so a rebuild that follows it earns a second gate run. It is not folded into
    `checks` for the reason that check exists — regenerating inside the gate
    would leave `tests/docs/test_doc_index.py` comparing fresh output against
    itself, and CI runs on the committed tree."""
    session.run("python", "tools/doc_index.py", *session.posargs)
    session.run("python", "tools/doc_refs.py")
    session.run("python", "tools/guardrail_refs.py")
    session.run("python", "tools/doc_drift.py", "--summary")


@nox.session
def drift(session: nox.Session) -> None:
    """Which stamped docs and findings have had their subjects move.

    An audit, run when a session came to act on it. It never fails — a drifted
    doc is a candidate for one targeted revisit, not a broken build, and gating
    on it would make every code change a doc chore."""
    session.run("python", "tools/doc_drift.py", *session.posargs)


@nox.session
def hooks(session: nox.Session) -> None:
    """Point git at `tools/githooks`.

    `core.hooksPath` is per-clone and cannot be committed, so this is the one
    step a fresh clone runs by hand. It is not folded into `checks`: a gate that
    silently rewires git on every run is a surprise, and a machine that wants
    the hooks off should be able to leave them off."""
    session.run("git", "config", "core.hooksPath", "tools/githooks", external=True)
    session.log("core.hooksPath = tools/githooks")


@nox.session
def tests(session: nox.Session) -> None:
    """Full test suite. `--benchmark-disable` still runs the budget checks —
    it drops the timing rounds, not the assertions."""
    session.run("pytest", "--benchmark-disable", *session.posargs)


CHECK_STAGES: Sequence[tuple[str, Callable[[nox.Session], None]]] = (
    ("lint", lint),
    ("typecheck", typecheck),
    ("imports", imports),
    ("tests", tests),
)


def run_check_stages(
    session: nox.Session,
    stages: Sequence[tuple[str, Callable[[nox.Session], None]]],
    emit: Callable[[str], None],
) -> None:
    """Run `stages` in order, emitting exactly one verdict line, last.

    The verdict names the stage because nox's own summary does not: a failure
    prints `Session checks failed.`, and which of four tools said so is one
    line further up, mixed into that tool's output."""
    for name, stage in stages:
        try:
            stage(session)
        except Exception:
            emit(f"checks: FAIL ({name})")
            raise
    emit("checks: pass")


@nox.session
def checks(session: nox.Session) -> None:
    """The full quality gate — what CI runs.

    The last thing the session writes to **stdout** is `checks: pass` or
    `checks: FAIL (<stage>)`. nox reports through its logger, which is stderr,
    and the output is thousands of lines long, so it gets read through a
    `| tail -n` or `Select-Object -Last n` that carries stdout alone — and that
    stream ended on pytest's last progress line, `[ 83%]` and all, saying
    nothing about whether the gate passed. On a merged stream this verdict is
    the second-to-last line and nox's own concordant summary follows it."""
    run_check_stages(session, CHECK_STAGES, lambda line: print(line, flush=True))


@nox.session
def benchmark(session: nox.Session) -> None:
    """Latency budget checks, timed for real.

    Selected by marker rather than by `--benchmark-only` alone: that flag
    *skips* the rest of the suite, so a session with no budget checks left in
    it would report green on 181 skips. `-m benchmark` collects nothing
    instead, and pytest's exit code 5 is no longer forgiven — deleting the
    checks now breaks the gate, which is the whole point of having one.
    """
    session.run("pytest", "-m", "benchmark", "--benchmark-only", *session.posargs)
