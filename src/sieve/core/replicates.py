"""The replicate document: an ordered set of named regions cut from one source.

A replicate is a spatial subdivision of the source video — one arena, one
dish, one trial. Cutting to replicates is optional but near-universal, and it
is the first node of the DAG, so the model has to be pure data with no GUI
coupling. Undo lives in the GUI on top of these operations; this module knows
nothing about it.

Every mutator is index-addressed and returns what it displaced, so an inverse
operation is always constructible without the caller re-deriving state.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field, replace
from typing import Self
from uuid import uuid4

from sieve.core.types import ROI

DEFAULT_NAME_STEM = "Replicate"
_DEFAULT_NAME_PATTERN = re.compile(rf"^{DEFAULT_NAME_STEM} (\d+)$")


def _new_id() -> str:
    return uuid4().hex


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

    def renamed(self, name: str) -> Self:
        """Copy carrying a new display name and the same identity."""
        return replace(self, name=name)

    def with_roi(self, roi: ROI) -> Self:
        """Copy carrying new geometry and the same identity."""
        return replace(self, roi=roi)


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
