"""The synthesized graph, pinned exactly.

`docs/todo/the-graph-carries-the-crop-the-span-and-the-detector.md` asks for a
v5 fixture and a test that pins what the upgrade makes of it. This is that
test; the frame-for-frame half is `tests/integration/test_upgrade_run.py`.

Pinned exactly rather than checked property by property, because the failures
the migration is afraid of are all *plausible* — a crop node in the wrong
place, a box on the wrong replicate, a span whose bounds are the decode range
rather than the clip. Each of those satisfies every property one would think to
assert separately, and none of them survives a comparison against the whole
graph.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from sieve.core.filter_base import UNBOUNDED_FRAME
from sieve.core.pipeline_model import Project
from sieve.filters import discover
from sieve.filters.crop import WHOLE_FRAME_EXTENT
from sieve.pipeline.upgrade import (
    ROOTLESS_CROP_ID,
    UnupgradableDocumentError,
    carry_into_graph,
)

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "project-v5.sieve.yaml"

ARENA_ONE = {"x": 16, "y": 8, "width": 64, "height": 48}
ARENA_TWO = {"x": 80, "y": 40, "width": 48, "height": 32}
WHOLE = {"x": 0, "y": 0, "width": WHOLE_FRAME_EXTENT, "height": WHOLE_FRAME_EXTENT}


@pytest.fixture
def v5() -> dict[str, Any]:
    """The checked-in document, and proof that it is one.

    Loaded through `Project` before it is handed over: a fixture that had
    drifted out of v5 would make every assertion below a statement about a
    mapping nothing can read, which is the one way this test could pass while
    saying nothing.

    `discover()` here rather than in an autouse fixture: the ids and versions
    the expected graph is written with come off registered specs, so every test
    below needs the shelf, and every test below takes this.
    """
    assert discover()
    text = FIXTURE.read_text(encoding="utf-8")
    assert Project.from_yaml(text).schema_version == 5
    loaded: dict[str, Any] = yaml.safe_load(text)
    return loaded


def test_the_upgraded_document_carries_the_crop_and_the_span_in_its_graph(
    v5: dict[str, Any],
) -> None:
    upgraded = carry_into_graph(v5)

    assert upgraded["pipeline"] == {
        "nodes": [
            {
                "node_id": "crop-down",
                "filter_id": "crop",
                "version": "1.0.0",
                "params": {"roi": WHOLE},
            },
            {
                "node_id": "down",
                "filter_id": "downsample",
                "version": "1.0.0",
                "params": {"factor": 2, "anti_alias": True},
            },
            {
                "node_id": "ema",
                "filter_id": "background_ema",
                "version": "1.0.0",
                "params": {"alpha": 0.5, "emit": "foreground"},
            },
            {
                "node_id": "span-ema",
                "filter_id": "span",
                "version": "1.0.0",
                # The clip's own bounds, not the decode range the lead-in
                # widens them to. `background_ema` at alpha 0.5 wants five
                # frames of settling, so a span node built from what the reader
                # is asked for would say 17 here and run four frames that are
                # each the right shape and the wrong footage.
                "params": {"start": 22, "end": 26},
            },
        ],
        "edges": [
            {"upstream": "crop-down", "downstream": "down"},
            {"upstream": "down", "downstream": "ema", "port": "in"},
            {"upstream": "ema", "downstream": "span-ema"},
        ],
    }
    assert "clip" not in upgraded
    assert [replicate["overrides"] for replicate in upgraded["replicates"]] == [
        {"crop-down": {"roi": ARENA_ONE}},
        # The pre-existing deviation survives beside the new one: an upgrade
        # that rebuilt the mapping rather than adding to it would silently
        # un-tune every arena that had been configured.
        {"down": {"factor": 4}, "crop-down": {"roi": ARENA_TWO}},
    ]
    assert all("roi" not in replicate for replicate in upgraded["replicates"])


def test_upgrading_twice_gives_the_same_document(v5: dict[str, Any]) -> None:
    """Derived ids, not generated ones — see the module docstring in `upgrade`.

    The failure this catches leaves no trace at the time: `Node.node_id`
    defaults to a fresh uuid, so an upgrade that let it default would produce a
    valid graph every time and a *different* one on each machine, which is the
    one property the artifact exists to have.
    """
    assert carry_into_graph(v5) == carry_into_graph(v5)


def test_a_document_with_no_graph_still_keeps_its_geometry(v5: dict[str, Any]) -> None:
    """Arenas drawn, nothing built on them yet — a real state to save from.

    There is no root to hang a crop node off, and dropping `roi` without one
    would lose the only thing the file records.
    """
    upgraded = carry_into_graph({**v5, "pipeline": {"nodes": [], "edges": []}})

    assert [node["node_id"] for node in upgraded["pipeline"]["nodes"]] == [
        ROOTLESS_CROP_ID,
        f"span-{ROOTLESS_CROP_ID}",
    ]
    assert upgraded["replicates"][0]["overrides"] == {ROOTLESS_CROP_ID: {"roi": ARENA_ONE}}


def test_a_document_with_no_clip_gets_the_identity_span(v5: dict[str, Any]) -> None:
    """ "No span" is a value of the parameter, never the absence of the node.

    REWORK R1's identity-is-not-exemption clause: a document where the node
    appears only sometimes is a graph whose shape depends on whether a user
    happened to drag the timeline, and every reader of it would need the `None`
    branch back.
    """
    upgraded = carry_into_graph({**v5, "clip": None})
    span = next(node for node in upgraded["pipeline"]["nodes"] if node["node_id"] == "span-ema")

    assert span["params"] == {"start": 0, "end": UNBOUNDED_FRAME}


def test_a_tuned_detector_is_refused_by_name(v5: dict[str, Any]) -> None:
    """The one field the transform cannot carry says so, with its own name.

    Not an omission and not a scoping line: the detect filter's kernel is
    trailing, the saved field is centered and non-causal, and a node
    synthesized from it would claim different events. R2's posture — refuse by
    name rather than drop.
    """
    tuned = {**v5, "detector": {"window_frames": 30, "centered": True}}

    with pytest.raises(UnupgradableDocumentError, match="detector"):
        carry_into_graph(tuned)


def test_a_replicate_pinning_the_detector_is_refused_by_name(v5: dict[str, Any]) -> None:
    replicates = [dict(v5["replicates"][0], detector_overrides={"window_frames": 12})]

    with pytest.raises(UnupgradableDocumentError, match="detector_overrides"):
        carry_into_graph({**v5, "replicates": replicates})


def test_a_derived_id_the_document_already_uses_is_refused(v5: dict[str, Any]) -> None:
    """Refused rather than disambiguated, so one file has one upgrade."""
    nodes = [*v5["pipeline"]["nodes"], dict(v5["pipeline"]["nodes"][0], node_id="crop-down")]

    with pytest.raises(UnupgradableDocumentError, match="crop-down"):
        carry_into_graph({**v5, "pipeline": {**v5["pipeline"], "nodes": nodes}})
