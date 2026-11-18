"""A player offscreen over a clip made here, gray, threshold, blobs and track: the keys, how often
blobs ran and track ran and stepped, and the outline track's draw was last handed, before and
after `outline` is changed on the track node's card; then the same after `max_step` is, which
track's computing reads.
Run: .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-17-an-outline-changed-on-a-track-node.py"""
import os
import sys
import tempfile
import time
from types import SimpleNamespace as Tool

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.getcwd())

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document as D  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402
from tests.test_crop import clip  # noqa: E402
from tools import blobs, gray, threshold, track  # noqa: E402

WAIT = 10.0


def counted(module):
    """`module` as a tool whose computing counts its calls and whose draw keeps the outline it was handed."""
    t = Tool(**{k: v for k, v in vars(module).items() if not k.startswith("__")}, calls=0, handed=set(), drew=None)

    def count(facet):
        def call(*args):
            t.calls += 1
            t.handed |= set(args[-1])
            return facet(*args)
        return call

    def draw(painter, row, result, start, params):
        t.drew = params["outline"]
        return module.draw(painter, row, result, start, params)
    t.run, t.draw = count(module.run), draw
    if hasattr(module, "step"):
        t.step = count(module.step)
    return t


def settle(win):
    """The events turned until the worker has been still for a while and the frame is painted."""
    t, last, still = time.perf_counter(), None, time.perf_counter()
    while time.perf_counter() - t < WAIT:
        QApplication.processEvents()
        now = tuple(tool.calls for tool in win.tools.values() if hasattr(tool, "calls"))
        if now != last:
            last, still = now, time.perf_counter()
        elif time.perf_counter() - still > 0.5:
            break
        time.sleep(0.005)
    win.display.grab()
    QApplication.processEvents()


def say(what, win, b, t):
    print(f"{what}: track's key {win.graph.key('track')}, blobs ran {b.calls}, track ran or stepped {t.calls}, "
          f"track's draw handed {t.drew!r}; outline handed to blobs' computing {'outline' in b.handed}, to track's {'outline' in t.handed}")


def change(win, nid, name, value):
    w = win.pane.widget(nid)
    if w is not None:
        w.set_params({**win.doc.node(nid).params, name: value})
    else:
        win.doc.node(nid).params[name] = value
        win._params_changed(nid)


def main():
    QApplication.instance() or QApplication([])
    b, t = counted(blobs), counted(track)
    tools = [gray, threshold, b, t]
    with tempfile.TemporaryDirectory() as tmp:
        doc = D.from_tools(tools, clip(os.path.join(tmp, "v.avi")))
        path = os.path.join(tmp, "doc.json")
        D.save(doc, path)
        win = PlayerWindow(path, "t", tools)
        win.resize(900, 600)
        if win.playing:
            win.toggle_play()
        settle(win)
        say("opened", win, b, t)
        change(win, "track", "outline", "contour")
        settle(win)
        say("outline changed to contour", win, b, t)
        change(win, "track", "max_step", 9.0)
        settle(win)
        say("max_step changed to 9", win, b, t)
        win.save_document(path)     # a changed document asks before it closes
        win.close()


if __name__ == "__main__":
    main()
