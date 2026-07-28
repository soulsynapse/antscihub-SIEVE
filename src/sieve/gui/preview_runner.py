"""The GUI's producer of graph timings: a `PreviewSession` on a thread of its own.

`pipeline/preview.py` is a plain synchronous call by design, and its docstring
says what it owes an interactive caller: hold one render in flight and one
pending, run them off the event loop, and drop the answer to a render nobody
would have seen. This is the caller that does that. It is also the first thing
in `gui/` that computes a frame at all — before it, the application decoded
video and drew boxes on it, and the graph a project carried was displayed
nowhere.

**Per-frame cost, keyed by source index.** The bus carries whole-render spans:
`slider_to_preview` for the first frame and `full_preview_render` for all of
them, both published by `pipeline/preview.py` through the `measure` this hands
it. Those are the ceilings, and they are not a graph — two numbers per render
cannot show a user *where* in their representative clip the expensive frames
are, which is the question VISION step 4's live graph is asked. So this times
each frame as it is delivered and emits `(revision, source index, ms)`,
which is a series over the working window with the playhead as its cursor. The
bus is not the vehicle for it: a budget key is a named ceiling, and six hundred
frames are six hundred samples of one interval that has no ceiling of its own.

**`filter_to_first_tick` is published from the GUI thread, not from the render.**
The budget is "First filter → first graph tick", and a tick the user has not
been handed is not a tick. The interval therefore starts when a non-empty graph
is first submitted and ends when the first per-frame sample has crossed the
queued connection and arrived here — so it contains the render, the thread hop,
and the event loop's willingness to run, which is the whole of what the user
waits through. Measuring it inside the worker would report a number that is
correct about the render and silent about the two things most able to make it
feel slow.

**Two slots, latest wins, and deliberately not `RequestCoalescer`.** That class
ranks a commitment over a guess, because a released slider must not be displaced
by a later drag position. A render has no such pair: there is one desired graph
at any moment and it is always the most recent one, so importing the rank rule
would mean inventing a kind for every request and picking one arbitrarily. What
is shared is the shape — one in flight, one pending, later overwrites — and the
monotonic display rule, which arrives here as a revision number: anything
arriving for a revision that is no longer the newest is dropped on this side,
whatever the worker managed to finish.

**Cancellation is an exception out of the consumer, because that is the only
hook there is.** `execute` is a generator and `render_window` drives it to
exhaustion; nothing in `pipeline/` takes a cancel flag, and adding one would put
a GUI's impatience into the module a cluster runs. Raising from `on_frame`
abandons the iterator at the frame boundary, which is `executor.py`'s own stated
cancellation, and it has a second property worth having: `MetricBus.measure`
publishes nothing for a block that raises, so an abandoned render does not put a
truncated `full_preview_render` into the series the 3 s ceiling is judged on.

**What the two threads share is the newest revision, not a cancel flag.** A flag
has to be raised by one thread and lowered by the other, and there is no safe
moment for the lowering: the GUI thread cannot lower it when it issues the next
render, because the worker may not have reached the frame boundary where it
would have seen it raised, and the worker cannot lower it on entry, because a
request superseded while it sat in the queue would then run in full. A number
each side only ever *compares* has no such moment — the worker abandons exactly
when the revision it is rendering is no longer the newest, which is the same
question `_is_current` asks on the other side, asked in the one place that can
still act on the answer.

**The store outlives every revision, and that is the point.** One
`PreviewSession` per source, kept while the user tunes, because the whole claim
of `pipeline/preview.py` is that the second render after an edit pays only for
the nodes below it — 3.3 ms against a cold 1350. A runner that rebuilt the
session per render would be measuring a cold cache every time and would report
that tuning is a thousand times more expensive than it is.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import perf_counter

from pydantic import ValidationError
from PySide6.QtCore import QObject, QThread, Signal, Slot

from sieve.backend.dispatch import Backend, KernelRegistry, NoKernelError
from sieve.bench.metrics import METRICS, MetricBus
from sieve.core.filter_registry import FilterRegistry
from sieve.core.pipeline_model import ClipRange, CropArtifact, Pipeline
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

#: The budget this module exists to give a producer. A literal for the reason
#: `pipeline/preview.py` uses literals — except here it is not a layering
#: constraint but the same discipline: `MetricBus.publish` refusing an unknown
#: key is what turns a misspelling into a failure rather than a dead metric.
FIRST_TICK_BUDGET = "filter_to_first_tick"


class _AbandonedError(Exception):
    """Raised out of the frame consumer to drop a render that is no longer wanted.

    Private and deliberately not derived from anything `pipeline/` raises: it
    travels through `render_window`, which catches nothing, and it must not be
    mistaken for a graph that failed.
    """


class _Wanted:
    """The newest revision, read by the render thread and written by the GUI's.

    A guarded integer rather than a bare attribute. Assignment to an `int`
    happens to be atomic in CPython today, and a shared mutable that is correct
    by accident of the interpreter is the kind of thing that is still there
    when the accident stops holding.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._revision = 0

    def set(self, revision: int) -> None:
        """Declare `revision` the only one still worth rendering."""
        with self._lock:
            self._revision = revision

    def is_current(self, revision: int) -> bool:
        """Whether `revision` is still the newest. Asked once per frame."""
        with self._lock:
            return revision == self._revision


@dataclass(frozen=True, slots=True)
class RenderRequest:
    """One submitted render. Crosses to the worker thread whole.

    `revision` is the ordering, and it is the request's rather than the worker's
    so that a result can be judged stale on the GUI thread without asking the
    worker what it is doing — which is a question whose answer is out of date by
    the time it is delivered.
    """

    revision: int
    pipeline: Pipeline
    window: ClipRange
    replicate: Replicate | None
    #: Called with every `FrameResult` **on the render thread**, inside the
    #: timed spans and after the staleness check — so a superseded render's
    #: frames never reach it. This is how a series consumer (the detector's
    #: `SeriesCollector`) sees node outputs without them crossing a queued
    #: signal as six hundred separate events. It must be cheap and must not
    #: touch Qt widgets; heavy work belongs after `render_finished`.
    consumer: Consumer | None = None
    #: When set, render this single source frame instead of the window — the
    #: 100 ms `render_frame` path, which is what a wizard's hover-preview and
    #: a paused-playhead repaint ask for.
    frame_index: int | None = None


@dataclass(frozen=True, slots=True)
class _Crops:
    """The project's crop artifacts, as the render thread sees them.

    A value crossing a queued signal rather than a reference to the document,
    for `RenderRequest`'s reason: the worker must not read a model the GUI
    thread is free to replace underneath it. Records are frozen pydantic models
    and the tuple is a snapshot, so what arrives is what was true at the moment
    the project was adopted or saved.
    """

    records: tuple[CropArtifact, ...]
    #: What `CropArtifact.path` is relative to — the project file's directory.
    project_dir: Path


class _RenderWorker(QObject):
    """Lives on the render thread. Every slot here runs off the GUI thread.

    Holds the reader and the session, because both are unsafe to touch from two
    threads and this is the only thread that touches them.
    """

    opened = Signal()
    open_failed = Signal(str)
    #: `(revision, source frame index, milliseconds)` for one delivered frame.
    frame_timed = Signal(int, int, float)
    #: `(revision, PreviewRender)`.
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
    ) -> None:
        super().__init__()
        self._wanted = wanted
        self._ring = ring
        self._bus = bus
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
        """Open the footage a preview will read, or say why not.

        The identity string is computed by the caller and handed over rather
        than derived here, because `source_identity` stats the file and a
        `stat` that fails is a message about the project — which the GUI thread
        is where anything can be said about.

        **What this opens is one capture, and it closes it again.** The reader a
        render uses is a pool of captures in a format only the graph can
        decide (`_reader_for`), and no graph exists yet — a project's footage
        loads before its chain resolves. Building the real reader here would mean
        building it in whichever format was guessed and then rebuilding it on the
        first render, which is the N-capture open paid twice on every source.

        So this validates and reports, which is what `opened` promises and all
        the GUI does with it: a file that cannot be decoded says so now rather
        than at the first render, when the message would arrive as a failed graph.
        """
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
        """Render `request`'s window, timing and emitting each frame as it lands.

        Every deliberate refusal `pipeline/preview.py` documents is caught and
        reported as a string. They are the same five `sieve preview` catches and
        for the same reason: each names something about the graph, the
        parameters, or the machine that a user can act on, and a traceback on a
        worker thread would reach nobody at all.
        """
        session = self._session_for(request)
        if session is None:
            return

        # A window render's frontier starts from nothing; a single-frame
        # refresh is not a render filling and must not move it.
        window_render = request.frame_index is None
        if window_render:
            self._ring.begin()

        started = perf_counter()
        previous = started

        def on_frame(result: FrameResult) -> None:
            nonlocal previous
            # Checked before the consumer and the emit, so a render abandoned
            # between two frames contributes nothing at all rather than a
            # truncated series.
            if not self._wanted.is_current(request.revision):
                raise _AbandonedError
            # The proxy is made here, on the render thread, where the pixels
            # already are — a resize in front of every repaint would put the
            # cost on the GUI thread instead. `source` is None exactly when
            # the store served every root, which is the warm re-render where
            # there was no decode to share.
            #
            # `source_cropped` is the other refusal, and it is a rule 6 one:
            # a render served from a crop artifact never decodes the whole
            # frame, so what it could offer the ring is one arena's region.
            # The pane that plays these frames draws replicate boxes over them
            # in source coordinates — a crop there is not a smaller picture,
            # it is the wrong picture — and the contention render-fed playback
            # exists to remove is already gone for a crop-served render, which
            # touches the parent not at all. So the player decodes for itself,
            # exactly as it did before the ring existed. Same shape as the
            # ring's own refusal of chroma: decline, never convert.
            if window_render and result.source is not None and not result.source_cropped:
                self._ring.put(result.source)
            if request.consumer is not None:
                request.consumer(result)
            now = perf_counter()
            self.frame_timed.emit(request.revision, result.index, (now - previous) * 1000.0)
            previous = now

        try:
            if request.frame_index is None:
                rendered = session.render_window(request.pipeline, on_frame)
            else:
                rendered = session.render_frame(request.pipeline, request.frame_index, on_frame)
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
        """Drop the session and stop the decode threads. Idempotent.

        The ring again, though the runner already cleared it on its thread:
        this queued slot runs after any in-flight render has aborted, so it
        sweeps up a frame that slipped past the revision check in the same
        instant the GUI thread was clearing.
        """
        self._ring.clear()
        self._session = None
        self._path = None
        self._crops = None
        self._resolved = None
        if self._reader is not None:
            self._reader.close()
            self._reader = None

    @Slot(object)
    def set_crops(self, crops: _Crops) -> None:
        """Adopt the project's crop records. Takes effect on the next render.

        Not applied to the session in flight: resolution happens where a render
        is planned, and a record arriving mid-render must not change which file
        the remaining frames come from. The next `_session_for` sees it, which
        is at most one render away.
        """
        self._crops = crops

    def _resolve(self, request: RenderRequest) -> ResolvedSource | None:
        """Which file this request reads: a crop artifact for its arena, or the parent.

        `pipeline/resolve_source.py`'s one step, asked once per render on the
        thread that owns the reader. It is asked against the *request's* window
        rather than the project's clip, because that is what is about to be
        decoded — a hover outside what was cut falls back to the parent instead
        of asking the artifact for a frame it does not hold.
        """
        if self._path is None:
            return None
        crops = self._crops
        return resolve(
            () if crops is None else crops.records,
            request.replicate,
            project_dir=self._path.parent if crops is None else crops.project_dir,
            parent=self._path,
            parent_identity=self._source,
            luma=not graph_needs_chroma(request.pipeline, self._registry),
            want=request.window,
        )

    def _reader_for(
        self, request: RenderRequest, resolved: ResolvedSource
    ) -> PrefetchFrameSource | None:
        """The reader over the resolved file in the format this graph wants.

        The decode format is a property of the graph (`Dag.needs_chroma`), so it
        is not knowable at `open` and this is the first place it is. Built here
        on the first render, and rebuilt if a later graph disagrees — which must
        not be left to drift, because `source_key` hashes the format and a reader
        handing BGR to a graph keyed for luma would fill the store with entries
        labelled as something they are not.

        The *file* can change too, and for one reason: the selected arena moved
        to one that a crop artifact backs, or away from one. That is a rebuild
        on the same terms — a reader is bound to a path as firmly as to a
        format, and serving frame `i` of an artifact where the keys say frame
        `i` of the parent is the wrong-pixels failure with no symptom.

        A rebuild is expensive (one capture per preview worker). Format
        rebuilds are unreachable today, since nothing on the shelf declares a
        chroma-only input; file rebuilds are reachable the moment a session has
        one backed arena and one unbacked one, and are paid back within a render
        (0.09 ms/frame against 9.93). The session goes with the reader: its
        store holds frames keyed under a root the new file does not share.

        The comparison is on `identity` rather than on `path`, so footage
        replaced under the same name rebuilds too — `source_identity` is what
        every key is rooted in, and a reader outliving it would serve the new
        file's pixels under the old file's keys.
        """
        luma = not graph_needs_chroma(request.pipeline, self._registry)
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
            # The resolved split, not the declared constant: on an allocation
            # smaller than the reference class the preview's pool degrades
            # before the player's does (`concurrency.resolve_worker_split`).
            reader = PrefetchFrameSource(
                resolved.path, workers=resolve_worker_split().preview, luma=luma
            )
        except VideoDecodeError as error:
            self.render_failed.emit(request.revision, str(error))
            return None
        self._reader = reader
        self._resolved = resolved
        return reader

    def _session_for(self, request: RenderRequest) -> PreviewSession | None:
        """This source's session, built on first use and re-aimed after that.

        Built lazily because a session is constructed over a window and the
        window is not known until something asks for a render — and re-aimed
        rather than rebuilt because the store is the whole reason a second
        render is cheap. `set_window` and `set_replicate` both keep every
        entry; see `pipeline/preview.py` for why each of them can.

        Re-aiming stops being legal when the resolved file changes, and
        `_reader_for` has already dropped the session in that case: a session
        over a crop artifact is a session over *one* arena's pixels, so
        `set_replicate` on it would run the new arena's parameters over the old
        arena's footage.
        """
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
    """Renders the working window off the event loop and reports what each frame cost.

    Construct on the GUI thread. Owns the render thread for its whole life, so
    `shutdown` is required before the application exits for the same reason
    `VideoPlayer.shutdown` is.
    """

    #: `(source frame index, milliseconds)` for one frame of the newest render.
    #: The series a graph is drawn from; the playhead is its cursor.
    frame_cost = Signal(int, float)
    #: A new revision is about to produce frames. A consumer clears its series.
    render_started = Signal(int)
    #: The newest render completed. Carries the `PreviewRender`, which holds the
    #: plan, the frame count, and the store's reuse share.
    render_finished = Signal(object)
    #: The newest render was refused, with the reason as the user can read it.
    render_failed = Signal(str)
    #: Footage is loaded and renders will now be accepted. Worth a signal
    #: because `open` is asynchronous: a project's graph is in the document
    #: before the reader exists, so the window that submits on a graph change
    #: alone would submit once, be refused, and never try again.
    opened = Signal()
    #: The footage could not be opened for previewing.
    open_failed = Signal(str)
    #: A *window* render is outstanding (in flight or pending), or none is any
    #: more. Single-frame renders — composite refreshes, wizard hovers — do not
    #: count: they are over in ~100 ms and arrive one at a time, and a consumer
    #: treating them as "a render is filling" would flap once per playhead
    #: move. This is what the viewport's auto-gray policy listens to.
    window_render_changed = Signal(bool)

    _open_requested = Signal(str, str)
    _render_requested = Signal(RenderRequest)
    _crops_requested = Signal(object)
    _close_requested = Signal()

    def __init__(
        self,
        parent: QObject | None = None,
        *,
        metrics: MetricBus | None = None,
        backend: Backend = Backend.CPU,
        registry: FilterRegistry | None = None,
        kernels: KernelRegistry | None = None,
    ) -> None:
        """Start the render thread.

        Args:
            parent: Owner.
            metrics: Where `filter_to_first_tick` is published and where
                `pipeline/preview.py`'s two spans go. Injectable for
                `gui/player.py`'s reason: a test asserting on what was published
                must not hear the process-wide bus.
            backend: Where every node of every preview runs.
            registry: The filter shelf graphs resolve against. `None` is the
                process-wide one, which is what the application uses.
            kernels: The kernel shelf nodes are bound through. Both are here so
                that the ordering properties this module is built around —
                which render is abandoned, which revision's frames are
                forwarded — can be exercised against a kernel whose duration a
                test chooses. Against the real shelf they cannot: `downsample`
                over the synthetic fixture finishes faster than a test can
                supersede it, so the abandon path would be pinned by a race
                that passes on a slow machine and passes on a fast one for the
                opposite reason.
        """
        super().__init__(parent)
        # Before any graph can resolve. Idempotent, and here rather than in
        # `app.py` so that a runner constructed by a test has a populated shelf
        # without the test knowing it had to arrange one.
        discover()

        self._metrics = METRICS if metrics is None else metrics
        self._opened = False
        self._revision = 0
        self._in_flight: RenderRequest | None = None
        self._pending: RenderRequest | None = None
        self._window_render_active = False

        # The one thing both threads touch. Written here on every submission
        # and on every close, read by the worker once per frame.
        self._wanted = _Wanted()
        # The other thing both threads touch, and it carries its own lock:
        # the worker writes a proxy of every source frame a window render
        # decodes, and the player reads them back instead of decoding the
        # same file again (`gui/render_ring.py`).
        self._ring = RenderFrameRing()

        # When a non-empty graph was first submitted for this source, and
        # whether anything has ticked since. `None` means nothing is being
        # timed: either no graph has arrived yet or the first tick already went
        # out, and both are states in which publishing would be wrong.
        self._armed_at: float | None = None
        self._ticked = False

        self._thread = QThread()
        self._thread.setObjectName("sieve-preview")
        self._worker = _RenderWorker(
            self._wanted, self._ring, self._metrics, backend, registry, kernels
        )
        self._worker.moveToThread(self._thread)

        self._open_requested.connect(self._worker.open)
        self._render_requested.connect(self._worker.render)
        self._crops_requested.connect(self._worker.set_crops)
        self._close_requested.connect(self._worker.close)
        self._worker.opened.connect(self._on_opened)
        self._worker.open_failed.connect(self._on_open_failed)
        self._worker.frame_timed.connect(self._on_frame_timed)
        self._worker.render_finished.connect(self._on_render_finished)
        self._worker.render_failed.connect(self._on_render_failed)
        self._worker.render_abandoned.connect(self._on_render_abandoned)

        self._thread.start()

    # ---- state -----------------------------------------------------------

    @property
    def is_open(self) -> bool:
        """Whether footage is loaded and a render can be asked for."""
        return self._opened

    @property
    def ring(self) -> RenderFrameRing:
        """The render's recent source frames, for the player to play from."""
        return self._ring

    @property
    def revision(self) -> int:
        """The newest submitted render. Anything older is dropped on arrival."""
        return self._revision

    @property
    def window_render_active(self) -> bool:
        """Whether a window render is outstanding. `window_render_changed`'s state."""
        return self._window_render_active

    @property
    def has_ticked(self) -> bool:
        """Whether this source has delivered a first frame since a graph appeared.

        The `filter_to_first_tick` arm. False again after `close`, because the
        budget is about a session and the next video starts one.
        """
        return self._ticked

    # ---- lifecycle -------------------------------------------------------

    def open(self, video: Path) -> None:
        """Load `video` for previewing. `open_failed` follows if it cannot be.

        The identity is taken here, on the GUI thread, so that footage the
        project points at but the filesystem does not have is refused with a
        message rather than by a worker with nowhere to put one.
        """
        self.close()
        try:
            source = source_identity(video)
        except OSError:
            self.open_failed.emit(f"cannot preview footage that is not there: {video}")
            return
        self._open_requested.emit(str(video), source)

    def set_crops(self, crops: tuple[CropArtifact, ...], project_dir: Path) -> None:
        """Declare the crop artifacts renders of this footage may be served from.

        Call after adopting or saving a project — those are the two moments
        `Project.crops` changes, and the runner is told rather than asked
        because it holds no reference to the document (`gui/document.py` is a
        GUI-thread model and this is a worker's input).

        A replicate whose record matches is rendered from its crop from the next
        render onward, which is 107x cheaper per frame and re-keys once. No
        record and no match are the same thing here, and both leave every path
        exactly as it was.
        """
        self._crops_requested.emit(_Crops(records=crops, project_dir=project_dir))

    def close(self) -> None:
        """Unload the footage and forget everything about this source's session.

        The in-flight render goes with it. It cannot be recalled — the worker is
        inside `render_window` — so what stops its frames being plotted into the
        next video's graph is the revision they carry, exactly as the stamp on a
        decode request stops a closed video's frame being painted.
        """
        self._opened = False
        self._in_flight = None
        self._pending = None
        self._armed_at = None
        self._ticked = False
        # Bumped with nothing issued at it, which is what abandons the render
        # still running: no revision is current, so its next frame boundary is
        # its last.
        self._revision += 1
        self._wanted.set(self._revision)
        # After the bump, so the abandoned render cannot refill what is being
        # emptied: its next `on_frame` raises before it reaches the ring. The
        # ring is index-keyed with no source identity, so frames of the video
        # being closed must not survive into the next one's playback.
        self._ring.clear()
        self._note_slots_changed()
        self._close_requested.emit()

    def shutdown(self) -> None:
        """Stop the render thread. Call before the application exits."""
        self.close()
        self._thread.quit()
        self._thread.wait()

    # ---- rendering -------------------------------------------------------

    def request_render(
        self,
        pipeline: Pipeline,
        window: ClipRange,
        replicate: Replicate | None = None,
        consumer: Consumer | None = None,
    ) -> bool:
        """Render `window` through `pipeline`, superseding anything outstanding.

        Returns whether anything was submitted. An empty graph is refused rather
        than run: with no nodes the executor still decodes the whole window to
        produce a result carrying no outputs, which is a second decode of
        footage the player has already got, for a graph that has nothing to say
        about it. It is also what makes "first filter" a real event — the arm
        below is exactly the moment the answer to this stops being `False`.

        `consumer` receives every `FrameResult` **on the render thread**; see
        `RenderRequest.consumer` for the contract. Pair it with a
        `SeriesCollector` started from `render_started` to assemble a series.
        """
        if not self._opened or not pipeline.nodes:
            return False

        if not self._ticked and self._armed_at is None:
            self._armed_at = perf_counter()

        self._submit(
            RenderRequest(
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
        """Render the single source frame `index` — the 100 ms path.

        Same submission machinery as `request_render` (latest wins, so a hover
        that outruns its renders never queues more than one), but deliberately
        not the `filter_to_first_tick` arm: a wizard's hover-preview is not
        the tab's first graph tick, and arming here would publish a number
        about the wrong interval.
        """
        if not self._opened or not pipeline.nodes:
            return False
        self._submit(
            RenderRequest(
                revision=self._next_revision(),
                pipeline=pipeline,
                window=ClipRange(start=index, end=index + 1),
                replicate=replicate,
                consumer=consumer,
                frame_index=index,
            )
        )
        return True

    def _next_revision(self) -> int:
        """Bump and declare the newest revision.

        Before the request is built: declaring the new revision is what
        abandons an in-flight one, and it is also what a request that goes
        straight out needs true before the worker reads its first frame.
        """
        self._revision += 1
        self._wanted.set(self._revision)
        return self._revision

    def _submit(self, request: RenderRequest) -> None:
        if self._in_flight is None:
            self._issue(request)
        else:
            # The worker notices at its next frame boundary and reports back;
            # `_settle` is what issues this.
            self._pending = request
        self._note_slots_changed()

    def _issue(self, request: RenderRequest) -> None:
        self._in_flight = request
        self.render_started.emit(request.revision)
        self._render_requested.emit(request)

    def _settle(self, revision: int) -> None:
        """One render has reported back. Free the slot and issue what waited.

        Guarded by revision because `close` clears the slot under a render that
        is still running: without the check, the result that then arrives would
        release a slot the next source's first render already holds.
        """
        if self._in_flight is None or self._in_flight.revision != revision:
            return
        self._in_flight = None
        pending, self._pending = self._pending, None
        if pending is not None:
            self._issue(pending)
        self._note_slots_changed()

    def _note_slots_changed(self) -> None:
        """Recompute whether a window render is outstanding, announcing a flip.

        Derived from the two slots rather than kept as its own state machine:
        every path that starts, supersedes, finishes, fails, abandons, or
        closes a render already mutates the slots, so reading them is the one
        way this cannot drift from what the worker is actually doing.
        """
        active = any(
            request is not None and request.frame_index is None
            for request in (self._in_flight, self._pending)
        )
        if active != self._window_render_active:
            self._window_render_active = active
            self.window_render_changed.emit(active)

    def _is_current(self, revision: int) -> bool:
        """Whether anything arriving for `revision` is still worth forwarding."""
        return revision == self._revision

    # ---- worker feedback -------------------------------------------------

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
        """A frame's cost, on the GUI thread. The first one is the tick.

        The tick is published before the sample is forwarded, so a consumer that
        repaints on `frame_cost` is not inside the interval the budget names.
        That ordering is the same one `bench/metrics.py` keeps for its own
        subscribers, and it matters more here: a HUD's first paint builds axes
        and is the slowest one it will ever do.
        """
        if not self._is_current(revision):
            return
        if self._armed_at is not None:
            self._metrics.publish(FIRST_TICK_BUDGET, (perf_counter() - self._armed_at) * 1000.0)
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
        """A render dropped itself mid-window. Nothing to report, only a slot to free."""
        self._settle(revision)
