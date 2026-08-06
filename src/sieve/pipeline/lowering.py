"""Recognize the one root prefix safe to lower into an FFmpeg source."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, cast

from sieve.core.filter_registry import FilterRegistry
from sieve.core.pipeline_model import Node, Pipeline, resolved_params
from sieve.core.replicates import Replicate
from sieve.core.types import ROI, VideoMetadata
from sieve.decode.lowered import LoweredPrefix, LoweredScale, LoweredStep, roi_parts
from sieve.pipeline.dag import Dag, GraphError
from sieve.pipeline.resolve_source import ResolvedSource


@dataclass(frozen=True, slots=True)
class LoweredGraph:
    """A DAG whose root prefix has moved into the source contract."""

    dag: Dag
    prefix: LoweredPrefix
    removed: tuple[str, ...]


def lower_resolved_source(
    dag: Dag,
    resolved: ResolvedSource,
    *,
    replicate: Replicate | None,
    source_metadata: VideoMetadata,
    decoder_identity: str,
    registry: FilterRegistry | None = None,
    protected_nodes: Iterable[str] = (),
) -> tuple[Dag, ResolvedSource]:
    """Return `dag` and `resolved`, lowered when the safe prefix exists."""
    lowered = lower_root_prefix(
        dag,
        replicate=replicate,
        source_metadata=source_metadata,
        decoder_identity=decoder_identity,
        pre_cropped=resolved.pre_cropped,
        registry=registry,
        protected_nodes=protected_nodes,
    )
    if lowered is None:
        return dag, resolved
    return lowered.dag, resolved.with_lowered_prefix(lowered.prefix)


def lower_root_prefix(
    dag: Dag,
    *,
    replicate: Replicate | None,
    source_metadata: VideoMetadata,
    decoder_identity: str,
    pre_cropped: bool = False,
    registry: FilterRegistry | None = None,
    protected_nodes: Iterable[str] = (),
) -> LoweredGraph | None:
    """Lower a source-space crop plus one area scale, or decline.

    The safe route is intentionally narrow: one root chain, a source-space crop
    (from the replicate boundary or an explicit root crop with no replicate
    crop already applied), and a single `downsample(anti_alias=true)` or
    shrinking `rescale`. A crop after a scale is not source-space and is left in
    Python by declining the route.
    """
    if pre_cropped or dag.needs_chroma or len(dag.roots) != 1:
        return None
    protected = set(protected_nodes)
    root = dag.roots[0]
    source_roi = replicate.roi if replicate is not None else None
    removed: list[str] = []
    steps: list[LoweredStep] = []

    if source_roi is not None:
        crop = source_roi
        scale_node = root
        steps.append(LoweredStep("source-roi", "1", _roi_json(crop)))
    elif _is(root, "crop") and root.node_id not in protected:
        child = _single_child(dag, root)
        if child is None:
            return None
        params = cast(
            Any,
            dag.spec(root.node_id).params_model.model_validate(resolved_params(root, None)),
        )
        crop = cast(ROI, params.roi)
        removed.append(root.node_id)
        steps.append(LoweredStep("crop", root.version, params.canonical_json()))
        scale_node = child
    else:
        return None

    if scale_node.node_id in protected:
        return None
    scale = _scale(
        dag,
        scale_node,
        replicate,
        crop.clamped_to(source_metadata.width, source_metadata.height),
    )
    if scale is None:
        return None
    removed.append(scale_node.node_id)
    steps.append(LoweredStep(scale_node.filter_id, scale_node.version, scale.params_json))
    if not _can_remove(dag, tuple(removed), protected):
        return None

    ffmpeg_roi = crop.clamped_to(source_metadata.width, source_metadata.height)
    prefix = LoweredPrefix(
        decoder_identity=decoder_identity,
        source_roi=crop,
        ffmpeg_roi=ffmpeg_roi,
        scale=scale,
        steps=tuple(steps),
    )
    try:
        lowered_dag = Dag.build(_without_nodes(dag.pipeline, removed), registry)
    except GraphError:
        return None
    return LoweredGraph(dag=lowered_dag, prefix=prefix, removed=tuple(removed))


def _is(node: Node, filter_id: str) -> bool:
    return node.filter_id == filter_id and node.version == "1.0.0"


def _single_child(dag: Dag, node: Node) -> Node | None:
    children = dag.downstreams[node.node_id]
    if len(children) != 1:
        return None
    child_id = children[0]
    if dag.upstreams[child_id] != (node.node_id,):
        return None
    return dag.pipeline.node(child_id)


def _scale(dag: Dag, node: Node, replicate: Replicate | None, crop: ROI) -> LoweredScale | None:
    if _is(node, "downsample"):
        params = cast(
            Any,
            dag.spec(node.node_id).params_model.model_validate(resolved_params(node, replicate)),
        )
        anti_alias = bool(params.anti_alias)
        factor = int(params.factor)
        if not anti_alias:
            return None
        out_width = crop.width // factor
        out_height = crop.height // factor
        if out_width <= 0 or out_height <= 0:
            return None
        return LoweredScale(
            filter_id=node.filter_id,
            version=node.version,
            params_json=params.canonical_json(),
            output_width=out_width,
            output_height=out_height,
        )
    if _is(node, "rescale"):
        params = cast(
            Any,
            dag.spec(node.node_id).params_model.model_validate(resolved_params(node, replicate)),
        )
        scale = float(params.scale)
        if scale >= 1.0:
            return None
        return LoweredScale(
            filter_id=node.filter_id,
            version=node.version,
            params_json=params.canonical_json(),
            output_width=max(1, round(crop.width * scale)),
            output_height=max(1, round(crop.height * scale)),
        )
    return None


def _can_remove(dag: Dag, removed: tuple[str, ...], protected: set[str]) -> bool:
    removed_set = set(removed)
    remaining = [node for node in dag.order if node.node_id not in removed_set]
    if not remaining:
        return False
    for node_id in removed_set:
        for child in dag.downstreams[node_id]:
            if child in removed_set:
                continue
            if child in protected:
                return False
            if tuple(dag.upstreams[child]) != (node_id,):
                return False
    return True


def _without_nodes(pipeline: Pipeline, removed: Iterable[str]) -> Pipeline:
    removed_set = set(removed)
    return Pipeline(
        nodes=tuple(node for node in pipeline.nodes if node.node_id not in removed_set),
        edges=tuple(
            edge
            for edge in pipeline.edges
            if edge.upstream not in removed_set and edge.downstream not in removed_set
        ),
    )


def _roi_json(roi: ROI) -> str:
    x, y, width, height = roi_parts(roi)
    return json.dumps(
        {"height": height, "width": width, "x": x, "y": y},
        sort_keys=True,
        separators=(",", ":"),
    )
