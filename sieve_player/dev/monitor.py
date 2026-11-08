"""Dev > Monitor: the probe's stream read live as a summary of the clip and a line per node in walk order.

Two scopes. Share and runs are this walk's, reset when a progress row falls below the last. Per-run
means, the unprobed and series cost per cold row, and what they feed (the cold projection, store coverage in
windows, change costs) are each node's latest walk it ran in, so a rewalk that touched two nodes
keeps the rest. Stores are stated in windows because LRU under a scanning walk serves nothing below
one (docs/findings/2026-10-31-window-fit-and-lru-thrash.md). Runs landing between a restart and
its first progress event count toward the new walk's first row.
"""
from __future__ import annotations

import threading
from collections import defaultdict

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from .. import theme
from ..document import produces, static
from ..theme import GAP, PAD

READ_KINDS = ("cache", "decode", "seek")
COST_KINDS = READ_KINDS + ("run", "step", "error", "fold")


class Monitor:
    """The consumer: chains onto the graph's `on_event`, accumulates, answers `snapshot()`. `close()`
    restores the chain."""

    def __init__(self, graph):
        self.graph = graph
        self._lock = threading.Lock()
        # The row in progress: node -> [tool ms, bytes, first t, read kinds, fold ms, folds, runs].
        self._row = defaultdict(lambda: [0.0, 0, None, defaultdict(int), 0.0, 0, 0])
        self._last = {}                                     # node -> [ms, runs, bytes, fold ms, folds] over the latest walk it ran in
        self._last_other = None                             # (unprobed ms, cold rows) over the latest walk that had any
        self._last_kinds = {}                               # read kind -> count over the latest walk the video ran in
        self._scrub_ms, self._scrub_runs = 0.0, 0
        self._syncs, self._changed = 0, ()
        self._keys = {n.id: graph.key(n.id) for n in graph.doc.nodes}    # the plan now, so the first sync seen diffs against it
        self._reset()
        self._prev = graph.on_event
        graph.on_event = self.event

    def _reset(self):
        self._walk = defaultdict(lambda: [0.0, 0, 0, 0.0, 0])    # node -> [tool ms, runs, bytes, fold ms, folds] this walk
        self._other = [0.0, 0, 0.0]                         # [unprobed ms, cold rows, series ms] this walk
        self._row_series = 0.0                              # series ms since the last progress event
        self._kinds = defaultdict(int)                      # read kind -> count this walk
        self._done, self._length = 0, None
        self._t0 = self._t1 = None

    def event(self, ev):
        if self._prev is not None:
            self._prev(ev)
        with self._lock:
            if ev.kind == "sync":
                self._syncs += 1
                if self._keys is not None and ev.keys is not None:
                    self._changed = tuple(n for n, k in ev.keys.items() if self._keys.get(n) != k)
                self._keys = ev.keys
            elif ev.kind == "progress":
                self._progress(ev)
            elif ev.kind in COST_KINDS:
                if ev.serves == "scrub":
                    self._scrub_ms += ev.ms
                    self._scrub_runs += 1
                    return
                if ev.node in self.graph.chain:      # a series node: once per emit, not per row
                    self._row_series += ev.ms
                    self._add(ev.node, ev.ms, ev.bytes)
                    return
                r = self._row[ev.node]
                r[2] = ev.t if r[2] is None else min(r[2], ev.t)
                if ev.kind == "fold":                # kept apart from the tool's ms
                    r[4] += ev.ms
                    r[5] += 1
                    r[1] += ev.bytes
                    return
                r[0] += ev.ms
                r[1] += ev.bytes
                r[6] += 1
                if ev.kind in READ_KINDS:
                    r[3][ev.kind] += 1

    def _add(self, nid, ms, nbytes, runs=1, fold_ms=0.0, folds=0):
        """A row's figures into this walk's for `nid`, which becomes the latest figure for it."""
        w = self._walk[nid]
        w[0] += ms
        w[1] += runs
        w[2] += nbytes
        w[3] += fold_ms
        w[4] += folds
        self._last[nid] = w

    def _progress(self, ev):
        if ev.row < self._done:
            self._reset()               # a restart: the row count went back; equal is the worker closing the window early
        starts = [r[2] for r in self._row.values() if r[2] is not None]
        if self._t0 is None:
            self._t0 = min([ev.t] + starts)
        prev = self._t1 if self._t1 is not None else self._t0
        probed = 0.0
        for nid, (ms, nbytes, _, kinds, fold_ms, folds, runs) in self._row.items():
            self._add(nid, ms, nbytes, runs, fold_ms, folds)
            probed += ms + fold_ms
            for k, n in kinds.items():
                self._kinds[k] += n
                self._last_kinds = self._kinds
        if self._row:
            self._other[0] += (ev.t - prev) * 1000 - probed - self._row_series
            self._other[1] += 1
            self._other[2] += self._row_series
            self._last_other = self._other
        self._row.clear()
        self._row_series = 0.0
        self._done, self._length, self._t1 = ev.row, ev.length, ev.t

    def close(self):
        if self.graph.on_event == self.event:
            self.graph.on_event = self._prev

    def snapshot(self):
        g, d, m = self.graph, self.graph.decoder, self.graph.memo
        with self._lock:
            done, length = self._done, self._length or 0
            wall = (self._t1 - self._t0) if self._t0 is not None and self._t1 is not None else 0.0
            ms = {n: w[0] + w[3] for n, w in self._walk.items()}      # this walk's, tool and fold together
            runs = {n: max(w[1], w[4]) for n, w in self._walk.items()}
            life = {n: tuple(v) for n, v in self._last.items()}
            other_row = self._last_other[0] / self._last_other[1] if self._last_other else None
            series_row = self._last_other[2] / self._last_other[1] if self._last_other else None
            kinds = dict(self._last_kinds)
            scrub = {"ms": self._scrub_ms, "runs": self._scrub_runs}
            syncs, changed = self._syncs, self._changed
        chain = list(g.chain)
        video = g.doc.video_node()
        video = video.id if video is not None else None
        frame = [n for n in walk_order(g.doc) if n in life and n not in chain]
        order = frame + [n for n in chain if n in life]
        run_ms = {n: life[n][0] / life[n][1] if life[n][1] else 0.0 for n in order}        # the tool's, per run
        fold_ms = {n: life[n][3] / life[n][4] if life[n][4] else 0.0 for n in order}       # the density's, per fold
        fixed = {n for n in order if static(g.tools.get(g.doc.node(n).tool))}             # run once per key: a row pays nothing
        row_ms = {n: 0.0 if n in fixed else run_ms[n] + fold_ms[n] for n in order}         # what a cold row pays the node
        run_bytes = {n: life[n][2] / max(life[n][1], life[n][4], 1) for n in order}
        cache_row = run_bytes.get(video, 0.0)
        memo_row = sum(run_bytes[n] for n in frame if n != video)
        cache_windows = _windows(getattr(d, "cache_limit", None), cache_row, length)
        memo_windows = _windows(m.limit, memo_row, length)
        down = downstream(g.doc)
        nodes = []
        for n in order:
            kind = produces(g.doc, g.tools, n)
            if n in chain:
                nodes.append({"node": n, "type": kind, "series": True, "ms": ms.get(n, 0.0), "runs": runs.get(n, 0),
                              "run_ms": run_ms[n], "run_bytes": run_bytes[n]})
                continue
            cost = sum(row_ms.get(x, 0.0) for x in down[n] | {n})
            if n != video and video in row_ms and cache_windows is not None and cache_windows < 1:
                cost += row_ms[video]                    # the frames come back through the decoder too
            once = sum(run_ms[x] + fold_ms[x] for x in (down[n] | {n}) & fixed)   # each static node here rebuilds once
            nodes.append({"node": n, "type": kind, "series": False, "static": n in fixed, "ms": ms.get(n, 0.0),
                          "runs": runs.get(n, 0), "share": ms.get(n, 0.0) / (wall * 1000) if wall else None,
                          "run_ms": run_ms[n], "fold_ms": fold_ms[n], "row_ms": row_ms[n], "run_bytes": run_bytes[n],
                          "change_s": (cost * length + once) / 1000 if length else None,
                          "kinds": kinds if n == video else None})
        probed = sum(ms.get(n, 0.0) for n in frame)
        series_ms = sum(ms.get(n, 0.0) for n in chain)
        cold_row_ms = sum(row_ms[n] for n in frame) + (other_row or 0.0) + (series_row or 0.0) if frame else None    # one row, nothing held
        clip_s = g.count * cold_row_ms / 1000 if cold_row_ms else None
        footage_s = g.count / g.fps if g.fps else None
        return {
            "done": done, "length": length, "wall_s": wall, "rate": done / wall if wall else None,
            "fps": g.fps, "count": g.count, "footage_s": footage_s,
            "cold_row_ms": cold_row_ms, "clip_s": clip_s,
            "multiple": footage_s / clip_s if clip_s and footage_s else None,
            "left_s": (length - done) * (cold_row_ms or 0) / 1000 if cold_row_ms and length else None,
            "probed_ms": probed, "series_ms": series_ms, "other_ms": wall * 1000 - probed - series_ms,
            "other_row_ms": other_row, "series_row_ms": series_row,
            "memo": {"bytes": m.bytes, "limit": m.limit, "row_bytes": memo_row, "windows": memo_windows},
            "cache": {"bytes": d.cache_bytes, "limit": getattr(d, "cache_limit", None), "row_bytes": cache_row,
                      "windows": cache_windows},
            "scrub": scrub, "syncs": syncs, "changed": changed, "nodes": nodes,
        }


def _windows(limit, row_bytes, length):
    return limit / (row_bytes * length) if limit and row_bytes and length else None


def walk_order(doc):
    """Node ids by depth from the video, document order within a depth."""
    depth, ids = {}, [n.id for n in doc.nodes]

    def of(nid, stack=()):
        if nid not in depth:
            w = doc.source(nid)
            depth[nid] = 0 if w is None or w.src in stack else of(w.src, (*stack, nid)) + 1
        return depth[nid]
    return sorted(ids, key=lambda nid: (of(nid), ids.index(nid)))


def downstream(doc):
    """{node: set of nodes that read it, transitively}: what a change to it reruns."""
    reads = defaultdict(set)
    for w in doc.wires:
        reads[w.src].add(w.dst)
    out = {}
    for n in doc.nodes:
        seen, todo = set(), [n.id]
        while todo:
            for x in reads[todo.pop()]:
                if x not in seen:
                    seen.add(x)
                    todo.append(x)
        out[n.id] = seen
    return out


# -- text -----------------------------------------------------------------------------------

def _time(s):
    if s is None:
        return "-"
    if s < 60:
        return f"{s:.1f}s"
    m, s = divmod(int(round(s)), 60)
    h, m = divmod(m, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m{s:02d}s"


def _mb(b):
    return "-" if b is None else f"{b / 2**20:.0f} MB"


def summary(s):
    lines = [f"clip    {_time(s['footage_s'])} of footage, {s['count']} rows at {s['fps']:.2f} fps"]
    if s["clip_s"]:
        lines.append(f"cold    whole clip in ~{_time(s['clip_s'])}  ({s['multiple']:.1f}x realtime, "
                     f"{s['cold_row_ms']:.2f} ms/row of which {s['other_row_ms']:.2f} unprobed"
                     + (f", {s['series_row_ms']:.2f} series" if s["series_row_ms"] else "") + ")")
    else:
        lines.append("cold    whole clip in -  (nothing has run)")
    walk = f"walk    {s['done']} / {s['length']} rows"
    if s["rate"]:
        walk += f" in {_time(s['wall_s'])} at {s['rate']:.0f} rows/s"
        if s["done"] < s["length"]:
            walk += f", ~{_time(s['left_s'])} to go if the rest is cold"
    lines.append(walk)
    for name in ("memo", "cache"):
        st = s[name]
        w = "-" if st["windows"] is None else f"{st['windows']:.1f} windows"
        held = _mb(st["bytes"]) + (f" of {_mb(st['limit'])}" if st["limit"] else "")
        lines.append(f"{name:7} {held}, holds {w}" + (f" at {st['row_bytes'] / 2**20:.2f} MB/row" if st["row_bytes"] else ""))
    if s["wall_s"]:
        wall = s["wall_s"] * 1000
        lines.append(f"of this walk's time: {s['probed_ms'] / wall:.0%} in frame nodes, {s['series_ms'] / wall:.0%} in series "
                     f"nodes, {s['other_ms'] / wall:.0%} unprobed (memo hits, the worker loop, handoffs, the GUI's turn)")
    if s["scrub"]["runs"]:
        lines.append(f"scrub   {s['scrub']['runs']} runs, {s['scrub']['ms']:.0f} ms, outside the walk")
    if s["syncs"]:
        lines.append(f"changes {s['syncs']}" + (f", last touched {', '.join(s['changed'])}" if s["changed"] else ", last touched nothing"))
    return "\n".join(lines)


def table(s):
    rows = [f"{'':<14}{'this walk':>13}  {'per row: tool + density':>24}",
            f"{'node':<14}{'share':>6}{'runs':>7}  {'ms':>6}{'fold':>7}{'MB':>7}   a change here costs"]
    for n in s["nodes"]:
        if n["series"]:
            rows.append(f"{n['node']:<14}{'':>6}{n['runs']:>7}  {n['run_ms']:>6.1f}{'':>7}{n['run_bytes'] / 2**20:>7.2f}   per emit, not per row")
            continue
        share = "-" if n["share"] is None else f"{n['share']:.0%}"
        if n["static"]:
            rows.append(f"{n['node']:<14}{share:>6}{n['runs']:>7}  {n['run_ms']:>6.1f}{n['fold_ms']:>7.1f}{n['run_bytes'] / 2**20:>7.2f}"
                        f"   per change, not per row; ~{_time(n['change_s'])} with the window below it")
            continue
        tail = f"~{_time(n['change_s'])} over the window" if n["change_s"] is not None else ""
        if n["kinds"]:
            k = n["kinds"]
            tail = " ".join(f"{k.get(x, 0)} {x}" for x in READ_KINDS) + ("; " + tail if tail else "")
        fold = f"{n['fold_ms']:>7.2f}" if n["fold_ms"] else f"{'':>7}"
        rows.append(f"{n['node']:<14}{share:>6}{n['runs']:>7}  {n['run_ms']:>6.2f}{fold}{n['run_bytes'] / 2**20:>7.2f}   {tail}")
    return "\n".join(rows)


# -- the window -----------------------------------------------------------------------------

class MonitorWindow(QWidget):
    """A drop-down of views (monitor_views.py) over the chosen one, polled on a timer; re-attaches
    when the player's graph changes."""

    def __init__(self, player, period_ms=250):
        super().__init__(player, Qt.WindowType.Window)
        from .monitor_views import VIEWS
        self.setWindowTitle("Monitor")
        self.setStyleSheet(theme.sheet())
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.player, self.monitor, self.snapshot = player, None, None
        self.resize(820, 560)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(PAD, PAD, PAD, PAD)
        lay.setSpacing(GAP)
        top = QHBoxLayout()
        top.addWidget(theme.desc_label("style"))
        self.pick = QComboBox()
        self.pick.addItems(list(VIEWS))
        self.pick.currentTextChanged.connect(self.set_view)
        top.addWidget(self.pick)
        top.addStretch(1)
        self.status = theme.readout("no video")
        top.addWidget(self.status)
        lay.addLayout(top)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        lay.addWidget(self.scroll, 1)
        self.views, self.view = VIEWS, None
        self.set_view(self.pick.currentText())
        self._timer = QTimer(self, interval=period_ms)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

    def set_view(self, name):
        self.view = self.views[name]()
        self.scroll.setWidget(self.view)         # the scroll area deletes the one before
        if self.snapshot is not None:
            self.view.set_snapshot(self.snapshot)

    def refresh(self):
        g = self.player.graph
        if self.monitor is not None and self.monitor.graph is not g:
            self.monitor.close()
            self.monitor = None
        if g is None:
            self.status.setText("no video")
            self.snapshot = None
            return
        if self.monitor is None:
            self.monitor = Monitor(g)
        self.status.setText("")
        self.snapshot = self.monitor.snapshot()
        self.view.set_snapshot(self.snapshot)

    def closeEvent(self, e):
        self._timer.stop()
        if self.monitor is not None:
            self.monitor.close()
            self.monitor = None
        super().closeEvent(e)
