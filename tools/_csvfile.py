"""The file csv and tracks-csv write and resolve reads back: the key line, the atomic write, and the
Write widget. Not a tool; a tool imports it and no other tool (tests/test_seams.py).

The first line is a comment, `# sieve key=... rows=a-b footage=...`, the node's key as the player
computed it (see `sieve_player.graph`): it hashes the band and everything upstream, so a tool reads
it back and says whether the file on disk is this graph's or stale. Readers skip the line with
`comment="#"` (pandas) or `comment.char = "#"` (R). The second line names the columns, and every
line after is one row, or one record of a row, comma separated.

A tool using the widget gives it a module with `count(result)`, `default_name(footage, start, n)`,
`write(path, result, start, fps, footage)` and `FILTER`. Qt is imported inside `widget` alone.
"""
import os
import re

DEFAULTS = {"beside footage": True}
FILTER = "CSV (*.csv);;All (*)"
_KEY = re.compile(r"# sieve key=(\S*) rows=(\d+)-(\d+)")


def key_line(key, start, n, footage):
    return f"# sieve key={key} rows={start}-{start + n - 1} footage={os.path.basename(str(footage))}"


def parse_key(line):
    """(key, start, last) off a key line, or None when the line is not one."""
    m = _KEY.match(line)
    return None if m is None else (m.group(1), int(m.group(2)), int(m.group(3)))


def written_key(path):
    """The key the file at `path` was written under; None when there is no such file or it is not ours."""
    try:
        with open(path, encoding="utf-8") as f:
            first = f.readline()
    except OSError:
        return None
    m = re.match(r"# sieve key=(\S*)", first)
    return m.group(1) if m else None


def replace(path, text):
    """`text` at `path`, written whole or not at all: a write that fails leaves what was there."""
    part = f"{path}.part"
    with open(part, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(part, path)


def read(path):
    """(key line, start, n, header, lines) of a file this module's writers wrote: the header as a
    list of names, the lines each split on commas, blank ones dropped; ValueError when the first
    line is not a key line."""
    with open(path, encoding="utf-8") as f:
        key = f.readline().rstrip("\n")
        header = f.readline().rstrip("\n").split(",")
        lines = [line.rstrip("\n").split(",") for line in f if line.strip()]
    parsed = parse_key(key)
    if parsed is None:
        raise ValueError(f"{os.path.basename(path)} has no sieve key line; is it a csv a SIEVE node wrote?")
    _, start, last = parsed
    return key, start, last - start + 1, header, lines


def widget(parent, export):
    """The Write widget for `export`: a `beside footage` knob, the target's name, whether what is
    on disk is this graph's, and the button, which asks where with the default name filled in
    while the file is not beside the footage and remembers the folder for the session."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFontMetrics
    from PySide6.QtWidgets import QFileDialog, QPushButton

    from sieve_player import ParamWidget
    from sieve_player.theme import measured, readout

    class _Widget(ParamWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.add_bool("beside footage", DEFAULTS["beside footage"])
            self.target, self.disk = measured(wide=True), readout()
            self.button, self.status = QPushButton("Write"), readout()
            self.form.add_row("target", self.target)
            self.form.add_line(self.disk)
            self.form.add_row("write", self.button)
            self.form.add_line(self.status)
            self.button.clicked.connect(self._write)
            self.export = export
            self.footage = self.fps = self.result = None
            self.start, self.chosen = 0, None      # chosen: where the dialog last wrote, while not beside the footage
            self.changed.connect(self._describe)
            self._describe()

        def set_source(self, path, fps):
            self.footage, self.fps = path, fps
            self._describe()

        def show_result(self, result, start, fps):
            self.result, self.start, self.fps = result, start, fps
            self._describe()

        def _count(self):
            return self.export.count(self.result)

        def _default(self):
            return self.export.default_name(self.footage, self.start, self._count())

        def _path(self):
            """Where Write would write, or None while it is not known: no footage, no rows yet, or
            the dialog has not been asked."""
            if self.footage is None or not self._count():
                return None
            return self._default() if self.params()["beside footage"] else self.chosen

        def _describe(self):
            n = self._count()
            self.button.setEnabled(bool(n) and self.footage is not None)
            self.button.setText(f"Write {n} rows" if n else "Write")
            path = self._path()
            self._name = "" if path is None else os.path.basename(path)
            self._elide()
            self.target.setToolTip(path or "")
            if self.footage is None:
                self.disk.setText("pick a video on the video node")
            elif path is None:
                self.disk.setText("" if n == 0 or self.params()["beside footage"] else "asks where on write")
            else:
                k = written_key(path)
                self.disk.setText("nothing on disk" if k is None else "on disk: this graph's" if k == self.result.get("key")
                                  else "on disk: stale, the graph has changed since it was written")

        _name = ""

        def _elide(self):
            metrics = QFontMetrics(self.target.font())
            self.target.setText(metrics.elidedText(self._name, Qt.ElideMiddle, self.target.width() - 12))

        def resizeEvent(self, e):
            super().resizeEvent(e)
            self._elide()

        def _write(self):
            path = self._path()
            if path is None:
                folder = os.path.dirname(self.chosen or self._default())
                path, _ = QFileDialog.getSaveFileName(self, "Write csv", os.path.join(folder, os.path.basename(self._default())),
                                                      self.export.FILTER)
                if not path:
                    return
                self.chosen = path
            try:
                self.export.write(path, self.result, self.start, self.fps, self.footage)
            except OSError as e:
                self.status.setText(f"could not write: {e}")
                return
            self.status.setText(f"wrote {self._count()} rows to {os.path.basename(path)}")
            self._describe()

    return _Widget(parent)
