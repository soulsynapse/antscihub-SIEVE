"""The representative-clip preview: one window, one arena, many revisions.

A `PreviewSession` is what the tuning loop of VISION step 4 runs on. It holds
everything about a preview that does not change while a user drags a slider —
the footage, the working window, the replicate, the backend, and the store — and
takes the graph fresh on every render, because the graph is the only thing an
edit changes.

**A parameter edit invalidates a suffix of the graph, not the graph, and there
is no code here that does it.** That is the whole reason this is a module rather
than a loop in the GUI, and the mechanism is the store outliving the revision:
`cache_key.node_key` folds its upstreams' keys in, so editing the third node of
four leaves the first two keyed exactly as they were and gives the last two keys
nothing has ever written. Re-rendering therefore serves the head from the store
and computes the tail, without anything having to walk the graph deciding what
to drop. A deliberate `invalidate(node_id)` here would be a second answer to
what a key covers, and the two answers would disagree silently — the first
symptom being a preview that shows a stale head after an edit, which looks like
a repaint bug.

The consequence worth stating, because it is what the 3 s budget rests on: on a
re-render the roots hit the store, `execute` fetches a source frame only on the
first root that misses, and so an edit below the roots decodes *nothing*. A
preview that re-ran from the source on every edit would meet the budget on the
one filter that existed when this was written and miss it on the third.

**The window is not in any key, so moving it keeps every entry.** `cache.py`
keys by `(node key, source frame index)` precisely so that a partial entry is an
ordinary state; a session whose window slides two seconds later finds every
frame the old window shared with the new one and computes only the difference.
`set_window` therefore does not clear anything, and a session that cleared its
store on a window change would pay for the whole clip again to show the user a
span they had already tuned.

**Instrumented by construction.** `measure` is required rather than defaulted,
because a preview that reports no timings cannot say whether it works —
`slider_to_preview` (100 ms) and `full_preview_render` (3 s) *are* the claim.
It is a callable and not a `MetricBus` for a layering reason and not a taste
one: `sieve.bench` sits *above* `sieve.pipeline`, so this module may not import
the budget table it is measured against. The two keys below are therefore
literals, and `MetricBus.publish` refusing an unknown key is what turns a
misspelling into a first-render failure instead of an unwatched metric.
`tests/unit/test_preview.py` checks both against `BUDGETS` from a layer that may
see it.

**Nothing here coalesces, and the reason is the same boundary.**
`gui/coalescer.py` is Qt-free but lives in `sieve.gui`, above this layer, which
is correct: coalescing exists because a human is dragging something, and
`sieve preview` renders once and has nothing to discard. What this module owes
the interactive caller is that a render is a plain synchronous call with no
state of its own beyond the store — so the caller can hold one in flight and one
pending, run them on a worker thread, and drop the answer to a render nobody
would have seen, which is exactly the discipline `RequestCoalescer` already
implements against frame requests.

**The store is the caller's, and nothing here bounds it.** Each revision of an
edited node writes a fresh key per frame, so a long tuning session's store grows
with the number of edits and no entry is ever dropped. That is `cache.py`'s
deferral, not a new one — a bound picked here would be picked from nothing — and
the exact remedy is that the dead keys after an edit are *knowable* (the old
revision's keys, minus the new revision's) rather than a policy, so eviction
when it arrives is garbage collection and not a heuristic. Until it is measured,
a session over a cropped arena at preview resolution is small and a session over
a full-resolution window is `materialize.py`'s problem.

**A stateful node makes the anchor render cost the lead-in.** `render_frame` is
the 100 ms path, and it is 100 ms because the frames above the anchor come from
the store. A stateful node has no key at all
(`docs/findings/2026.07.26-stateful-output-is-not-keyed-by-what-it-is.md`), so a
graph containing one decodes and runs its whole `lead_in` on every single render
— 90 frames for `background_ema`. Nothing here can fix that, and it is not a
defect in this module: it is the price of the category, and the thing that will
pay it down is a materialized checkpoint upstream of the stateful node.
"""

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

#: How a span is timed and published. `MetricBus.measure` is one, and is what
#: every real caller passes; a test passes something that records the keys and
#: the nesting. A context manager rather than a `(key, elapsed_ms)` callback so
#: that the clock arithmetic stays in the one module that owns it — see
#: `bench/metrics.py`, which this layer may not import.
Measure = Callable[[str], AbstractContextManager[None]]

#: What the caller does with each previewed frame, in span order. Called on
#: whatever thread the render is running on.
Consumer = Callable[[FrameResult], None]

#: The interval from the start of a render to its first frame being delivered.
#: A literal because the budget table is one layer up; see the module docstring.
FIRST_FRAME_BUDGET = "slider_to_preview"

#: The interval covering a whole window render, first frame included — which is
#: why `bench/metrics.py` says nesting has to work.
WHOLE_WINDOW_BUDGET = "full_preview_render"


@dataclass(frozen=True, slots=True)
class PreviewRender:
    """What one render did, in units a HUD and a gate both read.

    Carries the `ExecutionPlan` rather than copies out of it: the span, the
    lead-in, the shortfall, and every node's key are all on the plan already,
    and a summary that restated them would be a second description of the run
    that produced it.
    """

    plan: ExecutionPlan
    #: Frames delivered to the consumer. The span's length, unless the reader
    #: ran out of footage.
    frames: int
    #: Node outputs computed by a kernel.
    computed: int
    #: Node outputs served from the store. This number moving is the whole
    #: subject of the module docstring.
    from_cache: int

    @property
    def span(self) -> ClipRange:
        """The frames this render covered."""
        return self.plan.span

    @property
    def reuse(self) -> float:
        """Share of node outputs served from the store, from 0.0 to 1.0.

        Zero for a render that computed nothing at all, which is a graph with no
        nodes rather than a cache that failed — reporting it as perfect reuse
        would make an empty graph the best-performing one in the table.
        """
        total = self.computed + self.from_cache
        return 0.0 if total == 0 else self.from_cache / total


class PreviewSession:
    """One asset, one window, one arena, one store — and a graph per render.

    Long-lived: constructed when a project opens and kept while the user tunes,
    because the store is the thing that makes the second render cheap and a
    session per render would throw it away. Everything a render needs that *is*
    allowed to change between renders is either an argument to the render or
    goes through a setter that says what it costs.

    Not thread-safe, and deliberately unguarded: a caller that renders on a
    worker thread already has to hold one render in flight at a time to get
    coalescing right, and a lock here would make that discipline look optional
    while doing nothing about two renders sharing one background model.
    """

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
    ) -> None:
        """Open a preview over `window` of the footage `reader` reads.

        Args:
            source: What identifies the footage — `cache_key.source_identity`
                builds one. A string for that function's reason: this module
                never opens a container either.
            reader: Where source frames come from. A `FrameSource`, so a run
                over a materialized crop is this same session with a different
                argument rather than a mode.
            window: The span to preview, in source indices.
                `ReplicateDocument.window` is what the GUI passes; it exists so
                this does not have to invent a span.
            measure: How a timed span is published. Required — see the module
                docstring. `MetricBus.measure` is the real one.
            replicate: The arena being previewed, or `None` for the whole frame.
                One rather than all of them: a preview is one viewport, and the
                fan-out belongs to a run.
            backend: Where every node runs.
            store: Where computed frames are kept between renders. Defaults to a
                fresh `MemoryFrameStore`, because a preview whose store kept
                nothing would re-run the whole graph on every edit and miss the
                budget it exists to hold — the opposite of `execute`'s default,
                and for the reason that makes that one right too: the caller
                that has not thought about caching gets what it obviously meant.
            registry: The filter shelf graphs resolve against.
            kernels: The kernel shelf nodes are bound through.
        """
        self._source = source
        self._reader = reader
        self._window = window
        self._measure = measure
        self._replicate = replicate
        self._backend = backend
        self._store = MemoryFrameStore() if store is None else store
        self._registry = registry
        self._kernels = kernels

    # ---- state -----------------------------------------------------------

    @property
    def window(self) -> ClipRange:
        """The span a full render covers."""
        return self._window

    @property
    def replicate(self) -> Replicate | None:
        """The arena being previewed, or None for the whole frame."""
        return self._replicate

    @property
    def store(self) -> FrameStore:
        """Where this session's computed frames live.

        Exposed so a HUD can report its size and a caller can clear it. Not so
        anything can look an entry up: the keys are the plan's, and a second
        place deriving one is the failure `cache_key.py` opens by naming.
        """
        return self._store

    def set_window(self, window: ClipRange) -> None:
        """Preview a different span of the same footage.

        Keeps every stored entry, and that is the point rather than an
        oversight: a key carries the node, the parameters, the ROI, and the
        backend, and never the span — so the frames the old and new windows
        share are already computed and the render after this one pays only for
        the difference. See the module docstring.
        """
        self._window = window

    def set_replicate(self, replicate: Replicate | None) -> None:
        """Preview a different arena of the same footage.

        Also keeps every entry, for a different reason: the ROI *is* in the key,
        so the new arena's entries are simply absent while the old arena's stay
        valid for the moment the user clicks back. Two arenas that cropped the
        same pixels share them, which is `equivalence_groups`' claim arriving
        here as a saving rather than as a report.
        """
        self._replicate = replicate

    # ---- renders ---------------------------------------------------------

    def render_window(self, pipeline: Pipeline, on_frame: Consumer | None = None) -> PreviewRender:
        """Run `pipeline` over the whole window, delivering frames in order.

        Publishes `FIRST_FRAME_BUDGET` around the first frame and
        `WHOLE_WINDOW_BUDGET` around all of them, nested. The first-frame span
        is inside the whole-render span rather than beside it because they are
        answers to two different questions about one render — when the user sees
        *something* and when the user has seen *everything* — and a render that
        met the second while missing the first would feel broken while measuring
        fine.

        Args:
            pipeline: The graph as it stands now. Taken per render rather than
                held, because an edit is the only thing that makes a re-render
                necessary and holding the graph would mean a caller could
                forget to say what changed.
            on_frame: Called with each frame as it is produced. `None` renders
                for the store and the timings alone, which is what a headless
                measurement wants.

        Returns:
            What the render did, including how much of it came from the store.

        Raises:
            GraphError: if the graph does not resolve, does not chain, or has a
                cycle. Raised rather than reported, because a caller editing a
                graph into an invalid state has to decide what to show for it
                and a `PreviewRender` describing no run would make that decision
                by omission.
            ValidationError: if any node's resolved parameters are invalid.
            UnrunnableNodeError: if a node cannot be called at all.
            NoKernelError: if a node has no kernel for this backend.
            VideoDecodeError: if a frame the render needs cannot be read.
        """
        return self._run(self._plan(pipeline, self._window), on_frame, whole=True)

    def render_frame(
        self, pipeline: Pipeline, index: int, on_frame: Consumer | None = None
    ) -> PreviewRender:
        """Run `pipeline` for the single source frame `index`.

        The 100 ms path: what a slider drag asks for, because re-rendering 600
        frames to show the one under the playhead is how a direct-manipulation
        control stops feeling direct. Publishes `FIRST_FRAME_BUDGET` only — for
        a one-frame render the first frame *is* the render, and publishing
        `WHOLE_WINDOW_BUDGET` for it too would put a cheap number into the
        series the 3 s ceiling is judged on and quietly improve its median.

        `index` need not be inside the window: the caller's playhead already is,
        and re-deriving that here would be a second definition of a bound
        `gui/player.py` owns.

        Raises:
            ValidationError: if `index` is negative — a span has to start
                somewhere real. Everything `render_window` raises, for the same
                reasons.
        """
        return self._run(
            self._plan(pipeline, ClipRange(start=index, end=index + 1)), on_frame, whole=False
        )

    # ---- internals -------------------------------------------------------

    def _plan(self, pipeline: Pipeline, span: ClipRange) -> ExecutionPlan:
        """Resolve and plan `pipeline` over `span` for this session's arena.

        Rebuilt per render, and cheap by construction: resolving nodes against
        the registry and hashing a parameter dict per node is arithmetic over
        the document, with no decode and no kernel call in it. Memoizing the
        last plan would save microseconds and introduce the question of whether
        two pipelines that compare equal are the same graph, which is a question
        with no upside here.
        """
        return ExecutionPlan.build(
            Dag.build(pipeline, self._registry),
            source=self._source,
            span=span,
            backend=self._backend,
            replicate=self._replicate,
        )

    def _run(self, plan: ExecutionPlan, on_frame: Consumer | None, *, whole: bool) -> PreviewRender:
        """Drive `execute` to exhaustion, timing the first frame and the rest.

        `execute` is a generator, so calling it does no work: everything —
        binding the kernels, refusing an uncallable node, decoding the lead-in,
        running the head of the graph — happens on the first `next` and is
        therefore inside the first-frame span. That is the honest boundary: a
        user who edits a parameter waits for all of it before seeing anything.

        The consumer is called inside the timed spans, matching what
        `gui/player.py` publishes for a scrub: the budget's label says "preview
        repaint", and a number that excluded the caller's paint would be a
        number about this module rather than about what the user waited for.
        """
        deliver = _discard if on_frame is None else on_frame
        tally = _Tally()
        with self._measure(WHOLE_WINDOW_BUDGET) if whole else nullcontext():
            stream = execute(plan, self._reader, store=self._store, kernels=self._kernels)
            with self._measure(FIRST_FRAME_BUDGET):
                # `ClipRange` cannot be empty and every index at or after
                # `span.start` is yielded, so there is a first frame whenever
                # the reader can supply it. A reader that cannot raises, which
                # is the caller's to handle rather than a shorter render.
                tally.add(next(stream), deliver)
            for result in stream:
                tally.add(result, deliver)
        return PreviewRender(
            plan=plan, frames=tally.frames, computed=tally.computed, from_cache=tally.from_cache
        )


class _Tally:
    """Running counts over one render, so `_run` holds no frame it has passed on.

    A class rather than three locals because `_run` counts in two places — the
    timed first frame and the loop after it — and two copies of the arithmetic
    is how `computed` and `from_cache` stop adding up to the same total.
    """

    def __init__(self) -> None:
        self.frames = 0
        self.computed = 0
        self.from_cache = 0

    def add(self, result: FrameResult, deliver: Consumer) -> None:
        """Count `result`'s node outputs, then hand it to the consumer."""
        self.frames += 1
        self.from_cache += len(result.from_cache)
        self.computed += len(result.outputs) - len(result.from_cache)
        deliver(result)


def _discard(result: FrameResult) -> None:
    """The consumer a render with no viewer uses.

    A function rather than `if on_frame is not None` at both call sites, for
    `NullFrameStore`'s reason: the absence of a consumer must not be a branch in
    the loop that both call sites share.
    """
    del result
