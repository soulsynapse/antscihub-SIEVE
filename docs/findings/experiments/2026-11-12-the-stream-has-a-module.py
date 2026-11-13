"""The first deliverable of docs/spec/stream-seams.md, offscreen: two simulations run and dumped by the
tree at a7ceace5, taken from git into a temporary folder, each dump replayed there and here to views
that are compared; a run with a long fold of the ledger's inside it beside the same run with none; and
a selection watched on the Emitter read back off the next sync. Prints each and exits 1 where one is
not as built.

    .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-12-the-stream-has-a-module.py
"""
import io
import os
import pickle
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from sieve_player import ledger as ledger_mod  # noqa: E402
from sieve_player.dev.simulations import _Run  # noqa: E402
from sieve_player.ledger import Ledger, replay  # noqa: E402
from sieve_player.stream import Emitter  # noqa: E402
from sieve_player.trace import FIELDS, read_dump  # noqa: E402

BEFORE = "a7ceace5"
NAMES = ("slot", "rewalk")
THERE = '''
import os, pickle, sys, tempfile
sys.path.insert(0, os.getcwd())
from sieve_player.dev.simulations import _Run, _named
from sieve_player.ledger import replay
from sieve_player.trace import Dump
for name in sys.argv[2:]:
    path = os.path.join(sys.argv[1], name + ".jsonl")
    with tempfile.TemporaryDirectory() as tmp, _Run(tmp, **_named(name).run) as r:
        dump = Dump(r.graph, path)
        r.graph.watch("gray")
        r.graph.sync()
        _named(name)(r)
        dump.close()
    with open(os.path.join(sys.argv[1], name + ".view"), "wb") as f:
        pickle.dump(replay(path).view(), f)
'''


def spin(ms):
    end = time.perf_counter() + ms / 1000
    while time.perf_counter() < end:
        pass


def enclosing(fold_ms):
    """(the enclosing run's ms, the ledger's own ms) with every emit folding for `fold_ms` first."""
    stream, events = Emitter(), []
    led = Ledger(timed=lambda: stream.turn("monitor", "ledger"))
    fold = led._fold
    led._fold = lambda: (spin(fold_ms), fold())
    stream.on_event = lambda ev: (events.append(ev), led.event(ev))
    with stream.probe("outer", 0, "k"):
        spin(5)
        with stream.probe("inner", 0, "k", reader="outer"):
            spin(1)
    return next(ev.ms for ev in events if ev.node == "outer"), sum(ev.ms for ev in events if ev.kind == "monitor")


checks = {}
with tempfile.TemporaryDirectory() as tmp:
    old, out = os.path.join(tmp, "tree"), os.path.join(tmp, "out")
    os.mkdir(out)
    tar = subprocess.run(["git", "archive", BEFORE, "sieve_player", "tools"], cwd=ROOT, capture_output=True, check=True).stdout
    tarfile.open(fileobj=io.BytesIO(tar)).extractall(old, filter="data")
    subprocess.run([sys.executable, "-X", "utf8", "-c", THERE, out, *NAMES], cwd=old, check=True)
    for name in NAMES:
        path = os.path.join(out, name + ".jsonl")
        header, events, _ = read_dump(path)
        with open(os.path.join(out, name + ".view"), "rb") as f:
            there = pickle.load(f)
        here = replay(path).view()
        kinds = sorted({ev.kind for ev in events})
        print(f"{name}: {len(events)} events of {kinds}; {len(here.buckets)} buckets and {len(here.walks)} walks here, "
              f"{len(there.buckets)} and {len(there.walks)} there; selected on its walks {[w.selected for w in here.walks]}")
        checks[f"{name}: a dump written at {BEFORE} names the fields Event has, in their order"] = tuple(header["fields"]) == FIELDS
        checks[f"{name}: it replays here to the view it replays to there"] = here == there and bool(here.walks)

ledger_mod.BACKLOG = 0      # every emit folds
(bare, own_bare), (folded, own) = enclosing(0), enclosing(30)
print(f"a run of 5 ms with a run inside it: {bare:.2f} ms with the ledger's fold taking {own_bare:.2f} ms, {folded:.2f} ms with it taking {own:.2f} ms")
checks["a long fold inside a run's emit is the ledger's own span and not the run's"] = own >= 30 and abs(folded - bare) < 5

with tempfile.TemporaryDirectory() as tmp, _Run(tmp) as r:
    events, emit = [], r.stream.on_event
    r.stream.on_event = lambda ev: (events.append(ev), emit(ev))
    r.stream.watch("gray")
    r.graph.sync()
    r.walk()
    watched, synced = [ev.node for ev in events if ev.kind == "watch"], [ev.facts["selected"] for ev in events if ev.kind == "sync"]
    print("watch events:", watched, "and the selection in the syncs after:", synced, "and on the walk's record:", r.ledger.view().walks[-1].selected)
    checks["a selection watched on the Emitter is a watch event and in every sync's facts after"] = watched == ["gray"] and synced and set(synced) == {"gray"}
    checks["and on the record of the walk begun under it"] = r.ledger.view().walks[-1].selected == ["gray"]
    checks["the graph holds an Emitter and no selection"] = r.graph.stream is r.stream and not hasattr(r.graph, "selected") and not hasattr(r.graph, "watch")

for name, ok in checks.items():
    print(f"{'ok  ' if ok else 'NOT '} {name}")
sys.exit(0 if all(checks.values()) else 1)
