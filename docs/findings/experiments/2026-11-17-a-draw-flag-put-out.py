"""A player offscreen over a clip made here, two nodes with a draw() below gray: what the display
paints, what the graph computes for the frame and how often each node runs, with both flags lit,
after a press on one node's draw flag on the canvas, and after the document is saved and opened
again; then the same document with its list cut from the file.
Run: .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-17-a-draw-flag-put-out.py"""
import json
import os
import sys
import tempfile
import time
from types import SimpleNamespace as Tool

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.getcwd())

from PySide6.QtCore import QEvent, Qt  # noqa: E402
from PySide6.QtGui import QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document as D  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402
from tests.test_crop import clip  # noqa: E402
from tools import gray  # noqa: E402

WAIT = 10.0


def drawer(name):
    t = Tool(NAME=name, KIND="frame", EXPECTS="gray", PRODUCES="gray", runs=0, painted=0)

    def run(frames, row, params):
        t.runs += 1
        return frames(row)

    def draw(painter, row, result, start, params):
        t.painted += 1
    t.run, t.draw = run, draw
    return t


def settle(win, row):
    """Row `row` asked for until the display holds it and every node the graph computes for the frame."""
    t = time.perf_counter()
    while time.perf_counter() - t < WAIT:
        win.goto(row, commit=True)
        QApplication.processEvents()
        if win.display._pix is not None and win.row == row and all(
                win.display.frame_results.get(n) is not None for n in win.graph.drawing()):
            break
        time.sleep(0.005)
    win.display.grab()
    QApplication.processEvents()


def say(what, win, tools):
    print(f"{what}: drawn {win.doc.drawn}, the display paints {[nid for nid, *_ in win.display.drawers]}, "
          f"the graph computes {win.graph.drawing()}; "
          + ", ".join(f"{t.NAME} ran {t.runs} painted {t.painted}" for t in tools))


def press(canvas, at):
    for kind, held in ((QEvent.MouseButtonPress, Qt.LeftButton), (QEvent.MouseButtonRelease, Qt.NoButton)):
        e = QMouseEvent(kind, at, canvas.mapToGlobal(at.toPoint()), Qt.LeftButton, held, Qt.NoModifier)
        (canvas.mousePressEvent if kind == QEvent.MouseButtonPress else canvas.mouseReleaseEvent)(e)
    QApplication.processEvents()


def opened(path, tools):
    win = PlayerWindow(path, "t", tools)
    win.resize(900, 600)
    if win.playing:
        win.toggle_play()
    return win


def main():
    QApplication.instance() or QApplication([])
    a, b = drawer("a"), drawer("b")
    tools = [gray, a, b]
    with tempfile.TemporaryDirectory() as tmp:
        doc = D.from_tools(tools, clip(os.path.join(tmp, "v.avi")))
        doc.connect("gray", "b")
        doc.display = "gray"
        path = os.path.join(tmp, "doc.json")
        D.save(doc, path)
        win = opened(path, tools)
        settle(win, 1)
        say("both flags lit, row 1", win, (a, b))
        for t in (a, b):
            t.runs = t.painted = 0
        win.worker.stop_clip()
        press(win.canvas, win.canvas.to_view(win.canvas.draw_flag(win.doc.node("b")).center()))
        settle(win, 4)
        say("b's flag pressed, row 4, counts from the press", win, (a, b))
        win.save_document(path)
        win.close()
        print(f"the file's drawn: {json.load(open(path, encoding='utf-8'))['drawn']}")
        win = opened(path, tools)
        settle(win, 1)
        say("saved and opened again", win, (a, b))
        win.close()
        d = json.load(open(path, encoding="utf-8"))
        del d["drawn"]
        json.dump(d, open(path, "w", encoding="utf-8", newline="\n"))
        win = opened(path, tools)
        settle(win, 1)
        say("the list cut from the file and opened", win, (a, b))
        win.close()


if __name__ == "__main__":
    main()
