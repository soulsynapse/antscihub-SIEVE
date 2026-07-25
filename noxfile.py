"""Nox sessions: SIEVE's development and CI task interface (ADR-009).

Session names are the supported automation interface. CI calls session names,
not their internals, so a session's implementation can change freely while its
name and contract stay put.

Environment setup follows ADR-012: sessions install the editable project and
its ``dev`` extra with uv. That install resolves the constraints declared in
``pyproject.toml``; it does not sync the committed ``uv.lock``. Nothing here
should be described as a locked environment.

Sessions whose real work does not exist yet are present and skip with a stated
reason rather than being omitted, because the interface is the contract. Each
one carries a tripwire: when the precondition that makes the session real
appears in the tree, the session fails and names what it now has to do. A
session that passes silently forever is worse than no session.
"""

from __future__ import annotations

import os
from pathlib import Path

import nox

ROOT = Path(__file__).parent
SRC = ROOT / "src" / "sieve"

nox.options.default_venv_backend = "uv|virtualenv"
nox.options.reuse_existing_virtualenvs = True
nox.options.sessions = ["checks"]

# Qt needs a platform plugin even with no display. ADR-009 keeps GL-dependent
# renderer tests out of this session; they get their own and are not offscreen.
OFFSCREEN_ENV = {"QT_QPA_PLATFORM": "offscreen"}


def install_project(session: nox.Session, extras: str = "dev") -> None:
    """Install the editable project plus an extra (ADR-012).

    Centralized here rather than repeated per session so the installation
    policy has one place to change.
    """
    session.install("-e", f".[{extras}]")


def _has_filters() -> bool:
    """Whether any filter implementation exists yet.

    Several sessions are waiting on the first filter: determinism needs
    something to run twice, the contract suite derives its Hypothesis
    strategies from a filter's Pydantic model, and the generated JSON Schema
    derives from the same model.
    """
    filters = SRC / "core" / "filters"
    if not filters.is_dir():
        return False
    # rglob, not glob: a filter lives in a category directory under
    # core/filters/, so a top-level-only check would never see one and the
    # tripwires below would stay silent forever.
    return any(p.name != "__init__.py" for p in filters.rglob("*.py"))


# --------------------------------------------------------------------------
# Gates. Non-mutating: they report and fail, they never rewrite the checkout.
# --------------------------------------------------------------------------


def _lint(session: nox.Session) -> None:
    session.run("ruff", "check", ".")
    session.run("ruff", "format", "--check", ".")


def _typecheck(session: nox.Session) -> None:
    session.run("pyright")


def _layers(session: nox.Session) -> None:
    session.run("lint-imports")


def _test(session: nox.Session, *args: str) -> None:
    # The fast suite runs against the headless install, which is the whole
    # point: if a test needs a Qt binding it is marked `qt` and belongs to
    # test_gui. A `not slow` suite that quietly required Qt would make the
    # headless guarantee untested by the thing that runs most often.
    session.run("pytest", "-m", "not slow and not qt", *args, env=OFFSCREEN_ENV)


@nox.session
def lint(session: nox.Session) -> None:
    """Ruff lint and format check (ADR-003)."""
    install_project(session)
    _lint(session)


@nox.session
def typecheck(session: nox.Session) -> None:
    """Pyright, strict on core/ and pipeline/ (ADR-003)."""
    install_project(session)
    _typecheck(session)


@nox.session
def layers(session: nox.Session) -> None:
    """Layer dependency contract (ARCHITECTURE.md 3).

    Not one of ADR-009's named sessions. It is a gate on a product guarantee
    rather than on style: a Qt import reaching core/, pipeline/, or bench/ is
    the loss of headless and CLI parity, not a formatting complaint.
    """
    install_project(session)
    _layers(session)


@nox.session
def test(session: nox.Session) -> None:
    """The fast suite. The inner loop (ADR-008)."""
    install_project(session)
    _test(session, *session.posargs)


@nox.session
def test_gui(session: nox.Session) -> None:
    """Tests marked qt, offscreen (ADR-009).

    Separate from `test` because pytest-qt cannot be installed into the
    headless environment: it errors at collection when no Qt binding is
    importable. GL-dependent renderer tests are marked `gl` and are not run
    here -- offscreen is not a GL-capable platform.

    [OPEN QUESTION] This session is not part of `checks`, so the default gate
    has no GUI coverage. That costs nothing while gui/ is empty. Whether it
    joins `checks` or stays a separately-invoked CI job is a decision due at
    the first GUI commit -- see NOTES.md.
    """
    install_project(session, "dev-gui")
    session.run("pytest", "-m", "qt and not gl", *session.posargs, env=OFFSCREEN_ENV)


@nox.session
def test_slow(session: nox.Session) -> None:
    """Only the tests marked slow (ADR-008)."""
    install_project(session)
    session.run("pytest", "-m", "slow", *session.posargs, env=OFFSCREEN_ENV)


@nox.session
def determinism_check(session: nox.Session) -> None:
    """Byte-comparable re-run of the canonical pipeline (ARCHITECTURE.md 12).

    Determinism is asserted, never timed (ADR-008).
    """
    if not _has_filters():
        session.skip(
            "No filter exists yet, so there is no canonical pipeline to run "
            "twice. This session becomes required at the first filter."
        )
    session.error(
        "core/filters/ now has an implementation, so the canonical-pipeline "
        "determinism check is due. Implement it here and remove this tripwire."
    )


@nox.session
def benchmark(session: nox.Session) -> None:
    """Latency budgets from ARCHITECTURE.md 1, measured (ADR-008).

    Separate from `checks`: its runtime and its sensitivity to the host make it
    unsuitable for every inner-loop run. CI invokes it explicitly.

    Reports rather than gates, by default. ADR-008 forbids a single universal
    wall-time threshold across heterogeneous developer machines, so a verdict
    is recorded into each result's metadata and read by a human. Setting
    SIEVE_BENCH_ENFORCE makes a past-margin regression a failure -- that is the
    switch a machine established as canonical throws, and it is deliberately
    not the default.

    The measurements read a generated corpus that is not committed. Tests skip
    with the regeneration command when it is absent, which is why an absent
    corpus is a quiet session rather than a red one.
    """
    bench_tests = ROOT / "tests" / "bench"
    if not bench_tests.is_dir():
        session.error(
            "tests/bench/ is gone. The latency harness is the only thing that reads "
            "the ARCHITECTURE.md 1 budget table as data; without it the budgets are "
            "prose again. Restore it or remove this session deliberately."
        )
    install_project(session)
    # --benchmark-only deselects tests that never call the benchmark fixture,
    # which is correct here: test_budget_table.py measures nothing and belongs
    # to `checks`. No `-m` filter, deliberately -- every measurement in here is
    # marked slow by construction, so the inner loop's exclusion would empty
    # this session out.
    session.run("pytest", str(bench_tests), "--benchmark-only", *session.posargs)


@nox.session
def build_docs(session: nox.Session) -> None:
    """Generated documentation and schema freshness (ADR-009).

    A gate session checks freshness and fails; it does not regenerate. The
    generated artifact is the JSON Schema derived from the filter models
    (ADR-004), so there is nothing to generate before the first filter.
    """
    if not _has_filters():
        session.skip(
            "No filter model exists, so no JSON Schema is generated yet. "
            "This session becomes required at the first filter."
        )
    session.error(
        "core/filters/ now has an implementation, so generated-schema "
        "freshness is checkable. Implement it here and remove this tripwire."
    )


@nox.session
def gpu_test(session: nox.Session) -> None:
    """Tests marked gpu, against CuPy (ADR-016).

    Capability-detected by default so a CPU-only machine reports why it
    skipped. Setting SIEVE_REQUIRE_GPU makes absent or unusable CUDA a
    failure, which is what a CI job claiming to prove GPU support must use --
    otherwise a nominal GPU job passes without executing GPU code (ADR-009).
    """
    required = os.environ.get("SIEVE_REQUIRE_GPU", "").strip().lower() in {"1", "true", "yes"}
    install_project(session, "dev,gpu" if required else "dev")

    # The probe reports the device count on stdout rather than through its exit
    # status. `session.run` returns the captured output whether or not the
    # command succeeded, so an exit code cannot be read back from its return
    # value -- a capability check written that way reports "available" always,
    # which is the exact failure ADR-009 warns about.
    probe = (
        "count = 0\n"
        "try:\n"
        "    import cupy\n"
        "    count = cupy.cuda.runtime.getDeviceCount()\n"
        "except Exception:\n"
        "    pass\n"
        "print(count)\n"
    )
    output = session.run("python", "-c", probe, silent=True) or ""
    device_count = output.strip().splitlines()[-1].strip() if output.strip() else "0"
    if device_count == "0":
        message = "CuPy or CUDA is unavailable in this environment."
        if required:
            session.error(f"{message} SIEVE_REQUIRE_GPU is set, so this is a failure.")
        session.skip(f"{message} Set SIEVE_REQUIRE_GPU to make this a failure.")

    session.run("pytest", "-m", "gpu", *session.posargs)


@nox.session(venv_backend="none")
def code_health(session: nox.Session) -> None:
    """Report on the shape of the tree. Never a gate.

    Deliberately not part of `checks`. The gates answer "is this allowed"; this
    answers "what grew in a direction nobody decided", and the honest response
    to most of its output is "noted" rather than "fix it". Folding it into a
    gate would turn its findings into things to suppress.

    No virtualenv: it is stdlib-only by design, so it runs against whatever
    interpreter invoked Nox rather than paying an install to analyze text.
    """
    session.run("python", str(ROOT / "tools" / "code_health.py"), *session.posargs)


@nox.session
def checks(session: nox.Session) -> None:
    """The composed, non-mutating quality gate (ADR-009).

    Runs in one environment rather than notifying the individual sessions, so
    the gate is one install and the failure output stays in one place.
    """
    install_project(session)
    _lint(session)
    _typecheck(session)
    _layers(session)
    _test(session)
    for name in ("determinism_check", "build_docs"):
        session.log(f"{name}: see its own session; skipped until the first filter exists.")


# --------------------------------------------------------------------------
# Developer sessions. These rewrite the checkout and are never part of a gate.
# --------------------------------------------------------------------------


@nox.session
def format(session: nox.Session) -> None:
    """Apply Ruff fixes and formatting. Local use only (ADR-003)."""
    install_project(session)
    session.run("ruff", "check", "--fix", ".")
    session.run("ruff", "format", ".")
