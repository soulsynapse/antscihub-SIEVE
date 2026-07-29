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
reader is a `FrameSource` rather than a `VideoReader` so a run over materialized
frames uses the same executor with a different source, not a mode.

**A stateful node keeps its state in its binding, and is never served a cache
entry.** The second half is not enforced here — `FilterSpec.cacheable` excludes
`stateful`, so the plan carries no key for such a node and the `key is None`
branch below already computes it and stores nothing. A stateful node must see
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

**A crop on every root, every frame — unless the reader already is one.** The
replicate's ROI is what the graph consumes, and `plan.roi` is where "which
pixels" is decided: it is the replicate's region over the parent, and `None`
over a materialized crop of that same replicate, whose file holds those pixels
already (`pipeline/resolve_source.py`). Nothing here knows which it was handed;
the plan resolved it, and the loop below crops or does not. `CropArtifact`
explains why an artifact is a source with an
identity of its own rather than a proxy for the parent.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Protocol, cast

from sieve.backend.dispatch import KERNELS, Kernel, KernelRegistry, MergingKernel
from sieve.core.filter_base import Mode
from sieve.core.pipeline_model import Node
from sieve.core.types import ROI, ChannelSpec, Frame
from sieve.pipeline.cache import FrameStore, NullFrameStore
from sieve.pipeline.plan import ExecutionPlan


class FormatMismatchError(RuntimeError):
    """The reader's decode format is not the one this run's keys were derived
    under.

    A defect rather than a user error, which is why it is a `RuntimeError` and
    not something a command catches to print nicely: nothing a user types
    chooses the format, so reaching this means two call sites derived it from
    different graphs. See `_check_format`.
    """


class UnrunnableNodeError(RuntimeError):
    """A node this graph contains cannot be executed by this executor.

    Not a `GraphError`: the graph is valid and the plan for it is buildable and
    useful — a dry run, a cost estimate, and a storage prediction all work on a
    graph containing one of these. What is missing is a way to *call* the node,
    and that is a property of the executor rather than of the document, so it is
    raised here and at run time rather than by `Dag.build` or `ExecutionPlan`.

    Two causes, one root cause: `Kernel` is one frame in, one frame out. A
    `WINDOWED` filter needs a span, and a `rate_changing` filter needs to emit
    nothing for some inputs. `dispatch.py` declines to invent those protocols
    before a filter needs one, so this names the gap instead of guessing at it.
    A node with several upstreams was the third cause until the temporal chain
    needed one; `MergingKernel` is its protocol now, and the executor hands it
    a frame per declared port.
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
    #: The frame as decoded, *before* the replicate crop — the crop is what
    #: the graph consumes, but the consumer this field exists for is a
    #: viewport that shows the whole frame (render-fed playback), and a crop
    #: cannot be undone. `None` when every root was served from the store and
    #: no decode happened, which is exactly the warm re-render where there is
    #: nothing to share. Carrying it costs one frame's reference for as long
    #: as the caller holds this, the same argument as `outputs` above.
    #:
    #: Read `source_cropped` before believing that promise: when the run is
    #: served from a materialized crop there *is* no whole frame to have, and
    #: this field carries the crop.
    source: Frame | None = None
    #: Whether `source` is already the replicate's crop rather than the whole
    #: decoded frame — `plan.pre_cropped`, carried to the consumer.
    #:
    #: It exists because the field above promises something a crop-served run
    #: cannot keep, and a consumer that painted a crop where it expected a frame
    #: would be showing a region of the arena as the whole of it. Rule 6 in its
    #: mirror direction: never let a result look better-founded than it is. The
    #: one consumer today declines the frame on this flag rather than drawing it
    #: (`gui/preview_runner.py`, feeding `gui/render_ring.py`).
    source_cropped: bool = False

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
    # `plan.roi`, not `plan.replicate.roi`: a run served from a materialized
    # crop has its replicate — its overrides are what the params resolved from —
    # and no crop left to apply. The plan is the one place those two facts are
    # reconciled.
    roi = plan.roi

    for index in plan.decode_range:
        decoded: Frame | None = None
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
            fed = plan.dag.ports[node.node_id]
            incoming: Frame | Mapping[str, Frame]
            if len(fed) > 1:
                # A merging node takes a frame per port. No alignment machinery:
                # every node in this loop computes the same source index in
                # lockstep, so its upstreams' outputs for `index` — however
                # different their warmup, and whether computed or served from
                # the store — are already in `outputs` by topological order.
                incoming = {port: outputs[parent] for port, parent in fed.items()}
            elif fed:
                incoming = outputs[next(iter(fed.values()))]
            else:
                if source is None:
                    # The one place the reader is touched, and only once per
                    # frame however many roots there are: a graph with two
                    # roots crops the same decoded frame once rather than
                    # seeking twice. `decoded` outlives the crop so the
                    # result below can carry the whole frame.
                    decoded = reader.read(index)
                    _check_format(decoded, plan)
                    source = decoded if roi is None else _crop(decoded, roi)
                incoming = source
            produced = _run_node(node, incoming, index, plan, bindings)
            outputs[node.node_id] = produced
            if key is not None:
                keep.put(key, index, produced)
        if index >= plan.span.start:
            yield FrameResult(
                index=index,
                outputs=outputs,
                from_cache=frozenset(hits),
                source=decoded,
                source_cropped=plan.pre_cropped,
            )


def _check_format(decoded: Frame, plan: ExecutionPlan) -> None:
    """Refuse a reader whose format is not the one the keys were derived under.

    The failure this catches is the one that leaves no trace. `source_key`
    hashes `plan.luma`, so a reader opened in the other format produces
    correctly-shaped frames computed from the wrong pixels, stored under keys
    that say otherwise — and the symptom is a preview that looks plausible and
    a cache that stays poisoned for the rest of the session. This check makes a
    disagreement between any two of them loud.

    Costs one enum comparison per decoded frame, which is nothing beside the
    decode that produced it, so it is not hoisted to the first frame only: a
    reader that changed format mid-run is exactly as wrong as one that started
    wrong, and a first-frame check would miss it.
    """
    if (decoded.channels is ChannelSpec.GRAY) == plan.luma:
        return
    wanted = "luma" if plan.luma else "colour"
    raise FormatMismatchError(
        f"this run is keyed for {wanted} but the reader handed {decoded.channels}. Every frame "
        "it computes would be stored under a key that names the other format."
    )


def _bind(
    plan: ExecutionPlan, kernels: KernelRegistry
) -> dict[str, Kernel[Any] | MergingKernel[Any]]:
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
    bindings: dict[str, Kernel[Any] | MergingKernel[Any]] = {}
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
    node: Node,
    incoming: Frame | Mapping[str, Frame],
    index: int,
    plan: ExecutionPlan,
    bindings: Mapping[str, Kernel[Any] | MergingKernel[Any]],
) -> Frame:
    """One kernel call, with the frame index checked on the way out.

    The check is cheap and closes a hole nothing else can see: the store is
    keyed by source frame index, so a streaming kernel that renumbered its
    output would write an entry under the wrong index and serve it back later
    as a different frame's result. That is a wrong answer from cache, which
    `cache_key.py`'s asymmetry rule says is the failure to spend a comparison
    on. A filter that genuinely reindexes is `rate_changing` and was already
    refused above. Checked against the loop's index rather than the input's,
    which for a merging node is also the assertion that its inputs were
    aligned — every frame handed over carries `index` or something upstream
    already failed this same check.

    The two casts are the executor trusting the registration guards: which
    calling convention a node gets is decided by its spec's `input_ports`, and
    `@kernel` / `@merging_kernel` refused at import any pairing where the
    callable disagrees with that declaration.
    """
    params = plan.params[node.node_id]
    if isinstance(incoming, Frame):
        produced = cast("Kernel[Any]", bindings[node.node_id])(incoming, params)
    else:
        produced = cast("MergingKernel[Any]", bindings[node.node_id])(incoming, params)
    if produced.index != index:
        spec = plan.dag.spec(node.node_id)
        raise UnrunnableNodeError(
            f"{node.node_id} ({spec.filter_id} {spec.version}) returned frame "
            f"{produced.index} for input frame {index}; a streaming filter preserves "
            "the index, and the cache is keyed on it"
        )
    return produced
