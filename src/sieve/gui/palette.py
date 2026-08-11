"""The colours every view draws with.

Held above `frame` because the frame is not the only thing that reads them: the
panes' contents paint cards, plots and footage against the same values,
and a palette owned by the frame would be imported back up out of it by
everything the frame contains.
"""

from __future__ import annotations

from PySide6.QtGui import QColor

#: The ground the panes leave uncovered — the menu bar's strip, splitter seams.
STACK_BG = QColor(24, 26, 30)

#: A pane's own fill, and the lighter one a control wears against it.
PANEL = QColor(31, 33, 38)
PANEL_HOT = QColor(38, 41, 47)

#: Hairlines and dividers. Legible on `PANEL`; against `STACK_BG` it is what a
#: seam is made of rather than a line drawn on one.
LINE = QColor(55, 58, 66)

#: What a view standing over the panes lays over them. Dark and translucent
#: rather than opaque: the work is not being replaced, only stood in front of,
#: and it stays visible enough to say so while being too dim to read against.
SCRIM = QColor(12, 13, 16, 210)

TEXT = QColor(230, 231, 235)
DIM = QColor(139, 142, 152)

#: The one colour that means *this is what you are acting on*: a hovered seam,
#: a selected crop, a detected block.
ACCENT = QColor(94, 200, 180)


def rgb(color: QColor) -> str:
    """A colour as a stylesheet's `rgb(...)`, since Qt's own repr is not one."""
    return f"rgb({color.red()},{color.green()},{color.blue()})"
