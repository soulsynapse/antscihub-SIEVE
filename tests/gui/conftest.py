"""One offscreen `QApplication` for every GUI test in this directory.

The platform is set here, at import time, rather than in a workflow's `env:`
block: Qt reads `QT_QPA_PLATFORM` when the first `QGuiApplication` is
constructed, and a laptop that happens to have a display would otherwise open
real windows for a `pytest` nobody asked to watch. `setdefault` rather than an
assignment, so a session deliberately exported something else — `xcb` to
actually look at a widget — still gets it.

The application is session-scoped because Qt permits exactly one per process
and refuses to build a second; a fixture that made one per test would fail on
the second test in the file.

**Qt is imported inside test bodies here, and that is now a convention rather
than a rule with teeth.** It was a rule: `tests/bench/test_loop_budget.py` used
to assert that no Qt module was resident at the moment the headless budget was
judged, and pytest imports every test module during collection, so one top-level
`from sieve.gui.app import ...` anywhere in this directory took that assertion
down. 07.11 measures the same ceilings *through* the GUI, in a session with a
`QApplication` in it by construction, so the assertion was restated as a claim
about what the measurement's own code imports — asked in a fresh interpreter,
where no test module's ordering can reach it
(`test_loop_budget.test_the_measurement_imports_no_qt`).

What deferring the import still buys is worth keeping: collecting this directory
costs nothing on a machine without a display, and a test that fails to import Qt
fails as itself rather than as a collection error for the whole run.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp() -> Iterator[Any]:
    from PySide6.QtWidgets import QApplication

    application = QApplication.instance() or QApplication([])
    yield application
    # Not `quit()` or `shutdown()`: the interpreter is about to exit anyway, and
    # tearing the application down while widgets from the last test are still
    # awaiting deletion is how a passing suite ends in a native crash.
