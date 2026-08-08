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

**Nothing under `tests/gui/` may import Qt, or a `sieve.gui` module, at module
scope.** `tests/bench/test_loop_budget.py` asserts that no Qt module is
resident while the headless loop budget is measured, and pytest imports every
test module during collection — before the first test runs — so a top-level
`from sieve.gui.app import ...` anywhere in this directory would make Qt
resident for the entire session and take that assertion down with it. Deferring
the import into the test body is enough: collection stays Qt-free, and
`tests/bench` runs before `tests/gui` in the order pytest walks `testpaths`.
It fails loudly rather than quietly if someone forgets.
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
