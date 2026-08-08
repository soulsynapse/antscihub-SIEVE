"""The graph: what the collector assembled, and whether it still answers.

Two things can be wrong here and each is its own case. The trace can misplace
the series it was handed — a graph whose x is not the frame it names is a graph
about the wrong footage, which is the failure `CollectedSeries.start_index`
exists to prevent one layer down and which this layer can reintroduce on its
own. And a graph left on screen after the parameters under it moved reads as an
answer about the current tuning, which is the claim VISION's honesty half
refuses to let a surface make silently.

The rest is what the panel is not allowed to do quietly: reduce a frame it was
handed to a number, and join a trace across a value the tool declined to give.

Qt and `sieve.gui` are imported inside the tests, for the reason `conftest.py`
gives.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pytest

from sieve.pipeline.series_collector import CollectedSeries

#: The panel these tests are laid out over. Wide enough that a frame's column is
#: a readable fraction of it, and a height that makes the value axis arithmetic
#: legible.
PANEL_WIDTH = 400
PANEL_HEIGHT = 200

#: Where the fixture series starts. Not zero: the panel is drawn from a rendered
#: window, and a panel that assumed frame zero would pass every assertion below
#: with the wrong axis.
START = 100


def series(values: Sequence[float], start: int = START) -> CollectedSeries:
    """`values` as the collector would hand them over — one scalar per frame."""
    return CollectedSeries(
        start_index=start,
        data=np.asarray(values, np.float32).reshape(len(values), 1, 1),
    )


@pytest.fixture
def panel(qapp) -> Any:
    del qapp
    from sieve.gui.graph_panel import GraphPanel

    widget = GraphPanel()
    widget.resize(PANEL_WIDTH, PANEL_HEIGHT)
    return widget


def test_the_panel_draws_the_series_it_is_handed(panel: Any) -> None:
    """One point per frame, in the column that frame names, zero on the floor.

    The x assertion is against `start_index` rather than against the ordinal:
    the two agree for a series starting at zero, which is exactly the series
    nobody renders.
    """
    panel.set_series(series([0.0, 1.0, 2.0, 3.0]))
    runs = panel.trace()

    assert len(runs) == 1
    points = runs[0]
    assert [point.x() for point in points] == pytest.approx(
        [PANEL_WIDTH * (offset + 0.5) / 4 for offset in range(4)]
    )
    assert panel.x_of(START) == pytest.approx(PANEL_WIDTH * 0.5 / 4)
    # Zero is the floor of the value axis, so it lands on the bottom edge: with
    # no tick labels a raised floor would draw a value of nothing as something.
    assert points[0].y() == pytest.approx(float(PANEL_HEIGHT))
    assert points[-1].y() < points[0].y()
    assert not panel.is_stale
    assert panel.status_text() == ""


def test_a_stale_series_is_labeled_stale(panel: Any) -> None:
    """The old graph stays up and says what it is, rather than blanking.

    Blanking would cost the user the only thing they had to compare the next
    refill against; leaving it silent would let it read as an answer about the
    parameters they just changed.
    """
    panel.set_series(series([1.0, 2.0]))
    panel.mark_stale()

    assert panel.is_stale
    assert "stale" in panel.status_text()
    assert len(panel.trace()[0]) == 2

    panel.set_series(series([3.0, 4.0]))
    assert not panel.is_stale


def test_a_frame_with_more_than_one_value_is_refused(panel: Any) -> None:
    """Reducing an image to a number is a tool's job, and it would be invisible here.

    A panel that took the first element, or the mean, would draw a plausible
    trace of a quantity nothing in the document named.
    """
    with pytest.raises(ValueError, match="1 value per frame"):
        panel.set_series(CollectedSeries(start_index=START, data=np.zeros((3, 2, 2), np.float32)))


def test_a_value_the_tool_declined_to_give_breaks_the_trace(panel: Any) -> None:
    """`detect` emits NaN where its gate has no answer, and a line drawn across
    that is a claim the tool refused to make."""
    panel.set_series(series([1.0, 2.0, float("nan"), 4.0, 5.0]))
    runs = panel.trace()

    assert [len(run) for run in runs] == [2, 2]
    assert runs[1][0].x() == pytest.approx(panel.x_of(START + 3))


def test_a_panel_with_nothing_to_draw_says_so(panel: Any) -> None:
    """The state before the first refill, and after one that reached no rows."""
    assert panel.trace() == []
    assert panel.status_text() != ""
    # A column of an axis that does not exist. Asked for by a resize arriving
    # before the first series, which is what a widget shown empty does.
    assert panel.x_of(START) == 0.0
