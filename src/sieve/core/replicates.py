"""The replicate document: an ordered set of named regions cut from one source.

A replicate is a spatial subdivision of the source video — one arena, one
dish, one trial. Cutting to replicates is optional but near-universal, and it
is the first node of the DAG, so the model has to be pure data with no GUI
coupling. Undo lives in the GUI on top of these operations; this module knows
nothing about it.

Every mutator is index-addressed and returns what it displaced, so an inverse
operation is always constructible without the caller re-deriving state.

A replicate also carries how its processing *deviates* from the rest — see
`Replicate.overrides`. That lives here rather than on `Node` because twelve
arenas would otherwise make one node carry twelve parameter dicts and the
source-level fan-out would stop being a fan-out. Resolving an override against
a node's baseline is `pipeline_model.resolved_params`, one layer up, since it
is the only place that can see both.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass, field, replace
from typing import Any, Self
from uuid import uuid4

from sieve.core.types import ROI

DEFAULT_NAME_STEM = "Replicate"
# `[1-9]\d*`, not `\d+`: a hand-typed "Replicate 01" is a different name from
# "Replicate 1", so treating it as number 1 would retire a name that is still
# free and break the "lowest unused" contract below.
_DEFAULT_NAME_PATTERN = re.compile(rf"^{DEFAULT_NAME_STEM} ([1-9]\d*)$")


def _new_id() -> str:
    return uuid4().hex


def _no_overrides() -> dict[str, dict[str, Any]]:
    """An empty deviation map, typed — `default_factory=dict` infers nothing."""
    return {}


def _no_detector_overrides() -> dict[str, Any]:
    """An empty detector deviation, typed for the same reason."""
    return {}


@dataclass(frozen=True, slots=True)
class Replicate:
    """A named region of the source, stable across renames and geometry edits.

    `replicate_id` is what downstream artifacts reference. Renaming a replicate
    must not invalidate a cache entry keyed on it, so identity is a generated
    id rather than the display name.
    """

    roi: ROI
    name: str
    replicate_id: str = field(default_factory=_new_id)
    #: Per-node parameter deviation: `{node_id: {param_name: value}}`, and
    #: sparse in *both* levels. A node absent from the mapping is processed
    #: with the node's own parameters; a parameter absent from a node's entry
    #: is inherited from them even when a sibling parameter is pinned. That
    #: second level is what lets one arena hold its own threshold while still
    #: following every later edit to a blur radius nobody varied.
    #:
    #: An override storing every parameter would be unable to tell "the user
    #: set this to the same value" from "the user never touched it", and that
    #: distinction is exactly what the replicate table renders — so sparsity is
    #: a construction rule, not a storage optimization. `hash=False` because a
    #: dict is unhashable and the identity of a replicate is `replicate_id`
    #: anyway; two replicates differing only in overrides hash alike and
    #: compare unequal, which is the correct pair of answers.
    overrides: dict[str, dict[str, Any]] = field(default_factory=_no_overrides, hash=False)
    #: The detector's deviation, `{field_name: value}` — `overrides`' twin for
    #: the tab-side detection settings, which belong to no node and so cannot
    #: live in the mapping above without inventing a node id nothing runs.
    #: Sparse for the same reason: a field absent here follows the project's
    #: detector baseline as it moves, so one arena can hold its own count
    #: threshold while still following every later edit to the frequency band.
    #: Which field names are legal is the artifact's question
    #: (`pipeline_model.DetectorSettings`), one layer up, exactly as node
    #: override keys are resolved against the graph there and not here.
    detector_overrides: dict[str, Any] = field(default_factory=_no_detector_overrides, hash=False)

    def renamed(self, name: str) -> Self:
        """Copy carrying a new display name and the same identity."""
        return replace(self, name=name)

    def with_roi(self, roi: ROI) -> Self:
        """Copy carrying new geometry and the same identity."""
        return replace(self, roi=roi)

    def override_for(self, node_id: str) -> dict[str, Any]:
        """This replicate's deviation at `node_id`, empty when it follows.

        A copy: the stored mapping is nested inside a frozen dataclass, and
        handing out the live dict would make `frozen=True` a claim the type
        cannot keep.
        """
        return dict(self.overrides.get(node_id, {}))

    def with_override(self, node_id: str, changes: Mapping[str, Any]) -> Self:
        """Copy whose deviation at `node_id` is merged with `changes`.

        Merged, not replaced, because an edit names only the parameters it
        touched. Replacing would silently un-pin every other parameter the
        replicate had been configured with.
        """
        if not changes:
            return self
        merged = dict(self.overrides)
        merged[node_id] = {**merged.get(node_id, {}), **changes}
        return replace(self, overrides=merged)

    def without_override(self, node_id: str) -> Self:
        """Copy that follows `node_id`'s baseline again.

        The way back from a pin. Without it a parameter set once could only
        ever be re-pinned to a new value, never returned to inheriting, and the
        replicate would drop out of the equivalence group it started in
        permanently.
        """
        if node_id not in self.overrides:
            return self
        return replace(self, overrides={k: v for k, v in self.overrides.items() if k != node_id})

    def with_overrides_limited_to(self, node_ids: Collection[str]) -> Self:
        """Copy keeping only the deviations that still name a real node.

        The prune a structural edit performs: a pin on a node the graph lost
        is a parameter set nothing will ever read, and the artifact refuses
        to save one. Returns `self` unchanged when nothing is stale, so an
        identity check can tell "pruned" from "already clean".
        """
        kept = {k: v for k, v in self.overrides.items() if k in node_ids}
        if kept == self.overrides:
            return self
        return replace(self, overrides=kept)

    def with_detector_pins(self, changes: Mapping[str, Any]) -> Self:
        """Copy whose detector deviation is merged with `changes`.

        Merged, not replaced, for `with_override`'s reason: an edit names only
        the fields it touched, and replacing would un-pin every other field
        this arena had deviated on.
        """
        if not changes:
            return self
        return replace(self, detector_overrides={**self.detector_overrides, **changes})

    def without_detector_pins(self) -> Self:
        """Copy that follows the detector baseline again — the way back."""
        if not self.detector_overrides:
            return self
        return replace(self, detector_overrides={})


class ReplicateSet:
    """Ordered, mutable collection of replicates addressed by position."""

    def __init__(self, replicates: Iterable[Replicate] = ()) -> None:
        self._items: list[Replicate] = list(replicates)

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Replicate]:
        return iter(self._items)

    def __getitem__(self, index: int) -> Replicate:
        return self._items[index]

    def __repr__(self) -> str:
        return f"ReplicateSet({self._items!r})"

    def as_list(self) -> list[Replicate]:
        """Snapshot copy — mutating the result does not touch the set."""
        return list(self._items)

    def index_of(self, replicate_id: str) -> int:
        """Position of the replicate with this id.

        Raises:
            KeyError: if no replicate carries the id.
        """
        for index, item in enumerate(self._items):
            if item.replicate_id == replicate_id:
                return index
        raise KeyError(replicate_id)

    def insert(self, index: int, replicate: Replicate) -> None:
        """Insert at `index`, shifting later entries right."""
        self._items.insert(index, replicate)

    def append(self, replicate: Replicate) -> int:
        """Append and return the position it landed at."""
        self._items.append(replicate)
        return len(self._items) - 1

    def remove_at(self, index: int) -> Replicate:
        """Remove and return the replicate at `index`."""
        return self._items.pop(index)

    def replace_at(self, index: int, replicate: Replicate) -> Replicate:
        """Overwrite position `index`, returning what was displaced."""
        previous = self._items[index]
        self._items[index] = replicate
        return previous

    def clear(self) -> None:
        """Drop every replicate."""
        self._items.clear()

    def next_default_name(self) -> str:
        """Lowest unused `Replicate N` name.

        Reuses gaps left by deletions so a user who deletes "Replicate 2" and
        draws again gets "Replicate 2" back rather than an ever-climbing count.
        """
        taken = {
            int(match.group(1))
            for match in (_DEFAULT_NAME_PATTERN.match(item.name) for item in self._items)
            if match is not None
        }
        candidate = 1
        while candidate in taken:
            candidate += 1
        return f"{DEFAULT_NAME_STEM} {candidate}"
