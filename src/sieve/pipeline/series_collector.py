"""Assemble one node's per-frame outputs into the series a graph is drawn from.

`execute` yields one frame at a time and a graph is drawn from a whole span at
once, so something has to hold the rows in between. That is the whole of this
module, and it is the reason `slider_to_graph` had no subject: a repo that can
render a preview and cannot assemble a series can measure the drag to the
*picture* and not the drag to the *graph*, which is half of the loop VISION is
about.

**Not the detector's feed, which is what v2 built this for.** There, the
detector ran outside the executor over a series something else had stacked, and
`gui/` and `cli/detect_cmd.py` both needed one. Under schema v1 the detector is a
node (`adr/detector-is-a-node.md`) and the executor hands it its own window, so
the only consumer left is the plotting path — which is why `PLAN.md` files this
module later than v2 would suggest and why it lands in Phase 6 anyway: a
`slider_to_graph` first measured through Qt could never be attributed to
anything else.

**The refill is the timed thing, and it ends at the array.** A span that closed
when the render finished would be a number about rendering; the user is waiting
for a graph, so `refill` stacks the rows before it lets the clock stop. The key
is a literal for `preview.py`'s reason — `sieve.bench` sits above this layer and
may not be imported from it — and `test_budget_producers.py` is what stops the
literal from being a metric nobody watches.

**No revision fence and no lock**, both of which v2's collector had. They are
for a caller that supersedes a render in flight, and nothing in this repo does:
`preview.py` renders synchronously and says outright that coalescing belongs to
the transport layer Phase 7 re-derives. A fence built before that caller exists
would be a second answer to what supersedes what, competing with the one the
transport will bring.

The frame axis is the *span's*, not the decode's: `execute` yields only frames at
or after `plan.span.start`, so the first row of a refill defines `start_index`
and every row after it must be the next frame. A gap means frames were lost
between the render and here, and a series with a silent hole in it plots as a
trace shifted at the hole rather than as an error.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from sieve.pipeline.executor import FrameResult
from sieve.pipeline.preview import Consumer, Measure

#: The interval from the gesture that starts a refill to its series existing.
#: A literal because the budget table is one layer up; see the module docstring.
SERIES_BUDGET = "slider_to_graph"


@dataclass(frozen=True, slots=True)
class CollectedSeries:
    """One refill's assembled series, aligned to source frame indices."""

    #: Source index of `data[0]` — the rendered span's start, and not zero: a
    #: working window is a stretch of footage, and a graph drawn as if it began
    #: at the file's first frame is a graph about the wrong frames.
    start_index: int
    #: `(T, *the node's frame shape)` float32, contiguous from `start_index`.
    data: NDArray[np.float32]


class SeriesCollector:
    """Rows in as a render produces them, one array out when it finishes.

    One collector watches one node. Not thread-safe, for `PreviewSession`'s
    reason and not a weaker one: a caller rendering on a worker thread already
    holds one render at a time, and a lock here would make that discipline look
    optional.
    """

    def __init__(self, node_id: str, *, measure: Measure) -> None:
        """Watch `node_id`, publishing each refill's interval through `measure`.

        Args:
            node_id: The node whose per-frame outputs make the series.
            measure: How a timed span is published — `MetricBus.measure` is the
                real one. Required for `PreviewSession`'s reason: the refill
                interval *is* the claim this module exists to make.
        """
        self._node_id = node_id
        self._measure = measure
        self._start: int | None = None
        self._rows: list[NDArray[np.float32]] = []
        self._series: CollectedSeries | None = None

    @property
    def node_id(self) -> str:
        """The node whose outputs this assembles."""
        return self._node_id

    @property
    def series(self) -> CollectedSeries | None:
        """The last completed refill's series, or `None` if it produced no rows.

        `None` while a refill is open, so a consumer that reads this at the
        wrong moment gets nothing rather than the previous drag's graph.

        A refill that produced no rows is `None` too, and that is a different
        claim from an empty series: the render never reached the watched node,
        which a caller reports as having nothing to draw rather than as a flat
        trace.
        """
        return self._series

    @contextmanager
    def refill(self) -> Iterator[Consumer]:
        """Time one refill, yielding the consumer the render feeds.

        The stack happens after the render and before the clock stops — see the
        module docstring. A render that raises publishes nothing, which is
        `MetricBus.measure`'s rule and the right one here: a refill that ended
        in an exception assembled no graph.
        """
        self._start = None
        self._rows = []
        self._series = None
        with self._measure(SERIES_BUDGET):
            yield self.add
            self._series = self._stacked()

    def add(self, result: FrameResult) -> None:
        """One frame's outputs, in the order the render produced them.

        Raises:
            KeyError: if `result` carries no output for the watched node.
                `execute` computes every node for every frame it yields, so an
                absence is a node id that names nothing rather than a graph
                legitimately rendering a prefix.
            ValueError: if `result` is not the frame after the last one added.
        """
        row = np.asarray(result[self._node_id].data, np.float32)
        if self._start is None:
            self._start = int(result.index)
        expected = self._start + len(self._rows)
        if int(result.index) != expected:
            raise ValueError(
                f"series for {self._node_id!r} expected frame {expected}, got "
                f"{int(result.index)}; a gap here plots as a shifted trace"
            )
        self._rows.append(row)

    def _stacked(self) -> CollectedSeries | None:
        if self._start is None:
            return None
        return CollectedSeries(start_index=self._start, data=np.stack(self._rows))
