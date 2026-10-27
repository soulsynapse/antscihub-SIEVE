"""The network editor. `spec/canvas.md` is the spec: a node one layer above the ground with its
connectors and its display flag, select, box-select, drag, Delete, the mark on a node whose tool was
not found and on an input nothing feeds; pan, zoom about the cursor, H to frame; wires dragged from
either end, picked up, cut with Y, and a node dropped onto a wire inserted in it; Tab or a
right-click on empty canvas for the menu that places a tool, which a wire grown into empty canvas
also opens, filtered to what the wire may feed or be fed by; a column of buttons at the top right,
one per key that is an action, for the mouse hand. It reads and writes the document and nothing
else. The tools' declared types reach it as data, for the connectors' colours, the unfed
mark, which connectors a dragged wire may land on and which tools the menu offers it; what the
runtime makes of the graph never does. A tool the registry listed but could not import reaches it
as its name and the error, for the menu to show greyed.

Geometry is in document space; the view is a pan and a zoom applied to the painter, never written
to the document. A key pressed with the cursor over the canvas is the canvas's, as in Houdini's
panes, unless something is being typed into: Space held pans with the left button instead of
toggling play, Y held cuts with it, H frames.

A type nobody declared matches every type: an unresolved node and an unfed pass-through can be
wired like any other, and the red wire says afterwards whether the types fit. Only a node's own
connectors are refused; a longer cycle is the document's to report and the runtime's to starve.
"""
import zlib

from PySide6.QtCore import QCoreApplication, QEvent, QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QAbstractSpinBox, QApplication, QLineEdit, QListWidget, QListWidgetItem,
                               QPlainTextEdit, QSizePolicy, QTextEdit, QToolTip, QWidget)

from . import theme
from .document import INPUT, PATH, VIDEO_PRODUCES, VIDEO_TOOL, expects, fed, fits, is_selector, produces
from .theme import GAP, PAD, qgray

NODE_W, NODE_H = 140, 28   # a node's box, canvas px
FLAG_R = 5                 # the display flag: a disc at the node's right end
PIN_R = 4                  # a connector: a disc on the node's top or bottom edge
HIT = 3                    # slack around a flag or a connector, px
WIRE_W = 1.5
WIRE_BEND = 24             # the least a wire runs vertically out of a connector before it turns
SNAP = 10                  # a dragged wire's loose end lands on a connector within this, view px
LIT = 2                    # the halo on a connector a dragged wire may land on, px beyond the disc
DIM = 70                   # alpha of a connector it may not
ZOOM_MIN, ZOOM_MAX = 0.25, 4.0
ZOOM_STEP = 1.15           # per wheel notch
FRAME_PAD = 2 * PAD        # view px kept clear around what H frames
MENU_W = 200               # the Tab menu's width, view px
MENU_ROWS = 10             # the most tools the Tab menu shows before it scrolls
BUTTON = theme.ROW_H       # a button in the column: a square this wide, its glyph centred
# the column, top to bottom: (glyph, tooltip, the key it stands in for). The key is the gesture and
# the button the same action for the mouse hand, so there is one per key that is an action and
# none for Space or Y, which are held
BUTTONS = (("focus-centered", "frame (H)", Qt.Key_H),
           ("plus", "add tool (Tab)", Qt.Key_Tab),
           ("trash", "delete selected (Delete)", Qt.Key_Delete))
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


class TabMenu(theme.Layer):
    """Houdini's Tab menu: a filter line over the tools, at the cursor. `entries` is [(name, error)],
    error "" for a tool that imported; one that did not is greyed, says its error on hover and
    cannot be chosen. `chosen` carries the name; `closed` follows every way out."""
    chosen = Signal(str)
    closed = Signal()

    def __init__(self, entries, parent):
        super().__init__(2, "", parent)
        self.entries = entries
        self.setFixedWidth(MENU_W)
        self.setStyleSheet(f"""
            QListWidget {{ background: transparent; border: none; outline: none; }}
            QListWidget::item {{ padding: 2px 6px; border-radius: {theme.RADIUS}px; }}
            QListWidget::item:selected {{ background: {theme.gray(theme.layer(3))}; }}
            """)
        self.edit = QLineEdit()
        self.edit.setPlaceholderText("tool")
        self.edit.setFixedHeight(theme.ROW_H)
        self.edit.installEventFilter(self)
        self.list = QListWidget()
        self.list.setFocusPolicy(Qt.NoFocus)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setMouseTracking(True)
        self.body.setSpacing(GAP // 2)
        self.add(self.edit)
        self.add(self.list)
        self.edit.textChanged.connect(self.refill)
        self.list.itemClicked.connect(self._pick)
        self.list.itemEntered.connect(self._hover)
        self.refill("")

    def refill(self, text):
        text = text.strip().lower()
        self.list.clear()
        for name, err in self.entries:
            if text not in name.lower():
                continue
            item = QListWidgetItem(name)
            if err:
                item.setFlags(Qt.NoItemFlags)
                item.setForeground(qgray(theme.INK_2 - 50))
                item.setToolTip(err)
            self.list.addItem(item)
        for i in range(self.list.count()):
            if self.list.item(i).flags() & Qt.ItemIsEnabled:
                self.list.setCurrentRow(i)
                break
        rows = max(1, min(MENU_ROWS, self.list.count()))
        self.list.setFixedHeight(rows * self.list.sizeHintForRow(0) + 2 if self.list.count() else theme.ROW_H)
        self.adjustSize()

    def _step(self, d):
        rows = [i for i in range(self.list.count()) if self.list.item(i).flags() & Qt.ItemIsEnabled]
        if not rows:
            return
        cur = self.list.currentRow()
        at = rows.index(cur) if cur in rows else -1
        self.list.setCurrentRow(rows[max(0, min(len(rows) - 1, at + d))])

    def _hover(self, item):
        """The pointer moves the highlight, so Enter and a click agree on what is chosen."""
        if item.flags() & Qt.ItemIsEnabled:
            self.list.setCurrentItem(item)

    def _pick(self, item):
        if item is not None and item.flags() & Qt.ItemIsEnabled:
            self.chosen.emit(item.text())
            self.closed.emit()

    def eventFilter(self, obj, e):
        if obj is self.edit and e.type() == QEvent.KeyPress:
            k = e.key()
            if k == Qt.Key_Escape:
                self.closed.emit()
            elif k in (Qt.Key_Return, Qt.Key_Enter):
                self._pick(self.list.currentItem())
            elif k in (Qt.Key_Up, Qt.Key_Down):
                self._step(-1 if k == Qt.Key_Up else 1)
            elif k in (Qt.Key_Tab, Qt.Key_Backtab):
                pass   # the key that opened it does nothing inside it
            else:
                return False
            return True
        return super().eventFilter(obj, e)


class Canvas(QWidget):
    """`tools` is the catalogue, name to module; the document's node names index it. `broken` is
    name to error for every tool the registry listed but could not import."""
    selectionChanged = Signal(list)   # the selected node ids, in selection order
    changed = Signal()                # the document's nodes, wires or flag changed here

    def __init__(self, tools, broken=None, parent=None):
        super().__init__(parent)
        self.tools = tools
        self.broken = dict(broken or {})
        self.doc = None
        self.errors = {}                        # node id -> the one line wrong with it, set by the window
        self.selected = []
        self.hover = None                       # the node id under the pointer
        self._drag = None                       # ("move", start, {id: pos}) | ("box", start, shift, base)
                                                # | ("pan", start, pan) | ("wire", end, id, input) | ("cut", start)
                                                # | None; starts in document space but pan's. A wire drag holds
                                                # its fixed end: "out" of node `id`, or "in" `input` of node `id`
        self._box = None                        # the rubber band, while one is drawn, document space
        self._loose = None                      # the dragged wire's free end, document space
        self._wires0 = None                     # the document's wires when a wire drag began
        self._cut = None                        # the cut line, while one is drawn, document space
        self._insert = None                     # the wire the single node being moved would drop into
        self._pending = None                    # (end, id, input) of a wire grown into space, while the menu
                                                # it opened is up; the loose end stays drawn at the menu
        self._menu = None                       # the Tab menu, while one is open
        self._hot = None                        # the index of the button under the pointer
        self._y = False                         # Y is held with the cursor here
        self.pan = QPointF(2 * PAD, 2 * PAD)    # where the document's (0, 0) sits, view px
        self.zoom = 1.0
        self._space = False                     # Space is held with the cursor here
        self.setMinimumSize(160, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.ClickFocus)

    # the key filter is application-wide, so it is installed only while the canvas is on screen;
    # a second window's canvas, or one being torn down, must not keep filtering every event
    def showEvent(self, e):
        QCoreApplication.instance().installEventFilter(self)
        super().showEvent(e)

    def hideEvent(self, e):
        QCoreApplication.instance().removeEventFilter(self)
        super().hideEvent(e)

    def set_document(self, doc):
        self.close_menu()
        self.doc = doc
        self.hover = self._drag = self._box = self._loose = self._cut = self._insert = None
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
        """(name, expected types or None) per input: PATH on the video node, none on a selector, one
        on every other."""
        if node.tool == VIDEO_TOOL:
            return [(INPUT, (PATH,))]
        if not node.unresolved and is_selector(self.tools.get(node.tool)):
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
        """The mark: a resolved node the video does not reach through wires whose types fit. The
        video node's input is optional and a selector has none, so neither is ever marked."""
        return bool(self.inputs(node)) and not node.unresolved and node.tool != VIDEO_TOOL \
            and not fed(self.doc, node.id, self.tools)

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
        """Fit the nodes `ids`, or every node, in the view, centred across and FRAME_PAD down from
        the view's top, since nodes flow top to bottom; fitting never magnifies past 1:1."""
        nodes = [n for n in (self.doc.nodes if self.doc else []) if not ids or n.id in ids]
        if not nodes:
            return
        r = self.box(nodes[0])
        for n in nodes[1:]:
            r = r.united(self.box(n))
        r = r.adjusted(-PIN_R, -PIN_R, PIN_R, PIN_R)
        z = min((self.width() - 2 * FRAME_PAD) / r.width(), (self.height() - 2 * FRAME_PAD) / r.height(), 1.0)
        self.zoom = max(ZOOM_MIN, z)
        self.pan = QPointF(self.width() / 2 - r.center().x() * self.zoom, FRAME_PAD - r.top() * self.zoom)
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

    def pin_at(self, pos, slack=HIT):
        """(node, input name) for an input connector, (node, None) for an output, else None; `slack`
        is view px around the disc."""
        r = PIN_R + slack / self.zoom
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

    def path_of(self, w):
        return self.wire_path(self.pin_out(self.doc.node(w.src)), self.pin_in(self.doc.node(w.dst), w.input))

    @staticmethod
    def segments(path):
        for poly in path.toSubpathPolygons():
            for i in range(1, len(poly)):
                yield QLineF(poly[i - 1], poly[i])

    @classmethod
    def crosses(cls, path, line):
        return any(s.intersects(line)[0] == QLineF.BoundedIntersection for s in cls.segments(path))

    @classmethod
    def touches(cls, path, rect):
        edges = (QLineF(rect.topLeft(), rect.topRight()), QLineF(rect.topRight(), rect.bottomRight()),
                 QLineF(rect.bottomRight(), rect.bottomLeft()), QLineF(rect.bottomLeft(), rect.topLeft()))
        return any(rect.contains(s.p1()) or any(s.intersects(e)[0] == QLineF.BoundedIntersection for e in edges)
                   for s in cls.segments(path))

    # -- wiring ------------------------------------------------------------
    @staticmethod
    def compatible(got, want):
        """Whether an output handing out `got` may feed an input expecting `want`; a type nobody
        declared matches every type."""
        return got is None or want is None or got in want

    def targets(self):
        """The connectors the dragged wire may land on: (node, input) for inputs, (node, None) for
        outputs; empty when no wire is being dragged."""
        if self._drag is None or self._drag[0] != "wire":
            return []
        _, end, nid, name = self._drag
        node, out = self.doc.node(nid), []
        if end == "out":
            got = self.output_type(node)
            for n in self.doc.nodes:
                if n.id != nid:
                    out += [(n, iname) for iname, want in self.inputs(n) if self.compatible(got, want)]
        else:
            want = dict(self.inputs(node))[name]
            out = [(n, None) for n in self.doc.nodes
                   if n.id != nid and self.has_output(n) and self.compatible(self.output_type(n), want)]
        return out

    def insertable(self, node):
        """The wire `node` would drop into: one its box crosses that it is not an end of, whose
        source fits its input and whose output, once so fed, fits the wire's destination."""
        ins = self.inputs(node)
        if not ins or not self.has_output(node):
            return None
        want, box = ins[0][1], self.box(node)
        passthru = getattr(self.tools.get(node.tool), "PRODUCES", None) == "same"
        for w in self.doc.wires:
            if node.id in (w.src, w.dst) or not self.touches(self.path_of(w), box):
                continue
            got = self.output_type(self.doc.node(w.src))
            down = dict(self.inputs(self.doc.node(w.dst)))[w.input]
            if self.compatible(got, want) and self.compatible(got if passthru else self.output_type(node), down):
                return w
        return None

    def _begin_wire(self, node, name, pos):
        """A drag from a connector: from an output, or from an unfed input, the wire grows from
        there; from a fed input, that wire is picked up and stays on its source."""
        self._wires0 = list(self.doc.wires)
        if name is None:
            self._drag = ("wire", "out", node.id, None)
        elif (w := self.doc.source(node.id, name)) is None:
            self._drag = ("wire", "in", node.id, name)
        else:
            self.doc.disconnect(node.id, name)
            self._drag = ("wire", "out", w.src, None)
        self._loose = pos

    def _end_wire(self, pos):
        _, end, nid, name = self._drag
        pin = self.pin_at(pos, SNAP)
        if pin is not None and any(n.id == pin[0].id and iname == pin[1] for n, iname in self.targets()):
            if end == "out":
                self.doc.connect(nid, pin[0].id, pin[1])
            else:
                self.doc.connect(pin[0].id, nid, name)
        elif self.doc.wires == self._wires0 and self.node_at(pos) is None:
            # grown, not picked up, and let go in space: the menu offers what it may join to
            self._pending, self._wires0 = (end, nid, name), None
            self.open_menu(self.to_view(pos))
            return
        changed = self.doc.wires != self._wires0
        self._loose = self._wires0 = None
        self.update()
        if changed:
            self.changed.emit()

    def _end_cut(self):
        line, self._cut = self._cut, None
        keep = [w for w in self.doc.wires if not self.crosses(self.path_of(w), line)]
        cut = len(keep) != len(self.doc.wires)
        self.doc.wires = keep
        self.update()
        if cut:
            self.changed.emit()

    def _end_move(self):
        w, self._insert = self._insert, None
        if w is not None:
            nid = self.selected[0]
            self.doc.connect(w.src, nid)
            self.doc.connect(nid, w.dst, w.input)
            self.changed.emit()
        self.update()

    # -- the Tab menu --------------------------------------------------------
    def menu_entries(self):
        """[(name, error)] the menu offers, by name: the video node and every tool, or with a wire
        pending, those its loose end may join; a tool that did not import is offered greyed either
        way, since what it expects is unknown, and the video node is greyed while the document
        has one, since a document names one video."""
        out = []
        for name in sorted(set(self.tools) | set(self.broken) | {VIDEO_TOOL}):
            if name == VIDEO_TOOL:
                if self.doc.video_node() is not None:
                    out.append((name, "the document has a video node"))
                elif self._pending is None or self._joins(name):
                    out.append((name, ""))
            elif name not in self.tools:
                out.append((name, self.broken[name]))
            elif self._pending is None or self._joins(name):
                out.append((name, ""))
        return out

    def _joins(self, name):
        """Whether a fresh node of tool `name` may take the pending wire."""
        end, nid, iname = self._pending
        node = self.doc.node(nid)
        if name == VIDEO_TOOL:
            if end == "out":
                return self.compatible(self.output_type(node), (PATH,))
            return self.compatible(VIDEO_PRODUCES, dict(self.inputs(node))[iname])
        tool = self.tools[name]
        if end == "out":
            return self.compatible(self.output_type(node), expects(tool))
        p = getattr(tool, "PRODUCES", None)
        return p is not None and self.compatible(None if p == "same" else p, dict(self.inputs(node))[iname])

    def open_menu(self, at, place_at=None):
        """The Tab menu at view point `at`, kept inside the canvas; the chosen tool lands at view
        point `place_at`, by default `at` itself."""
        if self._menu is not None:
            self.close_menu()
        where = self.to_doc(at if place_at is None else place_at)
        self._menu = TabMenu(self.menu_entries(), self)
        self._menu.chosen.connect(lambda name: self.place(name, where))
        self._menu.closed.connect(self.close_menu)
        self._menu.adjustSize()
        x = max(0, min(self.width() - self._menu.width(), int(at.x())))
        y = max(0, min(self.height() - self._menu.height(), int(at.y())))
        self._menu.move(x, y)
        self._menu.show()
        self._menu.edit.setFocus()
        self.update()

    def close_menu(self):
        """Closes the menu if one is open; a wire pending on it is let go."""
        if self._menu is not None:
            menu, self._menu = self._menu, None
            menu.hide()
            menu.setParent(None)
            menu.deleteLater()
            self.setFocus()
        self._pending = self._loose = None
        self.update()

    def place(self, name, pos):
        """A new node of tool `name` centred on document point `pos`; with a wire pending, the node
        sits so the connector the wire reaches is at `pos`, and the wire is made."""
        tool = self.tools.get(name)      # None for the video node
        pending, self._pending = self._pending, None
        x, y = pos.x() - NODE_W / 2, pos.y() - NODE_H / 2
        if pending is not None:
            y = pos.y() if pending[0] == "out" else pos.y() - NODE_H
        node = self.doc.add_node(name, (x, y), getattr(tool, "DEFAULTS", {}))
        if pending is not None:
            end, nid, iname = pending
            if end == "out":
                self.doc.connect(nid, node.id)
            else:
                self.doc.connect(node.id, nid, iname)
        self.changed.emit()
        self.select([node.id])
        return node

    # -- the buttons, view space -------------------------------------------
    def button_rect(self, i):
        """The i-th button's square, view px: the column sits PAD in from the top right corner."""
        return QRectF(self.width() - PAD - BUTTON, PAD + i * (BUTTON + GAP // 2), BUTTON, BUTTON)

    def button_at(self, v):
        for i in range(len(BUTTONS)):
            if self.button_rect(i).contains(v):
                return i
        return None

    def button_enabled(self, i):
        """Delete has nothing to do without a selection; frame, nothing without nodes."""
        key = BUTTONS[i][2]
        if key == Qt.Key_Delete:
            return bool(self.selected)
        if key == Qt.Key_H:
            return bool(self.doc.nodes)
        return True

    def press_button(self, i):
        """What the button's key does. The menu opens beside its button and places at the view's
        centre, since the cursor, which the key places at, is on the button."""
        if not self.button_enabled(i):
            return
        key = BUTTONS[i][2]
        if key == Qt.Key_H:
            self.frame(self.selected)
        elif key == Qt.Key_Tab:
            r = self.button_rect(i)
            self.open_menu(QPointF(r.left() - MENU_W - GAP // 2, r.top()),
                           place_at=QPointF(self.width() / 2, self.height() / 2))
        elif key == Qt.Key_Delete:
            self.delete_selected()

    def _paint_buttons(self, p):
        ratio = self.devicePixelRatioF()
        for i, (name, _, _) in enumerate(BUTTONS):
            r = self.button_rect(i)
            on = self.button_enabled(i)
            if i == self._hot and on:
                p.setPen(self.hairline(qgray(theme.layer(1) + theme.LINE_LIFT).lighter(theme.HOVER_EDGE)))
                p.setBrush(qgray(theme.layer(1) + theme.HOVER_LIFT))
                p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), theme.RADIUS, theme.RADIUS)
            pm = theme.glyph(name, theme.INK if on else theme.INK_2 - 50, theme.GLYPH, ratio)
            p.drawPixmap(r.center() - QPointF(theme.GLYPH / 2, theme.GLYPH / 2), pm)

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
        p.setBrush(Qt.NoBrush)
        for w in self.doc.wires:
            src, dst = self.doc.node(w.src), self.doc.node(w.dst)
            ok = dst.unresolved or src.unresolved or fits(self.doc, self.tools, w)
            if w is self._insert:
                p.setPen(QPen(qgray(theme.HEAD), WIRE_W + 1))
            else:
                p.setPen(QPen(theme.ACCENT if ok else theme.RED, WIRE_W))
            p.drawPath(self.path_of(w))
        if self._loose is not None:
            end, nid, name = self._pending or self._drag[1:]
            node = self.doc.node(nid)
            p.setPen(QPen(theme.ACCENT, WIRE_W))
            p.drawPath(self.wire_path(self.pin_out(node), self._loose) if end == "out"
                       else self.wire_path(self._loose, self.pin_in(node, name)))
        lit = {(n.id, name) for n, name in self.targets()} if self._drag and self._drag[0] == "wire" else None
        for n in self.doc.nodes:
            self._paint_node(p, n, lit)
        if self._box is not None:
            p.setPen(self.hairline(qgray(theme.INK_2), Qt.DashLine))
            p.setBrush(qgray(theme.HEAD, 16))
            p.drawRect(self._box)
        if self._cut is not None:
            p.setPen(self.hairline(theme.RED, Qt.DashLine))
            p.drawLine(self._cut)
        p.resetTransform()
        self._paint_buttons(p)
        p.end()

    def _paint_node(self, p, n, lit=None):
        """`lit`, while a wire is dragged, is the set of (node id, input name or None) it may land
        on; every other connector is dimmed."""
        box = self.box(n).adjusted(0.5, 0.5, -0.5, -0.5)
        fill = theme.layer(1) + (theme.HOVER_LIFT if n.id == self.hover else 0)
        edge = qgray(theme.HEAD) if n.id in self.selected else qgray(theme.layer(1) + theme.LINE_LIFT)
        if n.id == self.hover and n.id not in self.selected:
            edge = edge.lighter(theme.HOVER_EDGE)
        p.setPen(self.hairline(edge))
        p.setBrush(qgray(fill))
        p.drawRoundedRect(box, theme.RADIUS, theme.RADIUS)
        p.setPen(theme.RED if n.unresolved or n.id in self.errors else qgray(theme.INK))
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
            self._paint_pin(p, self.pin_in(n, name), types, ring=theme.RED if unfed else None,
                            lit=None if lit is None else (n.id, name) in lit)
        if self.has_output(n):
            self._paint_pin(p, self.pin_out(n), self.output_type(n), lit=None if lit is None else (n.id, None) in lit)

    @staticmethod
    def hairline(color, style=Qt.SolidLine):
        """One view px at any zoom: the edges that make a layer, never thickened by zooming."""
        pen = QPen(color, 1, style)
        pen.setCosmetic(True)
        return pen

    @staticmethod
    def _paint_pin(p, c, types, ring=None, lit=None):
        """A disc in the type's colour; a tuple of types is a pie, one slice each. `ring` is the
        unfed mark, drawn around it. `lit` True adds the halo a dragged wire may land on; False
        dims the disc; None is rest."""
        r = QRectF(c.x() - PIN_R, c.y() - PIN_R, 2 * PIN_R, 2 * PIN_R)
        types = (types,) if types is None or isinstance(types, str) else tuple(types)
        p.setPen(Qt.NoPen)
        span = 360 * 16 // len(types)
        for i, t in enumerate(types):
            color = type_color(t)
            if lit is False:
                color.setAlpha(DIM)
            p.setBrush(color)
            p.drawPie(r, 90 * 16 - i * span, -span)
        p.setBrush(Qt.NoBrush)
        if lit:
            p.setPen(QPen(qgray(theme.HEAD), 1.5))
            p.drawEllipse(r.adjusted(-LIT, -LIT, LIT, LIT))
        elif ring is not None:
            p.setPen(QPen(ring, 1.5))
            p.drawEllipse(r.adjusted(-2, -2, 2, 2))

    # -- gestures ----------------------------------------------------------
    def mousePressEvent(self, e):
        if self.doc is None or self._drag is not None:
            return
        if self._menu is not None:
            self.close_menu()   # a click anywhere else is the way out, and does nothing more
            return
        hot = self.button_at(e.position())
        if hot is not None:
            if e.button() == Qt.LeftButton:
                self.press_button(hot)
            return              # the column covers the canvas: no gesture starts under it
        if e.button() == Qt.MiddleButton or (e.button() == Qt.LeftButton and self._space):
            self._drag = ("pan", e.position(), QPointF(self.pan))
            self.setCursor(Qt.ClosedHandCursor)
            return
        pos, shift = self.to_doc(e.position()), bool(e.modifiers() & Qt.ShiftModifier)
        if e.button() == Qt.RightButton:
            if not self._y and self.pin_at(pos) is None and self.node_at(pos) is None:
                self.open_menu(e.position())     # the Tab menu, for the mouse hand
            return
        if e.button() != Qt.LeftButton:
            return
        if self._y:
            self._drag, self._cut = ("cut", pos), QLineF(pos, pos)
            return
        pin = self.pin_at(pos)
        if pin is not None:
            self._begin_wire(*pin, pos)
            self.update()
            return
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
            hot = self.button_at(e.position()) if self.doc else None
            node = self.node_at(self.to_doc(e.position())) if self.doc and hot is None else None
            nid = node.id if node else None
            if (nid, hot) != (self.hover, self._hot):
                self.hover, self._hot = nid, hot
                self.update()
            return
        kind, start, *rest = self._drag
        if kind == "pan":
            self.pan = rest[0] + (e.position() - start)
        elif kind == "move":
            d = self.to_doc(e.position()) - start
            for nid, (x, y) in rest[0].items():
                self.doc.node(nid).pos = (x + d.x(), y + d.y())
            self._insert = self.insertable(self.doc.node(self.selected[0])) if len(self.selected) == 1 else None
        elif kind == "wire":
            self._loose = self.to_doc(e.position())
        elif kind == "cut":
            self._cut.setP2(self.to_doc(e.position()))
        else:
            self._box = QRectF(start, self.to_doc(e.position())).normalized()
        self.update()

    def mouseReleaseEvent(self, e):
        if self._drag is None or e.button() not in (Qt.LeftButton, Qt.MiddleButton):
            return
        kind, start, *rest = self._drag
        if kind == "wire":
            self._end_wire(self.to_doc(e.position()))
        self._drag = None
        if kind == "pan":
            self._cursor()
        elif kind == "cut":
            self._end_cut()
        elif kind == "move":
            self._end_move()
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
        if self.hover is not None or self._hot is not None:
            self.hover = self._hot = None
            self.update()
        if self._space or self._y:
            self._space = self._y = False
            self._cursor()
        super().leaveEvent(e)

    def _cursor(self):
        self.setCursor(Qt.OpenHandCursor if self._space else Qt.CrossCursor if self._y else Qt.ArrowCursor)

    def takes_keys(self):
        """A key goes to the canvas when the cursor is over it and nothing is being typed into."""
        return self.isVisible() and self.underMouse() and not isinstance(QApplication.focusWidget(), TYPING)

    def eventFilter(self, obj, e):
        t = e.type()
        if t in (QEvent.ShortcutOverride, QEvent.KeyPress, QEvent.KeyRelease) and self.doc is not None and self.takes_keys():
            if e.key() in (Qt.Key_Space, Qt.Key_Y):
                if t == QEvent.ShortcutOverride:
                    e.accept()   # the window's Space would toggle play; over the canvas it is a pan modifier
                elif not e.isAutoRepeat():
                    held = t == QEvent.KeyPress
                    if e.key() == Qt.Key_Space:
                        self._space = held
                    else:
                        self._y = held
                    self._cursor()
                return True
            if e.key() == Qt.Key_H and t == QEvent.KeyPress:
                self.frame(self.selected)
                return True
            if e.key() == Qt.Key_Tab and t == QEvent.KeyPress and self._menu is None:
                self.open_menu(QPointF(self.mapFromGlobal(QCursor.pos())))
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
        i = self.button_at(self.to_view(pos))
        if i is not None:
            return BUTTONS[i][1]
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
        if node is not None and node.id in self.errors:
            return self.errors[node.id]
        return ""
