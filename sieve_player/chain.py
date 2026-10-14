"""Chain of frame tools with a keyed, byte-bounded memo, plus the views tools receive.

The chain is a list but reads as a graph: every stage names the stage it reads (`Links.sources`),
by default the nearest earlier one whose product it EXPECTS, the decoded video being stage -1. A
stage nobody reads is still a stage; it is computed only when shown. `Links` is the typing and the
wiring without a video, so the player can hold it before anything is loaded and hand it to each
Chain it builds."""
import hashlib
import json
import threading
from collections import OrderedDict

import numpy as np


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


VIDEO = -1   # the stage the decoder is


def _expects(tool):
    e = tool.EXPECTS
    return tuple(e) if isinstance(e, (tuple, list, set)) else (e,)


class Links:
    """Which stage each tool reads, and the types that constrain it. Frame stages are 0..n-1 in
    list order, the video is VIDEO, and the series tool (at most one) is `series`, numbered n.
    `sources[i]` is what frame stage i reads; `series_source` what the series tool stacks. Each
    defaults to the nearest earlier stage whose product the tool EXPECTS and raises if there is
    none. A source may later be None: the stage has no input, hands out nothing, and is computed
    as None. `shown` is the stage the display asks for, the last frame stage until the player says
    otherwise."""

    def __init__(self, tools):
        self.frame_tools = [t for t in tools if getattr(t, "KIND", "frame") == "frame"]
        series = [t for t in tools if getattr(t, "KIND", "frame") == "series"]
        if len(series) > 1:
            raise ValueError("at most one series tool")
        self.series_tool = series[0] if series else None
        self.sources = []
        for i, t in enumerate(self.frame_tools):
            self.sources.append(self._nearest(t, i))
        self.series_source = self._nearest(self.series_tool, len(self.frame_tools)) if self.series_tool else None
        self.shown = len(self.frame_tools) - 1

    @property
    def series(self):
        """The series tool's stage number, or None."""
        return len(self.frame_tools) if self.series_tool else None

    def _nearest(self, tool, stage):
        for j in reversed(self.compatible(stage)):
            return j
        raise ValueError(f"{tool.NAME} EXPECTS {tool.EXPECTS!r} but nothing before it produces that")

    def tool(self, stage):
        return self.series_tool if stage == self.series else self.frame_tools[stage]

    def produces(self, stage):
        """The type a stage hands out; a frame tool with PRODUCES None hands out what it reads."""
        if stage == VIDEO:
            return "bgr"
        if stage == self.series:
            return "series"
        t = self.frame_tools[stage]
        if self.sources[stage] is None:
            return None
        return getattr(t, "PRODUCES", None) or self.produces(self.sources[stage])

    def fed(self, stage):
        """Whether `stage` reaches the video through its sources."""
        while stage != VIDEO:
            stage = self.source(stage)
            if stage is None:
                return False
        return True

    def source(self, stage):
        return self.series_source if stage == self.series else self.sources[stage]

    def compatible(self, stage):
        """The stages `stage` may read: every earlier one whose product it EXPECTS, in order."""
        want = _expects(self.tool(stage))
        upto = len(self.frame_tools) if stage == self.series else stage
        return [j for j in range(VIDEO, upto) if self.produces(j) in want]

    def set_source(self, stage, src):
        """Point `stage` at `src`, or at nothing (None). A pass-through tool hands out what it
        reads, so this can change what later stages receive: each one left reading a type it does
        not EXPECT loses its input."""
        if src is not None and src not in self.compatible(stage):
            raise ValueError(f"{self.tool(stage).NAME} cannot read stage {src}")
        if stage == self.series:
            self.series_source = src
            return
        self.sources[stage] = src
        for i in range(stage + 1, len(self.frame_tools)):
            if self.sources[i] is not None and self.sources[i] not in self.compatible(i):
                self.sources[i] = None
        if self.series_tool and self.series_source is not None and self.series_source not in self.compatible(self.series):
            self.series_source = None

    def readers(self, stage):
        """The stages that may read `stage`: every later one that EXPECTS its product."""
        out = [j for j in range(stage + 1, len(self.frame_tools)) if stage in self.compatible(j)]
        if self.series_tool and stage in self.compatible(self.series):
            out.append(self.series)
        return out

    def detach(self, reader, stage):
        """Stop `reader` reading `stage`: it then reads nothing."""
        if self.source(reader) == stage:
            self.set_source(reader, None)

    def consumers(self, stage):
        """The stages that read `stage`, in order; the series tool last if it does."""
        out = [i for i, s in enumerate(self.sources) if s == stage]
        if self.series_source == stage:
            out.append(self.series)
        return out


class Frames:
    """What a frame tool's run() gets: frames(r) is the output of the stage it reads, at row r."""

    def __init__(self, chain, source, key):
        self._chain, self._source = chain, source
        self.key, self.fps, self.count = key, chain.fps, chain.count

    def __call__(self, row):
        return self._chain.compute(self._source, row)


class Series:
    """What a series tool's run() gets: data is (T, ...), the last stage stacked over the window."""

    def __init__(self, data, key, start, fps):
        self.data, self.key, self.start, self.fps = data, key, start, fps


class Chain:
    def __init__(self, decoder, tools, memo_bytes=512 << 20):
        """`tools` is a list of tool modules or a Links already wired; a list gets default wiring."""
        self.decoder = decoder
        self.fps, self.count = decoder.fps, decoder.count
        self.links = tools if isinstance(tools, Links) else Links(tools)
        self.frame_tools, self.series_tool = self.links.frame_tools, self.links.series_tool
        self.params = [dict(t.DEFAULTS) for t in self.frame_tools]
        self.series_params = dict(self.series_tool.DEFAULTS) if self.series_tool else {}
        self.memo = Memo(memo_bytes)
        self._lock = threading.Lock()
        self._base = _key("video", decoder.path, "bgr")
        self._keys = []
        self._rekey()

    @property
    def shown(self):
        """The stage the display asks for."""
        return self.links.shown

    @property
    def walk(self):
        """The stage the worker computes over the window: what the series tool stacks, else what
        is shown."""
        return self.links.series_source if self.series_tool else self.links.shown

    def _rekey(self):
        keys = []
        for i, (t, p) in enumerate(zip(self.frame_tools, self.params)):
            src = self.links.sources[i]
            k = "none" if src is None else self._base if src == VIDEO else keys[src]
            keys.append(_key(k, t.NAME, json.dumps(p, sort_keys=True)))
        self._keys = keys

    def key(self, stage):
        """Key of a stage's output; stage VIDEO is the decoded video."""
        return self._base if stage == VIDEO else self._keys[stage]

    def set_params(self, stage, params):
        with self._lock:
            self.params[stage] = dict(params)
            self._rekey()

    def relink(self):
        """The Links were rewired: keys follow the new sources."""
        with self._lock:
            self._rekey()

    def set_series_params(self, params):
        with self._lock:
            self.series_params = dict(params)

    def get_series_params(self):
        with self._lock:
            return dict(self.series_params)

    def compute(self, stage, row):
        """Output of `stage` at `row`, memoized; None for a stage the video does not reach.
        Called from worker threads only."""
        if stage == VIDEO:
            return self.decoder.read(row)
        with self._lock:
            if not self.links.fed(stage):
                return None
            key, tool, params = self._keys[stage], self.frame_tools[stage], dict(self.params[stage])
            src = self.links.sources[stage]
            src_key = self.key(src)
        mk = (key, row)
        v = self.memo.get(mk)
        if v is None:
            v = tool.run(Frames(self, src, src_key), row, params)
            self.memo.put(mk, v)
        return v

    def peek(self, row):
        """Memo-only read of the shown stage at `row`; None if it isn't there. GUI-safe."""
        if self.shown == VIDEO:
            return self.decoder.cached(row)
        if not self.links.fed(self.shown):
            return None
        return self.memo.get((self.key(self.shown), row))
