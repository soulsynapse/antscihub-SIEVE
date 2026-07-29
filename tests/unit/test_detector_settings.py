








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






    baseline = DetectorSettings.default_for(30.0)
    edited = _replicate("edited")
    follower = _replicate("follower")

    moved, pinned = edited_detector(baseline, edited, {"count_frac": (0.2, 1.0)})

    assert pinned.detector_overrides == {"count_frac": (0.2, 1.0)}
    assert moved.count_frac == (0.2, 1.0)
    assert resolved_detector(moved, follower) == moved



    moved2, repinned = edited_detector(moved, follower, {"count_frac": (0.2, 1.0)})
    assert repinned.detector_overrides == {}
    assert moved2 == moved


    moved3, _ = edited_detector(moved, follower, {"window_frames": 60})
    assert resolved_detector(moved3, pinned).count_frac == (0.2, 1.0)
    assert resolved_detector(moved3, pinned).window_frames == 60


def test_project_round_trips_detector_and_pins_including_infinite_edges() -> None:

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



    untuned = Project.model_validate({"schema_version": 2, "source": {"path": "video.mp4"}})
    assert untuned.detector is None


def test_an_infinite_edge_survives_in_a_pin_and_not_only_in_the_baseline() -> None:









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







    poisoned = Project(source=SourceRef(path="video.mp4"), replicates=(_replicate("r"),)).to_yaml()
    poisoned = poisoned.replace(
        "detector_overrides: {}", "detector_overrides:\n    value_band: [1043.6, null]"
    )

    with pytest.raises(ValidationError, match="does not fit its field"):
        Project.from_yaml(poisoned)


def test_a_readable_document_is_restamped_with_this_builds_schema() -> None:







    older = Project.model_validate({"schema_version": 2, "source": {"path": "video.mp4"}})

    assert older.schema_version == SCHEMA_VERSION
    assert f"schema_version: {SCHEMA_VERSION}" in older.to_yaml()


def test_grouping_and_validation_see_detector_pins() -> None:

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
