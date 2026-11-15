r"""What the process holds resident that no store counts: a Decoder's captures beside its cache, and
a video after the next is loaded over it, offscreen.

    .venv\Scripts\python docs\findings\experiments\2026-11-15-what-an-unloaded-video-still-holds.py PLATE FIRST SECOND

PLATE is read through one Decoder, 30 rows stepped and each cursor sought twice; FIRST is opened in
a PlayerWindow, left to walk four seconds, and SECOND loaded over it.
"""
import gc
import os
import sys
import time
import weakref

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.getcwd())

import psutil  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import decoder as decoding  # noqa: E402
from sieve_player.decoder import Decoder  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402
from tools import gray, reduce  # noqa: E402

plate, first, second = (os.path.abspath(p) for p in sys.argv[1:4])
P, MB = psutil.Process(), 2 ** 20


def rss():
    return P.memory_info().rss / MB


def captures():
    decoding.QUIET = True
    d = Decoder(plate)
    d.output = "luma"
    print(f"{rss():7.0f} MB resident, cache {d.cache_bytes / MB:5.0f} MB: opened, {d.width}x{d.height}")
    for r in range(30):
        d.read(r)
    print(f"{rss():7.0f} MB resident, cache {d.cache_bytes / MB:5.0f} MB: 30 rows stepped on the walk's cursor")
    for row in (3000, 6000):
        with d.scrub():
            d.read(row)
        print(f"{rss():7.0f} MB resident, cache {d.cache_bytes / MB:5.0f} MB: the scrub's cursor sought to {row}")
    for row in (5000, 9000):
        d.read(row)
        print(f"{rss():7.0f} MB resident, cache {d.cache_bytes / MB:5.0f} MB: the walk's cursor sought to {row}")
    d.empty()
    gc.collect()
    print(f"{rss():7.0f} MB resident, cache {d.cache_bytes / MB:5.0f} MB: the cache emptied, both captures open")
    d.close()
    gc.collect()
    print(f"{rss():7.0f} MB resident: closed")
    decoding.QUIET = False


def reload():
    app = QApplication.instance() or QApplication(sys.argv)

    def pump(seconds):
        end = time.perf_counter() + seconds
        while time.perf_counter() < end:
            app.processEvents()
            time.sleep(0.01)

    win = PlayerWindow([gray, reduce], "unloaded")
    win.show()
    win.load(first)
    pump(4.0)
    was = {name: weakref.ref(getattr(win, name)) for name in ("graph", "decoder", "worker", "ledger", "stream")}
    print(f"{rss():7.0f} MB resident with the first open, its cache and memo counting "
          f"{(win.decoder.cache_bytes + win.graph.memo.bytes) / MB:.0f} MB")
    win.load(second)
    pump(1.0)
    gc.collect()
    print(f"{rss():7.0f} MB resident with the second open, its cache and memo counting "
          f"{(win.decoder.cache_bytes + win.graph.memo.bytes) / MB:.0f} MB")
    for name, ref in was.items():
        o = ref()
        still = "" if o is None or name not in ("graph", "decoder") else (
            f", its cache counting {(o if name == 'decoder' else o.decoder).cache_bytes / MB:.0f} MB"
            + (f" and its memo {o.memo.bytes / MB:.0f} MB" if name == "graph" else ""))
        print(f"   the first's {name}: {'gone' if o is None else 'held' + still}")
        del o
    win._written = win._text()      # nothing to ask of on the way out
    win.close()


captures()
reload()
