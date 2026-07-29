

















































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
    pass









class UnrunnableNodeError(RuntimeError):
    pass

















class FrameSource(Protocol):









    def read(self, index: int) -> Frame:

        ...


@dataclass(frozen=True, slots=True)
class FrameResult:










    index: int

    outputs: Mapping[str, Frame]


    from_cache: frozenset[str]











    source: Frame | None = None









    source_cropped: bool = False

    def __getitem__(self, node_id: str) -> Frame:





        return self.outputs[node_id]


def execute(
    plan: ExecutionPlan,
    reader: FrameSource,
    *,
    store: FrameStore | None = None,
    kernels: KernelRegistry | None = None,
) -> Iterator[FrameResult]:






























    shelf = KERNELS if kernels is None else kernels
    keep = NullFrameStore() if store is None else store
    bindings = _bind(plan, shelf)




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





                incoming = {port: outputs[parent] for port, parent in fed.items()}
            elif fed:
                incoming = outputs[next(iter(fed.values()))]
            else:
                if source is None:





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


        bindings[node.node_id] = kernels.select(spec, (plan.backend_for(node.node_id),)).start()
    return bindings


def _crop(frame: Frame, roi: ROI) -> Frame:








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
