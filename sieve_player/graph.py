"""The runtime: what the graph says, computed and memoized.

A Graph is built from a document, a decoder and the tools the document's names resolve to. It
snapshots the document on `sync()`, which the window calls after any change, so a worker thread
mid-computation works from one consistent plan and the next computation sees the new one. Params
are read from the document's nodes; the runtime holds none of its own. A node is computed as None
when nothing reaches it: no wire, an unresolved tool, or a wire whose types do not fit.
"""
import hashlib
import json
import threading
from collections import OrderedDict
from dataclasses import dataclass

import numpy as np

from .document import OVERLAYABLE, VIDEO_PRODUCES, VIDEO_TOOL, fed, is_selector, produces


def _key(*parts):
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:16]


class Memo:
    """LRU bounded by bytes. Image-shaped entries (ndim >= 2) are evicted before small ones."""

    def __init__(self, limit_bytes):
        self.limit = limit_bytes
        self.bytes = 0
        self._big, self._small = OrderedDict(), OrderedDict()
        self._lock = threading.Lock()
        self.hits = self.misses = 0

    @staticmethod
    def _size(v):
        return v.nbytes if isinstance(v, np.ndarray) else 64

    def get(self, k):
        with self._lock:
            for d in (self._big, self._small):
                v = d.get(k)
                if v is not None:
                    d.move_to_end(k)
                    self.hits += 1
                    return v
            self.misses += 1
            return None

    def put(self, k, v):
        d = self._big if isinstance(v, np.ndarray) and v.ndim >= 2 else self._small
        with self._lock:
            if k in self._big or k in self._small:
                return
            d[k] = v
            self.bytes += self._size(v)
            while self.bytes > self.limit:
                src = self._big or self._small
                if not src:
                    break
                _, old = src.popitem(last=False)
                self.bytes -= self._size(old)


class Frames:
    """What a frame tool's run() gets: frames(r) is the output of the node it reads, at row r. It
    reads through the plan the computation began in, so one run() sees one graph even if the
    document is synced under it."""

    def __init__(self, graph, plan, source, key):
        self._graph, self._plan, self._source = graph, plan, source
        self.key, self.fps, self.count = key, graph.fps, graph.count

    def __call__(self, row):
        return self._graph._compute(self._plan, self._source, row)


class Series:
    """What a series tool's run() gets: data is (T, ...), the read node stacked over the window."""

    def __init__(self, data, key, start, fps):
        self.data, self.key, self.start, self.fps = data, key, start, fps


@dataclass
class _Entry:
    """One node as the plan saw it at sync()."""
    tool: object
    kind: str           # "video" | "frame" | "series" | "selector"
    params: dict
    src: str | None     # the node its input wire names
    key: str
    src_key: str | None
    fed: bool


class Graph:
    def __init__(self, doc, decoder, tools, memo_bytes=512 << 20):
        self.doc, self.decoder = doc, decoder
        self.tools = tools if hasattr(tools, "get") else {t.NAME: t for t in tools}
        self.fps, self.count = decoder.fps, decoder.count
        self.memo = Memo(memo_bytes)
        self._lock = threading.Lock()
        self._base = _key("video", decoder.path, VIDEO_PRODUCES)
        self._plan = {}
        self.shown = self.over = self.series = None
        self.chain, self.unrun_series = [], []
        self.sync()

    def sync(self):
        """Re-read the document: wiring, params, the flag, which series node runs."""
        doc, tools = self.doc, self.tools
        keys = {}

        def key_of(nid, stack=()):
            if nid not in keys:
                node = doc.node(nid)
                if node.tool == VIDEO_TOOL:
                    keys[nid] = self._base
                else:
                    w = doc.source(nid)
                    up = "none" if w is None or w.src in stack else key_of(w.src, (*stack, nid))
                    keys[nid] = _key(up, node.tool, json.dumps(node.params, sort_keys=True))
            return keys[nid]

        plan, series = {}, []
        for n in doc.nodes:
            tool = tools.get(n.tool)
            if n.tool == VIDEO_TOOL:
                kind = "video"
            elif is_selector(tool):
                kind = "selector"       # answers a path, once, before the decoder; never a row
            else:
                kind = getattr(tool, "KIND", "frame")
            w = doc.source(n.id)
            src = w.src if w else None
            plan[n.id] = _Entry(tool, kind, dict(n.params), src, key_of(n.id),
                                key_of(src) if src else None, fed(doc, n.id, tools))
            if kind == "series":
                series.append(n.id)
        # The head is the first series node reading a frame node: it runs on the walked stack. The
        # chain is it and every fed series node wired on from a chain node, which run on the
        # upstream result's "signal" in this order. Any other series node is unrun.
        heads = [s for s in series if plan[s].src is None or plan[plan[s].src].kind != "series"]
        chain = heads[:1]
        for nid in chain:
            chain += [s for s in series if plan[s].src == nid and plan[s].fed and s not in chain]
        with self._lock:
            self._plan = plan
            self.shown = doc.display if doc.display in plan else None
            # The overlay is a node the frame can be heated with: one plane, so only an OVERLAYABLE product.
            self.over = doc.overlay if doc.overlay in plan and produces(doc, tools, doc.overlay) in OVERLAYABLE else None
            self.series = chain[0] if chain else None
            self.chain, self.unrun_series = chain, [s for s in series if s not in chain]

    # -- what the worker and the display ask -------------------------------
    @property
    def walk(self):
        """The node the worker computes over the window: what the series node reads, else what is
        shown. None when the series node is not fed, so its tool never sees a type it does not expect."""
        with self._lock:
            if self.series is None:
                return self.shown
            e = self._plan[self.series]
            return e.src if e.fed else None

    @property
    def series_tool(self):
        with self._lock:
            return self._plan[self.series].tool if self.series else None

    def series_params(self):
        with self._lock:
            return dict(self._plan[self.series].params) if self.series else {}

    def series_chain(self):
        """[(node, tool, params, the node it reads)] in run order: the head first, then each series
        node on from a chain node. The worker feeds the head the stack and the rest the upstream
        result's "signal"."""
        with self._lock:
            return [(nid, self._plan[nid].tool, dict(self._plan[nid].params), self._plan[nid].src) for nid in self.chain]

    def key(self, nid):
        with self._lock:
            return self._plan[nid].key

    def fed(self, nid):
        """Whether the video reaches `nid` through wires whose types fit; None does not."""
        with self._lock:
            e = self._plan.get(nid)
        return e is not None and e.fed

    def compute(self, nid, row):
        """Output of `nid` at `row`, memoized; None for a node nothing reaches. Worker threads only.
        The whole recursion runs in the plan current at the call, so what lands in the memo under a
        key was computed from the graph that key describes."""
        with self._lock:
            plan = self._plan
        return self._compute(plan, nid, row)

    def _compute(self, plan, nid, row):
        e = plan.get(nid)
        if e is None or e.kind in ("series", "selector") or not e.fed:
            return None
        if e.kind == "video":
            return self.decoder.read(row)
        mk = (e.key, row)
        v = self.memo.get(mk)
        if v is None:
            v = e.tool.run(Frames(self, plan, e.src, e.src_key), row, e.params)
            self.memo.put(mk, v)
        return v

    def peek(self, row, nid=None):
        """Memo-only read of the shown node, or of `nid`, at `row`; None if it isn't there. GUI-safe."""
        with self._lock:
            e = self._plan.get(self.shown if nid is None else nid)
        if e is None or not e.fed:
            return None
        if e.kind == "video":
            return self.decoder.cached(row)
        return self.memo.get((e.key, row))
