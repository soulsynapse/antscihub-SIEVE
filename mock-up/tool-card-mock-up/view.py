"""Walk the card mock-up versions and fiddle with their knobs.

    python view.py            # opens on the newest version
    python view.py 2          # opens on version 2

Left/Right (or [ and ]) step between versions, 1-9 jump. Each file in
versions/ is a self-contained mock-up with a Window class and a TUNABLES
dict naming the module constants it lets you move, with (min, max, step).
The panel on the right rebuilds the current version whenever a value
changes; each version keeps its own values while the viewer runs. The
readout at the bottom of the panel is the thing to paste back when you
say what you like.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

VERSIONS = Path(__file__).parent / "versions"
STAGE_W = 560
PANEL_W = 300

_FAMILIES = [
    "Segoe UI Variable Text", "Segoe UI", "Inter", "Aptos", "Calibri", "Bahnschrift",
    "Roboto", "Open Sans", "Source Sans 3", "IBM Plex Sans", "Noto Sans", "Arial",
    "Verdana", "Tahoma", "Helvetica Neue",
]
_MONOS = ["Consolas", "Cascadia Mono", "Cascadia Code", "JetBrains Mono", "Fira Code",
          "IBM Plex Mono", "Source Code Pro", "Courier New"]
_WEIGHTS = {
    "Light": QFont.Weight.Light,
    "Normal": QFont.Weight.Normal,
    "Medium": QFont.Weight.Medium,
    "DemiBold": QFont.Weight.DemiBold,
    "Bold": QFont.Weight.Bold,
}


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module  # dataclasses look the module up by name
    spec.loader.exec_module(module)
    return module


def _installed(candidates: list[str]) -> list[str]:
    have = set(QFontDatabase.families())
    return [f for f in candidates if f in have]


class Version:
    """One loaded mock-up plus the defaults it shipped with."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.module = _load(path)
        self.tunables: dict[str, tuple[float, float, float]] = getattr(self.module, "TUNABLES", {})
        self.defaults = {name: getattr(self.module, name) for name in self.tunables}
        self.family = self.module._UI_FAMILIES[0]
        self.mono = self.module._MONO_FAMILIES[0]
        self.weight = next((k for k, v in _WEIGHTS.items() if v == self.module.NAME_WEIGHT), "Normal")
        self.default_fonts = (self.family, self.mono, self.weight)

    @property
    def name(self) -> str:
        return self.path.stem

    @property
    def note(self) -> str:
        doc = (self.module.__doc__ or "").strip().splitlines()
        return doc[0] if doc else ""

    def set_fonts(self, family: str, mono: str, weight: str) -> None:
        self.family, self.mono, self.weight = family, mono, weight
        m = self.module
        m._UI_FAMILIES = [family, "sans-serif"]
        m._UI_DISPLAY = [family + " Semibold", family, "sans-serif"]
        m._UI_FIGURE = [family + " Display Semibold", family + " Semibold", family, "sans-serif"]
        m._MONO_FAMILIES = [mono, "monospace"]
        m.NAME_WEIGHT = _WEIGHTS[weight]

    def reset(self) -> None:
        for name, value in self.defaults.items():
            setattr(self.module, name, value)
        self.set_fonts(*self.default_fonts)

    def readout(self) -> str:
        values = " ".join(f"{n}={getattr(self.module, n):g}" for n in self.tunables)
        return f"{self.name}  family={self.family}  mono={self.mono}  name-weight={self.weight}\n{values}"


class Knob(QWidget):
    """A slider that walks (lo, hi) in steps, showing its value beside it."""

    def __init__(self, lo: float, hi: float, step: float, on_change) -> None:
        super().__init__()
        self._lo, self._step = lo, step
        self._on_change = on_change
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, round((hi - lo) / step))
        self._value = QLabel()
        self._value.setFixedWidth(34)
        self._value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(self._slider, 1)
        row.addWidget(self._value)
        self._slider.valueChanged.connect(self._changed)

    def value(self) -> float:
        raw = self._lo + self._slider.value() * self._step
        return int(raw) if float(self._step).is_integer() and float(self._lo).is_integer() else raw

    def set_value(self, value: float) -> None:
        self._slider.blockSignals(True)
        self._slider.setValue(round((value - self._lo) / self._step))
        self._slider.blockSignals(False)
        self._value.setText(f"{self.value():g}")

    def _changed(self, _: int) -> None:
        self._value.setText(f"{self.value():g}")
        self._on_change(self.value())


class Panel(QWidget):
    """Controls for whichever version is showing. Rebuilt when the version changes."""

    def __init__(self, on_change, on_reset, on_copy) -> None:
        super().__init__()
        self.setFixedWidth(PANEL_W)
        self._on_change = on_change
        self._version: Version | None = None
        self._knobs: dict[str, Knob] = {}

        column = QVBoxLayout(self)
        column.setContentsMargins(14, 12, 14, 12)
        column.setSpacing(8)

        self._title = QLabel()
        self._title.setStyleSheet("font-weight: 600;")
        self._note = QLabel()
        self._note.setWordWrap(True)
        self._note.setStyleSheet("color: #646a74;")
        column.addWidget(self._title)
        column.addWidget(self._note)

        fonts = QGridLayout()
        fonts.setHorizontalSpacing(8)
        fonts.setVerticalSpacing(6)
        self._family = QComboBox()
        self._family.addItems(_installed(_FAMILIES))
        self._mono = QComboBox()
        self._mono.addItems(_installed(_MONOS))
        self._weight = QComboBox()
        self._weight.addItems(list(_WEIGHTS))
        for r, (label, box) in enumerate((("family", self._family), ("mono", self._mono),
                                          ("name weight", self._weight))):
            fonts.addWidget(QLabel(label), r, 0)
            fonts.addWidget(box, r, 1)
            box.currentTextChanged.connect(self._fonts_changed)
        column.addLayout(fonts)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #dcdee3;")
        column.addWidget(line)

        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(8)
        self._grid.setVerticalSpacing(4)
        scroll = QScrollArea()
        scroll.setWidget(self._grid_host)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        column.addWidget(scroll, 1)

        buttons = QHBoxLayout()
        reset = QPushButton("Reset")
        reset.clicked.connect(on_reset)
        copy = QPushButton("Copy readout")
        copy.clicked.connect(on_copy)
        buttons.addWidget(reset)
        buttons.addWidget(copy)
        column.addLayout(buttons)

        self._readout = QPlainTextEdit()
        self._readout.setReadOnly(True)
        self._readout.setFixedHeight(96)
        self._readout.setFont(QFont("Consolas", 8))
        column.addWidget(self._readout)

    def readout(self) -> str:
        return self._readout.toPlainText()

    def bind(self, version: Version) -> None:
        self._version = None  # quiet while the controls are rebuilt
        self._title.setText(version.name)
        self._note.setText(version.note)
        for box, text in ((self._family, version.family), (self._mono, version.mono),
                          (self._weight, version.weight)):
            box.blockSignals(True)
            box.setCurrentText(text)
            box.blockSignals(False)

        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self._knobs = {}
        for r, (name, (lo, hi, step)) in enumerate(version.tunables.items()):
            label = QLabel(name.lower().replace("_", " "))
            label.setStyleSheet("color: #565c66;")
            knob = Knob(lo, hi, step, lambda v, n=name: self._knob_changed(n, v))
            knob.set_value(getattr(version.module, name))
            self._grid.addWidget(label, r, 0)
            self._grid.addWidget(knob, r, 1)
            self._knobs[name] = knob
        self._grid.setColumnStretch(1, 1)
        self._version = version
        self.refresh()

    def refresh(self) -> None:
        if self._version is None:
            return
        for name, knob in self._knobs.items():
            knob.set_value(getattr(self._version.module, name))
        for box, text in ((self._family, self._version.family), (self._mono, self._version.mono),
                          (self._weight, self._version.weight)):
            box.blockSignals(True)
            box.setCurrentText(text)
            box.blockSignals(False)
        self._readout.setPlainText(self._version.readout())

    def _knob_changed(self, name: str, value: float) -> None:
        if self._version is None:
            return
        setattr(self._version.module, name, value)
        self._readout.setPlainText(self._version.readout())
        self._on_change()

    def _fonts_changed(self, _: str) -> None:
        if self._version is None:
            return
        self._version.set_fonts(self._family.currentText(), self._mono.currentText(),
                                self._weight.currentText())
        self._readout.setPlainText(self._version.readout())
        self._on_change()


class Viewer(QWidget):
    def __init__(self, start: int) -> None:
        super().__init__()
        paths = sorted(VERSIONS.glob("*.py"))
        if not paths:
            sys.exit(f"no versions in {VERSIONS}")
        self.versions = [Version(p) for p in paths]
        self._rebuild = QTimer(self)
        self._rebuild.setSingleShot(True)
        self._rebuild.setInterval(40)
        self._rebuild.timeout.connect(self._rebuild_current)

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)

        strip = QWidget()
        strip.setStyleSheet("background: #1b1d21; color: #e8eaee;")
        row = QHBoxLayout(strip)
        row.setContentsMargins(12, 6, 12, 6)
        self._title = QLabel()
        hint = QLabel("←  →  switch version    1-9 jump")
        hint.setStyleSheet("color: #9ca1aa;")
        row.addWidget(self._title)
        row.addStretch(1)
        row.addWidget(hint)
        column.addWidget(strip)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self.stack = QStackedWidget()
        self.stack.setFixedWidth(STAGE_W)
        for version in self.versions:
            self.stack.addWidget(version.module.Window())
        stage = QWidget()
        stage.setObjectName("stage")
        stage.setStyleSheet("#stage { background: #e4e6ea; }")
        centre = QHBoxLayout(stage)
        centre.setContentsMargins(0, 0, 0, 0)
        centre.addStretch(1)
        centre.addWidget(self.stack)
        centre.addStretch(1)
        body.addWidget(stage, 1)

        self.panel = Panel(self._schedule_rebuild, self._reset, self._copy)
        self.panel.setObjectName("panel")
        self.panel.setStyleSheet("#panel { background: #ffffff; border-left: 1px solid #dcdee3; }")
        body.addWidget(self.panel)
        column.addLayout(body, 1)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.show_version(start)

    # -- versions ----------------------------------------------------------
    def show_version(self, index: int) -> None:
        index = max(0, min(len(self.versions) - 1, index))
        self.stack.setCurrentIndex(index)
        version = self.versions[index]
        self._title.setText(f"<b>{version.name}</b> &nbsp; {index + 1}/{len(self.versions)}")
        self.setWindowTitle(f"SIEVE cards — {version.name}")
        self.panel.bind(version)
        self.setFocus()

    def _schedule_rebuild(self) -> None:
        self._rebuild.start()

    def _rebuild_current(self) -> None:
        index = self.stack.currentIndex()
        old = self.stack.widget(index)
        new = self.versions[index].module.Window()
        self.stack.insertWidget(index, new)
        self.stack.removeWidget(old)
        old.deleteLater()
        self.stack.setCurrentIndex(index)
        self.setFocus()

    def _reset(self) -> None:
        self.versions[self.stack.currentIndex()].reset()
        self.panel.refresh()
        self._rebuild_current()

    def _copy(self) -> None:
        QApplication.clipboard().setText(self.panel.readout())

    def keyPressEvent(self, event) -> None:
        key = event.key()
        current = self.stack.currentIndex()
        if key in (Qt.Key.Key_Left, Qt.Key.Key_BracketLeft):
            self.show_version(current - 1)
        elif key in (Qt.Key.Key_Right, Qt.Key.Key_BracketRight):
            self.show_version(current + 1)
        elif Qt.Key.Key_1 <= key <= Qt.Key.Key_9:
            self.show_version(key - Qt.Key.Key_1)
        else:
            super().keyPressEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    start = int(sys.argv[1]) - 1 if len(sys.argv) > 1 and sys.argv[1].isdigit() else 10**6
    viewer = Viewer(start)
    viewer.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
