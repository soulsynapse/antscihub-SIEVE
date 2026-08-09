"""The preview session: one working window, one replicate, many revisions.

A `PreviewSession` is what the tuning loop of VISION step 4 runs on. It holds
everything about a preview that does not change while a user drags a slider —
the footage, the working window, the replicate, and the store — and takes the
graph fresh on every render, because the graph is the only thing an edit
changes.

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
one tool that existed when this was written and miss it on the third.

**The window is not in any key, so moving it keeps every entry.** `cache.py`
keys by `(node key, source frame index)` precisely so that a partial entry is an
ordinary state; a session whose window slides two seconds later finds every
frame the old window shared with the new one and computes only the difference.
`set_window` therefore does not clear anything, and a session that cleared its
store on a window change would pay for the whole stretch again to show the user
a span they had already tuned.

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

**A source root is resolved here, per render, and it is the one thing in this
module that touches the filesystem.** A root that opens its own file is keyed on
what that file is, so a session that did not resolve it hands the plan no
identity for it and `Dag.node_keys` leaves it — and everything below it — out of
the keys entirely. That is a whole chain recomputed on every drag, with correct
frames and no message, which is the tuning loop rather than an efficiency note.
Per render rather than per session because the graph arrives per render: an edit
that moves a picker's pattern moves the file it names, and an identity fixed when
the session opened would key the new file under the old one's name — the
wrong-answer-from-cache failure `cache_key.py` is written against. `sieve run`
resolves the same thing once, because a run has one graph.

**Nothing here coalesces, and the reason is a boundary that does not exist
yet.** Coalescing exists because a human is dragging something, and `sieve
preview` renders once and has nothing to discard — so it belongs to the
transport layer Phase 7 re-derives, above this one. What this module owes that
caller is that a render is a plain synchronous call with no state of its own
beyond the store, so one render can be held in flight and one pending on a
worker thread and the answer to a render nobody would have seen can be dropped.

**The store is the caller's, and nothing here bounds it.** Each revision of an
edited node writes a fresh key per frame, so a long tuning session's store grows
with the number of edits and no entry is ever dropped. That is `cache.py`'s
deferral, not a new one — a bound picked here would be picked from nothing — and
the exact remedy is that the dead keys after an edit are *knowable* (the old
revision's keys, minus the new revision's) rather than a policy, so eviction
when it arrives is garbage collection and not a heuristic.

**An epsilon-warmup node makes every render pay its lead-in.** `render_frame` is
the 100 ms path, and it is 100 ms because the frames above the anchor come from
the store. `cache_key.cache_policy` gives a node whose warmup is an epsilon no
key at all, so a graph containing one decodes and runs its whole lead-in on
every single render — 90 frames for `background_ema`. Nothing here can fix that,
and it is not a defect in this module: it is the price of a dependence that
never ends, and the thing that will pay it down is a materialized checkpoint
upstream of it. A node whose warmup is *bounded* pays only that warmup, once,
where a served range hands its state back (`executor._resettle`) — which is why
`block_signal` and `detect` are on the cheap side of this sentence and
`background_ema` is not.

**What v2 carried here and v3 does not.** A `backend` and a kernel shelf go with
`adr/no-kernel-apparatus.md`; a lowered decode prefix goes with the lowering
`PLAN.md` refuses to build until a budget is missed. The `pre_cropped` flag and
the artifact's own frame floor go together: under schema v1 a written crop is a
child source with an identity of its own, so a session over one is handed a
different `source` and a reader already renumbered by
`resolve_source.ResolvedSource.wrap`, and there is no flag left to carry.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass

from sieve.core.pipeline_model import Pipeline, Replicate, SourceSpan
from sieve.core.tool_registry import ToolRegistry
from sieve.pipeline.cache import FrameStore, MemoryFrameStore
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import FrameResult, FrameSource, execute
from sieve.pipeline.plan import ExecutionPlan, validated_params
from sieve.pipeline.resolve_source import picked_identities, source_files

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
    #: Node outputs computed by a tool.
    computed: int
    #: Node outputs served from the store. This number moving is the whole
    #: subject of the module docstring.
    from_cache: int

    @property
    def span(self) -> SourceSpan:
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
    """One asset, one window, one replicate, one store — and a graph per render.

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
        window: SourceSpan,
        measure: Measure,
        replicate: Replicate | None = None,
        store: FrameStore | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        """Open a preview over `window` of the footage `reader` reads.

        Args:
            source: What identifies the footage — `cache_key.source_identity`
                builds one. A string for that function's reason: this module
                never opens a container either.
            reader: Where source frames come from. A `FrameSource`, so a run
                over a written crop is this same session with a different
                argument rather than a mode.
            window: The span to preview, in source indices. Required, because
                "the whole video" is a fact about a container and nothing here
                opens one — `cli/run_cmd.span_for` is what answers it for a
                command.
            measure: How a timed span is published. Required — see the module
                docstring. `MetricBus.measure` is the real one.
            replicate: The replicate being previewed, or `None` for the
                baseline. One rather than all of them: a preview is one
                viewport, and the fan-out belongs to a run.
            store: Where computed frames are kept between renders. Defaults to a
                fresh `MemoryFrameStore`, because a preview whose store kept
                nothing would re-run the whole graph on every edit and miss the
                budget it exists to hold — the opposite of `execute`'s default,
                and for the reason that makes that one right too: the caller
                that has not thought about caching gets what it obviously meant.
            registry: The shelf graphs resolve against.
        """
        self._source = source
        self._reader = reader
        self._window = window
        self._measure = measure
        self._replicate = replicate
        self._store = MemoryFrameStore() if store is None else store
        self._registry = registry

    # ---- state -----------------------------------------------------------

    @property
    def window(self) -> SourceSpan:
        """The span a full render covers."""
        return self._window

    @property
    def replicate(self) -> Replicate | None:
        """The replicate being previewed, or None for the baseline."""
        return self._replicate

    @property
    def store(self) -> FrameStore:
        """Where this session's computed frames live.

        Exposed so a HUD can report its size and a caller can clear it. Not so
        anything can look an entry up: the keys are the plan's, and a second
        place deriving one is the failure `cache_key.py` opens by naming.
        """
        return self._store

    def set_window(self, window: SourceSpan) -> None:
        """Preview a different span of the same footage.

        Keeps every stored entry, and that is the point rather than an
        oversight: a key carries the node, the parameters, the replicate's
        overrides and the footage, and never the span — so the frames the old
        and new windows share are already computed and the render after this one
        pays only for the difference. See the module docstring.
        """
        self._window = window

    def set_replicate(self, replicate: Replicate | None) -> None:
        """Preview a different replicate of the same footage.

        Also keeps every entry, for a different reason: the overrides are *in*
        the key, so the new replicate's entries are simply absent while the old
        one's stay valid for the moment the user clicks back. Two replicates
        that deviate in nothing share every entry, which is why a run fanning
        out over both computes once.

        **Not valid on a session reading a written crop.** The file holds one
        replicate's pixels and `source` names it, so re-aiming at another
        replicate would run the new one's parameters over the old one's footage
        and key it as if that were fine. A caller whose replicate changes
        resolves the source again and builds a new session.
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
            SourceFileError: if a source root's file does not resolve — see
                `_plan`.
            UnrunnableNodeError: if a node cannot be called at all, or returns a
                frame it was not asked for.
            FormatMismatchError: if the reader's format is not the graph's.
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
        and re-deriving that here would be a second definition of a bound the
        transport layer owns.

        Raises:
            ValidationError: if `index` is negative — a span has to start
                somewhere real. Everything `render_window` raises, for the same
                reasons.
        """
        return self._run(
            self._plan(pipeline, SourceSpan(start=index, end=index + 1)), on_frame, whole=False
        )

    # ---- internals -------------------------------------------------------

    def _plan(self, pipeline: Pipeline, span: SourceSpan) -> ExecutionPlan:
        """Resolve and plan `pipeline` over `span` for this session's replicate.

        Rebuilt per render, and cheap by construction: resolving nodes against
        the registry and hashing a parameter dict per node is arithmetic over
        the document, with no decode and no tool call in it. Memoizing the last
        plan would save microseconds and introduce the question of whether two
        pipelines that compare equal are the same graph, which is a question
        with no upside here.

        The one exception is the source roots, which are a glob and a stat each
        — see the module docstring on why that is paid per render. A graph with
        no source tool pays nothing: `source_files` walks a list that is empty.

        Raises:
            SourceFileError: if a source root's path parameter names no file or
                several. Here rather than at the first frame, where the tool
                would raise it resolving the same pattern: a render that cannot
                say which file it reads has no key for that node and no frame to
                show for it either.
        """
        dag = Dag.build(pipeline, self._registry)
        return ExecutionPlan.build(
            dag,
            source=self._source,
            span=span,
            replicate=self._replicate,
            picked=picked_identities(source_files(dag, validated_params(dag, self._replicate))),
        )

    def _run(self, plan: ExecutionPlan, on_frame: Consumer | None, *, whole: bool) -> PreviewRender:
        """Drive `execute` to exhaustion, timing the first frame and the rest.

        `execute` is a generator, so calling it does no work: everything —
        binding the tools, refusing an uncallable node, decoding the lead-in,
        running the head of the graph — happens on the first `next` and is
        therefore inside the first-frame span. That is the honest boundary: a
        user who edits a parameter waits for all of it before seeing anything.

        The consumer is called inside the timed spans. The budget's label says
        "preview repaint", and a number that excluded the caller's paint would be
        a number about this module rather than about what the user waited for.
        """
        deliver = _discard if on_frame is None else on_frame
        tally = _Tally()
        with self._measure(WHOLE_WINDOW_BUDGET) if whole else nullcontext():
            stream = execute(plan, self._reader, store=self._store)
            with self._measure(FIRST_FRAME_BUDGET):
                # `SourceSpan` cannot be empty and every index at or after
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
