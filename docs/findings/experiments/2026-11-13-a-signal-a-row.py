"""Experiment behind docs/findings/2026-11-13-a-signal-a-row.md: what the player's clip walk of video,
threshold and detect reads a second in a PlayerWindow, offscreen and under Qt's own event loop, as it
is and with one thing changed, and what the catalogue then says of the walk.

    .venv/Scripts/python.exe docs/findings/experiments/2026-11-13-a-signal-a-row.py [word ...] [clip]

Each word is a process of its own, SECONDS of the clip walk and then stopped: `base` the player as it
is; `report` with worker._Walk.report emitting at one row in EVERY and at the range's end; `hidden`
that with the window never shown; `nostream` that with nothing listening to the stream, so no ledger
and no catalogue; `batch` is `report` with the clip's turn taking rows for SLICE seconds before the
worker's loop reads its asks again, and Graph.progress, the stream's event a row, at one row in EVERY. `bare-button` is the player with its Bare button down, nothing patched. `bare` is Graph.walk_row with no worker, by OpenCV's threads and what the stores
hold. With no word, base and report twice by turns, then bare.
"""
import os
import subprocess
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, ROOT)
CLIP = os.path.join(ROOT, "video-tests", "Thermal hysteresis 4 days",
                    "Thermal-hysteresis-oct-2026__ant3b01__2026-10-25_02-56-36_60fps-crops", "square-1.mp4")
SECONDS, EVERY, BARE_ROWS, SLICE = 5.0, 30, 12000, 0.010
PARAMS = {"threshold": {"thresh": 163}, "detect": {"dark": True, "min_area": 20}}


def player(word, clip):
    if word not in ("base", "bare-button", "quiet", "silent", "silent-live") and not word.startswith("s-"):
        from sieve_player import worker
        report = worker._Walk.report
        worker._Walk.report = lambda self: report(self) if self.i % EVERY == 0 or self.i >= self.length else None
    if word == "batch":
        from sieve_player import graph
        turn, progress = worker._Walk.turn, graph.Graph.progress

        def batch(self):
            end = time.perf_counter() + SLICE
            turn(self)
            while self.name == "clip" and self.i < self.length and time.perf_counter() < end:
                turn(self)
        worker._Walk.turn = batch
        graph.Graph.progress = lambda self, done, length, stack=None: progress(self, done, length, stack) if done % EVERY == 0 or done >= length else None
    if word == "nostream":
        from sieve_player import stream
        stream.Emitter.on_event = property(lambda self: None, lambda self, v: None)
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from sieve_player import catalogue as C
    from sieve_player import document as D
    from sieve_player.window import PlayerWindow
    from tools import detect, threshold

    app = QApplication.instance() or QApplication([])
    doc = D.from_tools([threshold, detect], clip)
    doc.node("video").params["output"] = "luma"
    doc.connect("video", "threshold")
    for nid, p in PARAMS.items():
        doc.node(nid).params.update(p)
    doc.display = "detect"
    path = os.path.join(tempfile.mkdtemp(), "doc.json")
    D.save(doc, path)
    win = PlayerWindow(path, "t", [threshold, detect])
    if word.startswith("s-"):
        win.header.bare.setChecked(True)
        if "paint" in word:
            win.setUpdatesEnabled(False)
        if "late" in word:
            win.lateness.stop()
        if "mach" in word:
            win.machine.close()
    if word in ("bare-button", "quiet", "silent", "silent-live"):
        win.header.bare.setChecked(True)
    if word == "quiet":
        win.centralWidget().setUpdatesEnabled(False)
    if word in ("silent", "silent-live"):
        from sieve_player import worker
        worker.BARE_SLICE = 1.0
    if word == "silent":
        win.setUpdatesEnabled(False)
        win.lateness.stop()
        win.machine.close()
    ledger = win.ledger
    if word not in ("hidden", "nostream"):
        win.show()
    seen = []
    win.worker.clipWalked.connect(lambda done, total, *_: seen.append((time.perf_counter(), done)))
    QTimer.singleShot(1500, win._toggle_clip)       # after the opening window's walk
    QTimer.singleShot(int(1500 + SECONDS * 1000), app.quit)
    app.exec()
    (t0, d0), (t1, d1) = seen[0], seen[-1]
    print(f"{word:9} {d1 - d0} rows in {t1 - t0:.1f} s, {(d1 - d0) / (t1 - t0):.0f} rows a second, {(t1 - t0) / (d1 - d0) * 1000:.3f} ms a row")
    if word != "nostream":
        view = ledger.view()
        w = [x for x in view.walks if x.lane == "clip"][-1]
        rows = ", ".join(f"{n} {r.ms_row:.3f}" for n, r in C.rows(w, view).items())
        print(f"          the ledger's ms a row: {rows}, unprobed {w.unprobed / w.done:.3f}")
        for kind, detector in C.CLASSES.items():
            for p in detector(view, [w]):
                print(f"          {kind} · {p.subject} · {p.ms_row:.3f} ms a row · {p.line}")
    win.close()


def bare(clip):
    import cv2

    from sieve_player import decoder as decmod
    from sieve_player import document as D
    from sieve_player.decoder import Decoder
    from sieve_player.graph import Graph
    from tools import detect, threshold

    decmod.QUIET = True
    for threads, hold in ((1, 16 << 20), (32, 16 << 20), (1, 4 << 30), (32, 4 << 30)) * 2:
        cv2.setNumThreads(threads)
        doc = D.from_tools([threshold, detect], clip)
        doc.node("video").params["output"] = "luma"
        doc.connect("video", "threshold")
        for nid, p in PARAMS.items():
            doc.node(nid).params.update(p)
        doc.display = "detect"
        g = Graph(doc, Decoder(clip, cache_bytes=hold), [threshold, detect], memo_bytes=hold)
        g.sync()
        g.walk_row(0)
        t = time.perf_counter()
        for r in range(1, BARE_ROWS):
            g.walk_row(r)
        wall = time.perf_counter() - t
        print(f"bare      OpenCV at {threads:2} threads, each store {hold >> 20:4} MB: {wall / (BARE_ROWS - 1) * 1000:.3f} ms a row, "
              f"{(BARE_ROWS - 1) / wall:.0f} rows a second")
        g.close()
        g.decoder.close()


if __name__ == "__main__":
    words = [a for a in sys.argv[1:] if not a.lower().endswith(".mp4")]
    clip = next((a for a in sys.argv[1:] if a.lower().endswith(".mp4")), CLIP)
    if len(words) == 1:
        bare(clip) if words[0] == "bare" else player(words[0], clip)
    else:
        for word in words or ["base", "report", "base", "report", "bare"]:
            subprocess.run([sys.executable, "-X", "utf8", os.path.abspath(__file__), word, clip], stderr=subprocess.DEVNULL)
