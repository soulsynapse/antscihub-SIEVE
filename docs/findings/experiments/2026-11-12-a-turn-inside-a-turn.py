"""The Fork under A span's place in time, in docs/spec/stream-seams.md, offscreen. First as the Fork
words it: a "slot" opened just before a bucket's edge with a long "monitor" turn inside it and its own
work after, through an Emitter into a Ledger, the buckets its ms were put in beside the buckets it ran
in. Then what is inside a turn in practice: the player over a clip with its monitor open, walked, played
and walked whole, every "slot" and "paint" with a span inside it and how long what was inside took,
against a bucket's width.

    .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-12-a-turn-inside-a-turn.py
"""
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player import document as D  # noqa: E402
from sieve_player import theme  # noqa: E402
from sieve_player.ledger import Ledger  # noqa: E402
from sieve_player.stream import SPANS, TURNS, Emitter  # noqa: E402
from sieve_player.trace import totals  # noqa: E402
from sieve_player.window import PlayerWindow  # noqa: E402
from tests.test_crop import clip  # noqa: E402
from tests.test_plot import series  # noqa: E402
from tools import gray  # noqa: E402

WIDTH = 0.25
BEFORE, INSIDE, AFTER = 5, 500, 100     # ms: the slot's own work, the turn inside it, its own work after


def spin(ms):
    end = time.perf_counter() + ms / 1000
    while time.perf_counter() < end:
        pass


def over(a, b):
    """{bucket: ms} of the interval [a, b] seconds."""
    out = {}
    for i in range(int(a // WIDTH), int(b // WIDTH) + 1):
        ms = (min(b, (i + 1) * WIDTH) - max(a, i * WIDTH)) * 1000
        if ms > 0:
            out[i] = ms
    return out


stream, led, events = Emitter(), Ledger(width=WIDTH), []
stream.on_event = lambda ev: (events.append(ev), led.event(ev))
while not 0.238 < time.perf_counter() % WIDTH < 0.242:
    pass
with stream.turn("slot", "long"):
    spin(BEFORE)
    with stream.turn("monitor", "ledger"):
        spin(INSIDE)
    spin(AFTER)
inner, slot = events
end = slot.t + (slot.ms + inner.ms) / 1000
ran = over(slot.t, inner.t)
for i, ms in over(inner.t + inner.ms / 1000, end).items():
    ran[i] = ran.get(i, 0.0) + ms
view = led.view()
put = {i: b.turns["slot long"] for i, b in enumerate(view.buckets, view.first) if "slot long" in b.turns}
first = min(ran)
print(f"a slot of {slot.ms:.1f} ms of its own with a turn of {inner.ms:.1f} ms inside it, by bucket from the one it began in:")
print("   it ran in      ", {i - first: round(ms, 1) for i, ms in sorted(ran.items())})
print("   the ledger put ", {i - first: round(ms, 1) for i, ms in sorted(put.items())})
astray = sum(ms for i, ms in put.items() if i not in ran)
moved = sum(abs(put.get(i, 0.0) - ran.get(i, 0.0)) for i in ran.keys() | put.keys()) / 2
print(f"   {astray:.1f} ms in buckets it did not run in; {moved:.1f} of its {slot.ms:.1f} ms in another bucket than it ran in")

app = QApplication.instance() or QApplication([])
theme.install_font(app)
seen = []
with tempfile.TemporaryDirectory() as tmp:
    head = series("head", lambda v: np.arange(len(v), dtype=np.float64))
    D.save(D.from_tools([gray, head], clip(Path(tmp) / "v.avi", n=500, h=480, w=640)), Path(tmp) / "doc.json")
    win = PlayerWindow(str(Path(tmp) / "doc.json"), "t", [gray, head])
    win.resize(1280, 720)
    win.show()
    emit = win.stream.on_event
    win.stream.on_event = lambda ev: (seen.append(ev), emit(ev))
    win.header.figure.click()       # the monitor, which polls and paints

    def run(seconds):
        t = time.perf_counter()
        while time.perf_counter() - t < seconds:
            QApplication.processEvents()
            time.sleep(0.002)

    run(2.0)
    if not win.playing:
        win.toggle_play()
    run(3.0)
    win.toggle_play()
    win.set_window(300, 100)
    run(2.0)
    win._toggle_clip()
    run(4.0)
    win.close()

total = totals(seen)
turns = [ev for ev in seen if ev.kind in TURNS]
inside = {}
for ev in seen:
    if ev.kind in SPANS:
        for turn in turns:
            if turn is not ev and turn.thread == ev.thread and turn.t <= ev.t and ev.t + ev.ms / 1000 <= turn.t + total[id(turn)] / 1000:
                inside.setdefault(id(turn), [turn, 0.0, set()])
                inside[id(turn)][1] += ev.ms
                inside[id(turn)][2].add(ev.kind)
held = sorted(inside.values(), key=lambda x: -x[1])
print(f"\nthe player, its monitor open: {len(turns)} slots and paints, {len(held)} with a span inside")
gui = {ev.thread for ev in turns}
beside = [ev for ev in seen if ev.kind in SPANS and ev.kind not in TURNS and ev.thread in gui]
print(f"   the other spans on the thread the turns are on: {len(beside)}, of {sorted({ev.kind for ev in beside})}, "
      f"the longest {max((ev.ms for ev in beside), default=0.0):.2f} ms")
if held:
    lengths = [ms for _, ms, _ in held]
    print(f"   what was inside one took {np.median(lengths):.2f} ms at the median, {np.percentile(lengths, 99):.2f} at the 99th percentile, "
          f"{lengths[0]:.2f} at the most; a bucket is {WIDTH * 1000:.0f} ms")
    print("   the kinds inside:", sorted({k for _, _, kinds in held for k in kinds}))
    for turn, ms, kinds in held[:5]:
        print(f"   {turn.kind} {turn.node}: {turn.ms:.2f} ms of its own, {ms:.2f} ms inside it, of {sorted(kinds)}")
    crossing = sum(1 for turn, ms, _ in held if int(turn.t // WIDTH) != int((turn.t + total[id(turn)] / 1000) // WIDTH))
    print(f"   {crossing} of them lie across a bucket's edge")
