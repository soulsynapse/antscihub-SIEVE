"""Series tool: the signal it reads, written to a csv; signal in, the same signal out.

A pass-through, as Houdini's File Cache SOP is: the signal leaves unchanged, so the node has a trace
and a band like any series node, and the file is that trace. One line per row of the loop window:
`row`, the frame index; `time`, row over fps, in seconds; `signal`; `gate`, 1 where this node's band
keeps the row (see `sieve_player.graph.gated`). The band to export is this node's; an upstream band
zeroes rows before they reach here, as for any series node. The range is the window, so the whole
video is a window the length of the video, and Write writes the rows the walk has so far and says
how many.

The first line is a comment, `# sieve key=... rows=a-b footage=...`, the node's key as the player
computed it (see `sieve_player.graph`): it hashes the band and everything upstream, so the node reads
it back and says whether the file on disk is this graph's or stale. Readers skip the line with
`comment="#"` (pandas) or `comment.char = "#"` (R).

The file sits beside the footage as `<stem>_<a>-<b>.csv`, overwritten; with `beside footage` off,
Write asks where, with that name filled in, and remembers the folder for the session.

run() and the writing need only numpy; Qt and sieve_player are imported inside settings().
"""
import os
import re

import numpy as np

SIEVE_TOOL = True
NAME, KIND, EXPECTS, PRODUCES = "csv", "series", "signal", "signal"
DEFAULTS = {"beside footage": True}
COLUMNS = ("row", "time", "signal", "gate")
FILTER = "CSV (*.csv);;All (*)"


def run(series, params):
    return {"signal": np.asarray(series.data, np.float32).reshape(-1)}


def default_name(footage, start, n):
    root, _ = os.path.splitext(str(footage))
    return f"{root}_{start}-{start + n - 1}.csv"


def text(result, start, fps, footage):
    """The file: the key line, the column names, one line per row. A signal value is written as
    the shortest text that reads back to the same float32."""
    sig = np.asarray(result["signal"], np.float32).reshape(-1)
    gate = np.asarray(result.get("gate", np.ones(len(sig), bool)), bool)
    n = len(sig)
    lines = [f"# sieve key={result.get('key', '')} rows={start}-{start + n - 1} footage={os.path.basename(str(footage))}",
             ",".join(COLUMNS)]
    for i, (v, g) in enumerate(zip(sig, gate)):
        r = start + i
        lines.append(f"{r},{r / fps:.6f},{np.format_float_positional(v, trim='-')},{int(g)}")
    return "\n".join(lines) + "\n"


def write(path, result, start, fps, footage):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text(result, start, fps, footage))


def written_key(path):
    """The key the file at `path` was written under; None when there is no such file or it is not ours."""
    try:
        with open(path, encoding="utf-8") as f:
            first = f.readline()
    except OSError:
        return None
    m = re.match(r"# sieve key=(\S*)", first)
    return m.group(1) if m else None


def settings(parent=None):
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
            return 0 if not isinstance(self.result, dict) or "signal" not in self.result else len(self.result["signal"])

        def _default(self):
            return default_name(self.footage, self.start, self._count())

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
                path, _ = QFileDialog.getSaveFileName(self, "Write csv", os.path.join(folder, os.path.basename(self._default())), FILTER)
                if not path:
                    return
                self.chosen = path
            try:
                write(path, self.result, self.start, self.fps, self.footage)
            except OSError as e:
                self.status.setText(f"could not write: {e}")
                return
            self.status.setText(f"wrote {self._count()} rows to {os.path.basename(path)}")
            self._describe()

    return _Widget(parent)


if __name__ == "__main__":
    import sys

    from sieve_player import play
    from tools import gray, motion, reduce

    sys.exit(play([gray, motion, reduce, sys.modules[__name__]], sys.argv[1] if len(sys.argv) > 1 else None))
