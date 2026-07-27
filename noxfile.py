"""Nox sessions.

Sessions run inside the already-synced project environment rather than building
their own virtualenvs — there is one environment for this project and `uv sync`
owns it. Invoke as `uv run nox -s checks`.
"""

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
    """Regenerate the doc indexes and `.state.md`, then report drift.

    The drift report never fails the session — staleness announces itself
    here so revisits are targeted, and gating on it would make every code
    change a doc chore."""
    session.run("python", "tools/doc_index.py", *session.posargs)
    session.run("python", "tools/doc_drift.py")


@nox.session
def tests(session: nox.Session) -> None:
    """Full test suite. `--benchmark-disable` still runs the budget checks —
    it drops the timing rounds, not the assertions."""
    session.run("pytest", "--benchmark-disable", *session.posargs)


@nox.session
def checks(session: nox.Session) -> None:
    """The full quality gate — what CI runs."""
    lint(session)
    typecheck(session)
    imports(session)
    tests(session)


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
