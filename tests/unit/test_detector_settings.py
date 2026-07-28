"""The detector's home in the artifact, and the two-write edit over it.

Three claims, each a distinct way per-replicate settings memory could lie.
An edit that pinned everything submitted would freeze the edited arena out
of all future tuning; a save that dropped an infinite band edge would turn
"wide open" into a number; a grouping blind to detector pins would say
"same" about arenas that claim different events from identical series.
"""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from sieve.core.pipeline_model import (
    SCHEMA_VERSION,
    DetectorSettings,
    Node,
    Pipeline,
    Project,
    SourceRef,
    edited_detector,
    equivalence_groups,
    resolved_detector,
)
from sieve.core.replicates import Replicate
from sieve.core.types import ROI


def _replicate(name: str) -> Replicate:
    return Replicate(roi=ROI(0, 0, 10, 10), name=name)


def test_edited_detector_pins_the_diff_and_moves_the_default_for_followers() -> None:
    """The two writes: only what changed pins; everything submitted moves.

    The follower is the load-bearing half — an untouched replicate must
    resolve to the *moved* baseline, or twelve arenas stop tuning as one
    rack the moment any one of them is edited.
    """
    baseline = DetectorSettings.default_for(30.0)
    edited = _replicate("edited")
    follower = _replicate("follower")

    moved, pinned = edited_detector(baseline, edited, {"count_frac": (0.2, 1.0)})

    assert pinned.detector_overrides == {"count_frac": (0.2, 1.0)}
    assert moved.count_frac == (0.2, 1.0)
    assert resolved_detector(moved, follower) == moved

    # Submitting a value a replicate already resolves to pins nothing: the
    # group tracks what an arena runs with, not whether it was visited.
    moved2, repinned = edited_detector(moved, follower, {"count_frac": (0.2, 1.0)})
    assert repinned.detector_overrides == {}
    assert moved2 == moved

    # A pinned arena keeps its own value while following every other field.
    moved3, _ = edited_detector(moved, follower, {"window_frames": 60})
    assert resolved_detector(moved3, pinned).count_frac == (0.2, 1.0)
    assert resolved_detector(moved3, pinned).window_frames == 60


def test_project_round_trips_detector_and_pins_including_infinite_edges() -> None:
    """YAML out and back is identity, `.inf` and disarmed-None included."""
    baseline = DetectorSettings(value_band=(-math.inf, math.inf), count_frac=None)
    replicate = _replicate("r").with_detector_pins({"window_frames": 45})
    project = Project(
        source=SourceRef(path="video.mp4"),
        replicates=(replicate,),
        detector=baseline,
    )

    restored = Project.from_yaml(project.to_yaml())

    assert restored.detector == baseline
    assert restored.replicates[0].detector_overrides == {"window_frames": 45}

    # A document from before the fields existed still loads, and loads as
    # "never tuned" rather than as any particular choice.
    untuned = Project.model_validate({"schema_version": 2, "source": {"path": "video.mp4"}})
    assert untuned.detector is None


def test_an_infinite_edge_survives_in_a_pin_and_not_only_in_the_baseline() -> None:
    """The open edge of a *pinned* band is a number on the way back in.

    The seam the test above is named for and does not reach: its infinity is
    on `DetectorSettings.value_band`, a typed field pydantic leaves alone,
    while its only pin is an `int`. A pin lives in `Any`-typed storage, where
    the default serializer wrote `null` — one arena of a real project came
    back with `value_band: [51206.8, null]` and every tuning path over it
    raised from then on.
    """
    baseline = DetectorSettings(value_band=(51206.8, math.inf))
    pinned = _replicate("open top").with_detector_pins({"value_band": (1043.6, math.inf)})
    project = Project(source=SourceRef(path="video.mp4"), replicates=(pinned,), detector=baseline)

    restored = Project.from_yaml(project.to_yaml())

    assert restored.detector is not None
    assert restored.replicates[0].detector_overrides["value_band"] == [1043.6, math.inf]
    assert resolved_detector(restored.detector, restored.replicates[0]).value_band == (
        1043.6,
        math.inf,
    )


def test_a_pin_that_cannot_resolve_is_refused_by_the_reader() -> None:
    """A document that cannot say what an arena runs with is not a document.

    The half of the same failure that let it go unnoticed: the reader checked
    the spelling of a pin and not its value, so a project written with `null`
    where a band edge belonged loaded clean and raised later, inside a GUI
    slot, over a table that went on selecting rows.
    """
    poisoned = Project(source=SourceRef(path="video.mp4"), replicates=(_replicate("r"),)).to_yaml()
    poisoned = poisoned.replace(
        "detector_overrides: {}", "detector_overrides:\n    value_band: [1043.6, null]"
    )

    with pytest.raises(ValidationError, match="does not fit its field"):
        Project.from_yaml(poisoned)


def test_a_readable_document_is_restamped_with_this_builds_schema() -> None:
    """The stamp says what wrote the file, not what wrote its oldest ancestor.

    The GUI saves by copying the `Project` it opened, so a stamp carried
    through `model_copy` is carried forever: the reported file claimed v2
    while holding v3's `detector`, which sends a v2 build into `extra=forbid`
    instead of into the message the version check exists to give.
    """
    older = Project.model_validate({"schema_version": 2, "source": {"path": "video.mp4"}})

    assert older.schema_version == SCHEMA_VERSION
    assert f"schema_version: {SCHEMA_VERSION}" in older.to_yaml()


def test_grouping_and_validation_see_detector_pins() -> None:
    """A detector pin splits a group, and a misspelt pin refuses to save."""
    node = Node(filter_id="rescale", version="1.0.0", params={"scale": 1.0})
    pipeline = Pipeline(nodes=(node,))
    same = _replicate("a")
    deviant = _replicate("b").with_detector_pins({"centered": False})

    groups = equivalence_groups(pipeline, [same, deviant], DetectorSettings())
    assert groups == (1, 2)

    with pytest.raises(ValidationError, match="pins no such detector field"):
        Project(
            source=SourceRef(path="video.mp4"),
            replicates=(_replicate("c").with_detector_pins({"solo_block": 3}),),
        )
