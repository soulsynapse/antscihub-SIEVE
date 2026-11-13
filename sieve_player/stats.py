"""Stats: a reader of the stream that keeps each node's last and mean ms and the walk's rate, for
bench.py. It imports the stream's kinds and nothing else of sieve_player; the Graph it is made on
is held for `snapshot()`'s counters and for its `on_event`.
"""
import threading
from collections import deque

from .stream import CACHE, CANCEL, DECODE, PROGRESS, READ, RUN, SEEK, STEP

WINDOW = 64     # rows a running mean spans; the decoder's step and seek means keep their own literal, see Decoder._mean
MEANS = (RUN, STEP, CANCEL, CACHE, DECODE, SEEK, READ)      # the kinds a node's mean is of


def _mean(mean, x, n):
    return x if mean is None else mean + (x - mean) / min(n, WINDOW)


def _rate(hits, misses):
    return hits / (hits + misses) if hits + misses else None


class Stats:
    """The probe's first consumer. Per node, the last figure and a running mean over the window the
    decoder's means use, over the kinds of MEANS alike and blind to key and bytes; beside them the chain nodes' last figures
    summed, a whole run's or one step's,
    the walk's rate in rows per second, read off the progress events, and the decoder's and memo's
    own counters. Making one installs it as the graph's `on_event`, passing each event on to whatever
    was there before, so consumers chain in any order; `event` is its one entry point. `snapshot()`
    is one plain dict, the only thing a reader gets: the window and bench.py read the same and
    neither reaches into the runtime."""

    def __init__(self, graph):
        self.graph = graph
        self._lock = threading.Lock()
        self._nodes = {}                    # nid -> [last ms, mean ms, runs]
        self._walk = deque(maxlen=WINDOW)   # (time, rows done) as the walk reports them
        self._prev = graph.on_event
        graph.on_event = self.event

    def event(self, ev):
        if self._prev is not None:
            self._prev(ev)
        if ev.kind == PROGRESS:
            if ev.lane != "clip":           # the rate is the window's
                with self._lock:
                    if self._walk and ev.row < self._walk[-1][1]:
                        self._walk.clear()  # a new walk; the rate is this one's
                    self._walk.append((ev.t, ev.row))
        elif ev.kind in MEANS:
            with self._lock:
                e = self._nodes.setdefault(ev.node, [0.0, None, 0])
                e[2] += 1
                e[0], e[1] = ev.ms, _mean(e[1], ev.ms, e[2])

    def snapshot(self):
        g, d, m = self.graph, self.graph.decoder, self.graph.memo
        with self._lock:
            nodes = {nid: {"last": last, "mean": mean, "n": n} for nid, (last, mean, n) in self._nodes.items()}
            rate = None
            if len(self._walk) > 1 and self._walk[-1][0] > self._walk[0][0]:
                (t0, r0), (t1, r1) = self._walk[0], self._walk[-1]
                rate = (r1 - r0) / (t1 - t0)
        chain = [nid for nid in g.chain if nid in nodes]
        return {
            "nodes": nodes,
            "series_ms": sum(nodes[nid]["last"] for nid in chain) if chain else None,
            "walk_rows_s": rate, "fps": g.fps,
            "step_ms": d.step_ms, "seek_ms": d.seek_ms, "decodes": d.decodes, "seeks": d.seeks,
            "memo_mb": m.bytes / 2**20, "memo_hit": _rate(m.hits, m.misses), "evictions": m.evictions,
            "cache_mb": d.cache_bytes / 2**20, "cache_hit": _rate(d.cache_hits, d.reads - d.cache_hits),
        }
