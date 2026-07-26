"""The graph, resolved: what runs, in what order, and whether it can run at all.

`core/pipeline_model.py` deliberately stops at structure — ids unique, edges
pointing at nodes that exist — because a project must open on a machine where a
filter is not installed. This module is the other half: it takes a `Pipeline`
and a `FilterRegistry` and either produces something an executor may walk or
says precisely why it may not.

**Validation happens in the constructor, or it does not happen.** `Dag.build` is
the only way to get one, and it raises rather than returning a partly-checked
object. An `is_valid()` on an already-constructed graph would make the checked
and unchecked cases the same type, and the executor would be one forgotten call
away from walking a cycle.

**Four rejections, in a fixed order**, because the first useful message is the
one to give: an unresolved filter is reported before a cycle, since a graph
half of whose nodes name nothing has no meaningful cycle to describe; a cycle
is reported before an edge's types, since ordering the type check needs the
sort that the cycle check produces.

1. Every `(filter_id, version)` resolves against the registry.
2. The graph is acyclic.
3. Every edge chains: the downstream's `accepts` admits the upstream's `emits`.
4. Nothing else. Parameters are *not* validated here — that happens in
   `cache_key.node_key`, against `spec.params_model`, at the point where a wrong
   parameter would enter a hash. A second validation pass would be a second
   answer to whether a graph is runnable.

**The walk lives here.** `cache_key.py` computes one node's key given its
upstreams' keys and declines to say which nodes those are; `node_keys` below is
the traversal that answers it, and it is the only one. Anything else that needs
an order — the executor, a cost prediction, an HPC job script — takes `order`
from here rather than sorting again.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from sieve.backend.dispatch import Backend
from sieve.core.filter_base import FilterSpec, StreamSpec
from sieve.core.filter_registry import REGISTRY, FilterRegistry, UnknownFilterError
from sieve.core.pipeline_model import Node, Pipeline
from sieve.core.replicates import Replicate
from sieve.pipeline.cache_key import NotCacheableError, node_key, source_key


class GraphError(ValueError):
    """A pipeline that cannot be executed as written.

    One base for the three rejections so that a caller with nothing useful to
    say about which one it was — a CLI printing the message, a GUI colouring a
    node red — catches once. The subclasses carry the parts a caller that *can*
    do something with them needs, as attributes rather than only in the message,
    because re-parsing a sentence to find a node id is how a message becomes an
    interface nobody may reword.
    """


class UnresolvedFilterError(GraphError):
    """One or more nodes name a filter this build does not have.

    Reports *every* missing filter, not the first. The user's next action is to
    install what is missing, and a graph opened from another machine is
    typically missing a set rather than one — naming them one build-run at a
    time turns one install into four.
    """

    def __init__(self, missing: Sequence[tuple[str, str]]) -> None:
        self.missing = tuple(missing)
        listed = ", ".join(f"{filter_id} {version}" for filter_id, version in self.missing)
        super().__init__(
            f"no filter {listed}" if len(self.missing) == 1 else f"no filters: {listed}"
        )


class CycleError(GraphError):
    """The graph contains a cycle, so no node in it can be ordered.

    `nodes` is every node that could not be ordered, not a minimal cycle. Kahn's
    algorithm leaves behind the cycle *and* everything downstream of it, and
    distinguishing the two would need a second traversal to buy a shorter
    message. What the caller actually needs is the set to look at, and that set
    is the leftover.
    """

    def __init__(self, nodes: Iterable[str]) -> None:
        self.nodes = tuple(sorted(nodes))
        super().__init__(f"pipeline contains a cycle among nodes: {', '.join(self.nodes)}")


class EdgeTypeError(GraphError):
    """An edge carries something its downstream cannot consume.

    The rejection the I/O declarations exist to enable: it is available before
    a frame is decoded, on a machine with no codec, which is what makes a
    mistyped graph a message at load rather than a traceback ten minutes into a
    run.
    """

    def __init__(
        self, upstream: str, downstream: str, emits: StreamSpec, accepts: StreamSpec
    ) -> None:
        self.upstream = upstream
        self.downstream = downstream
        super().__init__(
            f"{upstream} emits {emits}, which {downstream} does not accept ({accepts})"
        )


@dataclass(frozen=True, slots=True)
class Dag:
    """A `Pipeline` whose filters resolve, whose edges chain, and which sorts.

    Frozen, and every collection on it is immutable, because it is derived from
    a frozen document: a `Dag` that could be edited would be a second place a
    graph is represented, and the two would drift the moment an edit went to one
    of them.
    """

    #: The document this was built from, so a holder of a `Dag` never needs to
    #: carry the `Pipeline` alongside it.
    pipeline: Pipeline
    #: Every node, ordered so each appears after all of its upstreams.
    order: tuple[Node, ...]
    #: The resolved spec per `node_id`. Total over `order`.
    specs: Mapping[str, FilterSpec]
    #: Upstream node ids per `node_id`, in the graph's edge-declaration order.
    #: Total over `order` — a root maps to `()` rather than being absent.
    upstreams: Mapping[str, tuple[str, ...]]
    #: Downstream node ids per `node_id`. Total over `order`.
    downstreams: Mapping[str, tuple[str, ...]]

    @classmethod
    def build(cls, pipeline: Pipeline, registry: FilterRegistry | None = None) -> Dag:
        """Resolve, order, and type-check `pipeline`.

        Args:
            pipeline: The graph, already structurally valid — `Pipeline`'s own
                validator has guaranteed unique ids and edges that name nodes.
            registry: Where filters are looked up. Defaults to the process-wide
                shelf `sieve.filters.discover()` populates.

        Raises:
            UnresolvedFilterError: if any node names a filter that is not
                registered at that version.
            CycleError: if the graph is cyclic.
            EdgeTypeError: if any edge's endpoints cannot be connected.
        """
        shelf = REGISTRY if registry is None else registry
        specs = cls._resolve(pipeline, shelf)
        upstreams, downstreams = cls._adjacency(pipeline)
        order = cls._topological(pipeline, upstreams, downstreams)
        cls._check_edges(order, specs, upstreams)
        return cls(
            pipeline=pipeline,
            order=order,
            specs=specs,
            upstreams=upstreams,
            downstreams=downstreams,
        )

    # ---- construction ----------------------------------------------------

    @staticmethod
    def _resolve(pipeline: Pipeline, registry: FilterRegistry) -> dict[str, FilterSpec]:
        specs: dict[str, FilterSpec] = {}
        missing: list[tuple[str, str]] = []
        for node in pipeline.nodes:
            try:
                specs[node.node_id] = registry.get(node.filter_id, node.version)
            except UnknownFilterError:
                # Collected rather than re-raised: see UnresolvedFilterError.
                # Deduplicated by the membership test because twelve nodes of
                # one missing filter is one thing to install.
                if (node.filter_id, node.version) not in missing:
                    missing.append((node.filter_id, node.version))
        if missing:
            raise UnresolvedFilterError(missing)
        return specs

    @staticmethod
    def _adjacency(
        pipeline: Pipeline,
    ) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]]]:
        """Both directions, both total over the node set.

        Built as lists and frozen on the way out so that edge order is the
        document's. Nothing downstream depends on that order — `node_key` sorts
        its upstreams, precisely so it cannot — but a traversal whose output
        order is the document's is one whose diffs are readable.
        """
        up: dict[str, list[str]] = {node.node_id: [] for node in pipeline.nodes}
        down: dict[str, list[str]] = {node.node_id: [] for node in pipeline.nodes}
        for edge in pipeline.edges:
            up[edge.downstream].append(edge.upstream)
            down[edge.upstream].append(edge.downstream)
        return (
            {node_id: tuple(ids) for node_id, ids in up.items()},
            {node_id: tuple(ids) for node_id, ids in down.items()},
        )

    @staticmethod
    def _topological(
        pipeline: Pipeline,
        upstreams: Mapping[str, tuple[str, ...]],
        downstreams: Mapping[str, tuple[str, ...]],
    ) -> tuple[Node, ...]:
        """Kahn's algorithm, with declaration order as the tiebreak.

        A topological order is not unique, and which of the valid orders comes
        out has to be a property of the document rather than of a set's
        iteration or a dict's insertion history. The ready set is therefore
        drained in `pipeline.nodes` order: two builds of one document give one
        order, and a document whose nodes were written in a different order is
        a different document rather than a different run of the same one.

        This is load-bearing for more than readability. The executor will
        schedule in this order and a cost report will key against it, so an
        order that varied per process would make two runs of one project
        incomparable without anything having changed.
        """
        position = {node.node_id: index for index, node in enumerate(pipeline.nodes)}
        remaining = {node_id: len(ids) for node_id, ids in upstreams.items()}
        ready = sorted(
            (node_id for node_id, count in remaining.items() if count == 0),
            key=lambda candidate: position[candidate],
        )
        ordered: list[Node] = []
        while ready:
            node_id = ready.pop(0)
            ordered.append(pipeline.node(node_id))
            freed: list[str] = []
            for downstream in downstreams[node_id]:
                remaining[downstream] -= 1
                if remaining[downstream] == 0:
                    freed.append(downstream)
            # Merged and re-sorted rather than appended: appending would make
            # the order depend on when a node was freed, which is the
            # arbitrariness the tiebreak exists to remove.
            ready = sorted([*ready, *freed], key=lambda candidate: position[candidate])
        if len(ordered) != len(pipeline.nodes):
            placed = {node.node_id for node in ordered}
            raise CycleError(node_id for node_id in remaining if node_id not in placed)
        return tuple(ordered)

    @staticmethod
    def _check_edges(
        order: Sequence[Node],
        specs: Mapping[str, FilterSpec],
        upstreams: Mapping[str, tuple[str, ...]],
    ) -> None:
        """Every edge, in topological order.

        The order is not needed for correctness — an edge check is local — but
        it decides *which* mismatch is reported first in a graph with several,
        and reporting the earliest is what lets a user fix a chain from the top
        rather than from wherever a dict happened to start.

        A root's input is unchecked, and deliberately: what feeds it is the
        replicate's cropped source, which is an array of whatever the decoder
        produces. Checking that would mean this module knowing about codecs,
        and the layer contract is what keeps `dag.py` runnable on a machine
        with none.
        """
        for node in order:
            accepts = specs[node.node_id].accepts
            for upstream_id in upstreams[node.node_id]:
                emits = specs[upstream_id].emits
                if not accepts.admits(emits):
                    raise EdgeTypeError(upstream_id, node.node_id, emits, accepts)

    # ---- queries ---------------------------------------------------------

    @property
    def roots(self) -> tuple[Node, ...]:
        """Nodes with no upstream: each consumes the replicate's cropped source.

        In topological order, so a caller feeding them frames does so in the
        document's order. A graph with no nodes has no roots; a graph with
        nodes always has at least one, since a graph where every node had an
        upstream would have been rejected as cyclic.
        """
        return tuple(node for node in self.order if not self.upstreams[node.node_id])

    @property
    def leaves(self) -> tuple[Node, ...]:
        """Nodes nothing consumes. What a `Sink` names is usually one of these."""
        return tuple(node for node in self.order if not self.downstreams[node.node_id])

    def spec(self, node_id: str) -> FilterSpec:
        """The resolved filter for `node_id`.

        Raises:
            KeyError: if no node in this graph carries it.
        """
        return self.specs[node_id]

    def node_keys(
        self,
        *,
        source: str,
        backend: Backend | Mapping[str, Backend],
        replicate: Replicate | None = None,
    ) -> dict[str, str]:
        """Every cacheable node's key, for one replicate.

        The traversal `cache_key.py` names and declines to own. One pass in
        topological order, so each node's upstreams are already keyed when it is
        reached — which is the whole reason the sort happens before this rather
        than a second walk happening after it.

        **A node absent from the result is a node that must be computed.** Two
        causes, and neither is an error: the filter has not claimed determinism,
        or something upstream of it has not. `NotCacheableError` is swallowed at
        exactly the node that raises it and then propagates for free, because a
        downstream that cannot find an upstream's key has no key of its own to
        build. The alternative — raising out of the walk — would make one
        non-deterministic node in a twelve-node graph cost the cache entries of
        the eleven that are fine.

        Args:
            source: What identifies the footage — `cache_key.source_identity`
                builds one. Taken as a string rather than a `Path` so that a
                caller that already computed it does not stat the file twice,
                and so this stays runnable against footage that is not present.
            backend: Where each node runs. One `Backend` means all of them; a
                mapping gives it per `node_id` and must be total over `order`.

                *This argument used to be a single `Backend`, documented as "a
                graph split across two is two walks". That was wrong and the
                sentence is corrected rather than deleted: a downstream key
                folds in its upstreams' keys, so two independent walks can only
                describe two disconnected subgraphs. A chain whose backend
                changes partway is one walk in which the backend varies, which
                is what the per-node shape of `node_key` actually allows.*
            replicate: The replicate being processed. Its ROI enters at the
                root through `source_key`. `None` is the baseline a project
                with no fan-out runs.

        Returns:
            `node_id` to key, for the cacheable nodes only.

        Raises:
            ValidationError: if a node's resolved parameters are not valid for
                its filter — the one check this module does not do up front,
                done here because this is where they would enter a hash.
            KeyError: if `backend` is a mapping missing a node in `order`.
        """
        root_key = source_key(source, None if replicate is None else replicate.roi)
        keys: dict[str, str] = {}
        for node in self.order:
            parents = self.upstreams[node.node_id]
            if parents:
                if any(parent not in keys for parent in parents):
                    continue
                upstream = [keys[parent] for parent in parents]
            else:
                upstream = [root_key]
            try:
                keys[node.node_id] = node_key(
                    node,
                    spec=self.specs[node.node_id],
                    upstream=upstream,
                    backend=(backend[node.node_id] if isinstance(backend, Mapping) else backend),
                    replicate=replicate,
                )
            except NotCacheableError:
                continue
        return keys
