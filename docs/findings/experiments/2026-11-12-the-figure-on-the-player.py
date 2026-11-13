"""The header's figure over a cold window walk, the same walk again, one overlapping it by half, a
cold walk under playback and a clip walk, with nothing attached to the probe: each figure's words,
and with a folder as the argument the header grabbed to a PNG at each. Then the press.

    .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-12-the-figure-on-the-player.py [folder]
"""
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np  # noqa: E402
from PySide6.QtCore import QPoint, QRect  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document as D  # noqa: E402
from sieve_player import theme  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402
from tests.test_crop import clip  # noqa: E402
from tests.test_plot import series  # noqa: E402
from tools import gray  # noqa: E402

ROWS, WINDOW = 500, 50
out = Path(sys.argv[1]) if len(sys.argv) > 1 else None


def until(win, lane, total, timeout=20.0):
    """The figure once `lane` has finished a walk of `total` rows begun after this call."""
    win.pace._walks.pop(lane, None)
    t = time.perf_counter()
    while True:
        QApplication.processEvents()
        f = win.pace.figure(win.fps, win.count)
        if f is not None and f.lane == lane and f.over and f.total == total:
            return f
        assert time.perf_counter() - t < timeout, f
        time.sleep(0.002)


def say(win, name, f):
    print(f"-- {name}\n{f.words()}\n")
    if out is not None:
        win.grab(QRect(win.header.mapTo(win, QPoint(0, 0)), win.header.size())).save(str(out / f"{name}.png"))   # through the window, for its ground


app = QApplication.instance() or QApplication([])
theme.install_font(app)
with tempfile.TemporaryDirectory() as tmp:
    head = series("head", lambda v: np.arange(len(v), dtype=np.float64))
    D.save(D.from_tools([gray, head], clip(Path(tmp) / "v.avi", n=ROWS, h=480, w=640)), Path(tmp) / "doc.json")
    win = PlayerWindow(str(Path(tmp) / "doc.json"), "t", [gray, head])
    win.resize(1280, 720)
    win.show()
    win.graph.on_event = None       # the open's first walk covers rows 0 to 299 either way; every walk read below is past them
    if win.playing:
        win.toggle_play()
    until(win, "window", 300)

    win.set_window(300, WINDOW)
    say(win, "1-cold", until(win, "window", WINDOW))
    win.worker.set_window(300, WINDOW)
    say(win, "2-again", until(win, "window", WINDOW))
    win.set_window(300 + WINDOW // 2, WINDOW)
    say(win, "3-half", until(win, "window", WINDOW))
    win.toggle_play()
    win.set_window(400, WINDOW)
    say(win, "4-cold-under-playback", until(win, "window", WINDOW))
    win.toggle_play()
    win._toggle_clip()
    say(win, "5-clip", until(win, "clip", ROWS))

    print("on_event before the press:", win.graph.on_event)
    win.header.figure.click()
    QApplication.processEvents()
    print("the press opened:", [k for k, w in win.__dict__["_dev_windows"].items() if w.isVisible()])
    win.close()
