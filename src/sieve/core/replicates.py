from __future__ import annotations

import re
from collections.abc import Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass, field, replace
from typing import Any, Self
from uuid import uuid4

from sieve.core.types import ROI

DEFAULT_NAME_STEM = "Replicate"


_DEFAULT_NAME_PATTERN = re.compile(rf"^{DEFAULT_NAME_STEM} ([1-9]\d*)$")


def _new_id() -> str:
    return uuid4().hex


def _no_overrides() -> dict[str, dict[str, Any]]:
    return {}


def _no_detector_overrides() -> dict[str, Any]:
    return {}


@dataclass(frozen=True, slots=True)
class Replicate:
    roi: ROI
    name: str
    replicate_id: str = field(default_factory=_new_id)

    overrides: dict[str, dict[str, Any]] = field(
        default_factory=_no_overrides, hash=False
    )

    detector_overrides: dict[str, Any] = field(
        default_factory=_no_detector_overrides, hash=False
    )

    def renamed(self, name: str) -> Self:
        return replace(self, name=name)

    def with_roi(self, roi: ROI) -> Self:
        return replace(self, roi=roi)

    def override_for(self, node_id: str) -> dict[str, Any]:
        return dict(self.overrides.get(node_id, {}))

    def with_override(self, node_id: str, changes: Mapping[str, Any]) -> Self:
        if not changes:
            return self
        merged = dict(self.overrides)
        merged[node_id] = {**merged.get(node_id, {}), **changes}
        return replace(self, overrides=merged)

    def without_override(self, node_id: str) -> Self:
        if node_id not in self.overrides:
            return self
        return replace(
            self, overrides={k: v for k, v in self.overrides.items() if k != node_id}
        )

    def with_overrides_limited_to(self, node_ids: Collection[str]) -> Self:
        kept = {k: v for k, v in self.overrides.items() if k in node_ids}
        if kept == self.overrides:
            return self
        return replace(self, overrides=kept)

    def with_detector_pins(self, changes: Mapping[str, Any]) -> Self:
        if not changes:
            return self
        return replace(self, detector_overrides={**self.detector_overrides, **changes})

    def without_detector_pins(self) -> Self:
        if not self.detector_overrides:
            return self
        return replace(self, detector_overrides={})


class ReplicateSet:
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
        return list(self._items)

    def index_of(self, replicate_id: str) -> int:
        for index, item in enumerate(self._items):
            if item.replicate_id == replicate_id:
                return index
        raise KeyError(replicate_id)

    def insert(self, index: int, replicate: Replicate) -> None:
        self._items.insert(index, replicate)

    def append(self, replicate: Replicate) -> int:
        self._items.append(replicate)
        return len(self._items) - 1

    def remove_at(self, index: int) -> Replicate:
        return self._items.pop(index)

    def replace_at(self, index: int, replicate: Replicate) -> Replicate:
        previous = self._items[index]
        self._items[index] = replicate
        return previous

    def clear(self) -> None:
        self._items.clear()

    def next_default_name(self) -> str:
        taken = {
            int(match.group(1))
            for match in (
                _DEFAULT_NAME_PATTERN.match(item.name) for item in self._items
            )
            if match is not None
        }
        candidate = 1
        while candidate in taken:
            candidate += 1
        return f"{DEFAULT_NAME_STEM} {candidate}"
