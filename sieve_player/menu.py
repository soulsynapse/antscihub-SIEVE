"""The Tab menu: a widget the canvas opens at the cursor and reads a name back from. It knows no
document and no tool: the canvas hands it the entries it may offer, name to (category, description,
signature) for each, and the order the groups read; it draws them, filters them as text is typed,
and emits the one chosen. A second presentation is a second class here, swapped in the canvas.
"""
from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QWidget

from . import theme
from .theme import GAP, PAD

MENU_W = 560                    # the menu's width, view px: a name column, a description, a signature
ROW_W = MENU_W - 2 * PAD - 24   # a row's face: the list's width less its scrollbar, so the columns span it
MENU_ROWS = 14                  # the most rows, group heads counted, shown before the list scrolls
UNLOADED = "not loaded"         # the last group: tools the registry listed but could not import


def out_of(sig):
    """The right side of a signature, "→ blobs" of "gray, mask → blobs"; "" for none."""
    return f"→ {sig.split('→')[-1].strip()}" if "→" in sig else ""


class _Head(QLabel):
    """A group's rule: its category in small letter-spaced capitals, tertiary ink."""

    def __init__(self, cat):
        super().__init__(cat.upper())
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setStyleSheet(f"color: {theme.gray(theme.INK_2)}; font-size: 10px; letter-spacing: 1px; padding: 6px 0 0 6px;")


class _Row(QWidget):
    """An entry's face, three columns aligned down the list: the name in a column `col` wide, the
    description's leading clause elided to the room left, and what the tool hands out, the
    signature's right side, right-aligned in a column `sig_col` wide; the hover carries the rest.
    Mouse events pass through to the list, which owns hover and the click."""

    def __init__(self, name, desc, sig, greyed, col, sig_col):
        super().__init__()
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 0, 6, 0)
        lay.setSpacing(GAP)
        self.name, self.desc, self.sig = QLabel(name), QLabel(), QLabel(out_of(sig))
        self.name.setFixedWidth(col)
        self.sig.setFixedWidth(sig_col)
        self.sig.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.name.setStyleSheet(f"color: {theme.gray(theme.INK_2 - 50 if greyed else theme.HEAD)}")
        self.desc.setStyleSheet(f"color: {theme.gray(theme.INK)}")
        self.sig.setStyleSheet(f"color: {theme.gray(theme.INK_2)}")
        room = ROW_W - 12 - 2 * GAP - col - sig_col
        self.desc.setFixedWidth(room)
        self.desc.setText(QFontMetrics(self.desc.font()).elidedText(desc.split(";")[0], Qt.ElideRight, room))
        lay.addWidget(self.name)
        lay.addWidget(self.desc)
        lay.addWidget(self.sig)
        lay.addStretch(1)


class TabMenu(theme.Layer):
    """Houdini's Tab menu grouped as Blender's Shift+A is: a filter line over the tools, each entry
    under its category with its description beside it, the typed text matching group, name and
    description alike and a group it empties gone. `entries` is [(name, error)], error "" for a tool
    that imported; one that did not is greyed, says its error on hover and cannot be chosen. `info`
    is name -> (category, description, signature) for every name an entry may carry, and `order`
    the categories as the groups read, any other after them. `chosen` carries the name; `closed`
    follows every way out."""
    chosen = Signal(str)
    closed = Signal()

    def __init__(self, entries, info, order, parent):
        super().__init__(2, "", parent)
        self.entries, self.info, self.order = entries, info, tuple(order)
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
        groups = {}
        for name, err in self.entries:
            cat, desc, sig = self.info.get(name, ("", "", ""))
            if any(text in s.lower() for s in (cat, name, desc)):
                groups.setdefault(cat, []).append((name, err, desc, sig))
        rank = lambda c: self.order.index(c) if c in self.order else len(self.order)  # noqa: E731
        metrics = QFontMetrics(self.font())
        shown = [row for cat in groups for row in groups[cat]]
        col = max((metrics.horizontalAdvance(name) for name, *_ in shown), default=0)
        sig_col = max((metrics.horizontalAdvance(out_of(sig)) for *_, sig in shown), default=0)
        for cat in sorted(groups, key=rank):
            head = QListWidgetItem()
            head.setFlags(Qt.NoItemFlags)
            head.setData(Qt.UserRole + 1, cat)
            head.setSizeHint(QSize(ROW_W, theme.ROW_H + 4))
            self.list.addItem(head)
            self.list.setItemWidget(head, _Head(cat))
            for name, err, desc, sig in groups[cat]:
                item = QListWidgetItem()       # no text of its own: the row's face draws the name, the data carries it
                item.setData(Qt.UserRole, name)
                item.setSizeHint(QSize(ROW_W, theme.ROW_H))
                item.setToolTip(err or f"{desc}\n{sig}".strip())
                if err:
                    item.setFlags(Qt.NoItemFlags)
                self.list.addItem(item)
                self.list.setItemWidget(item, _Row(name, desc, sig, bool(err), col, sig_col))
        for i in range(self.list.count()):
            if self.list.item(i).flags() & Qt.ItemIsEnabled:
                self.list.setCurrentRow(i)
                break
        shown_rows = range(min(MENU_ROWS, self.list.count()))
        self.list.setFixedHeight(sum(self.list.sizeHintForRow(i) for i in shown_rows) + 2 if shown_rows else theme.ROW_H)
        self.adjustSize()

    def shown(self):
        """[(category, [name, ...])] as the list stands, group heads read as the categories."""
        out = []
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.data(Qt.UserRole) is None:
                out.append((item.data(Qt.UserRole + 1), []))
            else:
                out[-1][1].append(item.data(Qt.UserRole))
        return out

    def description(self, name):
        return self.info.get(name, ("", "", ""))[1]

    def item_of(self, name):
        """The list item carrying `name`, or None while the filter hides it."""
        return next((self.list.item(i) for i in range(self.list.count()) if self.list.item(i).data(Qt.UserRole) == name), None)

    def wheelEvent(self, e):
        e.accept()   # a wheel the list has scrolled to the end of stops here and never zooms the canvas under it

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
            self.chosen.emit(item.data(Qt.UserRole))
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
