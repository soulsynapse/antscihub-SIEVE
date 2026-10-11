"""A chain of tools over one source: memoized per stage, keyed by params.

Qt-free. A frame tool at stage i sees `frames(row)`, which is stage i-1's
output at that row (the decoded frame for stage 0). A series tool sees the
stack of the last frame stage's outputs over the loop window.

The memo is the second optimization hook: a stage's key folds its params and
its upstream key, so changing stage 3's slider invalidates stages 3 and
later and nothing before them.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Callable

import numpy as np

from .source import VideoSource


def params_key(name: str, params: dict[str, Any], upstream: str) -> str:
    blob = json.dumps([name, params, upstream], sort_keys=True, default=str)
    return hashlib.sha1(blob.encode()).hexdigest()[:12]


class Frames:
    """What a frame tool is handed: a callable, plus the facts a cache needs."""

    def __init__(self, get: Callable[[int], np.ndarray], key: str, fps: float, count: int) -> None:
        self._get = get
        self.key = key
        self.fps = fps
        self.count = count

    def __call__(self, row: int) -> np.ndarray:
        return self._get(int(row))


@dataclass
class Series:
    """What a series tool is handed: the stack so far, and where it starts."""

    data: np.ndarray
    key: str
    fps: float
    start: int


@dataclass
class StageTrace:
    runs: int = 0
    seconds: float = 0.0


@dataclass
class Stage:
    tool: ModuleType
    params: dict[str, Any]
    key: str = ""
    trace: StageTrace = field(default_factory=StageTrace)


class Chain:
    def __init__(self, source: VideoSource, tools: list[ModuleType]) -> None:
        self.source = source
        self.stages = [Stage(t, dict(t.DEFAULTS)) for t in tools if t.KIND == "frame"]
        series = [t for t in tools if t.KIND == "series"]
        self.series_stage = Stage(series[0], dict(series[0].DEFAULTS)) if series else None
        self._memo: dict[tuple[int, int, str], np.ndarray] = {}
        self.revision = 0
        self._rekey()

    @property
    def fps(self) -> float:
        return self.source.fps

    def _rekey(self) -> None:
        upstream = self.source.key
        for stage in self.stages:
            stage.key = params_key(stage.tool.NAME, stage.params, upstream)
            upstream = stage.key
        if self.series_stage is not None:
            self.series_stage.key = params_key(self.series_stage.tool.NAME, self.series_stage.params, upstream)

    def set_params(self, index: int, params: dict[str, Any]) -> None:
        """Replace stage `index`'s params; drop memo entries at or after it."""
        self.stages[index].params = dict(params)
        self._rekey()
        self._memo = {k: v for k, v in self._memo.items() if k[0] < index}
        self.revision += 1

    def set_series_params(self, params: dict[str, Any]) -> None:
        assert self.series_stage is not None
        self.series_stage.params = dict(params)
        self._rekey()

    def frames_for(self, index: int) -> Frames:
        """The input of stage `index`: stage index-1's output, or the decode."""
        if index == 0:
            return Frames(self.source.frame, self.source.key, self.fps, self.source.count)
        prev = self.stages[index - 1]
        return Frames(lambda row: self.stage(index - 1, row), prev.key, self.fps, self.source.count)

    def stage(self, index: int, row: int) -> np.ndarray:
        if index < 0:
            return self.source.frame(row)
        stage = self.stages[index]
        memo_key = (index, row, stage.key)
        hit = self._memo.get(memo_key)
        if hit is not None:
            return hit
        t0 = time.perf_counter()
        out = stage.tool.run(self.frames_for(index), row, stage.params)
        stage.trace.runs += 1
        stage.trace.seconds += time.perf_counter() - t0
        self._memo[memo_key] = out
        return out

    def last_frame_stage(self) -> int:
        return len(self.stages) - 1

    def run_series(self, stack: np.ndarray, start: int) -> dict[str, Any] | None:
        if self.series_stage is None:
            return None
        series = Series(stack, self.stages[-1].key if self.stages else self.source.key, self.fps, start)
        t0 = time.perf_counter()
        out = self.series_stage.tool.run(series, self.series_stage.params)
        self.series_stage.trace.runs += 1
        self.series_stage.trace.seconds += time.perf_counter() - t0
        return out

    def report(self) -> dict[str, Any]:
        """What the trace knows: per-stage runs and time, and decodes.

        This is the whole of the "report for an agent" idea at its smallest.
        """
        rows = [
            {"stage": s.tool.NAME, "runs": s.trace.runs, "ms_per_run": 1000 * s.trace.seconds / max(1, s.trace.runs)}
            for s in self.stages
        ]
        if self.series_stage is not None:
            s = self.series_stage
            rows.append({"stage": s.tool.NAME, "runs": s.trace.runs, "ms_per_run": 1000 * s.trace.seconds / max(1, s.trace.runs)})
        return {"decodes": self.source.decodes, "memo_entries": len(self._memo), "stages": rows}
