"""The single shared execution path: a plan, a reader, and a store go in.

CLI, GUI, and HPC call this identically. The GUI adds a *view* over it — a
thread, a coalescer, a progress signal — and never a second traversal, because
two execution paths is two answers to what a project computes and the
disagreement would be invisible: both would report success against caches keyed
on their own arithmetic.

**What is left here is only the loop.** Ordering came from `Dag`, keys and
lead-in and resolved parameters came from `ExecutionPlan`, and where a computed
frame goes came from `FrameStore`. This module decodes, crops, dispatches, and
discards the lead-in. Everything it would otherwise have had to invent is
somewhere that can be tested without a codec.

**Decode is lazy, per frame.** The source frame is fetched on the first root
that misses the cache and not at all when every root hits, which is what makes
re-running a tuned clip cost nothing rather than cost a seek per frame. The
reader is a `FrameSource` rather than a `VideoReader` for the same reason the
store is a protocol: a run over materialized frames (VISION step 4) is the same
executor with a different source, not a mode.

**A stateful node keeps its state in its binding, and is never served a cache
entry.** The second half is not enforced here — `FilterSpec.cacheable` excludes
`stateful`, so the plan carries no key for such a node and the `key is None`
branch below already computes it and stores nothing. Why the category is
excluded is
`docs/findings/2026.07.26-stateful-output-is-not-keyed-by-what-it-is.md`; what
matters to this loop is the consequence, which is that a stateful node sees
every frame of `decode_range` in order and never a gap. A store that could serve
frame `i-1` and miss frame `i` would leave the kernel running on a state that
had seen nothing, and there is no branch here defending against that because
there is no key to hit. What the lead-in is for finally has a consumer: those
frames reach the kernel, settle its state, and are discarded before the caller
sees anything.

**The backend is the plan's, per node.** `KernelRegistry.select` is asked for
`plan.backend_for(node_id)` alone rather than for a preference order, because
the plan's keys already have that backend hashed into them for every filter
that is not `backend_agnostic`. Letting the registry fall back to CPU here
would write GPU-keyed entries containing CPU output, which is the one cache
failure that is silent. Choosing is the plan's job precisely so that by the
time execution starts there is nothing left to choose — a fallback here could
only ever contradict a key that has already been derived.

**A crop on every root, every frame.** The replicate's ROI is what the graph
consumes; the materialized crop VISION step 4 offers is a faster route to the
same pixels and never a different input. See
`docs/findings/2026.07.25-the-crop-belongs-in-the-graph.md`.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from sieve.backend.dispatch import KERNELS, Kernel, KernelRegistry
from sieve.core.filter_base import Mode
from sieve.core.pipeline_model import Node
from sieve.core.types import ROI, Frame
from sieve.pipeline.cache import FrameStore, NullFrameStore
from sieve.pipeline.plan import ExecutionPlan


class UnrunnableNodeError(RuntimeError):
    """A node this graph contains cannot be executed by this executor.

    Not a `GraphError`: the graph is valid and the plan for it is buildable and
    useful — a dry run, a cost estimate, and a storage prediction all work on a
    graph containing one of these. What is missing is a way to *call* the node,
    and that is a property of the executor rather than of the document, so it is
    raised here and at run time rather than by `Dag.build` or `ExecutionPlan`.

    Three causes, all one root cause: `Kernel` is one frame in, one frame out.
    A `WINDOWED` filter needs a span, a `rate_changing` filter needs to emit
    nothing for some inputs, and a node with two upstreams needs two frames.
    `dispatch.py` declines to invent the second protocol before a filter needs
    one, so this names the gap instead of guessing at it.
    """


class FrameSource(Protocol):
    """Random access to source frames by index.

    `VideoReader` satisfies it. So does a Zarr-backed reader over a
    materialized crop, and so does a list of frames in a test — which is why
    this is here rather than the concrete class: `sieve.pipeline` importing
    `sieve.decode.reader` would put a codec underneath the one module that most
    needs to run without one.
    """

    def read(self, index: int) -> Frame:
        """The frame at `index`, in source coordinates and uncropped."""
        ...


@dataclass(frozen=True, slots=True)
class FrameResult:
    """Every node's output for one source frame.

    All nodes rather than only the leaves: the GUI shows intermediates, a
    checkpoint materializes one, and the cost of carrying them is one frame per
    node held for as long as the caller holds this — which it already paid to
    compute them. A caller wanting one node indexes for it.
    """

    #: The source frame index these outputs derive from. Authoritative, and
    #: preserved through every node — see `_run_node`.
    index: int
    #: `node_id` to that node's output.
    outputs: Mapping[str, Frame]
    #: Which nodes were served from the store rather than computed. What a HUD
    #: reports and what a test asserts caching actually happened on.
    from_cache: frozenset[str]

    def __getitem__(self, node_id: str) -> Frame:
        """That node's output.

        Raises:
            KeyError: if the plan did not compute it.
        """
        return self.outputs[node_id]


def execute(
    plan: ExecutionPlan,
    reader: FrameSource,
    *,
    store: FrameStore | None = None,
    kernels: KernelRegistry | None = None,
) -> Iterator[FrameResult]:
    """Run `plan` against `reader`, yielding one result per frame of the span.

    A generator, so a caller cancels by stopping consumption and the memory held
    is one frame per node rather than one per node per frame. The GUI's cheapest
    correct cancellation is to abandon the iterator; nothing here needs a flag.

    Lead-in frames are computed and stored but never yielded — they exist to
    warm stateful filters, and handing them to a caller would make the discard
    the caller's problem in every one of three call sites.

    Args:
        plan: What to run. Its `decode_range` is what the reader is asked for.
        reader: Where source frames come from.
        store: Where computed frames are looked up and kept. Defaults to
            keeping nothing, so a caller that has not thought about caching gets
            correct results rather than an unbounded dict it did not ask for.
        kernels: The kernel shelf. Defaults to the process-wide one that
            `sieve.filters` populates on import.

    Yields:
        One `FrameResult` per frame in `plan.span`, in order.

    Raises:
        UnrunnableNodeError: if any node cannot be called — checked once, up
            front, so a graph that cannot finish does not first decode half of
            it.
        NoKernelError: if a node has no kernel for the plan's backend on this
            machine. Also up front.
        VideoDecodeError: if a frame in the range cannot be read.
    """
    shelf = KERNELS if kernels is None else kernels
    keep = NullFrameStore() if store is None else store
    bindings = _bind(plan, shelf)
    roi = None if plan.replicate is None else plan.replicate.roi

    for index in plan.decode_range:
        source: Frame | None = None
        outputs: dict[str, Frame] = {}
        hits: set[str] = set()
        for node in plan.dag.order:
            key = plan.keys.get(node.node_id)
            cached = None if key is None else keep.get(key, index)
            if cached is not None:
                outputs[node.node_id] = cached
                hits.add(node.node_id)
                continue
            parents = plan.dag.upstreams[node.node_id]
            if parents:
                incoming = outputs[parents[0]]
            else:
                if source is None:
                    # The one place the reader is touched, and only once per
                    # frame however many roots there are: a graph with two roots
                    # crops the same decoded frame twice rather than seeking
                    # twice.
                    decoded = reader.read(index)
                    source = decoded if roi is None else _crop(decoded, roi)
                incoming = source
            produced = _run_node(node, incoming, plan, bindings)
            outputs[node.node_id] = produced
            if key is not None:
                keep.put(key, index, produced)
        if index >= plan.span.start:
            yield FrameResult(index=index, outputs=outputs, from_cache=frozenset(hits))


def _bind(plan: ExecutionPlan, kernels: KernelRegistry) -> dict[str, Kernel[Any]]:
    """Resolve every node to the callable that implements it, or refuse.

    Up front, over the whole graph, before a frame is read. The alternative —
    resolving lazily at the node — would decode the lead-in, run four nodes,
    and then discover that the fifth is `WINDOWED`, which is a minute of work
    to deliver a message that was available immediately. Every rejection here
    is static: it reads declarations and the kernel shelf, and nothing about
    the footage can change the answer.

    **`start()` rather than `.run`, and that is what makes state per-run.** This
    function is called once inside `execute`, so a stateful node's state is
    created here, lives in the closure `start` returned, and is unreachable from
    anywhere else — two concurrent `execute` calls over the same node are two
    bindings and therefore two states, with no registry entry, no dict keyed by
    node id, and nothing to reset between runs. The generator is the state's
    lifetime, which is also the right one: a caller that cancels a preview by
    abandoning the iterator drops the half-warmed background model with it.
    """
    bindings: dict[str, Kernel[Any]] = {}
    for node in plan.dag.order:
        spec = plan.dag.spec(node.node_id)
        if spec.mode is not Mode.STREAMING:
            raise UnrunnableNodeError(
                f"{node.node_id} ({spec.filter_id} {spec.version}) is {spec.mode}, and the kernel "
                "protocol is one frame in, one frame out — a windowed filter needs a span"
            )
        if spec.rate_changing:
            raise UnrunnableNodeError(
                f"{node.node_id} ({spec.filter_id} {spec.version}) is rate-changing, and the "
                "kernel protocol has no way to emit nothing for an input frame"
            )
        if len(plan.dag.upstreams[node.node_id]) > 1:
            raise UnrunnableNodeError(
                f"{node.node_id} ({spec.filter_id} {spec.version}) has "
                f"{len(plan.dag.upstreams[node.node_id])} upstreams, and the kernel protocol takes "
                "one frame — a merging filter needs named ports on Edge first"
            )
        # A one-element preference: see the module docstring. A fallback here
        # would write entries keyed on a backend that did not produce them.
        bindings[node.node_id] = kernels.select(spec, (plan.backend_for(node.node_id),)).start()
    return bindings


def _crop(frame: Frame, roi: ROI) -> Frame:
    """The replicate's region of `frame`, clamped to what was decoded.

    Clamped rather than checked, because an ROI drawn against the source's
    dimensions can legitimately exceed a frame the reader returned smaller —
    and because `ROI.clamped_to` is already the one definition of what "trim to
    fit" means. Index and channel layout carry through: a crop changes which
    pixels, never which frame.
    """
    return Frame(
        data=roi.clamped_to(frame.width, frame.height).crop(frame.data),
        index=frame.index,
        channels=frame.channels,
    )


def _run_node(
    node: Node, incoming: Frame, plan: ExecutionPlan, bindings: Mapping[str, Kernel[Any]]
) -> Frame:
    """One kernel call, with the frame index checked on the way out.

    The check is cheap and closes a hole nothing else can see: the store is
    keyed by source frame index, so a streaming kernel that renumbered its
    output would write an entry under the wrong index and serve it back later
    as a different frame's result. That is a wrong answer from cache, which
    `cache_key.py`'s asymmetry rule says is the failure to spend a comparison
    on. A filter that genuinely reindexes is `rate_changing` and was already
    refused above.
    """
    produced = bindings[node.node_id](incoming, plan.params[node.node_id])
    if produced.index != incoming.index:
        spec = plan.dag.spec(node.node_id)
        raise UnrunnableNodeError(
            f"{node.node_id} ({spec.filter_id} {spec.version}) returned frame "
            f"{produced.index} for input frame {incoming.index}; a streaming filter preserves "
            "the index, and the cache is keyed on it"
        )
    return produced
