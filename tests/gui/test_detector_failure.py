"""A derivation that raises says so, instead of leaving the graph quiet.

`_DetectorWorker.compute` used to catch `ValueError` and `FloatingPointError`
and simply return. The argument for it was half right — every input was
validated by the chain that produced it, so a raise is a defect in that module
rather than something a user can act on, and a partial pass must not replace a
merely-incomplete graph with one claiming to be broken. What it did not justify
is silence: the graph stopped advancing and said nothing, which reads as "the
derivation is still coming", and that is rule 6 exactly.

Three claims, three distinct failures:

* the worker reports rather than swallows — otherwise nothing downstream can
  possibly say anything;
* the runner's one-in-flight slot is freed by a failure as it is by a success —
  otherwise one raised pass takes the tab's whole pacing loop down with it, and
  the *second* symptom is a tab that never derives again;
* the notice survives a repaint — the tab rebuilds every plot notice from the
  chain in `_apply`, so a notice written straight to the widget would last
  until the next mouse-move and no longer.
"""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import pytest
from pytestqt.qtbot import QtBot

from sieve.bench.metrics import MetricBus
from sieve.gui.chain_model import DetectorState
from sieve.gui.detector_worker import DetectorFailure, DetectorRequest, DetectorRunner
from sieve.gui.document import ReplicateDocument
from sieve.gui.filter_tab import FilterTab
from sieve.gui.preview_runner import PreviewRunner
from sieve.gui.transport.player import VideoPlayer

pytestmark = pytest.mark.gui

WAIT_MS = 5000


def request_over(series: np.ndarray, *, revision: int = 0) -> DetectorRequest:
    return DetectorRequest(
        revision=revision,
        series=series,
        start_index=0,
        fps=30.0,
        state=DetectorState(),
        final=True,
    )


#: A `(T, ny, nx)` series with a zero-length time axis. `derive` stacks it,
#: reshapes it, and the transform raises on the empty axis — a real raise from
#: the real code path, rather than a monkeypatched one that would prove only
#: that `try` blocks work.
EMPTY_SERIES = np.zeros((0, 2, 2), np.float32)


class TestAFailedPassIsReportedRatherThanSwallowed:
    @pytest.fixture
    def runner(self, qapp: object) -> Iterator[DetectorRunner]:
        del qapp
        instance = DetectorRunner()
        yield instance
        instance.shutdown()

    def test_a_raising_derivation_arrives_as_a_failure_with_something_to_say(
        self, qtbot: QtBot, runner: DetectorRunner
    ) -> None:
        """Through the runner rather than the worker: the claim is that a
        failure reaches the GUI thread, and the worker's own emit is only half
        of that path."""
        caught: list[object] = []
        runner.failed.connect(caught.append)
        with qtbot.waitSignal(runner.failed, timeout=WAIT_MS):
            runner.submit(request_over(EMPTY_SERIES))
        failure = caught[0]
        assert isinstance(failure, DetectorFailure)
        assert failure.revision == 0
        # The type name at least, or the notice reads "the graphs did not
        # derive — " and stops, which says no more than silence did.
        assert failure.message.strip()

    def test_the_in_flight_slot_is_freed_by_a_failure(
        self, qtbot: QtBot, runner: DetectorRunner
    ) -> None:
        """`busy` must fall back to false, or the tab's idle gate never opens.

        A good pass is submitted afterwards and has to land: asserting only on
        `busy` would pass against a runner that freed the flag and left the
        thread wedged.
        """
        with qtbot.waitSignal(runner.failed, timeout=WAIT_MS):
            runner.submit(request_over(EMPTY_SERIES))
        assert not runner.busy

        good = np.random.default_rng(1).random((24, 2, 2)).astype(np.float32)
        with qtbot.waitSignal(runner.ready, timeout=WAIT_MS):
            runner.submit(request_over(good))


class TestTheTabSaysSoOnTheGraph:
    @pytest.fixture
    def player(self, qapp: object) -> Iterator[VideoPlayer]:
        del qapp
        instance = VideoPlayer()
        yield instance
        instance.shutdown()

    @pytest.fixture
    def preview(self, qapp: object) -> Iterator[PreviewRunner]:
        del qapp
        instance = PreviewRunner(metrics=MetricBus())
        yield instance
        instance.shutdown()

    @pytest.fixture
    def tab(
        self,
        qtbot: QtBot,
        player: VideoPlayer,
        document: ReplicateDocument,
        preview: PreviewRunner,
    ) -> Iterator[FilterTab]:
        instance = FilterTab(player, document, preview, metrics=MetricBus())
        qtbot.addWidget(instance)
        yield instance
        instance.shutdown()

    def test_the_notice_names_the_failure_and_survives_a_repaint(self, tab: FilterTab) -> None:
        """The whole point: a graph that is not current must not look current.

        `_apply` is called a second time by hand because it is what every
        later interaction calls — a drag, a playhead move, a step selection.
        A notice that did not survive it would be gone before the user's next
        mouse-move, which is indistinguishable from never having been shown.
        """
        failure = DetectorFailure(revision=0, message="MemoryError: nope")
        tab._on_detector_failed(failure)  # pyright: ignore[reportPrivateUsage]
        assert "MemoryError: nope" in tab._count.notice  # pyright: ignore[reportPrivateUsage]

        tab._apply()  # pyright: ignore[reportPrivateUsage]
        assert "MemoryError: nope" in tab._count.notice  # pyright: ignore[reportPrivateUsage]
