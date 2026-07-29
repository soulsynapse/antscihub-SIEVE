







































from __future__ import annotations

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QToolButton, QWidget

from sieve.gui.preferences import Preferences





LABEL_COLOR = "Color · 1x"
LABEL_GRAY = "Gray · ~2.5x"

LABEL_AUTO = "Gray · ~2.5x · rendering"

_TOOLTIP = (
    "Decode the viewport in grayscale: colour off, playback roughly 2.5x.\n"
    "The graphs are computed from luma either way — this changes nothing "
    "about the analysis.\nWhile a render is filling the pane goes gray on "
    "its own; clicking then keeps colour for that render."
)


class GrayToggle(QToolButton):



    luma_changed = Signal(bool)

    def __init__(self, preferences: Preferences, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._preferences = preferences
        self._manual = preferences.viewport_luma
        self._rendering = False
        self._pinned = False
        self._effective = self._manual

        self.setCheckable(True)
        self.setToolTip(_TOOLTIP)
        self.clicked.connect(self._on_clicked)


        preferences.changed.connect(self._on_preferences_changed)
        self._refresh()

    @property
    def effective_luma(self) -> bool:

        return self._effective

    @Slot(bool)
    def set_rendering(self, active: bool) -> None:

        if active == self._rendering:
            return
        self._rendering = active
        if not active:

            self._pinned = False
        self._refresh()

    @Slot()
    def _on_clicked(self) -> None:






        if self._effective:
            if self._manual:
                self._manual = False
                self._preferences.viewport_luma = False
            if self._rendering:
                self._pinned = True
        else:
            self._manual = True
            self._pinned = False
            self._preferences.viewport_luma = True
        self._refresh()

    @Slot()
    def _on_preferences_changed(self) -> None:
        stored = self._preferences.viewport_luma
        if stored == self._manual:
            return
        self._manual = stored
        self._refresh()

    def _refresh(self) -> None:
        effective = self._manual or (self._rendering and not self._pinned)
        auto = effective and not self._manual
        self.setChecked(effective)
        if not effective:
            self.setText(LABEL_COLOR)
        else:
            self.setText(LABEL_AUTO if auto else LABEL_GRAY)
        if effective != self._effective:
            self._effective = effective
            self.luma_changed.emit(effective)
