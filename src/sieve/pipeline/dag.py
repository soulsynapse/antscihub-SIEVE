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

**Five rejections, in a fixed order**, because the first useful message is the
one to give: an unresolved filter is reported before a cycle, since a graph
half of whose nodes name nothing has no meaningful cycle to describe; a cycle
is reported before port wiring, since ordering the later checks needs the sort
that the cycle check produces; and wiring is reported before an edge's types,
since an edge feeding a port the filter does not declare has no `accepts` to
check a type against.

1. Every `(filter_id, version)` resolves against the registry.
2. The graph is acyclic.
3. Every node's incoming edges fill its declared input ports exactly — no
   unknown port, no unfilled port, and a merging filter is never a root.
4. Every edge chains: what the downstream's port `accepts` admits the
   upstream's `emits`.
5. Nothing else. Parameters are *not* validated here — that happens in
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
from sieve.core.filter_base import ArraySpec, FilterSpec, StreamSpec
from sieve.core.filter_registry import REGISTRY, FilterRegistry, UnknownFilterError
from sieve.core.pipeline_model import Node, Pipeline
from sieve.core.replicates import Replicate
from sieve.core.types import ChannelSpec
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


class PortWiringError(GraphError):
    """A node's incoming edges do not line up with its declared input ports.

    Three shapes, one error: an edge names a port the filter does not declare,
    a declared port has no edge feeding it, or a filter declaring several ports
    sits at a root — where the one stream available is the source, and there is
    no rule for which port it would fill that is not a guess. All three are
    facts about declarations, so all three are available with nothing installed
    but the filter's spec.
    """

    def __init__(self, node_id: str, message: str) -> None:
        self.node_id = node_id
        super().__init__(message)


class EdgeTypeError(GraphError):
    """An edge carries something its downstream's port cannot consume.

    The rejection the I/O declarations exist to enable: it is available before
    a frame is decoded, on a machine with no codec, which is what makes a
    mistyped graph a message at load rather than a traceback ten minutes into a
    run.
    """

    def __init__(
        self, upstream: str, downstream: str, port: str, emits: StreamSpec, accepts: StreamSpec
    ) -> None:
        self.upstream = upstream
        self.downstream = downstream
        self.port = port
        super().__init__(
            f"{upstream} emits {emits}, which {downstream} does not accept "
            f"on port {port!r} ({accepts})"
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
    #: Which upstream feeds each of a node's input ports: `node_id` to
    #: `port -> upstream node_id`. Total over `order` — a root maps to `{}`.
    #: The port-resolved view of `upstreams`, and the one the executor and the
    #: cache key read, because for a merging filter *which port* a stream
    #: arrives on is part of what the node computes: a minus b is not b minus a.
    ports: Mapping[str, Mapping[str, str]]

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
            PortWiringError: if any node's incoming edges do not fill its
                declared input ports exactly.
            EdgeTypeError: if any edge's endpoints cannot be connected.
        """
        shelf = REGISTRY if registry is None else registry
        specs = cls._resolve(pipeline, shelf)
        upstreams, downstreams, ports = cls._adjacency(pipeline)
        order = cls._topological(pipeline, upstreams, downstreams)
        cls._check_ports(order, specs, ports)
        cls._check_edges(order, specs, ports)
        return cls(
            pipeline=pipeline,
            order=order,
            specs=specs,
            upstreams=upstreams,
            downstreams=downstreams,
            ports=ports,
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
    ) -> tuple[
        dict[str, tuple[str, ...]],
        dict[str, tuple[str, ...]],
        dict[str, dict[str, str]],
    ]:
        """Both directions plus the port view, all total over the node set.

        Built as lists and frozen on the way out so that edge order is the
        document's. Nothing downstream depends on that order — `node_key` sorts
        its upstreams, precisely so it cannot — but a traversal whose output
        order is the document's is one whose diffs are readable. The port
        mapping cannot lose an edge to a key collision: `Pipeline` has already
        refused two edges feeding one port.
        """
        up: dict[str, list[str]] = {node.node_id: [] for node in pipeline.nodes}
        down: dict[str, list[str]] = {node.node_id: [] for node in pipeline.nodes}
        ports: dict[str, dict[str, str]] = {node.node_id: {} for node in pipeline.nodes}
        for edge in pipeline.edges:
            up[edge.downstream].append(edge.upstream)
            down[edge.upstream].append(edge.downstream)
            ports[edge.downstream][edge.port] = edge.upstream
        return (
            {node_id: tuple(ids) for node_id, ids in up.items()},
            {node_id: tuple(ids) for node_id, ids in down.items()},
            ports,
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
    def _check_ports(
        order: Sequence[Node],
        specs: Mapping[str, FilterSpec],
        ports: Mapping[str, Mapping[str, str]],
    ) -> None:
        """Every node's incoming edges against its declared input ports.

        Exact agreement, both directions, because both failures are silent at
        run time otherwise: an edge into an undeclared port is a stream the
        kernel would never read, and an unfilled port is an argument the kernel
        would be called without. A node with no incoming edge is a root and is
        exempt from filling — the source fills its one port — but a filter
        declaring several ports cannot sit there, because the source is one
        stream and choosing which port receives it would be a guess this module
        is not entitled to make.
        """
        for node in order:
            declared = specs[node.node_id].input_ports
            fed = ports[node.node_id]
            if not fed:
                if len(declared) > 1:
                    raise PortWiringError(
                        node.node_id,
                        f"{node.node_id} declares input ports {sorted(declared)} but has no "
                        "incoming edge; the source is one stream, so a merging filter cannot "
                        "be a root",
                    )
                continue
            unknown = sorted(set(fed) - set(declared))
            if unknown:
                raise PortWiringError(
                    node.node_id,
                    f"{node.node_id} has edges into {unknown}, which "
                    f"{specs[node.node_id].filter_id} does not declare "
                    f"(its ports: {sorted(declared)})",
                )
            unfilled = sorted(set(declared) - set(fed))
            if unfilled:
                raise PortWiringError(
                    node.node_id,
                    f"{node.node_id} leaves {unfilled} unfilled; every declared port needs "
                    "an edge, because the kernel will be called with all of them",
                )

    @staticmethod
    def _check_edges(
        order: Sequence[Node],
        specs: Mapping[str, FilterSpec],
        ports: Mapping[str, Mapping[str, str]],
    ) -> None:
        """Every edge, in topological order, against the port it feeds.

        The order is not needed for correctness — an edge check is local — but
        it decides *which* mismatch is reported first in a graph with several,
        and reporting the earliest is what lets a user fix a chain from the top
        rather than from wherever a dict happened to start. Within a node,
        edge-declaration order, for the same reason.

        A root's input is unchecked, and deliberately: what feeds it is the
        replicate's cropped source, which is an array of whatever the decoder
        produces. Checking that would mean this module knowing about codecs,
        and the layer contract is what keeps `dag.py` runnable on a machine
        with none.
        """
        for node in order:
            declared = specs[node.node_id].input_ports
            for port, upstream_id in ports[node.node_id].items():
                accepts = declared[port]
                emits = specs[upstream_id].emits
                if not accepts.admits(emits):
                    raise EdgeTypeError(upstream_id, node.node_id, port, emits, accepts)

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

    @property
    def needs_chroma(self) -> bool:
        """Whether this graph must be fed colour frames rather than luma.

        The decode format is a property of the graph, not a setting: a chain
        that nowhere reads colour is decoded from the luma plane, which is 2.4x
        cheaper and drops the per-frame buffer from 47.6 MB to 15.9
        (`decode/reader.py`). Today no filter on the shelf declares a chroma-only
        input, so this is false for every real graph — and the point of deriving
        it rather than hard-coding it is that the first filter which *does* read
        hue flips it back without anyone having to remember that it must.

        **Over-inclusive on purpose, and it is the whole graph rather than the
        roots.** Only roots touch the source frame, so a strict reading would
        ask about them alone; but channel layout propagates — most filters emit
        what they were handed — and a downstream node demanding colour is
        evidence the chain was meant to carry it. `cache_key.py`'s rule applies
        unchanged: an input wrongly included is a slower correct answer, an
        input wrongly omitted is a wrong one served from cache and never noticed.

        A filter that leaves `accepts.channels` empty means "any", which
        includes GRAY, so silence is never read as a demand for colour.
        """
        return any(_requires_chroma(spec) for spec in self.specs.values())

    def node_keys(
        self,
        *,
        source: str,
        backend: Backend | Mapping[str, Backend],
        replicate: Replicate | None = None,
        pre_cropped: bool = False,
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
            pre_cropped: Whether `source` already identifies footage holding
                this replicate's crop. Then the ROI does *not* enter the root
                key — the region was cut before the file existed, and claiming
                it here would describe a crop of a crop. The replicate's
                parameter overrides still enter every node's key, which is the
                whole reason this is a separate flag and not `replicate=None`.

        Returns:
            `node_id` to key, for the cacheable nodes only.

        Raises:
            ValidationError: if a node's resolved parameters are not valid for
                its filter — the one check this module does not do up front,
                done here because this is where they would enter a hash.
            KeyError: if `backend` is a mapping missing a node in `order`.
        """
        # The format is derived here rather than passed in, so the key and the
        # reader cannot disagree about what was decoded: whoever opens the
        # reader asks this same graph the same question.
        root_key = source_key(
            source,
            None if pre_cropped or replicate is None else replicate.roi,
            luma=not self.needs_chroma,
        )
        keys: dict[str, str] = {}
        for node in self.order:
            fed = self.ports[node.node_id]
            if fed:
                if any(parent not in keys for parent in fed.values()):
                    continue
                upstream = {port: keys[parent] for port, parent in fed.items()}
            else:
                # A root's one port is fed by the source. Keyed under its
                # declared name rather than a fixed one, so that the key means
                # what the kernel will actually be handed — `_check_ports` has
                # already refused a multi-port root.
                (port,) = self.specs[node.node_id].input_ports
                upstream = {port: root_key}
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


def graph_needs_chroma(pipeline: Pipeline, registry: FilterRegistry | None = None) -> bool:
    """`Dag.needs_chroma` for a graph nobody has built a `Dag` from yet.

    For the caller that must choose a decode format *before* it plans — the GUI's
    render worker owns its reader and has to know which format to open it in, and
    a reader is not something a `PreviewSession` can reopen on its behalf.

    A graph that does not resolve needs colour, because "this filter is missing"
    is not a question about chroma and the caller is about to fail on it properly
    a moment later; answering `True` keeps the fallback the format that has
    always been the default.

    This does build a second `Dag` for a render that will build one again when it
    plans. That is a resolve and a topological sort over a handful of nodes
    against a render measured in seconds, and it is not a second *answer*: both
    derive from this function on the same input, which is the property that
    matters.
    """
    try:
        return Dag.build(pipeline, registry).needs_chroma
    except GraphError:
        return True


def _requires_chroma(spec: FilterSpec) -> bool:
    """Whether `spec` refuses a single-channel frame.

    A demand, not a preference: the question is whether GRAY is *excluded* from
    what this filter accepts, so an empty `channels` tuple — the "any" wildcard
    `ArraySpec` documents — answers no, and so does any set that lists GRAY
    alongside colour layouts. Only a filter that names colour layouts and omits
    GRAY is asking for chroma it would not otherwise get.

    A non-array input (a `TableSpec`) never reads pixels and so never demands
    them, which is why the isinstance is a `False` rather than an error.
    """
    accepts = spec.accepts
    if not isinstance(accepts, ArraySpec) or not accepts.channels:
        return False
    return ChannelSpec.GRAY not in accepts.channels
