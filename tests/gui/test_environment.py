"""The Qt binding, proven rather than assumed (ADR-001).

[INTENT] The first `qt`-marked test, so `nox -s test_gui` stops skipping.
NOTES.md 28-33: the absence of PyQt6 is what enforces the licensing choice --
qtpy resolving to PySide6 says which binding qtpy *picked*, not that PyQt6 is
unreachable. A reintroduced PyQt6 alongside PySide6 would still let qtpy
resolve to PySide6 (it is not deterministic across environments which one
wins) while silently returning the project to a GPLv3 dependency. Both halves
have to hold.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.qt


def test_qtpy_resolves_to_pyside6() -> None:
    # Local: a module-level import would fail collection in the headless `dev`
    # environment, where neither binding exists -- `not qt` deselection only
    # skips execution, not collection.
    import qtpy  # noqa: PLC0415

    assert qtpy.API_NAME == "PySide6"


def test_pyqt6_is_not_installed() -> None:
    with pytest.raises(ImportError):
        import PyQt6  # noqa: F401, PLC0415  # pyright: ignore[reportMissingImports]
