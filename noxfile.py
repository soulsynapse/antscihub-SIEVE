"""Project checks run in the environment managed by uv."""

import nox

nox.options.default_venv_backend = "none"
nox.options.sessions = ["checks"]


@nox.session
def typecheck(session: nox.Session) -> None:
    """Static type checking."""
    session.run("pyright")


@nox.session
def imports(session: nox.Session) -> None:
    """Layer boundary contracts."""
    session.run("lint-imports", env={"PYTHONIOENCODING": "utf-8"})


@nox.session
def tests(session: nox.Session) -> None:
    """Full test suite without benchmark timing rounds."""
    session.run("pytest", "--benchmark-disable", *session.posargs)


@nox.session
def checks(session: nox.Session) -> None:
    """The CI quality gate."""
    typecheck(session)
    imports(session)
    tests(session)


@nox.session
def benchmark(session: nox.Session) -> None:
    """Run latency budget checks with timing enabled."""
    session.run("pytest", "-m", "benchmark", "--benchmark-only", *session.posargs)
