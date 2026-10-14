"""Chain of frame tools with a keyed, byte-bounded memo, plus the views tools receive."""
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


class Frames:
    """What a frame tool's run() gets: frames(r) is the upstream output at row r."""

    def __init__(self, chain, stage, key):
        self._chain, self._stage = chain, stage
        self.key, self.fps, self.count = key, chain.fps, chain.count

    def __call__(self, row):
        return self._chain.compute(self._stage - 1, row)


class Series:
    """What a series tool's run() gets: data is (T, ...), the last stage stacked over the window."""

    def __init__(self, data, key, start, fps):
        self.data, self.key, self.start, self.fps = data, key, start, fps


class Chain:
    def __init__(self, decoder, tools, memo_bytes=512 << 20):
        self.decoder = decoder
        self.fps, self.count = decoder.fps, decoder.count
        self.frame_tools = [t for t in tools if getattr(t, "KIND", "frame") == "frame"]
        series = [t for t in tools if getattr(t, "KIND", "frame") == "series"]
        if len(series) > 1:
            raise ValueError("at most one series tool")
        self.series_tool = series[0] if series else None
        produces = "bgr"   # what the decoder hands out
        for t in self.frame_tools + series:
            expects = t.EXPECTS if isinstance(t.EXPECTS, (tuple, list, set)) else (t.EXPECTS,)
            if produces not in expects:
                raise ValueError(f"{t.NAME} EXPECTS {t.EXPECTS!r} but upstream PRODUCES {produces!r}")
            produces = getattr(t, "PRODUCES", None) or produces   # PRODUCES None: same type as its input
        self.params = [dict(t.DEFAULTS) for t in self.frame_tools]
        self.series_params = dict(self.series_tool.DEFAULTS) if self.series_tool else {}
        self.memo = Memo(memo_bytes)
        self._lock = threading.Lock()
        self._base = _key("video", decoder.path, "bgr")
        self._keys = []
        self._rekey()

    @property
    def last(self):
        return len(self.frame_tools) - 1

    def _rekey(self):
        k, keys = self._base, []
        for t, p in zip(self.frame_tools, self.params):
            k = _key(k, t.NAME, json.dumps(p, sort_keys=True))
            keys.append(k)
        self._keys = keys

    def key(self, stage):
        """Key of a stage's output; stage -1 is the decoded video."""
        return self._base if stage < 0 else self._keys[stage]

    def set_params(self, stage, params):
        with self._lock:
            self.params[stage] = dict(params)
            self._rekey()

    def set_series_params(self, params):
        with self._lock:
            self.series_params = dict(params)

    def get_series_params(self):
        with self._lock:
            return dict(self.series_params)

    def compute(self, stage, row):
        """Output of `stage` at `row`, memoized. Called from worker threads only."""
        if stage < 0:
            return self.decoder.read(row)
        with self._lock:
            key, tool, params = self._keys[stage], self.frame_tools[stage], dict(self.params[stage])
        mk = (key, row)
        v = self.memo.get(mk)
        if v is None:
            v = tool.run(Frames(self, stage, self.key(stage - 1)), row, params)
            self.memo.put(mk, v)
        return v

    def peek(self, row):
        """Memo-only read of the last stage at `row`; None if it isn't there. GUI-safe."""
        if self.last < 0:
            return self.decoder.cached(row)
        return self.memo.get((self.key(self.last), row))
