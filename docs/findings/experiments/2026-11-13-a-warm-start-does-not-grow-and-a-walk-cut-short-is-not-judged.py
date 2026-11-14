"""Two feeds through a Ledger and the catalogue's Log: a walk whose first half of video rows the
decoder's cache held and whose second it decoded, and a walk dropped after one row, that row a
recomputation. Prints what the log found in each and exits 1 where it found anything.

    .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-13-a-warm-start-does-not-grow-and-a-walk-cut-short-is-not-judged.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from sieve_player.catalogue import Log  # noqa: E402
from sieve_player.ledger import Ledger  # noqa: E402
from sieve_player.stream import Event  # noqa: E402


def ev(kind, node=None, row=None, key=None, ms=0.0, t=0.0, length=None, facts=None, nbytes=0):
    return Event(node, row, key, kind, nbytes, ms, t, "worker", ms, "walk", length, None, None, "walk", "work", "window", facts, None)


def found(led):
    log = Log()
    log.read(led.view())
    return [f"{e.problem.kind} {e.problem.subject}: {e.problem.line}" for e in log.ordered()]


warm, t = Ledger(), 0.0
warm.event(ev("begin", row=0, length=80, t=t))
for i in range(80):
    warm.event(ev("cache" if i < 40 else "decode", "video", i, "kv", 0.05 if i < 40 else 5.0, t))
    warm.event(ev("run", "work", i, "kw", 2.0, t + 0.006))
    t += 0.01
    warm.event(ev("progress", row=i + 1, length=80, t=t, facts={}))

short = Ledger()
short.event(ev("begin", row=0, length=100, t=0.0))
short.event(ev("evict", None, 5, "kw", t=0.0, nbytes=10))
short.event(ev("run", "work", 5, "kw", 3.0, 0.001))
short.event(ev("progress", row=1, length=100, t=0.01, facts={}))
short.event(ev("begin", row=0, length=100, t=0.02))

said = {"a walk begun warm in the decoder's cache": found(warm), "a walk dropped after one row": found(short)}
for name, problems in said.items():
    print(f"{name}: {problems or 'nothing found'}")
sys.exit(1 if any(said.values()) else 0)
