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
