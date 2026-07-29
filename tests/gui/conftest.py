

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest

pytest.importorskip("PySide6", reason="requires the gui extra")

from PySide6.QtWidgets import QMessageBox

from sieve.gui.document import ReplicateDocument








SOURCE_FRAMES = 1000




SOURCE_FPS = 30.0


def answering(button: QMessageBox.StandardButton) -> Callable[..., QMessageBox.StandardButton]:


    def reply(*_args: object, **_kwargs: object) -> QMessageBox.StandardButton:
        return button

    return reply


@pytest.fixture(autouse=True)
def no_modal_dialogs(monkeypatch: pytest.MonkeyPatch) -> None:










    monkeypatch.setattr(QMessageBox, "warning", answering(QMessageBox.StandardButton.Ok))
    monkeypatch.setattr(QMessageBox, "question", answering(QMessageBox.StandardButton.No))
    monkeypatch.setattr(QMessageBox, "information", answering(QMessageBox.StandardButton.Ok))




    monkeypatch.setattr(QMessageBox, "exec", answering(QMessageBox.StandardButton.Cancel))


@pytest.fixture
def document(qapp: object) -> Iterator[ReplicateDocument]:

    del qapp
    doc = ReplicateDocument()
    doc.bind_source(1000, 800, SOURCE_FRAMES, SOURCE_FPS)
    yield doc
    doc.deleteLater()
