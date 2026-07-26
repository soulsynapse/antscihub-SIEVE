"""The pure replicate model."""

from __future__ import annotations

import pytest

from sieve.core.replicates import Replicate, ReplicateSet
from sieve.core.types import ROI


def _replicate(name: str, x: int = 0) -> Replicate:
    return Replicate(roi=ROI(x=x, y=0, width=10, height=10), name=name)


class TestReplicate:
    def test_identity_survives_rename(self) -> None:
        original = _replicate("Dish A")
        renamed = original.renamed("Dish B")
        assert renamed.replicate_id == original.replicate_id
        assert renamed.name == "Dish B"

    def test_identity_survives_geometry_change(self) -> None:
        original = _replicate("Dish A")
        moved = original.with_roi(ROI(x=99, y=99, width=5, height=5))
        assert moved.replicate_id == original.replicate_id
        assert moved.roi.x == 99

    def test_distinct_replicates_get_distinct_ids(self) -> None:
        assert _replicate("a").replicate_id != _replicate("a").replicate_id


class TestReplicateSet:
    def test_append_returns_landing_position(self) -> None:
        replicates = ReplicateSet()
        assert replicates.append(_replicate("one")) == 0
        assert replicates.append(_replicate("two")) == 1

    def test_index_of_finds_by_id(self) -> None:
        first, second = _replicate("one"), _replicate("two")
        replicates = ReplicateSet([first, second])
        assert replicates.index_of(second.replicate_id) == 1

    def test_index_of_raises_for_unknown_id(self) -> None:
        with pytest.raises(KeyError):
            ReplicateSet().index_of("nope")

    def test_remove_and_insert_are_inverses(self) -> None:
        items = [_replicate("one"), _replicate("two"), _replicate("three")]
        replicates = ReplicateSet(items)
        removed = replicates.remove_at(1)
        replicates.insert(1, removed)
        assert replicates.as_list() == items

    def test_replace_returns_what_it_displaced(self) -> None:
        original = _replicate("one")
        replicates = ReplicateSet([original])
        displaced = replicates.replace_at(0, _replicate("two"))
        assert displaced is original
        assert replicates[0].name == "two"

    def test_as_list_is_a_snapshot(self) -> None:
        replicates = ReplicateSet([_replicate("one")])
        snapshot = replicates.as_list()
        snapshot.clear()
        assert len(replicates) == 1

    def test_default_names_count_up(self) -> None:
        replicates = ReplicateSet()
        assert replicates.next_default_name() == "Replicate 1"
        replicates.append(_replicate("Replicate 1"))
        assert replicates.next_default_name() == "Replicate 2"

    def test_default_names_reuse_gaps(self) -> None:
        replicates = ReplicateSet(
            [_replicate("Replicate 1"), _replicate("Replicate 2"), _replicate("Replicate 3")]
        )
        replicates.remove_at(1)
        assert replicates.next_default_name() == "Replicate 2"

    def test_custom_names_do_not_consume_default_numbers(self) -> None:
        replicates = ReplicateSet([_replicate("Nest 4"), _replicate("Replicate")])
        assert replicates.next_default_name() == "Replicate 1"
