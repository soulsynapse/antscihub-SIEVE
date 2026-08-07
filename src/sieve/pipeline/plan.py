"""Everything about a run that is knowable before a frame is decoded.

`Dag` answers whether a graph *can* run and in what order. This answers what
one particular run of it would do: which parameters each node resolves to for
the replicate being processed, what each node's cache key is, how many source
frames have to be decoded ahead of the requested span so that every node is
warmed, and therefore which frames the reader is asked for.

**Split from `executor.py` for the same reason `filter_base.py` is split from
`sieve.filters`: so that it needs nothing installed.** A plan is buildable on a
machine with no codec and no CUDA, which is what makes `sieve run --dry-run`,
`sieve inspect`, and the storage HUD possible without going through a
`VideoReader`. `pipeline/preview.py` needs the same lead-in arithmetic; a
private helper inside the executor would leave it reimplementing this or
reaching into a private, and the reimplementation is the failure `filter_base`'s
`source_warmup_frames` docstring is already about.

**Lead-in is the maximum over a node's paths, computed without enumerating
them.** `input_warmup_frames` is monotone non-decreasing in its second argument,
so propagating the maximum node-by-node backwards along `Dag.order` gives the
same answer as taking the maximum over paths — of which a diamond chain has
exponentially many. `tests/property/test_warmup.py` checks the walk against
brute-force path enumeration on random graphs, because that equivalence is the
whole justification for the walk and it is not visible in the code.

**Every node's parameters are validated here, not just the cacheable ones.**
`Dag.node_keys` validates as a side effect of hashing, and a node that has not
claimed determinism is never hashed — so before this module a filter declaring
`deterministic=False` could carry a misspelled parameter all the way to its
kernel. The plan needs the parsed params anyway to call kernels with, so the
gap closes for free.

**Which frames are in the answer is the graph's, and the decode range is an
optimization over it.** `span` is folded here from every `selecting` node's
declared range intersected with what the caller asked for, and `decode_range`
then *widens* that by the lead-in and hands it to the reader. The widening is a
predicate pushdown and nothing more: the frames it adds are exactly the lead-in
ones the executor already discards, so narrowing what is read changes when a
result arrives and never what it is. Two consequences worth naming, because
neither is visible at the fold:

- **The selection is the run's, not a branch's.** `execute` yields one
  `FrameResult` per frame carrying *every* node's output, so a graph has one
  frame set and a per-branch selection has nowhere to live. Intersecting over
  the whole graph is therefore not a simplification — it is the only reading
  the executor can express, and it is what makes a selecting node's placement
  irrelevant to the result.
- **Lead-in flows through a selecting node, and has to.** A selection that
  genuinely dropped frames at a root would leave everything below it with no
  frames to warm on, and every stateful filter in the graph would be unsettled
  for the whole span. The frames are cut once, at the yield, after they have
  done the warming — which is what the executor has always done and is the half
  of the span that was never the problem.

**The cache is not consulted here.** A plan says what the run computes, and
what is already in a store is a property of a machine at a moment, not of the
run. The executor takes both. The consequence worth naming is that `lead_in` is
static: a cached upstream could in principle shorten it, but only if the entry
covered the lead-in span too, which the store does not record. Decoding more
than strictly necessary is slow and correct, and `cache_key.py`'s asymmetry rule
— a wrong answer served from cache is invisible, a miss is merely slow — says
take that one.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from sieve.backend.dispatch import Backend
from sieve.core.filter_base import ALL_FRAMES, ParamsBase, input_warmup_frames
from sieve.core.pipeline_model import ClipRange, Node, resolved_params
from sieve.core.replicates import Replicate
from sieve.core.types import NO_FRAMES, ROI, FrameCount, FrameIndex, FrameRange
from sieve.decode.lowered import LoweredPrefix
from sieve.pipeline.dag import Dag

SOURCE_FRAME_ZERO = FrameIndex(0)


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    """One run of one graph, over one span, for one replicate, on one backend.

    Frozen for `Dag`'s reason: it is derived from a frozen document, and a plan
    that could be edited after a key was computed from it would be a second
    place the run is described.
    """

    #: The validated graph. Carried rather than copied out of, so a holder of a
    #: plan never needs the `Dag` alongside it.
    dag: Dag
    #: The frames in the answer, half-open, in source indices: what the caller
    #: asked for, narrowed by every `selecting` node in the graph.
    span: ClipRange
    #: Resolved and validated parameters per `node_id`. Total over `dag.order`.
    params: Mapping[str, ParamsBase]
    #: Cache key per `node_id`, for the cacheable nodes only — a node absent
    #: from this map is one that must be computed. `Dag.node_keys`' map,
    #: carried so nothing recomputes it.
    keys: Mapping[str, str]
    #: Source frames to decode ahead of `span.start` so every node is warmed.
    #: The maximum over the graph, not per node: one decode feeds all of them.
    lead_in: FrameCount
    #: Where each node runs, per `node_id`. Total over `dag.order`.
    #:
    #: **Per node rather than one for the graph**, because `dispatch.py` holds
    #: that "a filter with a CPU kernel and no GPU kernel is complete, not
    #: deficient" — and a single backend on the plan makes it deficient the
    #: moment anything asks for GPU, since one CPU-only node in a chain would
    #: fail the whole run. The selection is a *plan-time* decision and the key
    #: is derived from what was selected, which is what lets the executor
    #: refuse to fall back: by the time it runs, there is nothing left to fall
    #: back from. Uniform today, because no GPU kernel exists to make it
    #: otherwise; the shape is here so the day one lands is not the day every
    #: caller changes.
    backends: Mapping[str, Backend]
    replicate: Replicate | None
    #: Whether the source this run reads already holds the replicate's pixels.
    #:
    #: False for footage a replicate is cut *out of*, which is every run there
    #: was before crop artifacts existed. True when the reader is a materialized
    #: crop of this replicate (`pipeline/resolve_source.py`): the fan-out already
    #: happened on disk, so there is no crop left to apply and the root key must
    #: not claim one — the artifact is a source in its own right with an identity
    #: of its own, and `roi` below is where both consequences are read from.
    #:
    #: Separate from `replicate` rather than folded into it, because the two
    #: answer different questions: which arena's *parameters* resolve (still this
    #: replicate's, artifact or not) and which *pixels* the reader hands over.
    #: Under the child-source model those stopped being the same fact.
    pre_cropped: bool = False
    #: The lowest source frame index the reader can supply. Zero for a whole
    #: video; `CropArtifact.span.start` for a crop, whose frame 0 *is* that
    #: source frame. `decode_start` clamps here, so lead-in that falls before
    #: the artifact begins is reported by `lead_in_shortfall` rather than
    #: requested and refused — the same treatment a clip near frame 0 already
    #: gets, for the same reason.
    source_start: FrameIndex = SOURCE_FRAME_ZERO
    lowered_prefix: LoweredPrefix | None = None

    @classmethod
    def build(
        cls,
        dag: Dag,
        *,
        source: str,
        span: ClipRange,
        backend: Backend | Mapping[str, Backend],
        replicate: Replicate | None = None,
        pre_cropped: bool = False,
        source_start: int | FrameIndex = SOURCE_FRAME_ZERO,
        lowered_prefix: LoweredPrefix | None = None,
    ) -> ExecutionPlan:
        """Derive the run of `dag` over `span`.

        Args:
            dag: The validated graph. Already resolved against a registry, so
                nothing here can fail to find a filter.
            source: What identifies the footage — `cache_key.source_identity`
                builds one. A string rather than a `Path` for that function's
                reason, and because it keeps this buildable against footage
                that is not mounted.
            span: The frames wanted, half-open, before the graph has its say —
                every `selecting` node narrows it further, and `ExecutionPlan.
                span` is the result. Required rather than defaulting to the
                whole video, because "the whole video" is a fact about the
                container and this module may not open one. A caller with a
                `Project` whose `clip` is `None` builds the full-length range
                from the reader's metadata.
            backend: Where each node runs. A single `Backend` assigns all of
                them, which is the whole of what a caller wants until a graph
                genuinely spans two; a mapping assigns them individually and
                must cover every node.
            replicate: The replicate being processed. Its ROI enters the keys at
                the root and its overrides enter every node's params. `None` is
                the baseline a project with no fan-out runs.
            pre_cropped: Whether `source` already names footage holding this
                replicate's crop — a materialized artifact rather than the
                parent. The overrides still resolve; the ROI stops applying, at
                the root key and at the executor's crop alike. Defaulted so a
                caller that has never heard of artifacts gets the behaviour that
                predates them.
            source_start: Lowest source frame index the reader can supply.

        Raises:
            ValidationError: if any node's resolved parameters are not valid for
                its filter.
            ValueError: if any node declares a non-positive output rate, or if
                the `selecting` nodes and the requested span have no frame in
                common. Refused rather than run empty: a graph that computes
                nothing and reports success is a result that looks better
                founded than it is, and the message names the ranges that
                disagree so the reader can see which one to move.
            KeyError: if `backend` is a mapping and a node is missing from it.
                Refused rather than defaulted: a node silently falling to CPU
                because a caller forgot it would key correctly and run on the
                wrong device, which is a performance bug with no symptom.
        """
        if lowered_prefix is not None and not pre_cropped:
            raise ValueError("a lowered source must be planned as pre_cropped")
        if lowered_prefix is not None and dag.needs_chroma:
            raise ValueError("a lowered source emits gray frames and cannot feed a chroma graph")
        params = {
            node.node_id: dag.specs[node.node_id].params_model.model_validate(
                resolved_params(node, replicate)
            )
            for node in dag.order
        }
        backends = {
            node.node_id: (backend[node.node_id] if isinstance(backend, Mapping) else backend)
            for node in dag.order
        }
        return cls(
            dag=dag,
            span=_selected(dag, params, span),
            params=params,
            keys=dag.node_keys(
                source=source,
                backend=backends,
                replicate=replicate,
                pre_cropped=pre_cropped,
                lowered_prefix=lowered_prefix,
            ),
            lead_in=_lead_in(dag, params),
            backends=backends,
            replicate=replicate,
            pre_cropped=pre_cropped,
            source_start=FrameIndex.of(source_start),
            lowered_prefix=lowered_prefix,
        )

    # ---- what the reader is asked for ------------------------------------

    @property
    def roi(self) -> ROI | None:
        """The region the executor cuts from each decoded frame, or None.

        The one place the two ways of having no crop are answered together: a
        project with no fan-out (`replicate is None`) and a run whose reader is
        already this replicate's crop (`pre_cropped`). Both mean *do not cut*,
        and both mean the root key names no region — so `dag.node_keys` and
        `executor.execute` ask this rather than reaching for `replicate.roi`,
        which under the child-source model is the geometry of a cut that has
        already happened.
        """
        if self.pre_cropped or self.replicate is None:
            return None
        return self.replicate.roi

    @property
    def decode_start(self) -> FrameIndex:
        """First source frame to decode, clamped at the start of the footage.

        Clamped rather than rejected. A clip that begins at frame 3 behind a
        filter wanting 30 frames of lead-in cannot be warmed, and there is no
        footage that would fix it — refusing to run would make the opening
        seconds of every video untunable, which is worse than a first frame
        that is under-warmed and reported as such by `lead_in_shortfall`.

        The floor is `source_start` and not 0 for exactly that reason applied
        once more: a crop artifact's footage begins partway into the source's
        numbering, and lead-in reaching before it is unavailable in the same
        unfixable way. It is the same clamp, and the shortfall reports it in
        the same field.
        """
        span_start = FrameIndex(self.span.start)
        if span_start <= self.source_start:
            # A span that begins before the footage does is the clamp taken to
            # its limit, not a new case. `resolve_source.resolve` declines an
            # artifact that does not cover the request, so nothing in the tree
            # builds this plan today — but the subtraction below is
            # `FrameIndex - FrameIndex`, which is a `FrameCount`, and a
            # `FrameCount` refuses to be negative. Without this line the
            # documented clamp would raise instead of clamping, from inside
            # `core/types.py`, on an invariant held one module away.
            return self.source_start
        available = span_start - self.source_start
        if available < self.lead_in:
            return self.source_start
        return span_start - self.lead_in

    @property
    def decode_range(self) -> FrameRange:
        """Every source frame the run touches, lead-in included, in order."""
        return FrameRange(self.decode_start, FrameIndex(self.span.end))

    @property
    def lead_in_shortfall(self) -> FrameCount:
        """Lead-in frames wanted that the video cannot supply. 0 when warmed.

        Nonzero means the first outputs of the span are computed from a filter
        that has not settled. A caller that cares — a batch run writing results
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

        `not dag.needs_chroma`, which is what `cache_key.source_key` hashes —
        so this is not a preference and a caller must not choose it. The
        failure it exists to prevent leaves no trace: a reader handing BGR to a
        graph keyed for luma fills the store with correctly-shaped frames
        computed from the wrong pixels, and the symptom is a preview that looks
        plausible.

        Here rather than at each call site because a plan is "everything about
        a run that is knowable before a frame is decoded", and this is exactly
        that — the `Dag` it derives from is already built and already the one
        the keys came from. A caller that must decide *before* it plans (the
        render worker, `sieve preview`) has no plan to ask and calls
        `dag.graph_needs_chroma` instead; what those two must not do is decide
        it a second time once a plan exists.
        """
        return not self.dag.needs_chroma

    # ---- queries ---------------------------------------------------------

    def backend_for(self, node_id: str) -> Backend:
        """Where `node_id` runs.

        Raises:
            KeyError: if no node in this graph carries it.
        """
        return self.backends[node_id]

    def key(self, node_id: str) -> str | None:
        """`node_id`'s cache key, or `None` if it may not be cached at all.

        `None` rather than `KeyError`: a caller asking this is deciding whether
        to look something up, and "not cacheable" is an ordinary answer to that
        question rather than a mistake. `KeyError` is still what an unknown
        `node_id` gets, via `dag.spec`.
        """
        self.dag.spec(node_id)
        return self.keys.get(node_id)


def _selected(dag: Dag, params: Mapping[str, ParamsBase], requested: ClipRange) -> ClipRange:
    """`requested` intersected with what every node in the graph keeps.

    No node is asked which filter it is and nothing is enumerated: a filter that
    selects overrides `ParamsBase.selected_frames`, every other filter inherits
    `ALL_FRAMES`, and the intersection over the whole graph is the same
    expression either way. That is what keeps the span a *discovered* filter —
    naming `span` here would make `pipeline` the registry that rule 3 forbids,
    and `tests/unit/test_filter_id_spelling.py` is what says so out loud.

    Unordered, unlike `_lead_in`: intersection is commutative and associative, so
    there is nothing for the topological order to contribute. Two selecting nodes
    on unrelated branches narrow the one answer together, which is
    `ExecutionPlan`'s docstring on why a graph has one frame set.

    Raises:
        ValueError: if the intersection is empty. `ClipRange` refuses it anyway —
            "a clip must cover at least one frame" — and being refused by the
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
    return ClipRange(start=start, end=end)


def _lead_in(dag: Dag, params: Mapping[str, ParamsBase]) -> FrameCount:
    """Source frames of lead-in for the whole graph.

    One backward pass over the topological order. `need[node]` is the lead-in
    wanted at that node's *input*, in that node's own index space; a node's
    output requirement is the maximum of what its downstreams ask of it, which
    is where the max-over-paths happens. The answer is the maximum over the
    roots, whose input space *is* the source's.

    A leaf asks for nothing at its output and still contributes its own
    `warmup_frames`, which is the whole point: a leaf that needs 30 frames to
    settle needs them whether or not anything consumes it.

    An empty graph decodes no lead-in, and `max` is given a default rather than
    being handed an empty sequence for exactly that case.
    """
    need: dict[str, FrameCount] = {}
    for node in reversed(dag.order):
        downstream_need = max(
            (need[downstream] for downstream in dag.downstreams[node.node_id]),
            default=NO_FRAMES,
        )
        step = (dag.specs[node.node_id], params[node.node_id])
        need[node.node_id] = input_warmup_frames(step, downstream_need)
    return max((need[root.node_id] for root in dag.roots), default=NO_FRAMES)


def root_paths(dag: Dag, node_id: str) -> tuple[tuple[Node, ...], ...]:
    """Every root-to-`node_id` path, inclusive at both ends.

    Exponential in the graph, and deliberately not used by `_lead_in` — it
    exists so `tests/property/test_warmup.py` can check the walk against the
    definition, and so a diagnostic can show a user *which* chain is asking for
    a lead-in they think is too long. It lives here rather than in the test
    because the second use is real and because a definition kept in a test file
    is one the code is free to drift from.
    """
    paths: dict[str, tuple[tuple[Node, ...], ...]] = {}
    for node in dag.order:
        parents = dag.upstreams[node.node_id]
        if not parents:
            paths[node.node_id] = ((node,),)
        else:
            paths[node.node_id] = tuple(
                (*prefix, node) for parent in parents for prefix in paths[parent]
            )
    return paths[node_id]
