"""Nox sessions.

Sessions run inside the already-synced project environment rather than building
their own virtualenvs — there is one environment for this project and `uv sync`
owns it. Invoke as `uv run nox -s checks`.
"""

import nox

nox.options.default_venv_backend = "none"
nox.options.sessions = ["checks"]

# pytest exits 5 when it collects nothing. The suite is still being built out,
# so an empty collection is not yet a failure.
NO_TESTS_COLLECTED = 5


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
def tests(session: nox.Session) -> None:
    """Test suite, excluding benchmarks."""
    session.run(
        "pytest",
        "--benchmark-disable",
        *session.posargs,
        success_codes=[0, NO_TESTS_COLLECTED],
    )


@nox.session
def checks(session: nox.Session) -> None:
    """The full quality gate — what CI runs."""
    lint(session)
    typecheck(session)
    imports(session)
    tests(session)


@nox.session
def benchmark(session: nox.Session) -> None:
    """Latency budget checks."""
    session.run(
        "pytest",
        "--benchmark-only",
        *session.posargs,
        success_codes=[0, NO_TESTS_COLLECTED],
    )
