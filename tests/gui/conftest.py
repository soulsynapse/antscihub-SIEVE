"""GUI test fixtures. Every test in this package needs a Qt runtime."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from fractions import Fraction

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
SOURCE_FPS = Fraction(30)


def answering(button: QMessageBox.StandardButton) -> Callable[..., QMessageBox.StandardButton]:
    """A stand-in for a `QMessageBox` static method that always answers `button`."""

    def reply(*_args: object, **_kwargs: object) -> QMessageBox.StandardButton:
        return button

    return reply


@pytest.fixture(autouse=True)
def no_modal_dialogs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Answer every message box, so a stray one cannot hang the run.

    A modal in a headless suite is not a failure — it is a test that never
    returns, and the report names nothing. What survives here is the failure
    dialogs `_warn` raises: `warning` is now only ever a statement, so the
    button it answers with no longer decides anything. `question` and
    `information` are patched for anything that grows one later; nothing in the
    window asks a question today. A test that cares whether something was asked
    overrides this with its own patch and asserts on the arguments.
    """
    monkeypatch.setattr(QMessageBox, "warning", answering(QMessageBox.StandardButton.Ok))
    monkeypatch.setattr(QMessageBox, "question", answering(QMessageBox.StandardButton.No))
    monkeypatch.setattr(QMessageBox, "information", answering(QMessageBox.StandardButton.Ok))
    # And the constructed kind, which the static helpers cannot cover: the
    # geometry lock's dialog carries its own button wording, so it is a
    # `QMessageBox` instance and its `exec` is what would hang. Cancel is the
    # safe stand-in answer — the reply that changes nothing.
    monkeypatch.setattr(QMessageBox, "exec", answering(QMessageBox.StandardButton.Cancel))


@pytest.fixture
def document(qapp: object) -> Iterator[ReplicateDocument]:
    """A fresh document bound to a 1000x800 source, 1000 frames at 30 fps."""
    del qapp
    doc = ReplicateDocument()
    doc.bind_source(1000, 800, SOURCE_FRAMES, SOURCE_FPS)
    yield doc
    doc.deleteLater()
