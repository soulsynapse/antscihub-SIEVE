"""GUI test fixtures. Every test in this package needs a Qt runtime."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest

pytest.importorskip("PySide6", reason="requires the gui extra")

from PySide6.QtWidgets import QMessageBox

from sieve.gui.document import ReplicateDocument

# The `gui` marker is declared per module, not here: pytest reads `pytestmark`
# from test modules and classes only, so a conftest-level one is silently inert.


#: Length of the source the `document` fixture binds. Named because the clip
#: tests assert against it: a mark past the end lands here, and an in point on
#: its own runs to here.
SOURCE_FRAMES = 1000


def answering(button: QMessageBox.StandardButton) -> Callable[..., QMessageBox.StandardButton]:
    """A stand-in for a `QMessageBox` static method that always answers `button`."""

    def reply(*_args: object, **_kwargs: object) -> QMessageBox.StandardButton:
        return button

    return reply


@pytest.fixture(autouse=True)
def no_modal_dialogs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Answer every message box, so a stray one cannot hang the run.

    A modal in a headless suite is not a failure — it is a test that never
    returns, and the report names nothing. The answers are the ones that let
    teardown finish: discard unsaved work, decline the offer to open a
    neighbouring project. A test about either prompt overrides this with its own
    patch and asserts on the arguments.
    """
    monkeypatch.setattr(QMessageBox, "warning", answering(QMessageBox.StandardButton.Discard))
    monkeypatch.setattr(QMessageBox, "question", answering(QMessageBox.StandardButton.No))
    monkeypatch.setattr(QMessageBox, "information", answering(QMessageBox.StandardButton.Ok))


@pytest.fixture
def document(qapp: object) -> Iterator[ReplicateDocument]:
    """A fresh document bound to a 1000x800 source, 1000 frames long."""
    del qapp
    doc = ReplicateDocument()
    doc.bind_source(1000, 800, SOURCE_FRAMES)
    yield doc
    doc.deleteLater()
