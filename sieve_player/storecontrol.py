"""The store control: a store.Store drawn as one button, for the player's header. It reads the
store it is handed and the theme, and nothing of the window it sits in.
"""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QAbstractButton

from . import theme
from .store import fmt_bytes
from .theme import GAP, ROW_H


class StoreControl(QAbstractButton):
    """A Store as one control, drawn and not written: a bar and the bytes held. The bar's width is
    the disk the folder is on: the store's files bright, the part files of a bake that died with its
    process hatched, what else is on the disk dim, and the rest free. A store that holds anything is
    a pixel of the bar at least. The tooltip is the folder and the whole of it in words, then `hint`,
    what a press does. Its width never follows its text."""
    BAR_W, BAR_H, EDGE = 100, 8, 6
    OTHER = 105     # the gray of what else is on the disk, between the bar's ground and the store's own

    def __init__(self, hint="", parent=None):
        super().__init__(parent)
        self.hint = hint
        self.held, self.stray, self.total, self.free = 0, 0, 0, 0
        self.setFont(theme.mono_font())
        self._size_w = QFontMetrics(self.font()).horizontalAdvance("0000.0 GB")
        self.setFixedSize(2 * self.EDGE + self.BAR_W + GAP + self._size_w, ROW_H)
        self.setAttribute(Qt.WA_Hover, True)
        self.setCursor(Qt.PointingHandCursor)

    def set_store(self, st):
        """`st`, the store.Store to draw, read now: a file landing in it later is not seen until this is called again."""
        self.held = st.held()
        n, self.stray = st.strays()
        self.total, self.free = st.disk()
        lines = [st.folder, f"holds {fmt_bytes(self.held)}; {fmt_bytes(self.free)} free of {fmt_bytes(self.total)} on its disk"]
        if n:
            lines.append(f"{n} part file{'s' if n > 1 else ''} of a bake that died with its process, {fmt_bytes(self.stray)}")
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
        if e.type() in (e.Type.HoverEnter, e.Type.HoverLeave):
            self.update()
        return super().event(e)
