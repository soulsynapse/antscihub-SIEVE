from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import perf_counter

from pydantic import ValidationError
from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot

from sieve.backend.dispatch import Backend, KernelRegistry, NoKernelError
from sieve.bench.metrics import METRICS, MetricBus
from sieve.core.filter_registry import FilterRegistry
from sieve.core.pipeline_model import ClipRange, CropArtifact, Pipeline
from sieve.core.pool_meter import PoolMeter
from sieve.core.replicates import Replicate
from sieve.decode.prefetch import PrefetchFrameSource
from sieve.decode.reader import VideoDecodeError, VideoReader
from sieve.filters import discover
from sieve.gui.concurrency import resolve_worker_split
from sieve.gui.render_ring import RenderFrameRing
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import GraphError, graph_needs_chroma
from sieve.pipeline.executor import FrameResult, UnrunnableNodeError
from sieve.pipeline.preview import Consumer, PreviewRender, PreviewSession
from sieve.pipeline.resolve_source import ResolvedSource, resolve


FIRST_TICK_BUDGET = "filter_to_first_tick"


class _AbandonedError(Exception):
    pass


class _Wanted:
    def __init__(self) -> None:
        self._lock = Lock()
        self._revision = 0

    def set(self, revision: int) -> None:
        with self._lock:
            self._revision = revision

    def is_current(self, revision: int) -> bool:
        with self._lock:
            return revision == self._revision


@dataclass(frozen=True, slots=True)
class RenderRequest:
    revision: int
    pipeline: Pipeline
    window: ClipRange
    replicate: Replicate | None

    luma: bool

    consumer: Consumer | None = None

    frame_index: int | None = None


@dataclass(frozen=True, slots=True)
class _Crops:
    records: tuple[CropArtifact, ...]

    project_dir: Path


class _RenderWorker(QObject):
    opened = Signal()
    open_failed = Signal(str)

    frame_timed = Signal(int, int, float)

    render_finished = Signal(int, object)
    render_failed = Signal(int, str)
    render_abandoned = Signal(int)

    def __init__(
        self,
        wanted: _Wanted,
        ring: RenderFrameRing,
        bus: MetricBus,
        backend: Backend,
        registry: FilterRegistry | None,
        kernels: KernelRegistry | None,
        meter: PoolMeter,
    ) -> None:
        super().__init__()
        self._wanted = wanted
        self._ring = ring
        self._bus = bus
        self._meter = meter
        self._backend = backend
        self._registry = registry
        self._kernels = kernels
        self._source = ""
        self._path: Path | None = None
        self._crops: _Crops | None = None
        self._reader: PrefetchFrameSource | None = None
        self._resolved: ResolvedSource | None = None
        self._session: PreviewSession | None = None

    @Slot(str, str)
    def open(self, path: str, source: str) -> None:
        self.close()
        try:
            VideoReader(Path(path)).close()
        except VideoDecodeError as error:
            self.open_failed.emit(str(error))
            return
        self._path = Path(path)
        self._source = source
        self.opened.emit()

    @Slot(RenderRequest)
    def render(self, request: RenderRequest) -> None:
        session = self._session_for(request)
        if session is None:
            return
        window_render = request.frame_index is None
        if window_render:
            self._ring.begin()
        started = perf_counter()
        previous = started
        def on_frame(result: FrameResult) -> None:
            nonlocal previous
            if not self._wanted.is_current(request.revision):
                raise _AbandonedError
            if (
                window_render
                and result.source is not None
                and not result.source_cropped
            ):
                self._ring.put(result.source)
            if request.consumer is not None:
                request.consumer(result)
            now = perf_counter()
            self.frame_timed.emit(
                request.revision, result.index, (now - previous) * 1000.0
            )
            previous = now
        try:
            if request.frame_index is None:
                rendered = session.render_window(request.pipeline, on_frame)
            else:
                rendered = session.render_frame(
                    request.pipeline, request.frame_index, on_frame
                )
        except _AbandonedError:
            self.render_abandoned.emit(request.revision)
        except (
            GraphError,
            UnrunnableNodeError,
            NoKernelError,
            VideoDecodeError,
            ValidationError,
        ) as error:
            self.render_failed.emit(request.revision, str(error))
        else:
            self.render_finished.emit(request.revision, rendered)

    @Slot()
    def close(self) -> None:
        self._ring.clear()
        self._session = None
        self._path = None
        self._crops = None
        self._resolved = None
        if self._reader is not None:
            self._reader.close()
            self._reader = None

    @Slot()
    def release_files(self) -> None:
        self._ring.clear()
        self._session = None
        self._resolved = None
        if self._reader is not None:
            self._reader.close()
            self._reader = None

    @Slot(object)
    def set_crops(self, crops: _Crops) -> None:
        self._crops = crops

    def _resolve(self, request: RenderRequest) -> ResolvedSource | None:
        if self._path is None:
            return None
        crops = self._crops
        return resolve(
            () if crops is None else crops.records,
            request.replicate,
            project_dir=self._path.parent if crops is None else crops.project_dir,
            parent=self._path,
            parent_identity=self._source,
            luma=request.luma,
            want=request.window,
        )

    def _reader_for(
        self, request: RenderRequest, resolved: ResolvedSource
    ) -> PrefetchFrameSource | None:
        luma = request.luma
        if (
            self._reader is not None
            and self._reader.luma == luma
            and self._resolved is not None
            and self._resolved.identity == resolved.identity
        ):
            return self._reader
        if self._reader is not None:
            self._reader.close()
        self._reader = None
        self._resolved = None
        self._session = None
        try:
            reader = PrefetchFrameSource(
                resolved.path,
                workers=resolve_worker_split().preview,
                luma=luma,
                meter=self._meter,
            )
        except VideoDecodeError as error:
            self.render_failed.emit(request.revision, str(error))
            return None
        self._reader = reader
        self._resolved = resolved
        return reader

    def _session_for(self, request: RenderRequest) -> PreviewSession | None:
        resolved = self._resolve(request)
        if resolved is None:
            return None
        reader = self._reader_for(request, resolved)
        if reader is None:
            return None
        if self._session is None:
            self._session = PreviewSession(
                source=resolved.identity,
                reader=resolved.wrap(reader),
                window=request.window,
                measure=self._bus.measure,
                replicate=request.replicate,
                backend=self._backend,
                registry=self._registry,
                kernels=self._kernels,
                pre_cropped=resolved.pre_cropped,
                source_start=resolved.first_index,
            )
        else:
            self._session.set_window(request.window)
            self._session.set_replicate(request.replicate)
        return self._session


class PreviewRunner(QObject):
    frame_cost = Signal(int, float)

    render_started = Signal(int)

    render_finished = Signal(object)

    render_failed = Signal(str)

    opened = Signal()

    open_failed = Signal(str)

    window_render_changed = Signal(bool)

    _open_requested = Signal(str, str)
    _render_requested = Signal(RenderRequest)
    _crops_requested = Signal(object)
    _close_requested = Signal()
    _release_requested = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        metrics: MetricBus | None = None,
        backend: Backend = Backend.CPU,
        registry: FilterRegistry | None = None,
        kernels: KernelRegistry | None = None,
    ) -> None:
        super().__init__(parent)
        discover()
        self._metrics = METRICS if metrics is None else metrics
        self._registry: FilterRegistry | None = registry
        self._opened = False
        self._paused = False
        self._revision = 0
        self._in_flight: RenderRequest | None = None
        self._pending: RenderRequest | None = None
        self._window_render_active = False
        self._wanted = _Wanted()
        self._ring = RenderFrameRing()
        self._armed_at: float | None = None
        self._ticked = False
        self._prefetch_meter = PoolMeter()
        self._thread = QThread()
        self._thread.setObjectName("sieve-preview")
        self._worker = _RenderWorker(
            self._wanted,
            self._ring,
            self._metrics,
            backend,
            registry,
            kernels,
            self._prefetch_meter,
        )
        self._worker.moveToThread(self._thread)
        self._open_requested.connect(self._worker.open)
        self._render_requested.connect(self._worker.render)
        self._crops_requested.connect(self._worker.set_crops)
        self._close_requested.connect(self._worker.close)
        self._release_requested.connect(
            self._worker.release_files, Qt.ConnectionType.BlockingQueuedConnection
        )
        self._worker.opened.connect(self._on_opened)
        self._worker.open_failed.connect(self._on_open_failed)
        self._worker.frame_timed.connect(self._on_frame_timed)
        self._worker.render_finished.connect(self._on_render_finished)
        self._worker.render_failed.connect(self._on_render_failed)
        self._worker.render_abandoned.connect(self._on_render_abandoned)
        self._thread.start()

    @property
    def is_open(self) -> bool:
        return self._opened

    @property
    def paused(self) -> bool:
        return self._paused

    def set_paused(self, paused: bool) -> None:
        if paused == self._paused:
            return
        self._paused = paused
        if not paused:
            return
        self._in_flight = None
        self._pending = None
        self._revision += 1
        self._wanted.set(self._revision)
        self._note_slots_changed()

    @property
    def ring(self) -> RenderFrameRing:
        return self._ring

    @property
    def prefetch_meter(self) -> PoolMeter:
        return self._prefetch_meter

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def window_render_active(self) -> bool:
        return self._window_render_active

    @property
    def has_ticked(self) -> bool:
        return self._ticked

    def open(self, video: Path) -> None:
        self.close()
        try:
            source = source_identity(video)
        except OSError:
            self.open_failed.emit(f"cannot preview footage that is not there: {video}")
            return
        self._open_requested.emit(str(video), source)

    def set_crops(self, crops: tuple[CropArtifact, ...], project_dir: Path) -> None:
        self._crops_requested.emit(_Crops(records=crops, project_dir=project_dir))

    def release_files(self) -> None:
        if not self._thread.isRunning():
            return
        self._release_requested.emit()

    def close(self) -> None:
        self._opened = False
        self._in_flight = None
        self._pending = None
        self._armed_at = None
        self._ticked = False
        self._revision += 1
        self._wanted.set(self._revision)
        self._ring.clear()
        self._note_slots_changed()
        self._close_requested.emit()

    def shutdown(self) -> None:
        self.close()
        self._thread.quit()
        self._thread.wait()

    def request_render(
        self,
        pipeline: Pipeline,
        window: ClipRange,
        replicate: Replicate | None = None,
        consumer: Consumer | None = None,
    ) -> bool:
        if not self._opened or self._paused or not pipeline.nodes:
            return False
        if not self._ticked and self._armed_at is None:
            self._armed_at = perf_counter()
        self._submit(
            self._request(
                revision=self._next_revision(),
                pipeline=pipeline,
                window=window,
                replicate=replicate,
                consumer=consumer,
            )
        )
        return True

    def request_frame(
        self,
        pipeline: Pipeline,
        index: int,
        replicate: Replicate | None = None,
        consumer: Consumer | None = None,
    ) -> bool:
        if not self._opened or self._paused or not pipeline.nodes:
            return False
        self._submit(
            self._request(
                revision=self._next_revision(),
                pipeline=pipeline,
                window=ClipRange(start=index, end=index + 1),
                replicate=replicate,
                consumer=consumer,
                frame_index=index,
            )
        )
        return True

    def _request(
        self,
        *,
        revision: int,
        pipeline: Pipeline,
        window: ClipRange,
        replicate: Replicate | None,
        consumer: Consumer | None,
        frame_index: int | None = None,
    ) -> RenderRequest:
        return RenderRequest(
            revision=revision,
            pipeline=pipeline,
            window=window,
            replicate=replicate,
            luma=not graph_needs_chroma(pipeline, self._registry),
            consumer=consumer,
            frame_index=frame_index,
        )

    def _next_revision(self) -> int:
        self._revision += 1
        self._wanted.set(self._revision)
        return self._revision

    def _submit(self, request: RenderRequest) -> None:
        if self._in_flight is None:
            self._issue(request)
        else:
            self._pending = request
        self._note_slots_changed()

    def _issue(self, request: RenderRequest) -> None:
        self._in_flight = request
        self.render_started.emit(request.revision)
        self._render_requested.emit(request)

    def _settle(self, revision: int) -> None:
        if self._in_flight is None or self._in_flight.revision != revision:
            return
        self._in_flight = None
        pending, self._pending = self._pending, None
        if pending is not None:
            self._issue(pending)
        self._note_slots_changed()

    def _note_slots_changed(self) -> None:
        active = any(
            request is not None and request.frame_index is None
            for request in (self._in_flight, self._pending)
        )
        if active != self._window_render_active:
            self._window_render_active = active
            self.window_render_changed.emit(active)

    def _is_current(self, revision: int) -> bool:
        return revision == self._revision

    @Slot()
    def _on_opened(self) -> None:
        self._opened = True
        self.opened.emit()

    @Slot(str)
    def _on_open_failed(self, message: str) -> None:
        self._opened = False
        self.open_failed.emit(message)

    @Slot(int, int, float)
    def _on_frame_timed(self, revision: int, index: int, elapsed_ms: float) -> None:
        if not self._is_current(revision):
            return
        if self._armed_at is not None:
            self._metrics.publish(
                FIRST_TICK_BUDGET, (perf_counter() - self._armed_at) * 1000.0
            )
            self._armed_at = None
            self._ticked = True
        self.frame_cost.emit(index, elapsed_ms)

    @Slot(int, object)
    def _on_render_finished(self, revision: int, rendered: PreviewRender) -> None:
        if self._is_current(revision):
            self.render_finished.emit(rendered)
        self._settle(revision)

    @Slot(int, str)
    def _on_render_failed(self, revision: int, message: str) -> None:
        if self._is_current(revision):
            self.render_failed.emit(message)
        self._settle(revision)

    @Slot(int)
    def _on_render_abandoned(self, revision: int) -> None:
        self._settle(revision)
