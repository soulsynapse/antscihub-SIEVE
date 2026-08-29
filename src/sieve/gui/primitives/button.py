"""Text button in four emphasis weights: PRIMARY, DEFAULT, SUBTLE, GHOST."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QPushButton, QWidget

from sieve.gui import metrics, palette
from sieve.gui.palette import ACCENT, DIM, LINE, PANEL, PANEL_HOT, TEXT, mix, rgb

PRIMARY = "primary"
DEFAULT = "default"
SUBTLE = "subtle"
GHOST = "ghost"

# Public: any filled surface mixes toward ink by this fraction on hover.
HOVER = 0.14
_PRESS = 0.26

_HOVER_EDGE = 0.22

_OFF_INK = 0.45

_PAD_X = 12
_PAD_Y = 6
_PAD_X_SMALL = 8
_PAD_Y_SMALL = 3
_RADIUS = 4


class Button(QPushButton):
    """Labelled button in one of the four emphasis kinds."""

    def __init__(
        self,
        text: str = "",
        kind: str = DEFAULT,
        *,
        small: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName("button")
        self._kind = kind
        self._small = small
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dress()
        # Bound methods so PySide6 drops the connection when the receiver dies.
        palette.CHANGED.connect(self._dress)
        metrics.CHANGED.connect(self._dress)

    def set_kind(self, kind: str) -> None:
        self._kind = kind
        self._dress()

    def _dress(self) -> None:
        fill, ink, edge = _rest(self._kind)
        hover_fill, hover_ink, hover_edge = _hover(self._kind)
        pad_x = _PAD_X_SMALL if self._small else _PAD_X
        pad_y = _PAD_Y_SMALL if self._small else _PAD_Y
        role = "gloss" if self._small else "name"
        self.setStyleSheet(f"""
            #button {{
                background: {fill};
                color: {rgb(ink)};
                border: 1px solid {edge};
                border-radius: {_RADIUS}px;
                padding: {pad_y}px {pad_x}px;
                font-size: {metrics.pt(role)}pt;
            }}
            #button:hover {{
                background: {hover_fill};
                color: {rgb(hover_ink)};
                border-color: {hover_edge};
            }}
            #button:pressed {{ background: {_pressed(self._kind)}; }}
            #button:focus {{ border-color: {rgb(ACCENT)}; }}
            #button:disabled {{
                background: {_off_fill(self._kind)};
                color: {rgb(_off_ink(self._kind))};
                border-color: {_off_edge(self._kind)};
            }}
        """)


_NONE = "transparent"


def _rest(kind: str) -> tuple[str, QColor, str]:
    if kind == PRIMARY:
        return rgb(ACCENT), PANEL, rgb(ACCENT)
    if kind == SUBTLE:
        return rgb(PANEL_HOT), TEXT, rgb(PANEL_HOT)
    if kind == GHOST:
        return _NONE, DIM, _NONE
    return rgb(PANEL), TEXT, rgb(LINE)


def _hover(kind: str) -> tuple[str, QColor, str]:
    if kind == PRIMARY:
        return rgb(mix(ACCENT, TEXT, HOVER)), PANEL, rgb(mix(ACCENT, TEXT, HOVER))
    if kind == SUBTLE:
        step = rgb(mix(PANEL_HOT, TEXT, HOVER))
        return step, TEXT, step
    if kind == GHOST:
        return rgb(PANEL_HOT), TEXT, _NONE
    return rgb(PANEL_HOT), TEXT, rgb(mix(LINE, TEXT, _HOVER_EDGE))


def _pressed(kind: str) -> str:
    if kind == PRIMARY:
        return rgb(mix(ACCENT, TEXT, _PRESS))
    return rgb(mix(PANEL_HOT, TEXT, _PRESS - HOVER))


def _off_fill(kind: str) -> str:
    return _NONE if kind == GHOST else rgb(PANEL_HOT)


def _off_ink(kind: str) -> QColor:
    return mix(DIM, PANEL, _OFF_INK) if kind == GHOST else DIM


def _off_edge(kind: str) -> str:
    if kind == GHOST:
        return _NONE
    return rgb(LINE)
