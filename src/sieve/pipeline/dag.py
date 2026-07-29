from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from sieve.backend.dispatch import Backend
from sieve.core.filter_base import (
    ArraySpec,
    ElementKind,
    FilterSpec,
    StreamSpec,
    node_element,
)
from sieve.core.filter_registry import REGISTRY, FilterRegistry, UnknownFilterError
from sieve.core.pipeline_model import Node, Pipeline
from sieve.core.replicates import Replicate
from sieve.core.types import ChannelSpec
from sieve.pipeline.cache_key import NotCacheableError, node_key, source_key


class GraphError(ValueError):
    pass


class UnresolvedFilterError(GraphError):
    def __init__(self, missing: Sequence[tuple[str, str]]) -> None:
        self.missing = tuple(missing)
        listed = ", ".join(
            f"{filter_id} {version}" for filter_id, version in self.missing
        )
        super().__init__(
            f"no filter {listed}" if len(self.missing) == 1 else f"no filters: {listed}"
        )


class CycleError(GraphError):
    def __init__(self, nodes: Iterable[str]) -> None:
        self.nodes = tuple(sorted(nodes))
        super().__init__(
            f"pipeline contains a cycle among nodes: {', '.join(self.nodes)}"
        )


class PortWiringError(GraphError):
    def __init__(self, node_id: str, message: str) -> None:
        self.node_id = node_id
        super().__init__(message)


class EdgeTypeError(GraphError):
    def __init__(
        self,
        upstream: str,
        downstream: str,
        port: str,
        emits: StreamSpec,
        accepts: StreamSpec,
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
    pipeline: Pipeline

    order: tuple[Node, ...]

    specs: Mapping[str, FilterSpec]

    upstreams: Mapping[str, tuple[str, ...]]

    downstreams: Mapping[str, tuple[str, ...]]

    ports: Mapping[str, Mapping[str, str]]

    elements: Mapping[str, ElementKind | None]

    source_indexed: Mapping[str, bool]

    @classmethod
    def build(cls, pipeline: Pipeline, registry: FilterRegistry | None = None) -> Dag:
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
            elements=cls._elements(order, specs, ports),
            source_indexed=cls._source_indexed(order, specs, ports),
        )

    @staticmethod
    def _resolve(pipeline: Pipeline, registry: FilterRegistry) -> dict[str, FilterSpec]:
        specs: dict[str, FilterSpec] = {}
        missing: list[tuple[str, str]] = []
        for node in pipeline.nodes:
            try:
                specs[node.node_id] = registry.get(node.filter_id, node.version)
            except UnknownFilterError:
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
        for node in order:
            declared = specs[node.node_id].input_ports
            for port, upstream_id in ports[node.node_id].items():
                accepts = declared[port]
                emits = specs[upstream_id].emits
                if not accepts.admits(emits):
                    raise EdgeTypeError(upstream_id, node.node_id, port, emits, accepts)

    @staticmethod
    def _elements(
        order: Sequence[Node],
        specs: Mapping[str, FilterSpec],
        ports: Mapping[str, Mapping[str, str]],
    ) -> dict[str, ElementKind | None]:
        resolved: dict[str, ElementKind | None] = {}
        for node in order:
            fed = ports[node.node_id]
            if not fed:
                upstream: ElementKind | None = ElementKind.PIXEL
            else:
                arriving = {resolved[parent] for parent in fed.values()}
                upstream = arriving.pop() if len(arriving) == 1 else None
            resolved[node.node_id] = node_element(specs[node.node_id].element, upstream)
        return resolved

    @staticmethod
    def _source_indexed(
        order: Sequence[Node],
        specs: Mapping[str, FilterSpec],
        ports: Mapping[str, Mapping[str, str]],
    ) -> dict[str, bool]:
        indexed: dict[str, bool] = {}
        for node in order:
            spec = specs[node.node_id]
            upstream = all(indexed[parent] for parent in ports[node.node_id].values())
            indexed[node.node_id] = upstream and not spec.rate_changing
        return indexed

    @property
    def roots(self) -> tuple[Node, ...]:
        return tuple(node for node in self.order if not self.upstreams[node.node_id])

    @property
    def leaves(self) -> tuple[Node, ...]:
        return tuple(node for node in self.order if not self.downstreams[node.node_id])

    def element_lost_at(self, node_id: str) -> str:
        if self.elements[node_id] is not None:
            raise ValueError(
                f"{node_id} has element meaning {self.elements[node_id]}, so nothing was lost "
                "along the paths feeding it — read `elements` before asking this"
            )
        feeding = {node_id}
        for node in reversed(self.order):
            if node.node_id in feeding:
                feeding.update(self.upstreams[node.node_id])
        return next(
            node.node_id
            for node in self.order
            if node.node_id in feeding and self.elements[node.node_id] is None
        )

    def spec(self, node_id: str) -> FilterSpec:
        return self.specs[node_id]

    @property
    def needs_chroma(self) -> bool:
        return any(_requires_chroma(spec) for spec in self.specs.values())

    def node_keys(
        self,
        *,
        source: str,
        backend: Backend | Mapping[str, Backend],
        replicate: Replicate | None = None,
        pre_cropped: bool = False,
    ) -> dict[str, str]:
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
                (port,) = self.specs[node.node_id].input_ports
                upstream = {port: root_key}
            try:
                keys[node.node_id] = node_key(
                    node,
                    spec=self.specs[node.node_id],
                    upstream=upstream,
                    backend=(
                        backend[node.node_id]
                        if isinstance(backend, Mapping)
                        else backend
                    ),
                    replicate=replicate,
                )
            except NotCacheableError:
                continue
        return keys


def graph_needs_chroma(
    pipeline: Pipeline, registry: FilterRegistry | None = None
) -> bool:
    try:
        return Dag.build(pipeline, registry).needs_chroma
    except GraphError:
        return True


def _requires_chroma(spec: FilterSpec) -> bool:
    accepts = spec.accepts
    if not isinstance(accepts, ArraySpec) or not accepts.channels:
        return False
    return ChannelSpec.GRAY not in accepts.channels
