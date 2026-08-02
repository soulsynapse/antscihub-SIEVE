"""Conftest adapter: part of the closed debt-machinery class (docs/PLAN.md).

A caught Owed marker becomes a pytest skip carrying the debt as its reason,
so the suite stays green while the debt shows in the skip summary.
Membership is checked against a fresh once-per-session enumeration: a caught
marker the enumerator cannot see fails instead, so the static and dynamic
instruments cross-verify.
"""

from functools import cache
from pathlib import Path

import pytest

from sieve.debt import MODULE_QUALNAME, Owed, enumerate_markers

REPO_ROOT = Path(__file__).resolve().parent.parent


@cache
def _reasons() -> "dict[tuple[str, str], str]":
    return {(e.path, e.qualname): e.reason for e in enumerate_markers(REPO_ROOT)}


def _raise_site(excinfo):
    """(repo-relative path, qualname, lineno) of the frame that raised."""
    tb = excinfo.tb
    while tb.tb_next is not None:
        tb = tb.tb_next
    code = tb.tb_frame.f_code
    try:
        rel = Path(code.co_filename).resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return None
    return rel, code.co_qualname.replace(".<locals>.", "."), tb.tb_lineno


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    if call.excinfo is None or not call.excinfo.errisinstance(Owed):
        return
    report = outcome.get_result()
    site = _raise_site(call.excinfo)
    reason = _reasons().get(site[:2]) if site else None
    if reason is None:
        report.outcome = "failed"
        report.longrepr = (
            f"Owed raised at {site}: a marker the enumerator cannot see "
            "(outside marker form rule v1)"
        )
    else:
        report.outcome = "skipped"
        report.longrepr = (str(item.path), site[2], f"owed: {reason}")


@pytest.hookimpl(hookwrapper=True)
def pytest_collect_file(file_path, parent):
    """Module-form placeholder test files skip instead of dying at import.

    A wrapper because this hook aggregates results: returning our collector
    alongside the default module collector would import the file anyway.
    """
    outcome = yield
    if not file_path.name.startswith("test_"):
        return
    try:
        rel = file_path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return
    if (rel, MODULE_QUALNAME) in _reasons():
        outcome.force_result([_OwedFile.from_parent(parent, path=file_path)])


class _OwedFile(pytest.File):
    def collect(self):
        rel = self.path.resolve().relative_to(REPO_ROOT).as_posix()
        reason = _reasons()[(rel, MODULE_QUALNAME)]
        yield _OwedItem.from_parent(self, name="owed", reason=reason)


class _OwedItem(pytest.Item):
    def __init__(self, *, reason: str, **kwargs):
        super().__init__(**kwargs)
        self._reason = reason

    def runtest(self):
        pytest.skip(f"owed: {self._reason}")

    def reportinfo(self):
        return self.path, 0, f"owed: {self._reason}"
