"""The upgraded document computes what the document it came from computed.

The migration's second test
(`docs/todo/the-graph-carries-the-crop-the-span-and-the-detector.md`): a v5
document rendered through the path it was written for, diffed frame for frame
against the same document upgraded and rendered through its graph. The
per-node halves of this already exist in `test_executor_run.py` — a crop node
against `plan.roi`, a span node against a requested clip — and neither can make
this claim, because what the upgrade can get wrong is not the node, it is which
replicate's box landed on it and which of the two ranges reached its bounds.

**Both sides run against the same reader through the same executor**, and the
only difference is where the crop and the span come from. The v6 side's
replicates are given `WHOLE_FRAME` so `plan.roi` is the identity — the field is
still on the model until the flip lands, and setting it to its identity value
is how this test says "the graph is carrying this now" rather than deleting a
field it cannot yet delete.

Two replicates with different boxes and a per-node deviation on one of them,
because a fixture whose arenas resolve alike passes against an upgrade that
drops per-replicate pinning entirely — the same trap `test_gui_cli_parity.py`
records for its own fixture.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

from sieve.backend.dispatch import Backend
from sieve.core.pipeline_model import ClipRange, Project
from sieve.core.replicates import Replicate
from sieve.decode.reader import VideoReader
from sieve.filters import discover
from sieve.filters.crop import WHOLE_FRAME
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import Dag
from sieve.pipeline.executor import execute
from sieve.pipeline.plan import ExecutionPlan
from sieve.pipeline.upgrade import carry_into_graph

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "project-v5.sieve.yaml"

#: The node whose output is compared. The last node the *original* document
#: had, so the comparison is over pixels both documents claim to produce — the
#: span node above it exists on one side only.
LEAF = "ema"

#: Wider than the fixture's clip on both sides, and wider than the footage on
#: one. What the v6 side is asked for is "everything", exactly as a caller
#: holding a document with no `clip` would ask; the graph is what narrows it.
WHOLE_VIDEO = ClipRange(start=0, end=40)


@pytest.fixture(scope="module")
def v5() -> dict[str, Any]:
    text = FIXTURE.read_text(encoding="utf-8")
    assert Project.from_yaml(text).schema_version == 5
    loaded: dict[str, Any] = yaml.safe_load(text)
    return loaded


def _rendered(
    project: Project, video: Path, replicate: Replicate, span: ClipRange
) -> list[tuple[int, np.ndarray[Any, Any]]]:
    plan = ExecutionPlan.build(
        Dag.build(project.pipeline),
        source=source_identity(video),
        span=span,
        backend=Backend.CPU,
        replicate=replicate,
    )
    with VideoReader(video, luma=plan.luma) as reader:
        return [(result.index, result[LEAF].data) for result in execute(plan, reader)]


def _as_v6_shell(upgraded: dict[str, Any]) -> Project:
    """The upgraded document, loaded through a model that still has the fields.

    `Replicate.roi` is required and `Project.clip` exists until the flip drops
    them, so a document that no longer carries either cannot be validated yet.
    Filling them with their identity values — the unbounded region, and no clip
    — is what makes this a test of the graph: whatever the run produces, none of
    it came from the two fields.
    """
    whole = {"x": 0, "y": 0, "width": WHOLE_FRAME.width, "height": WHOLE_FRAME.height}
    replicates = [{**replicate, "roi": whole} for replicate in upgraded["replicates"]]
    return Project.model_validate({**upgraded, "replicates": replicates, "clip": None})


def test_the_upgraded_document_renders_the_frames_its_v5_form_rendered(
    synthetic_video: Path, v5: dict[str, Any]
) -> None:
    assert discover()
    before = Project.model_validate(v5)
    after = _as_v6_shell(carry_into_graph(v5))
    assert before.clip is not None

    for old, new in zip(before.replicates, after.replicates, strict=True):
        by_field = _rendered(before, synthetic_video, old, before.clip)
        by_graph = _rendered(after, synthetic_video, new, WHOLE_VIDEO)

        assert [index for index, _ in by_graph] == [22, 23, 24, 25]
        assert [index for index, _ in by_field] == [index for index, _ in by_graph]
        assert all(
            np.array_equal(left, right)
            for (_, left), (_, right) in zip(by_field, by_graph, strict=True)
        )


def test_the_two_replicates_disagree_with_each_other(
    synthetic_video: Path, v5: dict[str, Any]
) -> None:
    """The guard the equivalence above needs, and cannot supply itself.

    Two arenas whose renders match make every assertion in this module pass
    against an upgrade that pins one replicate's box on both — which is exactly
    the mistake a per-replicate migration makes. So the fixture has to be able
    to disagree with itself, and something has to check that it still does.
    """
    assert discover()
    after = _as_v6_shell(carry_into_graph(v5))
    first, second = (
        _rendered(after, synthetic_video, replicate, WHOLE_VIDEO) for replicate in after.replicates
    )

    assert first[0][1].shape != second[0][1].shape
