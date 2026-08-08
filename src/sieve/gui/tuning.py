"""The loop itself: an edit lands, the graph goes stale, a refill answers it.

Everything Phase 6 measured headless, wired to the two things that make it a
product — a document a user edits, and a panel that draws the answer. The
session, the collector and the store are the pipeline layer's; what is here is
*when* a refill happens and what it does to the widget in between.

**Two surfaces, one store.** An edit moves the graph and the picture, and both
come out of the same `PreviewSession` — the window render for the trace, a
single-frame render for the viewport. The playhead the picture is at is not
held here: the transport owns it, and a copy would be the stale one, so
`render_at` is asked for a frame rather than told to keep up.

**A refill is deferred by one turn of the event loop, and that is the whole of
the coalescing.** The stale mark has to be painted before the render begins or
it is a state nothing can ever see, and a burst of edits — a spin box counting
through the digits of a typed number, a slider emitting on every pixel — must
cost one render rather than one each. A single-shot timer restarted on every
request does both: the mark is drawn on the turn the edit lands, and only the
last request of that turn survives to render. What it is not is a fence around a
render already in flight, which is `preview.py`'s deferral and belongs to
whatever eventually moves the render off this thread.

**The render is synchronous on the GUI thread**, which is what the budget scope
promises and no more: the reference workload renders inside `slider_to_graph`,
so nothing freezes for a perceptible interval, and outside that scope VISION's
honesty half is what survives — the graph says it is stale and says so for as
long as the render takes. Moving the render to a worker is the coalescing
discipline `preview.py` describes and is not bought here, where it would be a
second answer to what supersedes what
(`todo/the-generated-controls-commit-on-intent-not-on-pass-through.md`).

**A refill that raises leaves the mark up.** The panel has two states and
neither of them is "the render failed"; a graph that answered to the previous
parameters and says so is the honest reading of a document that has just been
edited into something that will not render, and blanking it would take away the
only thing the next refill can be compared against. The exception is held rather
than swallowed, because a window with no console is where an unreported
`GraphError` goes to die.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from PySide6.QtCore import QObject, QTimer, Signal

from sieve.bench.metrics import METRICS
from sieve.core.pipeline_model import Pipeline, SourceSpan
from sieve.core.tool_registry import ToolRegistry
from sieve.decode.prefetch import PrefetchFrameSource
from sieve.gui.graph_panel import GraphPanel
from sieve.pipeline.cache import MemoryFrameStore
from sieve.pipeline.cache_key import source_identity
from sieve.pipeline.dag import graph_needs_chroma
from sieve.pipeline.preview import Measure, PreviewSession
from sieve.pipeline.series_collector import SeriesCollector

#: How long a request waits before it renders. Zero: what the delay is for is
#: reaching the event loop at all, not letting further edits accumulate — a
#: timeout tuned to catch the next keystroke would be a debounce, which decides
#: on the user's behalf that they have stopped typing.
_DEFER_MS = 0


class TuningLoop(QObject):
    """One footage, one window, one watched node, and the panel it fills."""

    #: A refill has produced a series. What it is for is the *other* surface the
    #: same edit moved: the viewport shows a rendered frame too, and the window
    #: is where the two are kept in step because only it knows where the
    #: playhead is. Emitted after the panel is handed the series, and not at all
    #: for a refill that raised — a render that could not produce a graph cannot
    #: produce a picture either.
    refilled = Signal()

    def __init__(
        self,
        panel: GraphPanel,
        parent: QObject | None = None,
        *,
        measure: Measure = METRICS.measure,
        registry: ToolRegistry | None = None,
    ) -> None:
        """Fill `panel` from renders of whatever graph a request carries.

        Args:
            panel: Where a completed refill lands, and where a pending one is
                announced.
            measure: How a timed span is published. The process-wide bus by
                default, so a HUD subscribing to it hears the loop without
                anything being threaded through the window; injectable for
                `bench/metrics.py`'s reason — a benchmark must hear itself and
                not another window.
            registry: The shelf graphs resolve against.
        """
        super().__init__(parent)
        self._panel = panel
        self._measure = measure
        self._registry = registry

        self._reader: PrefetchFrameSource | None = None
        self._session: PreviewSession | None = None
        self._collector: SeriesCollector | None = None
        self._pending: Pipeline | None = None
        self._error: Exception | None = None

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._render)

    # ---- state -----------------------------------------------------------

    @property
    def is_open(self) -> bool:
        """Whether there is footage a refill could render."""
        return self._session is not None

    @property
    def watching(self) -> str | None:
        """The node whose series the panel is drawing, or None."""
        return None if self._collector is None else self._collector.node_id

    @property
    def last_error(self) -> Exception | None:
        """What the last refill raised, or None if it produced a series."""
        return self._error

    # ---- the footage -----------------------------------------------------

    def open(self, video: Path, pipeline: Pipeline, window: SourceSpan) -> None:
        """Preview `window` of `video`, replacing whatever was open.

        Called when the transport reports metadata rather than when a project
        is chosen: that signal is the one thing in the window that has actually
        read the container, and a second check here of whether the file is
        there could disagree with it.

        The decode format is decided from the graph and held for the session,
        because a reader is not something a preview can reopen mid-render
        (`dag.graph_needs_chroma`). An edit cannot change it — a parameter moves
        no tool onto or off the graph.

        Raises:
            VideoDecodeError: if the container cannot be opened.
        """
        self.close()
        self._reader = PrefetchFrameSource(
            video, luma=not graph_needs_chroma(pipeline, self._registry)
        )
        self._session = PreviewSession(
            source=source_identity(video),
            reader=self._reader,
            window=window,
            measure=self._measure,
            store=MemoryFrameStore(),
            registry=self._registry,
        )

    def close(self) -> None:
        """Drop the footage and everything keyed against it."""
        self._timer.stop()
        self._pending = None
        self._session = None
        self._collector = None
        self._panel.set_series(None)
        if self._reader is not None:
            self._reader.close()
            self._reader = None

    def set_window(self, window: SourceSpan) -> None:
        """Preview a different stretch. Keeps the store — see `preview.py`."""
        if self._session is not None:
            self._session.set_window(window)

    def watch(self, node_id: str | None) -> None:
        """Draw `node_id`'s series from now on, or nothing for None.

        A fresh collector rather than a retargeted one: the rows already
        assembled are the previous node's, and a collector that changed its mind
        mid-series would stack two nodes' frames into one array.
        """
        self._collector = (
            None if node_id is None else SeriesCollector(node_id, measure=self._measure)
        )
        self._panel.set_series(None)

    # ---- the loop --------------------------------------------------------

    def request_refill(self, pipeline: Pipeline) -> None:
        """The graph has moved; mark what is drawn and render on the next turn.

        A no-op with nothing open or nothing watched, and the panel is left
        showing whatever it had: a window with no footage has no graph to be
        stale about.
        """
        if self._session is None or self._collector is None:
            return
        self._pending = pipeline
        self._panel.mark_stale()
        self._timer.start(_DEFER_MS)

    def refill_now(self, pipeline: Pipeline) -> None:
        """`request_refill` without the deferral, for a caller with no event loop."""
        self.request_refill(pipeline)
        if self._timer.isActive():
            self._timer.stop()
            self._render()

    def render_at(self, pipeline: Pipeline, node_id: str, index: int) -> NDArray[np.float32] | None:
        """`node_id`'s output for source frame `index`, off the store the graph uses.

        `preview.render_frame` and not a second `render_window`: the picture
        under the playhead is one frame, and re-running the whole window to move
        it is what that method's docstring calls the end of direct manipulation.
        The store is the session's, so everything above the edited node is served
        rather than recomputed — the same mechanism the graph's refill rests on.

        `None` when there is no footage open, and `None` for a render that
        raised, which is held in `last_error` on the module docstring's terms:
        the previous frame stays on the viewport, because it is the only thing
        the next render can be compared against.
        """
        if self._session is None:
            return None
        held: list[NDArray[np.float32]] = []
        try:
            self._session.render_frame(
                pipeline,
                index,
                on_frame=lambda result: held.append(np.asarray(result[node_id].data, np.float32)),
            )
        except Exception as error:  # noqa: BLE001 — held, not swallowed; see the docstring
            self._error = error
            return None
        return held[0] if held else None

    def _render(self) -> None:
        pipeline, self._pending = self._pending, None
        if pipeline is None or self._session is None or self._collector is None:
            return
        self._error = None
        try:
            with self._collector.refill() as consume:
                self._session.render_window(pipeline, on_frame=consume)
        except Exception as error:  # noqa: BLE001 — held, not swallowed; see the docstring
            self._error = error
            return
        self._panel.set_series(self._collector.series)
        self.refilled.emit()
