"""What a Ledger and a Log hold over hours of a session, by tracemalloc, with no video and no Qt: the
events and samples are made here on a clock of their own, so an hour takes seconds.

Read: a reader takes a view and the log reads it every 250 ms, as the monitor's poll does, while a
lane walks windows of 300 rows, three nodes a row, each walk under new keys as a drag would leave
it, every result discarded as it is made, a slot at every row, lateness at 10 Hz and the machine at 1 Hz.
Unread: no reader and no event, the samples alone, as the player stands with a video open, nothing
walking and the monitor shut; then one event.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\2026-11-13-what-the-ledger-holds-over-hours.py [hours] [read | unread]
"""
import os
import sys
import tracemalloc

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from sieve_player.catalogue import Log  # noqa: E402
from sieve_player.ledger import Ledger  # noqa: E402
from sieve_player.stream import BEGIN, EVICT, PROGRESS, RUN, SLOT, SYNC, Event  # noqa: E402

HOURS = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
ROW_S, ROWS, NODES = 0.04, 300, ("video", "blur", "blobs")
MACHINE = {"memory": (2 << 30, 8 << 30, 32 << 30), "cores": (1.0, 2.0, 8), "disk": (1 << 20, 1 << 20, 0.1), "faults": 0.0}


def event(kind, t, node=None, row=None, key=None, ms=0.0, thread="worker", lane="window", length=None, keys=None, facts=None,
          nbytes=0, demand=None):
    return Event(node, row, key, kind, nbytes, ms, t, thread, ms, "walk", length, keys, None, demand, demand and NODES[-1],
                 lane, facts, None)


def mb():
    return tracemalloc.get_traced_memory()[0] / 2**20


def read():
    led, log, t, walk, polled, sampled, said = Ledger(), Log(), 0.0, 0, 0.0, 0.0, 0.0
    print(f"{'hours':>6} {'traced MB':>10} {'buckets':>8} {'walks':>6} {'discards':>9} {'entries':>8} {'queued':>7}")
    while t < HOURS * 3600:
        keys = {n: f"{n}-{walk}" for n in NODES}
        plan = {"walk": NODES[-1], "chain": [], "pinned": [], "shown": None,
                "nodes": {n: {"served": False, "static": False, "kind": "frame", "steps": False, "reads": {}} for n in NODES}}
        led.event(event(SYNC, t, lane=None, keys=keys, facts=plan))
        led.event(event(BEGIN, t, row=0, length=ROWS))
        for row in range(ROWS):
            for n in NODES:
                led.event(event(RUN, t, n, row, keys[n], ROW_S * 250, nbytes=1 << 20, demand="walk"))
                led.event(event(EVICT, t, n, row, keys[n], nbytes=1 << 20))
                t += ROW_S / 4
            led.event(event(SLOT, t, "walked", ms=0.2, thread="MainThread", lane=None))
            t += ROW_S / 4
            led.event(event(PROGRESS, t, row=row + 1, length=ROWS,
                            facts={"memo": {"bytes": 1 << 30, "limit": 4 << 30}, "caches": {}, "stack": None, "hits": {}, "fold_hits": {}}))
            while sampled < t:
                led.sample("late", 1.0, sampled)
                if round(sampled * 10) % 10 == 0:
                    led.sample("machine", MACHINE, sampled)
                sampled += 0.1
            if t - polled >= 0.25:
                polled = t
                log.read(led.view())
        walk += 1
        if t - said >= 600 or t >= HOURS * 3600:
            said = t
            print(f"{t / 3600:>6.2f} {mb():>10.1f} {len(led._buckets):>8} {len(led._walks):>6} {len(led._gone):>9} "
                  f"{len(log.entries):>8} {len(led._q):>7}")


def unread():
    led, t = Ledger(), 0.0
    led.event(event(SYNC, t, lane=None, keys={}, facts={}))
    print(f"{'hours':>6} {'traced MB':>10} {'queued':>8}")
    while t < HOURS * 3600:
        led.sample("late", 1.0, t)
        if round(t * 10) % 10 == 0:
            led.sample("machine", MACHINE, t)
        t += 0.1
        if round(t * 10) % 9000 == 0:
            print(f"{t / 3600:>6.2f} {mb():>10.1f} {len(led._q):>8}")
    led.event(event(SLOT, t, "walked", ms=0.2, thread="MainThread", lane=None))
    print(f"after one event: {mb():.1f} MB, {len(led._q)} queued, {len(led._buckets)} buckets")


if __name__ == "__main__":
    tracemalloc.start()
    if "unread" not in sys.argv:
        print(f"read at every 250 ms, {HOURS:g} h on the stream's clock")
        read()
    if "read" not in sys.argv:
        print(f"never read and no event, {HOURS:g} h of samples")
        unread()
