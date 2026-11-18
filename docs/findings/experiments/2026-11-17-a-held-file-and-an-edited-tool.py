"""Two parts. The first reads every held file under video-tests/ as it lies: what it begins
with, the runs that load, and whether a result of them says what it was made under. The second
is a player offscreen over a clip made here and copies of gray, reduce and smooth in a folder of
their own: the nodes marked stale once the window's run is held, after smooth's file is edited,
after gray's is, after the document is closed and opened again, and after the held results are
let go.
Run: .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-17-a-held-file-and-an-edited-tool.py"""
import glob
import os
import pickle
import shutil
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document as D  # noqa: E402
from sieve_player import held  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402
from tests.test_crop import clip  # noqa: E402

WAIT = 10.0


def as_they_lie():
    for path in sorted(glob.glob("video-tests/*.series")):
        with open(path, "rb") as f:
            began = pickle.load(f)
        runs = held.File(path).load()
        says = any("code" in r for run in runs for r in run.results.values())
        print(f"{os.path.basename(path)}: begins with ({began[0]}, {began[1][:8]}...); {len(runs)} runs over {sum(run.rows for run in runs)} rows, "
              f"of {sorted({nid for run in runs for nid in run.results})}; a result says its code: {says}")


def until(what, win):
    t = time.perf_counter()
    while not what() and time.perf_counter() - t < WAIT:
        QApplication.processEvents()
        time.sleep(0.005)
    return what()


def marked(win):
    win._show_held()
    return sorted(nid for nid, badge in win.pane.stale.items() if badge.text())


def opened(path, entries):
    win = PlayerWindow(path, "t", entries)
    if win.playing:
        win.toggle_play()
    return win


def edit(folder, name):
    with open(os.path.join(folder, name), "a", encoding="utf-8", newline="\n") as f:
        f.write("# edited\n")


def main():
    as_they_lie()
    QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as tmp:
        folder = os.path.join(tmp, "copied_tools")
        os.mkdir(folder)
        for name in ("gray.py", "reduce.py", "smooth.py"):
            shutil.copy(os.path.join("tools", name), folder)
        entries = discover(folder)
        doc = D.from_tools([e.module for e in entries], clip(os.path.join(tmp, "v.avi")))
        path = os.path.join(tmp, "doc.json")
        D.save(doc, path)
        win = opened(path, entries)
        print(f"the window's run held: {until(lambda: len(win.runs) > 0, win)}; marked {marked(win)}")
        edit(folder, "smooth.py")
        print(f"smooth's file edited: marked {marked(win)}")
        edit(folder, "gray.py")
        print(f"gray's file edited: marked {marked(win)}")
        win.close()
        win = opened(path, entries)
        print(f"closed and opened again: {len(win.runs)} runs read back, the window served of them: {win._spared}; marked {marked(win)}")
        win.let_go()
        print(f"let go: {len(win.runs)} runs held, the file's {held.File(held.path_for(path)).load()}")
        print(f"walked again in this process, which still runs the tools as it imported them: "
              f"held {until(lambda: len(win.runs) > 0, win)}; marked {marked(win)}")
        win.close()


if __name__ == "__main__":
    main()
