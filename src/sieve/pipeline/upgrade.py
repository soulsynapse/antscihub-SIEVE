"""Carry a saved document's crop and span into the graph that computes them.

The transform behind the schema flip
(`docs/todo/the-graph-carries-the-crop-the-span-and-the-detector.md`): a
document whose `Replicate.roi` and `Project.clip` decide a result from outside
the graph, rewritten so the graph decides it. A crop node above every root
carrying each replicate's box as a pin, a span node below every leaf carrying
the clip's bounds, and the two fields gone from the document.

**It lives in `pipeline/` and not on `Project` as a `model_validator`, which is
where the item asked for it.** Synthesizing a node means naming a filter — its
id, its version, and the identity value of its parameters — and
`core/pipeline_model.py` is deliberately not registry-aware, for the reason its
own docstring gives: a project must open on a machine where a filter is
missing. A validator spelling `crop` and `span` in `core/` would also be three
new entries on `test_filter_id_spelling.py`'s shrink-only list, which is REWORK
R4's enumeration coming back in the one module that most needs to stay blind to
it. So no literal here is typed: the ids and versions come off the registered
specs, and the identity values come from the filters that own them.

The consequence for the flip is that a v6 reader cannot be a validator either.
Whatever loads a document has to upgrade it *before* handing it to `Project`,
which puts the reader in this layer too.

**Node ids are derived, never generated.** `Node.node_id`'s default is a fresh
uuid, and an upgrade that used it would give two machines upgrading one file
two different documents — which is the one thing the artifact exists to stop.
`crop-<root>` and `span-<leaf>` are derived from ids the document already
carries, so upgrading twice is upgrading once.

**Every replicate pins its own box; the node's baseline is the identity crop.**
The alternative — baseline from the first replicate, the rest pinning their
deviation — is what `edited_params` does for every other parameter, and it is
wrong for this one: under v5 no replicate's geometry followed any other's, so a
later edit to the baseline would move an arena that never agreed to it. An
unpinned baseline of `WHOLE_FRAME` also means the next arena drawn opens on the
whole frame rather than on the last one's box, which is what the GUI already
does.

**The detector is refused, by name, and that is not a scoping decision.** Three
things block it, and the first is fatal on its own: `detect`'s kernel is
trailing and per-target, while the whole-record semantics a v5 `detector` field
means are centered and non-causal, so a synthesized detect node computes
something else — see `docs/findings/2026.08.05-three-things-the-graph-
migration-cannot-do-as-written.md`. Refusing is R2's posture: a transform that
cannot carry a field must say so with the field's name in the message rather
than drop it.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from sieve.filters.crop import WHOLE_FRAME, CropParams
from sieve.filters.span import SpanParams

#: Prefixes for the derived ids, built from the ids rather than typed beside
#: them. Not a flourish: typing `"crop-"` here is one keystroke from typing
#: `"crop"`, which `test_filter_id_spelling.py` fails — this module argues in
#: its own docstring that a filter id has one home, and these are where it
#: would have stopped being true.
CROP_ID_PREFIX = f"{CropParams.spec().filter_id}-"
SPAN_ID_PREFIX = f"{SpanParams.spec().filter_id}-"

#: The crop node's id when the document carries no graph at all — a project
#: where arenas were drawn and nothing was built on them yet. There is no root
#: to derive from, and the geometry still has to land somewhere or the upgrade
#: loses it.
ROOTLESS_CROP_ID = CropParams.spec().filter_id


class UnupgradableDocumentError(ValueError):
    """A saved document whose meaning cannot be carried into the graph."""


def carry_into_graph(document: Mapping[str, Any]) -> dict[str, Any]:
    """`document` with its crop and span moved into the pipeline.

    Args:
        document: A parsed saved project — the mapping `yaml.safe_load` returns
            or `Project.model_dump(mode="json")` produces, not a `Project`.
            Values are read as they appear in the file, so an `ROI` arrives as
            a mapping and is passed through as one.

    Returns:
        A new mapping. `clip` is gone, no replicate carries `roi`, and the
        pipeline carries a crop node above every root and a span node below
        every leaf. `schema_version` is *not* stamped: the bump belongs to the
        commit that drops the fields from the model, and stamping it here would
        put the schema number in two places.

    Raises:
        UnupgradableDocumentError: if the document carries a tuned detector, if
            a derived node id is already taken, or if a replicate already
            overrides one.
    """
    replicates = [dict(replicate) for replicate in document.get("replicates") or ()]
    _refuse_a_detector(document, replicates)

    pipeline = dict(document.get("pipeline") or {})
    nodes = [dict(node) for node in pipeline.get("nodes") or ()]
    edges = [dict(edge) for edge in pipeline.get("edges") or ()]
    taken = {str(node["node_id"]) for node in nodes}

    fed = {str(edge["downstream"]) for edge in edges}
    roots = [str(node["node_id"]) for node in nodes if str(node["node_id"]) not in fed]
    crops = (
        [(root, f"{CROP_ID_PREFIX}{root}") for root in roots]
        if roots
        else [(None, ROOTLESS_CROP_ID)]
    )
    _refuse_taken((crop_id for _, crop_id in crops), taken)

    spec = CropParams.spec()
    crop_nodes = [
        {
            "node_id": crop_id,
            "filter_id": spec.filter_id,
            "version": spec.version,
            "params": CropParams(roi=WHOLE_FRAME).model_dump(mode="json"),
        }
        for _, crop_id in crops
    ]
    crop_edges = [
        {"upstream": crop_id, "downstream": root} for root, crop_id in crops if root is not None
    ]

    nodes = crop_nodes + nodes
    edges = crop_edges + edges
    taken |= {crop_id for _, crop_id in crops}

    # Leaves of the *crop-augmented* graph, so that the empty-pipeline case —
    # where the crop node is the only node there is — still gets its span.
    feeding = {str(edge["upstream"]) for edge in edges}
    leaves = [str(node["node_id"]) for node in nodes if str(node["node_id"]) not in feeding]
    spans = [(leaf, f"{SPAN_ID_PREFIX}{leaf}") for leaf in leaves]
    _refuse_taken((span_id for _, span_id in spans), taken)

    span_spec = SpanParams.spec()
    span_params = _span_params(document.get("clip")).model_dump(mode="json")
    nodes += [
        {
            "node_id": span_id,
            "filter_id": span_spec.filter_id,
            "version": span_spec.version,
            "params": span_params,
        }
        for _, span_id in spans
    ]
    edges += [{"upstream": leaf, "downstream": span_id} for leaf, span_id in spans]

    # `clip` dropped rather than rebuilt around, and the other keys left where
    # they were: `Project.to_yaml` keeps declaration order so that a saved file
    # does not change byte for byte on every write, and an upgrade that
    # reordered the document would spend that stability once, for nothing.
    upgraded = {key: value for key, value in document.items() if key != "clip"}
    upgraded["replicates"] = [
        _pinning(replicate, [crop_id for _, crop_id in crops]) for replicate in replicates
    ]
    upgraded["pipeline"] = {**pipeline, "nodes": nodes, "edges": edges}
    return upgraded


def _refuse_a_detector(document: Mapping[str, Any], replicates: list[dict[str, Any]]) -> None:
    """Refuse a document whose detection cannot be carried — see the docstring."""
    if document.get("detector") is not None:
        raise UnupgradableDocumentError(
            "detector: a tuned detector cannot be carried into the graph — the detect "
            "filter's kernel is trailing and per-target, and a whole-record detector "
            "field is centered and non-causal, so the synthesized node would claim "
            "different events from the same series"
        )
    for replicate in replicates:
        if replicate.get("detector_overrides"):
            raise UnupgradableDocumentError(
                f"detector_overrides: replicate {replicate.get('replicate_id')!r} pins "
                "detector fields, and there is no node yet to pin them on"
            )


def _refuse_taken(derived: Iterable[str], taken: set[str]) -> None:
    """Refuse rather than disambiguate a derived id the document already uses.

    Disambiguating — appending a suffix until the id is free — would make the
    upgrade depend on what else is in the document, so one file could upgrade
    to two graphs. A collision here means a hand-written node called
    `crop-<something>`, which is rare enough to be worth a message.
    """
    for node_id in derived:
        if node_id in taken:
            raise UnupgradableDocumentError(
                f"the upgrade would synthesize a node called {node_id!r}, and the "
                "document already has one"
            )


def _span_params(clip: Mapping[str, Any] | None) -> SpanParams:
    """The span node's parameters: the clip's bounds, or the identity range.

    `SpanParams()` rather than an empty mapping for the absent clip. The
    defaults are written out because a saved node whose params are empty means
    "whatever this filter's defaults are today", and the document is the thing
    two machines have to agree about across a version boundary.
    """
    if clip is None:
        return SpanParams()
    return SpanParams(start=int(clip["start"]), end=int(clip["end"]))


def _pinning(replicate: Mapping[str, Any], crop_ids: list[str]) -> dict[str, Any]:
    """`replicate` without its `roi`, pinning that box on every crop node.

    Through `model_validate` rather than the constructor because the region
    arrives as whatever the document held — a mapping from YAML, or a whole
    `ROI` from a caller who reached for `model_dump()` without `mode="json"` —
    and validating is the one call that takes both and canonicalizes them.
    """
    roi = replicate.get("roi")
    pin = CropParams.model_validate({"roi": WHOLE_FRAME if roi is None else roi}).model_dump(
        mode="json"
    )
    stored: Mapping[str, Mapping[str, Any]] = replicate.get("overrides") or {}
    overrides: dict[str, Any] = {key: dict(value) for key, value in stored.items()}
    for crop_id in crop_ids:
        if crop_id in overrides:
            raise UnupgradableDocumentError(
                f"replicate {replicate.get('replicate_id')!r} already overrides "
                f"{crop_id!r}, which the upgrade needs for its crop"
            )
        overrides[crop_id] = pin
    return {**{k: v for k, v in replicate.items() if k != "roi"}, "overrides": overrides}
