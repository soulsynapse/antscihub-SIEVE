r"""The dump: the probe's stream written to a file as it arrives, one JSON line per event behind a
header line of what no event carries, so a file a crash closed reads back to its last complete
line. Beside the events sit samples the probe does not carry, resident memory at each progress
event and how late the GUI thread's timer fired, which the window reports while a dump is attached.
The emitting thread only appends to a list; a writer thread encodes and writes a batch at a time.
`to_trace()` converts a dump to the Chrome trace event format, for Perfetto or chrome://tracing.

    .venv\Scripts\python -m sieve_player.trace dump.jsonl trace.json
"""
import json
import sys
import threading
import time
from dataclasses import fields

from .graph import Event

SPANS = ("run", "fold", "error", "cache", "decode", "seek", "dump")    # the kinds with a duration; the rest are instants
FIELDS = tuple(f.name for f in fields(Event))


def as_dict(ev):
    return {n: getattr(ev, n) for n in FIELDS}      # asdict() deep-copies


if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    class _Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (n, ctypes.c_size_t) for n in ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                                           "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage",
                                           "PagefileUsage", "PeakPagefileUsage")]
    _k32 = ctypes.WinDLL("kernel32")       # own handle: argtypes set on the shared windll.kernel32 are process-global
    _k32.GetCurrentProcess.restype = wintypes.HANDLE
    _k32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(_Counters), wintypes.DWORD]


def rss():
    """The process's resident set in bytes, as the OS reports it now."""
    if sys.platform == "win32":
        c = _Counters()
        c.cb = ctypes.sizeof(c)
        _k32.K32GetProcessMemoryInfo(_k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
        return int(c.WorkingSetSize)
    try:
        with open("/proc/self/statm") as f:
            return int(f.read().split()[1]) * 4096
    except OSError:
        import resource
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


class Dump:
    """Writes every event to `path`, and passes it on to whatever `on_event` was before, so Stats
    keeps reading; `close()` restores the chain. The emitting thread only appends the event to a
    list; a writer thread takes the list every `period` seconds, encodes each event, samples the
    resident set at each progress event, and writes through a buffered file. One handoff per batch
    rather than one per event is what keeps the writer from stealing the GIL at every emit. A crash
    loses at most the last period's events and the file's buffer. An event that reaches a closed
    dump, a worker mid-emit as the GUI closes it, is dropped and still passed on."""

    def __init__(self, graph, path, period=0.1):
        self.graph, self.path = graph, path
        d = graph.decoder
        self._f = open(path, "w", encoding="utf-8", buffering=1 << 16)
        self._buf = []                  # swapped out whole by the writer; list.append is atomic under the GIL
        self._stop = threading.Event()
        self._closed = False
        self._write({"path": d.path, "fps": d.fps, "count": d.count,
                     "width": getattr(d, "width", None), "height": getattr(d, "height", None),
                     "memo_bytes": graph.memo.limit, "cache_bytes": getattr(d, "cache_limit", None),
                     "fields": list(FIELDS)})
        self._writer = threading.Thread(target=self._drain, args=(period,), name="dump", daemon=True)
        self._prev = graph.on_event
        graph.on_event = self.event
        self._writer.start()

    def _write(self, d):
        return self._f.write(json.dumps(d, separators=(",", ":")) + "\n")

    def _drain(self, period):
        while True:
            stopped = self._stop.wait(period)
            batch, self._buf = self._buf, []
            if batch:
                t, c, n = time.perf_counter(), time.thread_time(), 0
                for item in batch:
                    if isinstance(item, Event):
                        n += self._write(as_dict(item))
                        if item.kind == "progress":
                            n += self._write({"sample": "rss", "value": rss(), "t": item.t})
                    else:
                        n += self._write(item)
                # The writer's own cost as a span on its own thread, so a reader sees a node inflated or
                # a GUI tick late while the writer held the GIL for what it is.
                self._write(as_dict(Event("dump", None, None, "dump", n, (time.perf_counter() - t) * 1000, t,
                                          "dump", (time.thread_time() - c) * 1000, None, None, None)))
            if stopped:
                return

    def event(self, ev):
        if not self._closed:
            self._buf.append(ev)
        if self._prev is not None:
            self._prev(ev)

    def sample(self, name, value, t=None):
        """A measurement into the dump beside the events: `name` and `value`, at `t` on the probe's
        clock, now when not given. The dump's own is "rss" at each progress event; the window's is
        "late", the ms its timer fired behind."""
        if not self._closed:
            self._buf.append({"sample": name, "value": value, "t": time.perf_counter() if t is None else t})

    def close(self):
        if self.graph.on_event == self.event:
            self.graph.on_event = self._prev
        self._closed = True
        self._stop.set()                # the writer drains what is queued, then returns; a later append is dropped
        self._writer.join()
        self._f.close()


def read_dump(path):
    """(header, [Event], [sample]) from a dump, a sample being the dict its line holds. Reading stops
    at the first line that is not whole, the tail a crash left; a file a kill emptied before the
    buffer flushed reads as nothing. An event missing a field the record has, or carrying one it has
    not, refuses to build."""
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    lines.pop()                     # after the last newline: nothing, or a line no newline closed, not whole
    rows = []
    for line in lines:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            break
    samples = [r for r in rows[1:] if "sample" in r]
    return (rows[0] if rows else {}), [Event(**r) for r in rows[1:] if "sample" not in r], samples


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
    as args; each sample a counter track under its name. Returns the dict; writes it to `out` when given."""
    header, events, samples = read_dump(path)
    total = totals(events)
    t0 = min((ev.t for ev in events), default=0.0)
    tids = {}
    trace = []
    for ev in events:
        tid = tids.setdefault(ev.thread, len(tids) + 1)
        args = {k: v for k, v in as_dict(ev).items() if k not in ("node", "kind", "t", "thread") and v is not None}
        trace.append({"name": ev.node or ev.kind, "cat": ev.kind, "ph": "X", "pid": 1, "tid": tid,
                      "ts": (ev.t - t0) * 1e6, "dur": total.get(id(ev), 0.0) * 1e3, "args": args})
    for s in samples:
        trace.append({"name": s["sample"], "ph": "C", "pid": 1, "ts": (s["t"] - t0) * 1e6, "args": {s["sample"]: s["value"]}})
    for name, tid in tids.items():
        trace.append({"name": "thread_name", "ph": "M", "pid": 1, "tid": tid, "args": {"name": name}})
    doc = {"traceEvents": trace, "metadata": header}
    if out is not None:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(doc, f)
    return doc


if __name__ == "__main__":
    to_trace(sys.argv[1], sys.argv[2])
