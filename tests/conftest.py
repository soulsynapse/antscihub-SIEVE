"""Conftest adapter: part of the closed debt-machinery class (PAR-0002).

A caught Owed marker becomes a pytest skip carrying the debt as its reason,
so the suite stays green while the debt shows in the skip summary.
Membership is checked against a fresh once-per-session enumeration: a caught
marker the enumerator cannot see fails instead, so the static and dynamic
instruments cross-verify. Import-time markers are handled at collection by
a Module subclass; run-time markers by the makereport hook (setup and call
phases only -- a marker reached during teardown stays red, honestly, since
its finalizers never ran).
"""

from functools import cache
from pathlib import Path

import pytest

from sieve.debt import EnumerationError, Owed, enumerate_markers

REPO_ROOT = Path(__file__).resolve().parent.parent


@cache
def _reasons() -> "dict[tuple[str, str], str]":
    return {(e.path, e.qualname): e.reason for e in enumerate_markers(REPO_ROOT)}


def pytest_configure(config):
    # Eager: an enumeration failure surfaces once, pointedly, at session
    # start -- not as a plugin crash mid-collection.
    try:
        _reasons()
    except EnumerationError as err:
        pytest.exit(f"debt enumeration failed: {err}", returncode=4)


def _raise_site(tb):
    """(repo-relative path, qualname, lineno) of the frame that raised."""
    while tb.tb_next is not None:
        tb = tb.tb_next
    code = tb.tb_frame.f_code
    try:
        rel = Path(code.co_filename).resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return None
    return rel, code.co_qualname.replace(".<locals>.", "."), tb.tb_lineno


def _unseen_message(site, exc):
    if site is None:
        return (
            f"Owed({exc.args[0]!r}) raised outside the repo tree: only "
            "markers under the repo root are enumerable"
            if exc.args
            else "Owed raised outside the repo tree"
        )
    return (
        f"Owed raised at {site[0]}::{site[1]} (line {site[2]}): a marker "
        "the enumerator cannot see (outside marker form rule v2)"
    )


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    report = yield
    if (
        call.when not in ("setup", "call")
        or call.excinfo is None
        or not call.excinfo.errisinstance(Owed)
    ):
        return report
    site = _raise_site(call.excinfo.tb)
    reason = _reasons().get(site[:2]) if site else None
    if reason is None:
        report.outcome = "failed"
        report.longrepr = _unseen_message(site, call.excinfo.value)
    else:
        report.outcome = "skipped"
        report.longrepr = (site[0], site[2], f"owed: {reason}")
    return report


def pytest_pycollect_makemodule(module_path, parent):
    return _AdaptedModule.from_parent(parent, path=module_path)


class _AdaptedModule(pytest.Module):
    """Import-time Owed: a skip item for a member, a pointed error otherwise.

    Covers both a module-form placeholder collected as a test module and a
    test module that imports a placeholder at top level.
    """

    def collect(self):
        try:
            return list(super().collect())
        except Owed as exc:
            site = _raise_site(exc.__traceback__)
            reason = _reasons().get(site[:2]) if site else None
            if reason is None:
                raise pytest.Collector.CollectError(_unseen_message(site, exc)) from exc
            return [_OwedItem.from_parent(self, name="owed", reason=f"owed: {reason}")]


class _OwedItem(pytest.Item):
    def __init__(self, *, reason: str, **kwargs):
        super().__init__(**kwargs)
        self._reason = reason

    def runtest(self):
        pytest.skip(self._reason)

    def reportinfo(self):
        return self.path, 0, self._reason
