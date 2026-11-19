"""A player offscreen over a clip made here, gray, reduce and smooth: a clip walk stopped by the
header's button past row STOP_AT, what the window then has of it and holds; the held results let
go; and the clip walked again to its end, with how many of its rows ran and how many a store held.
Run: .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-17-a-clip-walk-stopped-midway.py"""
import os
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

WAIT = 20.0
ROWS = 4000
STOP_AT = 500


def until(what):
    t = time.perf_counter()
    while not what() and time.perf_counter() - t < WAIT:
        QApplication.processEvents()
        time.sleep(0.002)
    return what()


def rows_of(results):
    return sorted({len(r["signal"]) for r in results.values() if isinstance(r, dict) and "signal" in r})


def main():
    QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as tmp:
        entries = [e for e in discover("tools") if e.module.__name__.rsplit(".", 1)[-1] in ("gray", "reduce", "smooth")]
        order = {"gray": 0, "reduce": 1, "smooth": 2}
        entries.sort(key=lambda e: order[e.module.__name__.rsplit(".", 1)[-1]])
        doc = D.from_tools([e.module for e in entries], clip(os.path.join(tmp, "v.avi"), n=ROWS))
        path = os.path.join(tmp, "doc.json")
        D.save(doc, path)
        win = PlayerWindow(path, "t", discover("tools"))
        if win.playing:
            win.toggle_play()
        until(lambda: len(win.runs) > 0)
        print(f"opened: {win.count} rows, window {win.window_}, held {win.runs.spans(win._chain())}")

        told = []
        win.worker.clipWalked.connect(lambda done, total, ran: told.append((done, total, ran)))
        stopped = []

        def stop(done, total, ran):
            if done >= STOP_AT and not stopped:
                stopped.append(done)
                win._toggle_clip()
        win.worker.clipWalked.connect(stop)
        win._toggle_clip()
        until(lambda: bool(stopped) and told[-1][0] >= told[-1][1])
        t0 = time.perf_counter()
        until(lambda: time.perf_counter() - t0 > 0.5)      # what the stop sends after its count has landed by then
        done, total, ran = told[-1]
        print(f"stopped: the walk rests at {done} of {total} rows; the window has results over {rows_of(win.clip_results)} rows; "
              f"held {win.runs.spans(win._chain())}")
        win._write_held(wait=True)
        on_disk = held.File(held.path_for(path)).load() if os.path.exists(held.path_for(path)) else []
        print(f"written: the file has {[(r.start, r.rows) for r in on_disk]}")

        win.let_go()
        on_disk = held.File(held.path_for(path)).load()
        print(f"let go: {len(win.runs)} runs held, the file's {on_disk}, clip results over {rows_of(win.clip_results)} rows; "
              f"the memo holds {win.graph.memo.bytes / 2**20:.1f} MB, the decoder's cache {win.graph.decoder.cache_bytes / 2**20:.1f} MB")

        told.clear()
        stopped.append(None)
        t = time.perf_counter()
        win._toggle_clip()
        until(lambda: bool(told) and told[-1][0] >= told[-1][1] == win.count)
        done, total, ran = told[-1]
        print(f"walked again: {done} of {total} rows in {time.perf_counter() - t:.1f} s, {ran} of them ran and {done - ran} a store held")
        until(lambda: bool(win.runs.spans(win._chain())) and win.runs.spans(win._chain())[0][1] == win.count)
        print(f"held {win.runs.spans(win._chain())}")
        win.close()


if __name__ == "__main__":
    main()
