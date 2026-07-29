from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass

from sieve.backend.dispatch import Backend, KernelRegistry
from sieve.core.filter_registry import FilterRegistry
from sieve.core.pipeline_model import ClipRange, Pipeline
from sieve.core.replicates import Replicate
from sieve.pipeline.cache import FrameStore, MemoryFrameStore
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import FrameResult, FrameSource, execute
from sieve.pipeline.plan import ExecutionPlan


Measure = Callable[[str], AbstractContextManager[None]]


Consumer = Callable[[FrameResult], None]


FIRST_FRAME_BUDGET = "slider_to_preview"


WHOLE_WINDOW_BUDGET = "full_preview_render"


@dataclass(frozen=True, slots=True)
class PreviewRender:
    plan: ExecutionPlan

    frames: int

    computed: int

    from_cache: int

    @property
    def span(self) -> ClipRange:
        return self.plan.span

    @property
    def reuse(self) -> float:
        total = self.computed + self.from_cache
        return 0.0 if total == 0 else self.from_cache / total


class PreviewSession:
    def __init__(
        self,
        *,
        source: str,
        reader: FrameSource,
        window: ClipRange,
        measure: Measure,
        replicate: Replicate | None = None,
        backend: Backend = Backend.CPU,
        store: FrameStore | None = None,
        registry: FilterRegistry | None = None,
        kernels: KernelRegistry | None = None,
        pre_cropped: bool = False,
        source_start: int = 0,
    ) -> None:
        self._source = source
        self._reader = reader
        self._window = window
        self._measure = measure
        self._replicate = replicate
        self._backend = backend
        self._store = MemoryFrameStore() if store is None else store
        self._registry = registry
        self._kernels = kernels
        self._pre_cropped = pre_cropped
        self._source_start = source_start

    @property
    def window(self) -> ClipRange:
        return self._window

    @property
    def replicate(self) -> Replicate | None:
        return self._replicate

    @property
    def store(self) -> FrameStore:
        return self._store

    def set_window(self, window: ClipRange) -> None:
        self._window = window

    def set_replicate(self, replicate: Replicate | None) -> None:
        self._replicate = replicate

    def render_window(
        self, pipeline: Pipeline, on_frame: Consumer | None = None
    ) -> PreviewRender:
        return self._run(self._plan(pipeline, self._window), on_frame, whole=True)

    def render_frame(
        self, pipeline: Pipeline, index: int, on_frame: Consumer | None = None
    ) -> PreviewRender:
        return self._run(
            self._plan(pipeline, ClipRange(start=index, end=index + 1)),
            on_frame,
            whole=False,
        )

    def _plan(self, pipeline: Pipeline, span: ClipRange) -> ExecutionPlan:
        return ExecutionPlan.build(
            Dag.build(pipeline, self._registry),
            source=self._source,
            span=span,
            backend=self._backend,
            replicate=self._replicate,
            pre_cropped=self._pre_cropped,
            source_start=self._source_start,
        )

    def _run(
        self, plan: ExecutionPlan, on_frame: Consumer | None, *, whole: bool
    ) -> PreviewRender:
        deliver = _discard if on_frame is None else on_frame
        tally = _Tally()
        with self._measure(WHOLE_WINDOW_BUDGET) if whole else nullcontext():
            stream = execute(
                plan, self._reader, store=self._store, kernels=self._kernels
            )
            with self._measure(FIRST_FRAME_BUDGET):
                tally.add(next(stream), deliver)
            for result in stream:
                tally.add(result, deliver)
        return PreviewRender(
            plan=plan,
            frames=tally.frames,
            computed=tally.computed,
            from_cache=tally.from_cache,
        )


class _Tally:
    def __init__(self) -> None:
        self.frames = 0
        self.computed = 0
        self.from_cache = 0

    def add(self, result: FrameResult, deliver: Consumer) -> None:
        self.frames += 1
        self.from_cache += len(result.from_cache)
        self.computed += len(result.outputs) - len(result.from_cache)
        deliver(result)


def _discard(result: FrameResult) -> None:
    del result
