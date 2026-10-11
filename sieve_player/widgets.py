"""A small settings-widget base so a tool file stays one screen long."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget


class ParamWidget(QWidget):
    """Has .changed and .params(). Add rows with add_int / add_float / add_bool."""
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._get = {}
        self._lay = QVBoxLayout(self)
        self._lay.setContentsMargins(4, 4, 4, 4)

    def params(self):
        return {k: g() for k, g in self._get.items()}

    def _slider(self, name, lo, hi, value, fmt):
        row = QHBoxLayout()
        label, val = QLabel(name), QLabel(fmt(value))
        val.setMinimumWidth(48)
        s = QSlider(Qt.Horizontal)
        s.setRange(lo, hi)
        s.setValue(value)
        s.valueChanged.connect(lambda v: (val.setText(fmt(v)), self.changed.emit()))
        row.addWidget(label)
        row.addWidget(s, 1)
        row.addWidget(val)
        self._lay.addLayout(row)
        return s

    def add_int(self, name, lo, hi, value):
        s = self._slider(name, lo, hi, int(value), str)
        self._get[name] = s.value

    def add_float(self, name, lo, hi, value, decimals=2):
        k = 10 ** decimals
        s = self._slider(name, round(lo * k), round(hi * k), round(value * k), lambda v: f"{v / k:.{decimals}f}")
        self._get[name] = lambda: s.value() / k

    def add_bool(self, name, value):
        c = QCheckBox(name)
        c.setChecked(bool(value))
        c.toggled.connect(lambda _: self.changed.emit())
        self._lay.addWidget(c)
        self._get[name] = c.isChecked
