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
from sieve.core.filter_base import ParamsBase, input_warmup_frames
from sieve.core.pipeline_model import ClipRange, Node, resolved_params
from sieve.core.replicates import Replicate
from sieve.pipeline.dag import Dag


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
    #: The frames the caller asked for, half-open, in source indices.
    span: ClipRange
    #: Resolved and validated parameters per `node_id`. Total over `dag.order`.
    params: Mapping[str, ParamsBase]
    #: Cache key per `node_id`, for the cacheable nodes only — a node absent
    #: from this map is one that must be computed. `Dag.node_keys`' map,
    #: carried so nothing recomputes it.
    keys: Mapping[str, str]
    #: Source frames to decode ahead of `span.start` so every node is warmed.
    #: The maximum over the graph, not per node: one decode feeds all of them.
    lead_in: int
    backend: Backend
    replicate: Replicate | None

    @classmethod
    def build(
        cls,
        dag: Dag,
        *,
        source: str,
        span: ClipRange,
        backend: Backend,
        replicate: Replicate | None = None,
    ) -> ExecutionPlan:
        """Derive the run of `dag` over `span`.

        Args:
            dag: The validated graph. Already resolved against a registry, so
                nothing here can fail to find a filter.
            source: What identifies the footage — `cache_key.source_identity`
                builds one. A string rather than a `Path` for that function's
                reason, and because it keeps this buildable against footage
                that is not mounted.
            span: The frames wanted, half-open. Required rather than defaulting
                to the whole video, because "the whole video" is a fact about
                the container and this module may not open one. A caller with a
                `Project` whose `clip` is `None` builds the full-length range
                from the reader's metadata.
            backend: Where these nodes run.
            replicate: The replicate being processed. Its ROI enters the keys at
                the root and its overrides enter every node's params. `None` is
                the baseline a project with no fan-out runs.

        Raises:
            ValidationError: if any node's resolved parameters are not valid for
                its filter.
            ValueError: if any node declares a non-positive output rate.
        """
        params = {
            node.node_id: dag.specs[node.node_id].params_model.model_validate(
                resolved_params(node, replicate)
            )
            for node in dag.order
        }
        return cls(
            dag=dag,
            span=span,
            params=params,
            keys=dag.node_keys(source=source, backend=backend, replicate=replicate),
            lead_in=_lead_in(dag, params),
            backend=backend,
            replicate=replicate,
        )

    # ---- what the reader is asked for ------------------------------------

    @property
    def decode_start(self) -> int:
        """First source frame to decode, clamped at the start of the video.

        Clamped rather than rejected. A clip that begins at frame 3 behind a
        filter wanting 30 frames of lead-in cannot be warmed, and there is no
        footage that would fix it — refusing to run would make the opening
        seconds of every video untunable, which is worse than a first frame
        that is under-warmed and reported as such by `lead_in_shortfall`.
        """
        return max(self.span.start - self.lead_in, 0)

    @property
    def decode_range(self) -> range:
        """Every source frame the run touches, lead-in included, in order."""
        return range(self.decode_start, self.span.end)

    @property
    def lead_in_shortfall(self) -> int:
        """Lead-in frames wanted that the video cannot supply. 0 when warmed.

        Nonzero means the first outputs of the span are computed from a filter
        that has not settled. A caller that cares — a batch run writing results
        someone will publish — warns on it; a preview scrubbing near frame 0
        ignores it.
        """
        return self.lead_in - (self.span.start - self.decode_start)

    @property
    def warmed(self) -> bool:
        """Whether every node's lead-in is fully available in the source."""
        return self.lead_in_shortfall == 0

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


def _lead_in(dag: Dag, params: Mapping[str, ParamsBase]) -> int:
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
    need: dict[str, int] = {}
    for node in reversed(dag.order):
        downstream_need = max(
            (need[downstream] for downstream in dag.downstreams[node.node_id]), default=0
        )
        step = (dag.specs[node.node_id], params[node.node_id])
        need[node.node_id] = input_warmup_frames(step, downstream_need)
    return max((need[root.node_id] for root in dag.roots), default=0)


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
