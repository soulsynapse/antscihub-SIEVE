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
#: tests assert against it: a mark past the end lands here, and a window pushed
#: off the end comes to rest against it.
SOURCE_FRAMES = 1000

#: Frame rate the same source is bound at. Named for the same reason: the
#: default working window is ten *seconds*, so the length of the window a test
#: starts with is this number times ten.
SOURCE_FPS = 30.0


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
    """A fresh document bound to a 1000x800 source, 1000 frames at 30 fps."""
    del qapp
    doc = ReplicateDocument()
    doc.bind_source(1000, 800, SOURCE_FRAMES, SOURCE_FPS)
    yield doc
    doc.deleteLater()
