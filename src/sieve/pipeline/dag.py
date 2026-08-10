"""The graph, resolved: what runs, in what order, and whether it can run at all.

`core/pipeline_model.py` deliberately stops at structure — ids unique, edges
pointing at nodes that exist, one producer per node — because a project must
open on a machine where a tool is not installed. This module is the other half:
it takes a `Pipeline` and a `ToolRegistry` and either produces something an
executor may walk or says precisely why it may not.

**Validation happens in the constructor, or it does not happen.** `Dag.build` is
the only way to get one, and it raises rather than returning a partly-checked
object. An `is_valid()` on an already-constructed graph would make the checked
and unchecked cases the same type, and the executor would be one forgotten call
away from walking a cycle.

**One definition of legality, two consumption modes.** `Dag.validate` returns
every rejection as a `Diagnostic`; `Dag.build` is that walk plus raising the
first one. Fail-fast is right for the executor and useless for a caller that
must *render* a graph a removal or a loaded file broke, and the alternative to
this pair is what v2's GUI chain stack actually grew — a second spelling of edge
legality, in a widget, drifting from this one by construction. It is not
GUI-private knowledge either: a batch linter over saved projects wants the same
list.

`validate` is a classmethod taking a `Pipeline`, not a method on a built `Dag`.
That is the paragraph above restated rather than contradicted: the thing worth
validating is precisely the thing no `Dag` exists for, and an instance method
would be the `is_valid()` that makes the checked and unchecked cases one type.
A `Diagnostic` carries the `GraphError` itself rather than a re-rendered
sentence, so the two modes cannot word one rejection differently.

**Four rejections, in a fixed order**, because the first useful message is the
one to give: an unresolved tool is reported before a cycle, since a graph half
of whose nodes name nothing has no meaningful cycle to describe; and a cycle is
reported before anything about an edge, since reporting the earliest mismatch
needs the sort that the cycle check produces. The order is also what makes
collecting sound rather than merely longer: the first two rejections stop the
walk, because there is no later check whose inputs survive them.

1. Every `(tool_id, version)` resolves against the registry.
2. The graph is acyclic.
3. Every edge names a port its downstream tool has.
4. Every edge chains: what that port `accepts` admits the upstream's `emits`.
5. Nothing else. Parameters are *not* validated here — that happens where a
   wrong parameter would enter a hash, against `spec.params_model`, in the walk
   that keys nodes. A second validation pass would be a second answer to whether
   a graph is runnable.

The third of those is v2's port check arriving late rather than a new idea. v2
asked that a node's incoming edges filled its declared ports *exactly*; this
asks only that each edge names a port that exists, because whether an unfilled
port is a legal document is a question about what a half-wired merge is
(`todo/a-second-input-has-no-writer-and-the-box-splices-one-edge.md`) and
answering it here would settle it by construction. What `Pipeline` still refuses
before this module sees the graph is two edges into one *port*, which is
structural in the way a port set is not: a port carries one stream whatever the
tool turns out to be.

**The walk lives here.** `cache_key.py` computes one node's key given its
upstream's and declines to say which nodes those are; `node_keys` below is the
traversal that answers it, and it is the only one. Anything else that needs an
order — the executor, a cost prediction — takes `order` from here rather than
sorting again. `linear_order` is the second walk and not a second answer: it
refuses every graph `order` tolerates, because a caller that *draws* the graph
as a stack can host one path and nothing else.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

from pydantic import ValidationError

from sieve.core.pipeline_model import CropFormat, Node, Pipeline, Replicate
from sieve.core.tool_base import (
    SOLE_PORT,
    SOURCE_ELEMENT_NAMES,
    ArraySpec,
    ElementKind,
    ElementNames,
    StreamSpec,
    ToolSpec,
    node_element,
    node_element_names,
)
from sieve.core.tool_registry import REGISTRY, ToolRegistry, UnknownToolError
from sieve.core.types import ChannelSpec
from sieve.pipeline.cache_key import NotCacheableError, node_key, picked_key, source_key


def _arriving_element(
    resolved: Mapping[str, ElementKind | None], fed: Sequence[str]
) -> ElementKind | None:
    """The element meaning arriving at a node, given its parents' answers.

    A root is handed `PIXEL`: the source is frames of pixels, and this is the
    one place that enters. Parents that agree hand their agreement down; parents
    that disagree hand down nothing, because a merge of blocks and pixels emits
    values that are neither and no count over them has an honest denominator.

    v2 had exactly this branch and it went out with the merge in 03.3
    (`todo/dag-is-rederived-against-schema-v1.md`). What stood in its place
    until a fan-in was expressible was a refusal — folding the first of two
    would have carried a meaning nothing chose to everything downstream — and
    the refusal was the posture, not the answer.
    """
    if not fed:
        return ElementKind.PIXEL
    arriving = {resolved[parent] for parent in fed}
    return arriving.pop() if len(arriving) == 1 else None


class GraphError(ValueError):
    """A pipeline that cannot be executed as written.

    One base for the rejections so that a caller with nothing useful to say
    about which one it was — a CLI printing the message, a GUI colouring a node
    red — catches once. The subclasses carry the parts a caller that *can* do
    something with them needs, as attributes rather than only in the message,
    because re-parsing a sentence to find a node id is how a message becomes an
    interface nobody may reword.
    """


class UnresolvedToolError(GraphError):
    """One or more nodes name a tool this build does not have.

    Reports *every* missing tool, not the first. The user's next action is to
    install what is missing, and a graph opened from another machine is
    typically missing a set rather than one — naming them one build-run at a
    time turns one install into four.
    """

    def __init__(self, missing: Sequence[tuple[str, str]]) -> None:
        self.missing = tuple(missing)
        listed = ", ".join(f"{tool_id} {version}" for tool_id, version in self.missing)
        super().__init__(f"no tool {listed}" if len(self.missing) == 1 else f"no tools: {listed}")


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


class PortError(GraphError):
    """An edge feeds an input its downstream tool does not have.

    Separate from `EdgeTypeError` because there is no `accepts` to compare
    against: the edge does not carry the wrong thing, it arrives nowhere. Both
    ways of getting here are one mistake seen from either side — an edge naming
    a port on a tool that declares one input, and an edge naming nothing into a
    tool that declares several — so both are this rejection rather than two, and
    the message names the ports the tool does have because that is the list the
    reader has to pick from.
    """

    def __init__(
        self, upstream: str, downstream: str, port: str | None, ports: Sequence[str]
    ) -> None:
        self.upstream = upstream
        self.downstream = downstream
        self.port = port
        named = f"port {port!r}" if port is not None else "no port"
        has = f"has ports {sorted(ports)}" if ports else "has one input and names no port"
        super().__init__(f"edge {upstream} to {downstream} names {named}, but {downstream} {has}")


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


class InvalidParamsError(GraphError):
    """A node's parameters, resolved for one replicate, are not valid for its tool.

    Not a fourth rejection of `build`: parameters are checked where a wrong one
    would enter a hash or a kernel, so this is raised by the key walk and by
    `ExecutionPlan.build`, which validates every node — including the ones no
    key is derived for — and does so one statement earlier over the same order.
    A graph that builds may still fail it. It is a `GraphError` because what
    it reports is the same kind of thing the other three do — a document that
    cannot be executed as written, addressed to a node a renderer can colour.

    Wrapping rather than letting pydantic's own error out is the whole point:
    that message carries the field and the model and not the `node_id`, and this
    fires mid-traversal, where "radius must be odd" without a node is a hunt
    through the graph. The `ValidationError` is kept whole on `error` for the
    caller that wants the field back rather than the sentence.
    """

    def __init__(self, node_id: str, error: ValidationError) -> None:
        self.node_id = node_id
        self.error = error
        super().__init__(f"node {node_id} has invalid parameters: {error}")


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One rejection, addressed to the nodes it is about.

    The collect-all half of `Dag.validate`. It carries the `GraphError` rather
    than a message built beside it, so that a caller rendering a broken graph
    and a caller that let `build` raise are reading one sentence — and so that
    the parts each subclass already exposes as attributes
    (`EdgeTypeError.downstream`, `UnresolvedToolError.missing`) do not have to
    be re-parsed out of prose.
    """

    #: Every node this rejection is about, in topological order where one
    #: exists. Both ends for a mistyped edge — an edge is repairable from either
    #: side, which is why the error class carries both, and a caller that wants
    #: only the receiving end reads `error.downstream`. A cycle names every node
    #: that could not be ordered.
    nodes: tuple[str, ...]
    error: GraphError

    @property
    def message(self) -> str:
        """The rejection in words. `str(self.error)`, named for readability."""
        return str(self.error)


@dataclass(frozen=True, slots=True)
class Dag:
    """A `Pipeline` whose tools resolve, whose edges chain, and which sorts.

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
    specs: Mapping[str, ToolSpec]
    #: Upstream node ids per `node_id`, in the document's edge order. Total over
    #: `order` — a root maps to `()` rather than being absent. Kahn's algorithm
    #: below counts them, and a consumer that only needs to know *what* feeds a
    #: node reads this rather than `inputs`.
    upstreams: Mapping[str, tuple[str, ...]]
    #: `(port, upstream node id)` per `node_id`, ordered by port rather than by
    #: the document's edges. Total over `order`. The order is canonical because
    #: it is what the cache key folds: writing the same two edges in the other
    #: order is the same graph, and crossing which parent feeds which port is
    #: not (`cache_key.node_key`). `upstreams` beside it is the same set with
    #: the labels dropped, kept because most readers want exactly that.
    inputs: Mapping[str, tuple[tuple[str | None, str], ...]]
    #: Downstream node ids per `node_id`, in the document's edge order. Total
    #: over `order`.
    downstreams: Mapping[str, tuple[str, ...]]
    #: What one value of each node's output is a value of, or `None` where
    #: nothing can honestly say. Total over `order`. Read by any consumer that
    #: *counts* elements rather than moving them — a detection CSV names its
    #: columns from this, and refuses the node when it is `None`.
    elements: Mapping[str, ElementKind | None]
    #: Column-safe names for the elements above. The kind answers whether a
    #: count is admissible; these names answer what that count is called once
    #: it crosses into CSVs and plot axes.
    element_names: Mapping[str, ElementNames | None]
    #: Whether each node's output is still indexed in source frames. Total over
    #: `order`. False from the first `rate_changing` node onward, and a separate
    #: question from `elements`: one says what a *column* is, this says what a
    #: *row* is. A consumer that turns a row offset into a frame number is wrong
    #: by the decimation factor wherever this is false, silently and by a ratio
    #: plausible enough to survive being looked at.
    source_indexed: Mapping[str, bool]

    @classmethod
    def build(cls, pipeline: Pipeline, registry: ToolRegistry | None = None) -> Dag:
        """Resolve, order, and type-check `pipeline`.

        Args:
            pipeline: The graph, already structurally valid — `Pipeline`'s own
                validator has guaranteed unique ids, edges that name nodes, and
                one producer per node.
            registry: Where tools are looked up. Defaults to the process-wide
                shelf that `sieve.tools` populates on import.

        Raises:
            UnresolvedToolError: if any node names a tool that is not registered
                at that version.
            CycleError: if the graph is cyclic.
            EdgeTypeError: if any edge's endpoints cannot be connected.
        """
        diagnostics, built = cls._walk(pipeline, REGISTRY if registry is None else registry)
        if built is None:
            # Non-empty whenever nothing was built — `_walk` returns one or the
            # other — and the first is the earliest in the fixed order, which is
            # the message this method has always raised.
            raise diagnostics[0].error
        return built

    @classmethod
    def validate(
        cls, pipeline: Pipeline, registry: ToolRegistry | None = None
    ) -> tuple[Diagnostic, ...]:
        """Every reason `pipeline` cannot be executed, empty when it can be.

        `build` without the raise: same rejections, same order, same messages.
        What it buys is the graph that *does not* build — a chain a removal
        broke, a project opened where half the tools are missing — being
        describable node by node rather than one message at a time.

        Args:
            pipeline: The graph, already structurally valid.
            registry: Where tools are looked up. Defaults to the process-wide
                shelf.

        Returns:
            The rejections, earliest first. Empty means `build` will succeed on
            the same two arguments, which is the property that makes this worth
            having rather than a second opinion.
        """
        return cls._walk(pipeline, REGISTRY if registry is None else registry)[0]

    # ---- construction ----------------------------------------------------

    @classmethod
    def _walk(
        cls, pipeline: Pipeline, registry: ToolRegistry
    ) -> tuple[tuple[Diagnostic, ...], Dag | None]:
        """The one walk both modes read: diagnostics, or the graph, never both.

        Returning a union rather than always building would let a caller hold a
        `Dag` that had rejections against it, which is the partly-checked object
        the module docstring refuses. The empty-diagnostics case is the only one
        that constructs.

        The two early returns are the fixed order made structural. An unresolved
        tool leaves the later check with no `ToolSpec` to read, and a cycle
        leaves it with no order to read in — so those two stop the walk, and
        continuing past either would report faults derived from what is already
        known to be missing.
        """
        specs, unresolved = cls._resolve(pipeline, registry)
        if unresolved:
            missing: list[tuple[str, str]] = []
            for node_id in unresolved:
                # Deduplicated because twelve nodes of one missing tool is one
                # thing to install — see `UnresolvedToolError`.
                named = (pipeline.node(node_id).tool_id, pipeline.node(node_id).version)
                if named not in missing:
                    missing.append(named)
            return ((Diagnostic(unresolved, UnresolvedToolError(missing)),), None)
        upstreams, downstreams, inputs = cls._adjacency(pipeline)
        order, unordered = cls._topological(pipeline, upstreams, downstreams)
        if unordered:
            return ((Diagnostic(unordered, CycleError(unordered)),), None)
        edges = cls._edge_faults(order, specs, inputs)
        if edges:
            return (edges, None)
        return (
            (),
            cls(
                pipeline=pipeline,
                order=order,
                specs=specs,
                upstreams=upstreams,
                inputs=inputs,
                downstreams=downstreams,
                elements=cls._elements(order, specs, upstreams),
                element_names=cls._element_names(order, specs, upstreams),
                source_indexed=cls._source_indexed(order, specs, upstreams),
            ),
        )

    @staticmethod
    def _resolve(
        pipeline: Pipeline, registry: ToolRegistry
    ) -> tuple[dict[str, ToolSpec], tuple[str, ...]]:
        """Specs for what resolves, and the ids of what does not.

        Node ids rather than the `(tool_id, version)` pairs the error reports,
        because the two questions have different answers: the user installs a
        set of tools and a renderer colours a set of *nodes*, and twelve arenas
        of one missing detector is one install and twelve red cards.
        """
        specs: dict[str, ToolSpec] = {}
        unresolved: list[str] = []
        for node in pipeline.nodes:
            try:
                specs[node.node_id] = registry.get(node.tool_id, node.version)
            except UnknownToolError:
                unresolved.append(node.node_id)
        return specs, tuple(unresolved)

    @staticmethod
    def _adjacency(
        pipeline: Pipeline,
    ) -> tuple[
        dict[str, tuple[str, ...]],
        dict[str, tuple[str, ...]],
        dict[str, tuple[tuple[str | None, str], ...]],
    ]:
        """Both directions and the labelled one, total over the node set.

        Built as lists and frozen on the way out so that edge order is the
        document's. Nothing downstream depends on that order, but a traversal
        whose output order is the document's is one whose diffs are readable.

        `inputs` is the one exception and deliberately so: it is ordered by port
        because the cache key folds it, and a key that moved when two edges were
        written the other way round would say two spellings of one graph are two
        computations. `SOLE_PORT` is `None` and sorts first on its own, since a
        node has either that one input or named ones and never both.
        """
        up: dict[str, list[str]] = {node.node_id: [] for node in pipeline.nodes}
        down: dict[str, list[str]] = {node.node_id: [] for node in pipeline.nodes}
        ports: dict[str, list[tuple[str | None, str]]] = {
            node.node_id: [] for node in pipeline.nodes
        }
        for edge in pipeline.edges:
            up[edge.downstream].append(edge.upstream)
            down[edge.upstream].append(edge.downstream)
            ports[edge.downstream].append((edge.port, edge.upstream))
        return (
            {node_id: tuple(ids) for node_id, ids in up.items()},
            {node_id: tuple(ids) for node_id, ids in down.items()},
            {
                node_id: tuple(sorted(fed, key=lambda pair: (pair[0] is not None, pair[0] or "")))
                for node_id, fed in ports.items()
            },
        )

    @staticmethod
    def _topological(
        pipeline: Pipeline,
        upstreams: Mapping[str, tuple[str, ...]],
        downstreams: Mapping[str, tuple[str, ...]],
    ) -> tuple[tuple[Node, ...], tuple[str, ...]]:
        """Kahn's algorithm, with declaration order as the tiebreak.

        Returns the order and what could not be ordered. The second is empty
        exactly when the first is total over the node set, and a caller that
        gets a non-empty one must not read the partial order beside it: it is
        every node *outside* the cycle, which is a graph nobody wrote.

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
            return (), tuple(node_id for node_id in remaining if node_id not in placed)
        return tuple(ordered), ()

    @staticmethod
    def _edge_faults(
        order: Sequence[Node],
        specs: Mapping[str, ToolSpec],
        inputs: Mapping[str, tuple[tuple[str | None, str], ...]],
    ) -> tuple[Diagnostic, ...]:
        """Every edge, in topological order, against the input it feeds.

        The order is not needed for correctness — an edge check is local — but
        it decides *which* mismatch is reported first in a graph with several,
        and reporting the earliest is what lets a user fix a chain from the top
        rather than from wherever a dict happened to start.

        The port is resolved before the types are compared, because a miswired
        edge has no `accepts` to be compared against and reporting it as a type
        mismatch would name a stream the tool never declared.

        A root's input is unchecked, and deliberately: what feeds it is the
        replicate's cropped source, which is an array of whatever the decoder
        produces. Checking that would mean this module knowing about codecs,
        and the layer contract is what keeps `dag.py` runnable on a machine
        with none.
        """
        faults: list[Diagnostic] = []
        for node in order:
            spec = specs[node.node_id]
            for port, upstream_id in inputs[node.node_id]:
                accepts = spec.accepts_on(port)
                if accepts is None:
                    named = [name for name in spec.input_ports if name is not None]
                    faults.append(
                        Diagnostic(
                            (upstream_id, node.node_id),
                            PortError(upstream_id, node.node_id, port, named),
                        )
                    )
                    continue
                emits = specs[upstream_id].emits
                if not accepts.admits(emits):
                    faults.append(
                        Diagnostic(
                            (upstream_id, node.node_id),
                            EdgeTypeError(upstream_id, node.node_id, emits, accepts),
                        )
                    )
        return tuple(faults)

    @staticmethod
    def _elements(
        order: Sequence[Node],
        specs: Mapping[str, ToolSpec],
        upstreams: Mapping[str, tuple[str, ...]],
    ) -> dict[str, ElementKind | None]:
        """Element meaning, folded forward from the source.

        One pass in topological order, so a node's upstream is resolved when it
        is reached. `tool_base.node_element` is the conversion and this is only
        the traversal that supplies its second argument — the same split
        `input_warmup_frames` has, so that there is one answer to what a
        preserving tool preserves. What arrives at a node with several parents
        is `_arriving_element`.

        A root's input is the replicate's cropped source, which is frames of
        pixels; `ElementKind.PIXEL` enters here and nowhere else.
        """
        resolved: dict[str, ElementKind | None] = {}
        for node in order:
            upstream = _arriving_element(resolved, upstreams[node.node_id])
            resolved[node.node_id] = node_element(specs[node.node_id].element, upstream)
        return resolved

    @staticmethod
    def _element_names(
        order: Sequence[Node],
        specs: Mapping[str, ToolSpec],
        upstreams: Mapping[str, tuple[str, ...]],
    ) -> dict[str, ElementNames | None]:
        """Element names, folded forward beside `_elements`.

        The source starts as pixels. A kind-redefining tool introduces its own
        names; a relation tool preserves or loses names by the same rule as the
        element meaning.
        """
        elements: dict[str, ElementKind | None] = {}
        names: dict[str, ElementNames | None] = {}
        for node in order:
            fed = upstreams[node.node_id]
            upstream = _arriving_element(elements, fed)
            if not fed:
                upstream_names: ElementNames | None = SOURCE_ELEMENT_NAMES
            elif upstream is None:
                # The noun follows the meaning: where the parents disagreed
                # there is no kind left to name, and a name carried up from one
                # of them would be the wrong column heading on a count over
                # something neither parent emitted.
                upstream_names = None
            else:
                arriving = {names[parent] for parent in fed}
                upstream_names = arriving.pop() if len(arriving) == 1 else None
            spec = specs[node.node_id]
            elements[node.node_id] = node_element(spec.element, upstream)
            names[node.node_id] = node_element_names(
                spec.element, spec.element_names, upstream, upstream_names
            )
        return names

    @staticmethod
    def _source_indexed(
        order: Sequence[Node],
        specs: Mapping[str, ToolSpec],
        upstreams: Mapping[str, tuple[str, ...]],
    ) -> dict[str, bool]:
        """Whether each node still emits one frame per source frame.

        `rate_changing` is already the declaration and `ParamsBase.output_rate`
        already the arithmetic; neither says which *nodes* are downstream of a
        rate change, and that is the question a consumer converting a row offset
        into a frame number has. Folded here rather than derived at the call
        site, because it is a property of the graph and a caller that recomputed
        it would be a second answer.

        The flag, not the rate: a node whose params happen to resolve to 1 is
        still one an executor may reindex, and this is read where a wrong answer
        is a wrong timestamp rather than a slower one.
        """
        indexed: dict[str, bool] = {}
        for node in order:
            spec = specs[node.node_id]
            upstream = all(indexed[parent] for parent in upstreams[node.node_id])
            indexed[node.node_id] = upstream and not spec.rate_changing
        return indexed

    # ---- queries ---------------------------------------------------------

    @property
    def roots(self) -> tuple[Node, ...]:
        """Nodes with no upstream: each is fed the source, or opens its own file.

        Which of the two is `source_roots` below, and it is a property of the
        tool rather than of the graph. In topological order, so a caller feeding
        them frames does so in the
        document's order. A graph with no nodes has no roots; a graph with
        nodes always has at least one, since a graph where every node had an
        upstream would have been rejected as cyclic.
        """
        return tuple(node for node in self.order if not self.upstreams[node.node_id])

    @property
    def leaves(self) -> tuple[Node, ...]:
        """Nodes nothing consumes. What a `Sink` names is usually one of these."""
        return tuple(node for node in self.order if not self.downstreams[node.node_id])

    def element_lost_at(self, node_id: str) -> str:
        """Where on the paths feeding `node_id` the element meaning first went.

        Here rather than in the caller that builds the message, for
        `source_indexed`'s reason: it is a traversal, and a second traversal
        somewhere else is a second answer about the same graph. What it buys is
        the difference between a message a reader can act on and one that sends
        them to the wrong file — every array emitter *has* a declaration
        (`ToolSpec.__post_init__` refuses one without), so a node with no
        meaning never got there by failing to declare, and a message saying so
        points at a tool that is fine.

        The earliest such node in topological order, which is where the
        information was actually lost; every `None` after it is that one
        propagating. Detecting over anything above it still works, and that is
        the action the message can then name.

        Returns a `str` rather than `str | None` so no caller narrows an answer
        that is total under its own precondition. A node that *has* a meaning is
        a caller that has not read `elements` first, which is a mistake worth
        making loud rather than a `None` to thread through.

        Raises:
            ValueError: if `node_id` has an element meaning, so nothing was lost.
            KeyError: if no node in this graph carries that id.
        """
        if self.elements[node_id] is not None:
            raise ValueError(
                f"{node_id} has element meaning {self.elements[node_id]}, so nothing was lost "
                "along the paths feeding it — read `elements` before asking this"
            )
        # Downstream-first, so membership propagates up: `order` is topological,
        # so a node is always visited before the upstreams it names.
        feeding = {node_id}
        for node in reversed(self.order):
            if node.node_id in feeding:
                feeding.update(self.upstreams[node.node_id])
        # Non-empty: `node_id` is in `feeding` and is `None` by the guard above.
        return next(
            node.node_id
            for node in self.order
            if node.node_id in feeding and self.elements[node.node_id] is None
        )

    def spec(self, node_id: str) -> ToolSpec:
        """The resolved tool for `node_id`.

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
        (`decode/reader.py`). Today no tool on the shelf declares a chroma-only
        input, so this is false for every real graph — and the point of deriving
        it rather than hard-coding it is that the first tool which *does* read
        hue flips it back without anyone having to remember that it must.

        **Over-inclusive on purpose, and it is the whole graph rather than the
        roots.** Only roots touch the source frame, so a strict reading would
        ask about them alone; but channel layout propagates — most tools emit
        what they were handed — and a downstream node demanding colour is
        evidence the chain was meant to carry it. An input wrongly included is a
        slower correct answer, an input wrongly omitted is a wrong one served
        from cache and never noticed.

        A tool that leaves `accepts.channels` empty means "any", which includes
        GRAY, so silence is never read as a demand for colour.
        """
        return any(_requires_chroma(spec) for spec in self.specs.values())

    @property
    def source_roots(self) -> tuple[Node, ...]:
        """Roots that read a file of their own rather than the run's footage.

        `roots` split by the one declaration that separates them
        (`adr/a-users-file-wires-in-like-any-other-input.md`): a source tool
        opens the file its path parameter names, so it is neither fed by the
        reader nor keyed off the footage. Derived here rather than at each call
        site because three of them ask — the key walk below, the executor's
        binding, and the caller deciding whether a written crop can stand for a
        graph — and a fourth spelling of "no upstream and a source" would be the
        one that forgot half of it.
        """
        return tuple(node for node in self.roots if self.specs[node.node_id].source is not None)

    def node_keys(
        self,
        *,
        source: str,
        replicate: Replicate | None = None,
        picked: Mapping[str, str] = MappingProxyType({}),
    ) -> dict[str, str]:
        """Every cacheable node's key, for one replicate.

        The traversal `cache_key.py` names and declines to own. One pass in
        topological order, so each node's upstream is already keyed when it is
        reached — which is the whole reason the sort happens before this rather
        than a second walk happening after it.

        **A node absent from the result is a node that must be computed.** Two
        causes, and neither is an error: the tool has not claimed determinism,
        or something upstream of it has not. `NotCacheableError` is swallowed at
        exactly the node that raises it and then propagates for free, because a
        downstream that cannot find its upstream's key has no key of its own to
        build. The alternative — raising out of the walk — would make one
        non-deterministic node in a twelve-node graph cost the cache entries of
        the eleven that are fine.

        v2 took a `backend` here, and a `lowered_prefix` for the decode chain it
        had lowered into ffmpeg. The first has no referent
        (`adr/no-kernel-apparatus.md`); the second arrives with the lowering that
        produces one, which `PLAN.md` does not build until a budget is missed.

        Args:
            source: What identifies the footage — `cache_key.source_identity`
                builds one. Taken as a string rather than a `Path` so that a
                caller that already computed it does not stat the file twice,
                and so this stays runnable against footage that is not present.
                A replicate whose frames were already cut to a written crop is
                passed a *different* source, computed from that artifact; there
                is no flag here for it, because a crop of a crop is a different
                footage rather than a different key derivation.
            replicate: The replicate being processed, whose geometry is an
                ordinary override on the crop node's region
                (`adr/detector-is-a-node.md`) and so reaches the keys through
                `resolved_params` like any other deviation. `None` is the
                baseline a project with no fan-out runs.
            picked: `cache_key.source_identity` per source root, from a caller
                that has resolved each one's path parameter. Absent by default
                and absent per node without penalty: a source root with no
                identity here is left unkeyed, so the subtree below it computes,
                which is `NotCacheableError`'s treatment for the same reason —
                a caller that has not statted the file has no key to give it,
                and inventing one from the pattern would key two files alike.
                This module never opens a file, so nothing here can derive it.

        Returns:
            `node_id` to key, for the cacheable nodes only.

        Raises:
            InvalidParamsError: if a node's resolved parameters are not valid
                for its tool — the one check this module does not do up front,
                done here because this is where they would enter a hash, and
                named after the node because pydantic's own message is not.
        """
        # Derived here rather than passed in, so the key and the reader cannot
        # disagree about what was decoded: whoever opens the reader asks this
        # same graph the same question.
        decode_format: CropFormat = "bgr" if self.needs_chroma else "luma"
        root_key = source_key(source, decode_format=decode_format)
        keys: dict[str, str] = {}
        for node in self.order:
            fed = self.inputs[node.node_id]
            if fed:
                # Port-bound pairs, in `inputs`' canonical order: a node fed on
                # two ports is two keys the digest has to tell apart by which
                # port each arrived on, since `a - b` and `b - a` are fed by the
                # same two keys and are not the same computation. One unkeyed
                # parent takes the node with it, for the reason below.
                if any(parent not in keys for _port, parent in fed):
                    continue
                upstream = tuple((port, keys[parent]) for port, parent in fed)
            elif (opens := self.specs[node.node_id].source) is not None:
                # A source tool keys from its own file, so the footage's key is
                # not its ancestor — folding `root_key` here would make swapping
                # the picked file invisible to the store and make every project
                # over one video agree about a file none of them named. Which
                # flavour follows the reader and nothing else
                # (`adr/a-root-keys-by-its-reader.md`): a file opened through
                # `decode/` is keyed as the footage it stands in for, which is
                # what makes a written crop wired in at a crop node's place fold
                # the string a run over that file as *its* footage folds.
                identity = picked.get(node.node_id)
                if identity is None:
                    continue
                # A root's ancestor arrives on `SOLE_PORT` like any single
                # input: what feeds it is not an edge, but the digest's layout
                # is about arity and not about where the stream came from.
                upstream = (
                    (
                        SOLE_PORT,
                        source_key(identity, decode_format=decode_format)
                        if opens.decoded
                        else picked_key(identity),
                    ),
                )
            else:
                upstream = ((SOLE_PORT, root_key),)
            try:
                keys[node.node_id] = node_key(
                    node,
                    spec=self.specs[node.node_id],
                    upstream=upstream,
                    replicate=replicate,
                )
            except NotCacheableError:
                continue
            except ValidationError as invalid:
                raise InvalidParamsError(node.node_id, invalid) from invalid
        return keys


def linear_order(pipeline: Pipeline) -> tuple[Node, ...]:
    """The pipeline's nodes root to sink, refusing anything but one path.

    Deliberately not `Dag.order`: that one exists for execution and tolerates
    every DAG, while a caller that draws a chain — the tool stack — can only
    host one path. Accepting a genuine DAG here and flattening it would draw
    seams that lie about what feeds what.

    No registry and no `Dag`: this is a question about the graph's *shape*, and
    a chain whose tools are all missing is still a chain. Asking it of an
    unresolvable graph is what lets the stack rebuild from a project before it
    knows whether the project can run.

    Raises:
        GraphError: if the graph branches or is disconnected.
    """
    if not pipeline.nodes:
        return ()
    downstream_of = {edge.upstream: edge.downstream for edge in pipeline.edges}
    if len(downstream_of) != len(pipeline.edges):
        raise GraphError("graph branches — not a chain")
    fed = {edge.downstream for edge in pipeline.edges}
    roots = [node for node in pipeline.nodes if node.node_id not in fed]
    if len(roots) != 1:
        raise GraphError(f"expected one root, found {len(roots)}")
    ordered: list[Node] = [roots[0]]
    while ordered[-1].node_id in downstream_of:
        ordered.append(pipeline.node(downstream_of[ordered[-1].node_id]))
    if len(ordered) != len(pipeline.nodes):
        raise GraphError("graph is disconnected — not a chain")
    return tuple(ordered)


def graph_needs_chroma(pipeline: Pipeline, registry: ToolRegistry | None = None) -> bool:
    """`Dag.needs_chroma` for a graph nobody has built a `Dag` from yet.

    For the caller that must choose a decode format *before* it plans — a render
    worker owns its reader and has to know which format to open it in, and a
    reader is not something a preview session can reopen on its behalf.

    A graph that does not resolve needs colour, because "this tool is missing"
    is not a question about chroma and the caller is about to fail on it
    properly a moment later; answering `True` keeps the fallback the format that
    has always been the default.

    This does build a second `Dag` for a render that will build one again when
    it plans. That is a resolve and a topological sort over a handful of nodes
    against a render measured in seconds, and it is not a second *answer*: both
    derive from this function on the same input, which is the property that
    matters.
    """
    try:
        return Dag.build(pipeline, registry).needs_chroma
    except GraphError:
        return True


def _requires_chroma(spec: ToolSpec) -> bool:
    """Whether `spec` refuses a single-channel frame.

    A demand, not a preference: the question is whether GRAY is *excluded* from
    what this tool accepts, so an empty `channels` tuple — the "any" wildcard
    `ArraySpec` documents — answers no, and so does any set that lists GRAY
    alongside colour layouts. Only a tool that names colour layouts and omits
    GRAY is asking for chroma it would not otherwise get.

    A non-array input (a `TableSpec`) never reads pixels and so never demands
    them, which is why the isinstance is a `False` rather than an error.
    """
    accepts = spec.accepts
    if not isinstance(accepts, ArraySpec) or not accepts.channels:
        return False
    return ChannelSpec.GRAY not in accepts.channels
