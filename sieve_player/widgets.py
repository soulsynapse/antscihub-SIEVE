"""Optional bases so a tool file stays one screen long: a settings form and its rows."""
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QSlider, QVBoxLayout, QWidget

from .theme import CONTROL_W, GAP, ROW_H, VALUE_W, Form, mono_font, readout


class ChoiceList(QWidget):
    """A param that is one key of a listed set, or empty: clicking a row makes its key the value,
    clicking the value's row again clears it. `show(items, marked, status)` fills the list with
    (key, text, tooltip) rows, marks the row whose key is `marked`, which need not be the value,
    since a selector marks what its rule picked, and sets the status line beneath. The list does
    not refill itself when the value moves; the owner shows it again."""
    changed = Signal()

    def __init__(self, value="", rows=4, parent=None):
        super().__init__(parent)
        self.value = value
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(GAP)
        self.list = QListWidget()
        self.list.setFixedHeight(ROW_H * rows)
        self.list.setSelectionMode(QListWidget.NoSelection)
        self.list.setFocusPolicy(Qt.NoFocus)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.itemClicked.connect(lambda it: self.set_value("" if it.data(Qt.UserRole) == self.value else it.data(Qt.UserRole)))
        self.status = readout()
        lay.addWidget(self.list)
        lay.addWidget(self.status)

    def set_value(self, v):
        if v != self.value:
            self.value = v
            self.changed.emit()

    def show(self, items, marked=None, status=""):
        self.list.clear()
        for key, text, tip in items:
            it = QListWidgetItem(("● " if key == marked else "   ") + text)
            it.setData(Qt.UserRole, key)
            it.setToolTip(tip)
            self.list.addItem(it)
        self.status.setText(status)


class Slider(QSlider):
    """A wheel notch moves one step, in the slider's own units, where Qt would move three."""

    def wheelEvent(self, e):
        d = e.angleDelta().y() or e.angleDelta().x()
        if d:
            self.setValue(self.value() + (1 if d > 0 else -1))
        e.accept()


class ValueField(QLineEdit):
    """A slider's value as a field that reads as a readout until hovered or focused. Escape puts
    back the text `setText` last gave it, whatever was typed since, and leaves the field."""

    def __init__(self, text):
        super().__init__(text)
        self._given = text
        self.setProperty("role", "value")
        self.setFont(mono_font())
        self.setFixedSize(VALUE_W, ROW_H)
        self.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.setTextMargins(-2, 0, -2, 0)   # QLineEdit's own 2 px, so VALUE_W holds what a label's would

    def focusInEvent(self, e):
        super().focusInEvent(e)
        QTimer.singleShot(0, self.selectAll)   # after the press that gave focus has placed its cursor

    def setText(self, text):
        self._given = text
        super().setText(text)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            super().setText(self._given)
            self.clearFocus()
        else:
            super().keyPressEvent(e)


class ParamWidget(QWidget):
    """Has .changed and .params(). `declared` makes one of a tool's declaration, and a card of a
    tool's own adds rows with add_declared, or with add_int / add_float / add_bool / add_text /
    add_choice / add_list; each is one line of the form, a knob: slider and its mono value together
    fill the one control width. The value is a field: a number typed there and committed moves the
    slider, held to the slider's range and step, and anything else is put back. The int and float
    rows return their slider, for a tool that also sets the value from elsewhere, and add_list its
    ChoiceList, which the tool fills. A typed row commits on Enter or focus loss, as a Houdini field
    does, so a half-typed number or pattern is never a change. `set_driven(names, by)` greys the
    rows a wire drives, as Blender does a driven property: they take no typed value until the wire
    is broken."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._get, self._set, self._rows = {}, {}, {}
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(0, 0, 0, 0)
        self._lay.setSpacing(GAP)
        self.form = Form()
        self._lay.addWidget(self.form)

    @classmethod
    def declared(cls, params, parent=None):
        """The plain widget of a tool's declaration, the registry's `params(tool)`: a row for each
        param that says a kind, in its order."""
        w = cls(parent)
        for name, said in params.items():
            w.add_declared(name, said)
        return w

    def add_declared(self, name, said):
        """The row of one declared param, by the kind of its value, and what the add_ of that kind
        returns; None, and no row, for one that says no kind."""
        kind, value = said.get("kind"), said["default"]
        if kind == "int":
            return self.add_int(name, *said["range"], value)
        if kind == "float":
            return self.add_float(name, *said["range"], value, decimals=said.get("decimals", 2))
        if kind == "bool":
            return self.add_bool(name, value)
        if kind == "text":
            return self.add_text(name, value)
        if kind == "choice":
            return self.add_choice(name, said["choices"], value, editable=bool(said.get("unlisted")))

    def params(self):
        return {k: g() for k, g in self._get.items()}

    def set_params(self, params):
        """Move the knobs to `params`; each one that moves emits changed."""
        for k, v in params.items():
            if k in self._set:
                self._set[k](v)

    def set_driven(self, names, by=None):
        """Grey the rows in `names`, which node `by` drives, and free every other."""
        names = set(names)
        for name, row in self._rows.items():
            row.setEnabled(name not in names)
            row.setToolTip(f"driven by {by}; break the wire to edit" if name in names else "")

    def _slider(self, name, lo, hi, value, fmt, parse):
        """`fmt` is a slider position as text and `parse` typed text as a position, raising
        ValueError or OverflowError for text that is no number."""
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(GAP)
        s = Slider(Qt.Horizontal)
        s.setRange(lo, hi)
        s.setValue(value)
        s.setFixedWidth(CONTROL_W - VALUE_W - GAP)
        out = ValueField(fmt(value))
        s.valueChanged.connect(lambda v: (out.setText(fmt(v)), self.changed.emit()))

        def commit():
            try:
                s.setValue(max(s.minimum(), min(s.maximum(), parse(out.text()))))
            except (ValueError, OverflowError):
                pass
            out.setText(fmt(s.value()))
        out.editingFinished.connect(commit)
        h.addWidget(s)
        h.addWidget(out)
        w.setFixedWidth(CONTROL_W)
        self.form.add_row(name, w)
        self._rows[name] = w
        return s

    def add_int(self, name, lo, hi, value):
        s = self._slider(name, lo, hi, int(value), str, lambda t: round(float(t)))
        self._get[name], self._set[name] = s.value, lambda v: s.setValue(int(v))
        return s

    def add_float(self, name, lo, hi, value, decimals=2):
        k = 10 ** decimals
        s = self._slider(name, round(lo * k), round(hi * k), round(value * k), lambda v: f"{v / k:.{decimals}f}",
                         lambda t: round(float(t) * k))
        self._get[name], self._set[name] = lambda: s.value() / k, lambda v: s.setValue(round(v * k))
        return s

    def add_bool(self, name, value):
        c = QCheckBox()
        c.setChecked(bool(value))
        c.toggled.connect(lambda _: self.changed.emit())
        self.form.add_row(name, c)
        self._rows[name] = c
        self._get[name], self._set[name] = c.isChecked, lambda v: c.setChecked(bool(v))

    def add_text(self, name, value):
        e = QLineEdit(str(value))
        e.setFont(mono_font())
        e.setFixedWidth(CONTROL_W)
        last = [e.text()]

        def commit():
            if e.text() != last[0]:
                last[0] = e.text()
                self.changed.emit()
        e.editingFinished.connect(commit)
        self.form.add_row(name, e)
        self._rows[name] = e

        def set_(v):
            e.setText(str(v))
            commit()
        self._get[name], self._set[name] = e.text, set_
        return e

    def add_choice(self, name, options, value, editable=False):
        """`editable` lets a value outside `options` be typed, for a choice among names the tool
        cannot list, such as the columns a table carries."""
        c = QComboBox()
        c.addItems([str(o) for o in options])
        c.setEditable(editable)
        if editable:
            c.setInsertPolicy(QComboBox.NoInsert)
            c.lineEdit().setFont(mono_font())
        c.setCurrentText(str(value))
        c.setFixedWidth(CONTROL_W)
        c.currentTextChanged.connect(lambda _: self.changed.emit())
        self.form.add_row(name, c)
        self._rows[name] = c
        self._get[name], self._set[name] = c.currentText, lambda v: c.setCurrentText(str(v))
        return c

    def add_list(self, name, value="", rows=4):
        c = ChoiceList(str(value), rows)
        c.changed.connect(self.changed.emit)
        self.form.add_line(c)
        self._rows[name] = c
        self._get[name], self._set[name] = lambda: c.value, lambda v: c.set_value(str(v))
        return c
