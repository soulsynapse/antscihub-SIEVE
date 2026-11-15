"""The store control: the store's folder drawn as one button, for the player's header. It reads the
folder it is handed, through store.py, and the theme, and nothing of the window it sits in.
"""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton

from . import store, theme
from .held import in_units
from .theme import GAP, ROW_H


def fmt_bytes(n):
    return " ".join(in_units(n))


class StoreControl(QAbstractButton):
    """The store as one control, drawn and not written: a bar and the bytes held. The bar's width is
    the disk the folder is on: the store's files bright, the part files of a cut that died with its
    process hatched, what else is on the disk dim, and the rest free. A store that holds anything is
    a pixel of the bar at least. The tooltip is the folder and the whole of it in words, then `hint`,
    what a press does. The folder is read when it is set and again as the pointer comes over the
    control. Its width never follows its text."""
    BAR_W, BAR_H, EDGE = 100, 8, 6
    OTHER = 105     # the gray of what else is on the disk, between the bar's ground and the store's own

    def __init__(self, hint="", parent=None):
        super().__init__(parent)
        self.hint, self.folder = hint, None
        self.held, self.stray, self.total, self.free = 0, 0, 0, 0
        self.setFont(theme.mono_font())
        self._size_w = QFontMetrics(self.font()).horizontalAdvance("0000.0 GB")
        self.setFixedSize(2 * self.EDGE + self.BAR_W + GAP + self._size_w, ROW_H)
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)

    def set_store(self, folder):
        """`folder`, the store to draw, read now."""
        self.folder = folder
        self.held, n, self.stray = store.held(folder)
        self.total, self.free = store.disk(folder)
        lines = [folder, f"holds {fmt_bytes(self.held)}; {fmt_bytes(self.free)} free of {fmt_bytes(self.total)} on its disk"]
        if n:
            lines.append(f"{n} part file{'s' if n > 1 else ''} of a cut that died with its process, {fmt_bytes(self.stray)}")
        self.setToolTip("\n".join(lines + [self.hint] if self.hint else lines))
        self.update()

    def paintEvent(self, event):
        del event
        p = QPainter(self)
        base = theme.layer(theme.depth_of(self) + 1)
        if self.underMouse() and self.isEnabled():
            theme.paint_hover(p, self)
        h, x = self.height(), self.EDGE
        p.setFont(self.font())
        bar = QRectF(x, (h - self.BAR_H) / 2, self.BAR_W, self.BAR_H)
        p.setRenderHint(QPainter.Antialiasing, False)
        p.fillRect(bar, theme.qgray(theme.GROUND - theme.STEP))
        if self.total:
            px = lambda n: self.BAR_W * n / self.total
            own = min(self.BAR_W, max(1.0, px(self.held))) if self.held else 0.0
            stray = min(own, px(self.stray))
            other = max(0.0, px(self.total - self.free) - own)
            p.fillRect(QRectF(bar.left(), bar.top(), own - stray, self.BAR_H), theme.qgray(theme.INK))
            p.fillRect(QRectF(bar.left() + own - stray, bar.top(), stray, self.BAR_H), theme.qgray(self.OTHER - 45))
            p.fillRect(QRectF(bar.left() + own - stray, bar.top(), stray, self.BAR_H), QBrush(theme.qgray(theme.INK), Qt.BDiagPattern))
            p.fillRect(QRectF(bar.left() + own, bar.top(), other, self.BAR_H), theme.qgray(self.OTHER))
        p.setPen(QPen(theme.qgray(base + theme.LINE_LIFT), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(bar.adjusted(0, 0, -1, -1))
        p.setRenderHint(QPainter.Antialiasing, True)
        x += self.BAR_W + GAP
        p.setPen(theme.qgray(theme.INK))
        p.drawText(QRectF(x, 0, self._size_w, h), Qt.AlignLeft | Qt.AlignVCenter, fmt_bytes(self.held))
        p.end()

    def event(self, e):
        if e.type() == e.Type.HoverEnter and self.folder is not None:
            self.set_store(self.folder)     # a file deleted from it since is told to nobody
        if e.type() in (e.Type.HoverEnter, e.Type.HoverLeave):
            self.update()
        return super().event(e)
