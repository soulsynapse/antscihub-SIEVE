"""Everything about a run that is knowable before a frame is decoded.

`Dag` answers whether a graph *can* run and in what order. This answers what one
particular run of it would do: which parameters each node resolves to for the
replicate being processed, what each node's cache key is, how many source frames
have to be decoded around the requested span so that every node's window is
filled, and therefore which frames the reader is asked for.

**Split from `executor.py` for the same reason `tool_base.py` is split from
`sieve.tools`: so that it needs nothing installed.** A plan is buildable on a
machine with no codec, which is what makes a dry run, `sieve inspect`, and a
storage report possible without going through a reader. `pipeline/preview.py`
will need the same window arithmetic; a private helper inside the executor would
leave it reimplementing this or reaching into a private, and the
reimplementation is the failure `source_warmup_frames`' docstring is already
about.

**The window has two sides, and each is the maximum over a node's paths.**
`input_warmup_frames` is monotone non-decreasing in its second argument, so
propagating the maximum node-by-node backwards along `Dag.order` gives the same
answer as taking the maximum over paths; `_input_lookahead_frames` is the same
conversion on the other side of the frame being emitted, and folds the same way.
v2 had only the first, because a v2 window only ever trailed — a tool tuned
against a centred result could not be a node at all
(`adr/detector-is-a-node.md`). Both sides are real here, so the decode range is
widened at *both* ends and the executor honours the second by delaying emission.

The two sides are symmetric in the arithmetic and asymmetric in the clamp, and
that asymmetry is forced rather than chosen: the first source frame is zero on
every machine, so lead-in reaching before it is knowably unavailable and is
reported by `lead_in_shortfall`. There is no corresponding ceiling — how many
frames the footage holds is a fact about a container this module may not open —
so the trailing end is asked for and the reader supplies what exists. A caller
that has opened one and wants the run refused rather than short is asking a
question the *reader* can answer and this cannot.

**Every node's parameters are validated here, not just the cacheable ones.**
`Dag.node_keys` validates as a side effect of hashing, and a node that has not
claimed determinism is never hashed — so without this module a tool declaring
`deterministic=False` could carry a misspelled parameter all the way to its
kernel. The plan needs the parsed params anyway to call kernels with, so the gap
closes for free. It is also the validation that *runs first* — one statement
before `node_keys`, over the same `dag.order` — so it is the refusal every
caller of a plan reads, and it raises `InvalidParamsError` for the reason that
error was minted: pydantic names the field and the model, and the reader here is
the interactive loop, where a field with no owner is a hunt through the graph.
Wrapping only in the walk would leave that message reachable from nothing.

**Which frames are in the answer is the graph's, and the decode range is an
optimization over it.** `span` is folded here from every `selecting` node's
declared range intersected with what the caller asked for, and `decode_range`
then widens that by the window and hands it to the reader. The widening is a
predicate pushdown and nothing more: the frames it adds are exactly the ones the
executor already discards, so narrowing what is read changes when a result
arrives and never what it is. Two consequences worth naming, because neither is
visible at the fold:

- **The selection is the run's, not a branch's.** One run yields one result per
  frame carrying every node's output, so a graph has one frame set and a
  per-branch selection has nowhere to live. Intersecting over the whole graph is
  therefore not a simplification — it is the only reading the executor can
  express, and it is what makes a selecting node's placement irrelevant to the
  result.
- **The window flows through a selecting node, and has to.** A selection that
  genuinely dropped frames at a root would leave everything below it with no
  frames to fill on, and every stateful tool in the graph would be unsettled for
  the whole span. The frames are cut once, at the yield, after they have done the
  filling.

**The cache is not consulted here.** A plan says what the run computes, and what
is already in a store is a property of a machine at a moment, not of the run. The
executor takes both. The consequence worth naming is that the window is static: a
cached upstream could in principle shorten the lead-in, but only if the entry
covered the lead-in span too, which the store does not record. Decoding more than
strictly necessary is slow and correct, and `cache_key.py`'s asymmetry rule — a
wrong answer served from cache is invisible, a miss is merely slow — says take
that one.

**What v2 had here and v3 does not.** `backend` and `lowered_prefix` go with the
decisions that removed their subjects (`adr/no-kernel-apparatus.md`, and
`PLAN.md`'s refusal to lower until a budget is missed). The pre-cropped flag, the
region it suppressed, and the artifact's own frame floor go together and for one
reason: under schema v1 a written crop is a *child source* with an identity of
its own, so a run over one is handed a different `source` rather than a flag, a
replicate carries no geometry to stop applying (`adr/detector-is-a-node.md`), and
whose frame numbering a file is in is the read-back path's question — `PLAN.md`
builds that in Phase 5, which is where the floor stops being zero.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from pydantic import ValidationError

from sieve.core.pipeline_model import Replicate, SourceSpan, resolved_params
from sieve.core.tool_base import (
    ALL_FRAMES,
    ParamsBase,
    PathStep,
    input_warmup_frames,
    node_lookahead_frames,
)
from sieve.core.types import NO_FRAMES, FrameCount, FrameIndex, FrameRange
from sieve.pipeline.dag import Dag, InvalidParamsError

#: The first frame any source can supply. The floor `decode_start` clamps at
#: while every run reads whole footage; Phase 5's read-back path is what makes a
#: crop artifact's own start the floor instead.
SOURCE_FRAME_ZERO = FrameIndex(0)


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """One run of one graph, over one span, for one replicate.

    Frozen for `Dag`'s reason: it is derived from a frozen document, and a plan
    that could be edited after a key was computed from it would be a second place
    the run is described.
    """

    #: The validated graph. Carried rather than copied out of, so a holder of a
    #: plan never needs the `Dag` alongside it.
    dag: Dag
    #: The frames in the answer, half-open, in source indices: what the caller
    #: asked for, narrowed by every `selecting` node in the graph.
    span: SourceSpan
    #: Resolved and validated parameters per `node_id`. Total over `dag.order`.
    params: Mapping[str, ParamsBase]
    #: Cache key per `node_id`, for the cacheable nodes only — a node absent from
    #: this map is one that must be computed. `Dag.node_keys`' map, carried so
    #: nothing recomputes it.
    keys: Mapping[str, str]
    #: Source frames to decode *before* `span.start` so every node's window is
    #: filled behind the first frame in the answer. The maximum over the graph,
    #: not per node: one decode feeds all of them.
    lead_in: FrameCount
    #: Source frames to decode *after* `span.end`, on the same terms. Costs
    #: latency rather than decode where the two differ: the executor may not emit
    #: the frame at `i` until it has read `i + lookahead`.
    lookahead: FrameCount
    replicate: Replicate | None = None

    @classmethod
    def build(
        cls,
        dag: Dag,
        *,
        source: str,
        span: SourceSpan,
        replicate: Replicate | None = None,
    ) -> ExecutionPlan:
        """Derive the run of `dag` over `span`.

        Args:
            dag: The validated graph. Already resolved against a registry, so
                nothing here can fail to find a tool.
            source: What identifies the footage — `cache_key.source_identity`
                builds one. A string rather than a `Path` for that function's
                reason, and because it keeps this buildable against footage that
                is not mounted.
            span: The frames wanted, half-open, before the graph has its say —
                every `selecting` node narrows it further, and `ExecutionPlan.
                span` is the result. Required rather than defaulting to the whole
                video, because "the whole video" is a fact about the container and
                this module may not open one.
            replicate: The replicate being processed. Its overrides enter every
                node's params, geometry included (`adr/detector-is-a-node.md`).
                `None` is the baseline a project with no fan-out runs.

        Raises:
            InvalidParamsError: if any node's resolved parameters are not valid
                for its tool, naming that node — see the module docstring on why
                the wrap is here and not only in the walk below it.
            ValueError: if any node declares a non-positive output rate, or if
                the `selecting` nodes and the requested span have no frame in
                common. Refused rather than run empty: a graph that computes
                nothing and reports success is a result that looks better founded
                than it is, and the message names the ranges that disagree so the
                reader can see which one to move.
        """
        params: dict[str, ParamsBase] = {}
        for node in dag.order:
            try:
                params[node.node_id] = dag.specs[node.node_id].params_model.model_validate(
                    resolved_params(node, replicate)
                )
            except ValidationError as invalid:
                raise InvalidParamsError(node.node_id, invalid) from invalid
        return cls(
            dag=dag,
            span=_selected(dag, params, span),
            params=params,
            keys=dag.node_keys(source=source, replicate=replicate),
            lead_in=_fold(dag, params, input_warmup_frames),
            lookahead=_fold(dag, params, _input_lookahead_frames),
            replicate=replicate,
        )

    # ---- what the reader is asked for ------------------------------------

    @property
    def decode_start(self) -> FrameIndex:
        """First source frame to decode, clamped at the start of the footage.

        Clamped rather than rejected. A span that begins at frame 3 behind a tool
        wanting 30 frames of lead-in cannot be warmed, and there is no footage
        that would fix it — refusing to run would make the opening seconds of
        every video untunable, which is worse than a first frame that is
        under-warmed and reported as such by `lead_in_shortfall`.
        """
        span_start = FrameIndex(self.span.start)
        if span_start - SOURCE_FRAME_ZERO < self.lead_in:
            return SOURCE_FRAME_ZERO
        return span_start - self.lead_in

    @property
    def decode_range(self) -> FrameRange:
        """Every source frame the run touches, window included, in order.

        Unclamped at the far end, where `decode_start` is clamped at the near
        one — see the module docstring: this module knows where footage begins
        and cannot know where it ends.
        """
        return FrameRange(self.decode_start, FrameIndex(self.span.end) + self.lookahead)

    @property
    def lead_in_shortfall(self) -> FrameCount:
        """Lead-in frames wanted that the video cannot supply. 0 when warmed.

        Nonzero means the first outputs of the span are computed from a tool that
        has not settled. A caller that cares — a batch run writing results
        someone will publish — warns on it; a preview scrubbing near frame 0
        ignores it.
        """
        return self.lead_in - (FrameIndex(self.span.start) - self.decode_start)

    @property
    def warmed(self) -> bool:
        """Whether every node's lead-in is fully available in the source."""
        return self.lead_in_shortfall == NO_FRAMES

    @property
    def luma(self) -> bool:
        """Which format the reader for this run must be opened in.

        `not dag.needs_chroma`, which is what `cache_key.source_key` hashes — so
        this is not a preference and a caller must not choose it. The failure it
        exists to prevent leaves no trace: a reader handing BGR to a graph keyed
        for luma fills the store with correctly-shaped frames computed from the
        wrong pixels, and the symptom is a preview that looks plausible.

        Here rather than at each call site because a plan is "everything about a
        run that is knowable before a frame is decoded", and this is exactly that
        — the `Dag` it derives from is already built and already the one the keys
        came from. A caller that must decide *before* it plans has no plan to ask
        and calls `dag.graph_needs_chroma` instead; what those two must not do is
        decide it a second time once a plan exists.
        """
        return not self.dag.needs_chroma

    # ---- queries ---------------------------------------------------------

    def key(self, node_id: str) -> str | None:
        """`node_id`'s cache key, or `None` if it may not be cached at all.

        `None` rather than `KeyError`: a caller asking this is deciding whether
        to look something up, and "not cacheable" is an ordinary answer to that
        question rather than a mistake. `KeyError` is still what an unknown
        `node_id` gets, via `dag.spec`.
        """
        self.dag.spec(node_id)
        return self.keys.get(node_id)


def _selected(dag: Dag, params: Mapping[str, ParamsBase], requested: SourceSpan) -> SourceSpan:
    """`requested` intersected with what every node in the graph keeps.

    No node is asked which tool it is and nothing is enumerated: a tool that
    selects overrides `ParamsBase.selected_frames`, every other tool inherits
    `ALL_FRAMES`, and the intersection over the whole graph is the same
    expression either way. That is what keeps the span a *discovered* tool —
    naming `span` here would make `pipeline` a registry of tool ids, which
    `tests/unit/test_tool_id_spelling.py` is what says out loud.

    Unordered, unlike `_fold`: intersection is commutative and associative, so
    there is nothing for the topological order to contribute. Two selecting nodes
    on unrelated branches narrow the one answer together, which is
    `ExecutionPlan`'s docstring on why a graph has one frame set.

    Raises:
        ValueError: if the intersection is empty. `SourceSpan` refuses it anyway
            — "a span must cover at least one frame" — and being refused by the
            type would name neither the nodes nor the ranges, which is the whole
            of what a reader needs here.
    """
    start, end = requested.start, requested.end
    narrowed: list[str] = []
    for node in dag.order:
        kept = params[node.node_id].selected_frames()
        if kept == ALL_FRAMES:
            continue
        narrowed.append(f"{node.node_id} keeps [{kept.start}:{kept.stop})")
        start, end = max(start, kept.start), min(end, kept.stop)
    if end <= start:
        raise ValueError(
            f"nothing is left to compute: [{requested.start}:{requested.end}) was asked for and "
            f"{', '.join(narrowed)} — the intersection is empty"
        )
    return SourceSpan(start=start, end=end)


def _input_lookahead_frames(step: PathStep, output_lookahead: FrameCount) -> FrameCount:
    """`input_warmup_frames` on the other side of the frame being emitted.

    Here rather than beside `node_lookahead_frames` in `core/tool_base.py`, where
    its warmup twin lives, because moving the conversion into the contract is a
    decision about that contract and this item re-derives a `pipeline` module. It
    is the same expression for the same reason: `output_lookahead` frames wanted
    past a node's output cost `at_input_of` at its input, the node's own
    lookahead is already denominated there, and both operations are monotone —
    which is what lets `_fold` take the maximum node by node.

    Raises:
        ValueError: if the node reports a non-positive output rate.
    """
    spec, params = step
    rate = params.output_rate()
    if rate <= 0:
        raise ValueError(f"{spec.tool_id}: output_rate must be positive, got {rate}")
    return output_lookahead.at_input_of(rate) + node_lookahead_frames(step)


def _fold(
    dag: Dag,
    params: Mapping[str, ParamsBase],
    edge: Callable[[PathStep, FrameCount], FrameCount],
) -> FrameCount:
    """One side of the window for the whole graph, in *source* frames.

    One backward pass over the topological order. `need[node]` is what that node
    wants at its own *input*, in its own index space; a node's output requirement
    is the maximum of what its downstreams ask of it, which is where the
    max-over-paths happens. The answer is the maximum over the roots, whose input
    space *is* the source's.

    Both sides fold identically, so `edge` is the only difference between them —
    a second copy of this walk differing in one call is how the two sides start
    disagreeing about a rate change.

    A leaf asks for nothing at its output and still contributes its own
    declaration, which is the whole point: a tool that needs 30 frames to settle
    needs them whether or not anything consumes it.

    An empty graph decodes nothing extra, and `max` is given a default rather
    than being handed an empty sequence for exactly that case.
    """
    need: dict[str, FrameCount] = {}
    for node in reversed(dag.order):
        downstream_need = max(
            (need[downstream] for downstream in dag.downstreams[node.node_id]),
            default=NO_FRAMES,
        )
        step = (dag.specs[node.node_id], params[node.node_id])
        need[node.node_id] = edge(step, downstream_need)
    return max((need[root.node_id] for root in dag.roots), default=NO_FRAMES)
