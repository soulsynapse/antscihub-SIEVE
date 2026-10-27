"""The network editor. `spec/canvas.md` is the spec; this is its Nodes and Navigation share, with
the wires the document already holds drawn so that a chain can be seen and cut by deleting a node:
a node one layer above the ground with its connectors and its display flag, select, box-select,
drag, Delete, the mark on a node whose tool was not found and on an input nothing feeds; pan, zoom
about the cursor, H to frame. It reads and writes the document and nothing else. The tools'
declared types reach it as data, for the connectors' colours and the unfed mark; what the runtime
makes of the graph never does.

Geometry is in document space; the view is a pan and a zoom applied to the painter, never written
to the document. A key pressed with the cursor over the canvas is the canvas's, as in Houdini's
panes, unless something is being typed into: Space held pans with the left button instead of
toggling play, H frames.
"""
import zlib

from PySide6.QtCore import QCoreApplication, QEvent, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QAbstractSpinBox, QApplication, QLineEdit, QPlainTextEdit, QSizePolicy, QTextEdit,
                               QToolTip, QWidget)

from . import theme
from .document import INPUT, VIDEO_PRODUCES, VIDEO_TOOL, expects, fed, fits, produces
from .theme import PAD, qgray

NODE_W, NODE_H = 140, 28   # a node's box, canvas px
FLAG_R = 5                 # the display flag: a disc at the node's right end
PIN_R = 4                  # a connector: a disc on the node's top or bottom edge
HIT = 3                    # slack around a flag or a connector, px
WIRE_W = 1.5
WIRE_BEND = 24             # the least a wire runs vertically out of a connector before it turns
ZOOM_MIN, ZOOM_MAX = 0.25, 4.0
ZOOM_STEP = 1.15           # per wheel notch
FRAME_PAD = 2 * PAD        # view px kept clear around what H frames
TYPING = (QLineEdit, QAbstractSpinBox, QTextEdit, QPlainTextEdit)   # focus here keeps its keys


def type_color(t):
    """One colour per product type, the same in every document: the theme's hue for it, else one
    hashed from the name, kept out of the red and the accent bands so it never reads as a mark.
    None, a type nobody declared, is the tertiary ink."""
    if t is None:
        return qgray(theme.INK_2)
    h = theme.TYPE_HUES.get(t)
    if h is None:
        h = zlib.crc32(t.encode()) % 240
        h = 35 + h if h < 160 else 255 + (h - 160)
    return QColor.fromHsv(h, *theme.TYPE_SV)


class Canvas(QWidget):
    """`tools` is the catalogue, name to module; the document's node names index it."""
    selectionChanged = Signal(list)   # the selected node ids, in selection order
    changed = Signal()                # the document's nodes, wires or flag changed here

    def __init__(self, tools, parent=None):
        super().__init__(parent)
        self.tools = tools
        self.doc = None
        self.selected = []
        self.hover = None                       # the node id under the pointer
        self._drag = None                       # ("move", start, {id: pos}) | ("box", start, shift, base)
                                                # | ("pan", start, pan) | None; starts in document space but pan's
        self._box = None                        # the rubber band, while one is drawn, document space
        self.pan = QPointF(2 * PAD, 2 * PAD)    # where the document's (0, 0) sits, view px
        self.zoom = 1.0
        self._space = False                     # Space is held with the cursor here
        self.setMinimumSize(160, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.ClickFocus)
        QCoreApplication.instance().installEventFilter(self)

    def set_document(self, doc):
        self.doc = doc
        self.hover = self._drag = self._box = None
        self.select([])
        self.update()

    def select(self, ids):
        """Select exactly `ids`, dropping any the document lacks."""
        ids = [i for i in ids if any(n.id == i for n in self.doc.nodes)] if self.doc else []
        if ids != self.selected:
            self.selected = ids
            self.update()
            self.selectionChanged.emit(list(ids))

    def set_flag(self, nid):
        if self.doc is not None and nid != self.doc.display:
            self.doc.display = nid
            self.update()
            self.changed.emit()

    def delete_selected(self):
        """Removes the selected nodes and every wire into or out of them; the flag goes with its node."""
        if not self.selected:
            return
        for nid in self.selected:
            self.doc.remove_node(nid)
        self.hover = None
        self.update()
        self.changed.emit()
        self.select([])

    # -- what the document and the tools say of a node -----------------------
    def inputs(self, node):
        """(name, expected types or None) per input: none on the video node, one on every other."""
        if node.tool == VIDEO_TOOL:
            return []
        return [(INPUT, None if node.unresolved else expects(self.tools.get(node.tool)))]

    def has_output(self, node):
        """Whether the node hands anything out: a series node does not; an unresolved node might."""
        if node.tool == VIDEO_TOOL or node.unresolved:
            return True
        return getattr(self.tools.get(node.tool), "PRODUCES", None) is not None

    def output_type(self, node):
        if node.tool == VIDEO_TOOL:
            return VIDEO_PRODUCES
        return None if node.unresolved else produces(self.doc, self.tools, node.id)

    def unfed(self, node):
        """The mark: a resolved node the video does not reach through wires whose types fit."""
        return not node.unresolved and node.tool != VIDEO_TOOL and not fed(self.doc, node.id, self.tools)

    # -- the view ----------------------------------------------------------
    def to_doc(self, v):
        return QPointF((v.x() - self.pan.x()) / self.zoom, (v.y() - self.pan.y()) / self.zoom)

    def to_view(self, d):
        return QPointF(d.x() * self.zoom + self.pan.x(), d.y() * self.zoom + self.pan.y())

    def pan_by(self, d):
        """Shift the view by `d` view px."""
        self.pan += d
        self.update()

    def set_zoom(self, z, about):
        """Zoom to `z` keeping the document point under view point `about` under it."""
        z = max(ZOOM_MIN, min(ZOOM_MAX, z))
        self.pan = about - (about - self.pan) * (z / self.zoom)
        self.zoom = z
        self.update()

    def frame(self, ids=()):
        """Fit the nodes `ids`, or every node, in the view; fitting never magnifies past 1:1."""
        nodes = [n for n in (self.doc.nodes if self.doc else []) if not ids or n.id in ids]
        if not nodes:
            return
        r = self.box(nodes[0])
        for n in nodes[1:]:
            r = r.united(self.box(n))
        r = r.adjusted(-PIN_R, -PIN_R, PIN_R, PIN_R)
        z = min((self.width() - 2 * FRAME_PAD) / r.width(), (self.height() - 2 * FRAME_PAD) / r.height(), 1.0)
        self.zoom = max(ZOOM_MIN, z)
        self.pan = QPointF(self.width() / 2, self.height() / 2) - r.center() * self.zoom
        self.update()

    # -- geometry, document space ------------------------------------------
    def box(self, node):
        x, y = node.pos
        return QRectF(x, y, NODE_W, NODE_H)

    def flag(self, node):
        b = self.box(node)
        return QRectF(b.right() - PAD - 2 * FLAG_R, b.center().y() - FLAG_R, 2 * FLAG_R, 2 * FLAG_R)

    def pin_in(self, node, name=INPUT):
        b = self.box(node)
        return QPointF(b.center().x(), b.top())

    def pin_out(self, node):
        b = self.box(node)
        return QPointF(b.center().x(), b.bottom())

    def node_at(self, pos):
        s = HIT / self.zoom
        for n in reversed(self.doc.nodes if self.doc else []):
            if self.box(n).adjusted(-s, -s, s, s).contains(pos):
                return n
        return None

    def pin_at(self, pos):
        """(node, input name) for an input connector, (node, None) for an output, else None."""
        r = PIN_R + HIT / self.zoom
        for n in reversed(self.doc.nodes if self.doc else []):
            for name, _ in self.inputs(n):
                if (self.pin_in(n, name) - pos).manhattanLength() <= r:
                    return n, name
            if self.has_output(n) and (self.pin_out(n) - pos).manhattanLength() <= r:
                return n, None
        return None

    @staticmethod
    def wire_path(a, b):
        """An S-curve from output `a` to input `b`: vertical tangents at both ends, whatever the
        offset between them."""
        k = max(WIRE_BEND, abs(b.y() - a.y()) / 2)
        path = QPainterPath(a)
        path.cubicTo(QPointF(a.x(), a.y() + k), QPointF(b.x(), b.y() - k), b)
        return path

    # -- painting ----------------------------------------------------------
    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), qgray(theme.GROUND))
        if self.doc is None:
            p.end()
            return
        p.setRenderHint(QPainter.Antialiasing, True)
        p.translate(self.pan)
        p.scale(self.zoom, self.zoom)
        for w in self.doc.wires:
            src, dst = self.doc.node(w.src), self.doc.node(w.dst)
            ok = dst.unresolved or src.unresolved or fits(self.doc, self.tools, w)
            p.setPen(QPen(theme.ACCENT if ok else theme.RED, WIRE_W))
            p.setBrush(Qt.NoBrush)
            p.drawPath(self.wire_path(self.pin_out(src), self.pin_in(dst, w.input)))
        for n in self.doc.nodes:
            self._paint_node(p, n)
        if self._box is not None:
            p.setPen(self.hairline(qgray(theme.INK_2), Qt.DashLine))
            p.setBrush(qgray(theme.HEAD, 16))
            p.drawRect(self._box)
        p.end()

    def _paint_node(self, p, n):
        box = self.box(n).adjusted(0.5, 0.5, -0.5, -0.5)
        fill = theme.layer(1) + (theme.HOVER_LIFT if n.id == self.hover else 0)
        edge = qgray(theme.HEAD) if n.id in self.selected else qgray(theme.layer(1) + theme.LINE_LIFT)
        if n.id == self.hover and n.id not in self.selected:
            edge = edge.lighter(theme.HOVER_EDGE)
        p.setPen(self.hairline(edge))
        p.setBrush(qgray(fill))
        p.drawRoundedRect(box, theme.RADIUS, theme.RADIUS)
        p.setPen(theme.RED if n.unresolved else qgray(theme.INK))
        text = box.adjusted(PAD, 0, -(3 * PAD + 2 * FLAG_R), 0)
        p.drawText(text, Qt.AlignLeft | Qt.AlignVCenter, f"{n.id} ?" if n.unresolved else n.id)
        if n.id == self.doc.display:
            p.setPen(Qt.NoPen)
            p.setBrush(theme.ACCENT)
        else:
            p.setPen(QPen(qgray(theme.INK_2), 1))
            p.setBrush(Qt.NoBrush)
        p.drawEllipse(self.flag(n))
        unfed = self.unfed(n)
        for name, types in self.inputs(n):
            self._paint_pin(p, self.pin_in(n, name), types, ring=theme.RED if unfed else None)
        if self.has_output(n):
            self._paint_pin(p, self.pin_out(n), self.output_type(n))

    @staticmethod
    def hairline(color, style=Qt.SolidLine):
        """One view px at any zoom: the edges that make a layer, never thickened by zooming."""
        pen = QPen(color, 1, style)
        pen.setCosmetic(True)
        return pen

    @staticmethod
    def _paint_pin(p, c, types, ring=None):
        """A disc in the type's colour; a tuple of types is a pie, one slice each. `ring` is the
        unfed mark, drawn around it."""
        r = QRectF(c.x() - PIN_R, c.y() - PIN_R, 2 * PIN_R, 2 * PIN_R)
        types = (types,) if types is None or isinstance(types, str) else tuple(types)
        p.setPen(Qt.NoPen)
        span = 360 * 16 // len(types)
        for i, t in enumerate(types):
            p.setBrush(type_color(t))
            p.drawPie(r, 90 * 16 - i * span, -span)
        if ring is not None:
            p.setPen(QPen(ring, 1.5))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(r.adjusted(-2, -2, 2, 2))

    # -- gestures ----------------------------------------------------------
    def mousePressEvent(self, e):
        if self.doc is None or self._drag is not None:
            return
        if e.button() == Qt.MiddleButton or (e.button() == Qt.LeftButton and self._space):
            self._drag = ("pan", e.position(), QPointF(self.pan))
            self.setCursor(Qt.ClosedHandCursor)
            return
        if e.button() != Qt.LeftButton:
            return
        pos, shift = self.to_doc(e.position()), bool(e.modifiers() & Qt.ShiftModifier)
        node = self.node_at(pos)
        if node is None:
            if not shift:
                self.select([])
            self._drag = ("box", pos, shift, list(self.selected))
            return
        if self.flag(node).adjusted(-HIT, -HIT, HIT, HIT).contains(pos):
            self.set_flag(node.id)
            return
        if shift:
            self.select([i for i in self.selected if i != node.id] if node.id in self.selected else [*self.selected, node.id])
        elif node.id not in self.selected:
            self.select([node.id])
        if node.id in self.selected:
            self._drag = ("move", pos, {i: self.doc.node(i).pos for i in self.selected})

    def mouseMoveEvent(self, e):
        if self._drag is None:
            node = self.node_at(self.to_doc(e.position())) if self.doc else None
            nid = node.id if node else None
            if nid != self.hover:
                self.hover = nid
                self.update()
            return
        kind, start, *rest = self._drag
        if kind == "pan":
            self.pan = rest[0] + (e.position() - start)
        elif kind == "move":
            d = self.to_doc(e.position()) - start
            for nid, (x, y) in rest[0].items():
                self.doc.node(nid).pos = (x + d.x(), y + d.y())
        else:
            self._box = QRectF(start, self.to_doc(e.position())).normalized()
        self.update()

    def mouseReleaseEvent(self, e):
        if self._drag is None or e.button() not in (Qt.LeftButton, Qt.MiddleButton):
            return
        kind, start, *rest = self._drag
        self._drag = None
        if kind == "pan":
            self._cursor()
        elif kind == "box":
            shift, base = rest
            inside = [n.id for n in self.doc.nodes if self._box is not None and self._box.contains(self.box(n))]
            self._box = None
            self.select([*base, *(i for i in inside if i not in base)] if shift else inside)
            self.update()

    def wheelEvent(self, e):
        notches = e.angleDelta().y() / 120
        if notches:
            self.set_zoom(self.zoom * ZOOM_STEP ** notches, e.position())

    def leaveEvent(self, e):
        if self.hover is not None:
            self.hover = None
            self.update()
        if self._space:
            self._space = False
            self._cursor()
        super().leaveEvent(e)

    def _cursor(self):
        self.setCursor(Qt.OpenHandCursor if self._space else Qt.ArrowCursor)

    def takes_keys(self):
        """A key goes to the canvas when the cursor is over it and nothing is being typed into."""
        return self.isVisible() and self.underMouse() and not isinstance(QApplication.focusWidget(), TYPING)

    def eventFilter(self, obj, e):
        t = e.type()
        if t in (QEvent.ShortcutOverride, QEvent.KeyPress, QEvent.KeyRelease) and self.doc is not None and self.takes_keys():
            if e.key() == Qt.Key_Space:
                if t == QEvent.ShortcutOverride:
                    e.accept()   # the window's Space would toggle play; over the canvas it is a pan modifier
                elif not e.isAutoRepeat():
                    self._space = t == QEvent.KeyPress
                    self._cursor()
                return True
            if e.key() == Qt.Key_H and t == QEvent.KeyPress:
                self.frame(self.selected)
                return True
        return super().eventFilter(obj, e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_selected()
        else:
            super().keyPressEvent(e)

    def event(self, e):
        if e.type() == QEvent.ToolTip and self.doc is not None:
            text = self._tip(self.to_doc(QPointF(e.pos())))
            if text:
                QToolTip.showText(e.globalPos(), text, self)
            else:
                QToolTip.hideText()
            return True
        return super().event(e)

    def _tip(self, pos):
        pin = self.pin_at(pos)
        if pin is not None:
            node, name = pin
            if name is None:
                return f"out: {self.output_type(node) or '?'}"
            types = dict(self.inputs(node))[name]
            said = "any" if types is None else " | ".join(types)
            return f"{name}: {said}" + (" (nothing feeds it)" if self.unfed(node) else "")
        node = self.node_at(pos)
        if node is not None and node.unresolved:
            return f"tool {node.tool!r} not found"
        return ""
