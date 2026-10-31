"""The dump: the probe's stream written to a file as it arrives, one JSON line per event behind a
header line of what no event carries, so a reader derives from the file what a recorder exists to
derive and a file a crash closed reads back to its last complete line. `to_trace()` converts one to
the Chrome trace event format, for Perfetto or chrome://tracing.

    .venv\\Scripts\\python -m sieve_player.trace dump.jsonl trace.json
"""
import json
import sys
import threading
from dataclasses import asdict, fields

from .graph import Event

SPANS = ("run", "cache", "step", "seek")    # the kinds with a duration; the rest are instants


class Dump:
    """Writes every event to `path` on the thread that emits it, through a buffered file, and passes
    it on to whatever `on_event` was before, so Stats keeps reading. `close()` restores the chain.
    Writes are serialised under a lock, the worker and the GUI thread both emitting, and an event
    that reaches a closed dump, a worker mid-emit as the GUI closes it, is dropped and still passed on."""

    def __init__(self, graph, path):
        self.graph, self.path = graph, path
        d = graph.decoder
        self._f = open(path, "w", encoding="utf-8", buffering=1 << 16)
        self._lock = threading.Lock()
        self._write({"path": d.path, "fps": d.fps, "count": d.count,
                     "width": getattr(d, "width", None), "height": getattr(d, "height", None),
                     "memo_bytes": graph.memo.limit, "cache_bytes": getattr(d, "cache_limit", None),
                     "fields": [f.name for f in fields(Event)]})
        self._prev = graph.on_event
        graph.on_event = self.event

    def _write(self, d):
        line = json.dumps(d, separators=(",", ":")) + "\n"
        with self._lock:
            if not self._f.closed:
                self._f.write(line)

    def event(self, ev):
        self._write(asdict(ev))
        if self._prev is not None:
            self._prev(ev)

    def close(self):
        if self.graph.on_event == self.event:
            self.graph.on_event = self._prev
        with self._lock:
            self._f.close()


def read_dump(path):
    """(header, [Event]) from a dump. Reading stops at the first line that is not whole, the tail a
    crash left; a file a kill emptied before the buffer flushed reads as no header and no events. An
    event missing a field the record has, or carrying one it has not, refuses to build."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    lines.pop()                     # after the last newline: nothing, or a line no newline closed, not whole
    rows = []
    for line in lines:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            break
    return (rows[0] if rows else {}), [Event(**r) for r in rows[1:]]


def totals(events):
    """Each span event's total ms, exclusive plus the runs it opened: {id(event): ms}. On one thread
    the probe emits a run after the runs inside it, so the pending events that started after this one
    did are its children, and nothing else is."""
    out, pending = {}, {}
    for ev in events:
        if ev.kind not in SPANS:
            continue
        stack = pending.setdefault(ev.thread, [])
        inner = 0.0
        while stack and stack[-1].t > ev.t:
            inner += out[id(stack.pop())]
        out[id(ev)] = ev.ms + inner
        stack.append(ev)
    return out


def to_trace(path, out=None):
    """A dump as the Chrome trace event format: one complete event per run with its total as the
    duration and the thread as its lane, the instants as zero-length events, the event's other fields
    as args. Returns the dict; writes it to `out` when given."""
    header, events = read_dump(path)
    total = totals(events)
    t0 = min((ev.t for ev in events), default=0.0)
    tids = {}
    trace = []
    for ev in events:
        tid = tids.setdefault(ev.thread, len(tids) + 1)
        args = {k: v for k, v in asdict(ev).items() if k not in ("node", "kind", "t", "thread") and v is not None}
        trace.append({"name": ev.node or ev.kind, "cat": ev.kind, "ph": "X", "pid": 1, "tid": tid,
                      "ts": (ev.t - t0) * 1e6, "dur": total.get(id(ev), 0.0) * 1e3, "args": args})
    for name, tid in tids.items():
        trace.append({"name": "thread_name", "ph": "M", "pid": 1, "tid": tid, "args": {"name": name}})
    doc = {"traceEvents": trace, "metadata": header}
    if out is not None:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(doc, f)
    return doc


if __name__ == "__main__":
    to_trace(sys.argv[1], sys.argv[2])
