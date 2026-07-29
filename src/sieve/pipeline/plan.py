from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from sieve.backend.dispatch import Backend
from sieve.core.filter_base import ParamsBase, input_warmup_frames
from sieve.core.pipeline_model import ClipRange, Node, resolved_params
from sieve.core.replicates import Replicate
from sieve.core.types import ROI
from sieve.pipeline.dag import Dag


@dataclass(frozen=True, slots=True)
class ExecutionPlan:
    dag: Dag

    span: ClipRange

    params: Mapping[str, ParamsBase]

    keys: Mapping[str, str]

    lead_in: int

    backends: Mapping[str, Backend]
    replicate: Replicate | None

    pre_cropped: bool = False

    source_start: int = 0

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
        source_start: int = 0,
    ) -> ExecutionPlan:
        params = {
            node.node_id: dag.specs[node.node_id].params_model.model_validate(
                resolved_params(node, replicate)
            )
            for node in dag.order
        }
        backends = {
            node.node_id: (
                backend[node.node_id] if isinstance(backend, Mapping) else backend
            )
            for node in dag.order
        }
        return cls(
            dag=dag,
            span=span,
            params=params,
            keys=dag.node_keys(
                source=source,
                backend=backends,
                replicate=replicate,
                pre_cropped=pre_cropped,
            ),
            lead_in=_lead_in(dag, params),
            backends=backends,
            replicate=replicate,
            pre_cropped=pre_cropped,
            source_start=source_start,
        )

    @property
    def roi(self) -> ROI | None:
        if self.pre_cropped or self.replicate is None:
            return None
        return self.replicate.roi

    @property
    def decode_start(self) -> int:
        return max(self.span.start - self.lead_in, self.source_start)

    @property
    def decode_range(self) -> range:
        return range(self.decode_start, self.span.end)

    @property
    def lead_in_shortfall(self) -> int:
        return self.lead_in - (self.span.start - self.decode_start)

    @property
    def warmed(self) -> bool:
        return self.lead_in_shortfall == 0

    @property
    def luma(self) -> bool:
        return not self.dag.needs_chroma

    def backend_for(self, node_id: str) -> Backend:
        return self.backends[node_id]

    def key(self, node_id: str) -> str | None:
        self.dag.spec(node_id)
        return self.keys.get(node_id)


def _lead_in(dag: Dag, params: Mapping[str, ParamsBase]) -> int:
    need: dict[str, int] = {}
    for node in reversed(dag.order):
        downstream_need = max(
            (need[downstream] for downstream in dag.downstreams[node.node_id]),
            default=0,
        )
        step = (dag.specs[node.node_id], params[node.node_id])
        need[node.node_id] = input_warmup_frames(step, downstream_need)
    return max((need[root.node_id] for root in dag.roots), default=0)


def root_paths(dag: Dag, node_id: str) -> tuple[tuple[Node, ...], ...]:
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
