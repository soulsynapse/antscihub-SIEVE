"""The replicate: identity that survives every edit, and sparse deviation.

`Replicate` lives in `core/pipeline_model.py` rather than beside it — it is a
schema question end to end, and `adr/core-membership-is-closed.md` admits one
model module. The cases stay in their own file because what they are about is
the replicate rather than the document.
"""

from __future__ import annotations

import pytest

from sieve.core.pipeline_model import Replicate


def _replicate(name: str) -> Replicate:
    return Replicate(name=name)


class TestIdentity:
    def test_identity_survives_rename(self) -> None:
        original = _replicate("Dish A")
        renamed = original.renamed("Dish B")

        assert renamed.replicate_id == original.replicate_id
        assert renamed.name == "Dish B"

    def test_identity_survives_a_geometry_edit(self) -> None:
        # Geometry is a per-replicate override on the crop node's region
        # parameter (`adr/detector-is-a-node.md`), so moving a box is an
        # ordinary override edit. The claim is unchanged from when the ROI was a
        # field: what downstream artifacts reference must not move when the box
        # does.
        original = _replicate("Dish A")
        moved = original.with_override("n1", {"region": {"x": 99, "y": 99}})

        assert moved.replicate_id == original.replicate_id
        assert moved.override_for("n1") == {"region": {"x": 99, "y": 99}}

    def test_distinct_replicates_get_distinct_ids(self) -> None:
        assert _replicate("a").replicate_id != _replicate("a").replicate_id


class TestOverrides:
    def test_an_override_read_out_cannot_be_written_back_in(self) -> None:
        # `frozen=True` stops the field being reassigned and says nothing about
        # the dict inside it. Handing out the live mapping would make an edit
        # through a stale read reach a replicate nobody thought they were
        # touching — and would do it after the document had been hashed.
        original = _replicate("a").with_override("n1", {"level": 0.5})

        original.override_for("n1")["level"] = 0.9

        assert original.overrides == {"n1": {"level": 0.5}}

    def test_a_container_valued_override_cannot_be_written_through(self) -> None:
        # The case above pins the same claim for a scalar, and a shallow copy is
        # enough for that and for nothing else. A replicate's geometry is a
        # region — a mapping — since `adr/detector-is-a-node.md` moved it onto
        # the crop node's parameter, so the container case is the one the
        # document actually stores, not a hypothetical.
        original = _replicate("a").with_override("n1", {"region": {"x": 0, "y": 0}})

        with pytest.raises(TypeError):
            original.override_for("n1")["region"]["x"] = 999
        with pytest.raises(TypeError):
            original.overrides["n1"]["region"]["y"] = 999

        assert original.overrides == {"n1": {"region": {"x": 0, "y": 0}}}

    def test_the_mapping_an_override_was_built_from_is_not_the_one_stored(self) -> None:
        # `with_override` runs no validator — `model_copy` skips them — so the
        # freeze has to happen in the method. Without it a front end holding the
        # parameter form it submitted would hold a writable handle into a
        # document that has since been hashed.
        submitted = {"region": {"x": 0, "y": 0}}
        pinned = _replicate("a").with_override("n1", submitted)

        submitted["region"]["x"] = 999

        assert pinned.override_for("n1") == {"region": {"x": 0, "y": 0}}

    def test_pinning_one_parameter_leaves_the_others_pinned(self) -> None:
        # An edit names only what it touched, so overrides merge. Replacing
        # would un-pin every parameter the replicate had been configured with on
        # the next single-field edit.
        once = _replicate("a").with_override("n1", {"level": 0.5})
        pinned = once.with_override("n1", {"blur": 7})

        assert pinned.overrides == {"n1": {"level": 0.5, "blur": 7}}
        assert pinned.without_override("n1").overrides == {}

    def test_a_pin_does_not_reach_the_replicate_it_was_copied_from(self) -> None:
        # The nested mapping is copied on write as well as on read. Sharing the
        # inner dict between two versions of a document would make an edit to
        # the new one visible in the old, which is what undo holds.
        once = _replicate("a").with_override("n1", {"level": 0.5})

        once.with_override("n1", {"level": 0.9})

        assert once.overrides == {"n1": {"level": 0.5}}

    def test_pruning_keeps_only_deviations_that_still_name_a_node(self) -> None:
        # The prune a structural edit performs. `self` unchanged when nothing is
        # stale is what lets a caller tell "pruned" from "already clean" with an
        # identity check rather than by comparing dicts.
        replicate = _replicate("a").with_override("n1", {"level": 0.5})
        replicate = replicate.with_override("n2", {"radius": 3})

        assert replicate.with_overrides_limited_to({"n1", "n2"}) is replicate
        assert replicate.with_overrides_limited_to({"n1"}).overrides == {"n1": {"level": 0.5}}
