"""The one place that knows both the metric bus and Qt.

`bench/metrics.py` is Qt-free and the `headless` contract in `.importlinter`
keeps it that way, so something has to carry a `Sample` across the boundary.
This is that something, and it is deliberately the *only* such thing: every
widget that reacts to a timing connects to a signal here rather than calling
`MetricBus.subscribe` for itself.

**The job is the thread, not the translation.** A subscriber is called on the
publishing thread — `preview_runner.py`'s render thread, the decode thread,
whatever publishes next — and touching a widget from there is undefined
behaviour that manifests as a crash under load and as nothing at all in a test.
Re-emitting a `Sample` as a signal is trivial; getting it onto the GUI thread is
the whole reason this module exists, and it is why `bench/metrics.py` does not
try to do the hop itself: the bus has no way to know where its consumers want to
be, and a bus that queued to a thread would need a Qt event loop to queue to.

**The hop is an internal queued connection, not `QMetaObject.invokeMethod`.**
`_relayed` is emitted on the publishing thread and connected to `_on_relayed`
with an explicit `QueuedConnection`, so Qt posts the event to the thread this
object *lives* on and delivers it when that thread next runs its event loop.
Explicit rather than relying on `AutoConnection` working out that the emitting
thread differs: auto would deliver directly whenever a sample happens to be
published on the GUI thread, which is a real case — `gui/transport/player.py` publishes
`scrub_to_repaint` from a GUI-thread slot — and it would make delivery order
depend on who published. One rule, one order.

**The subscriber does as little as possible.** It sits inside whatever interval
the publisher is timing next, and `bench/metrics.py` promises only that a
subscriber is charged to the caller's wall clock rather than to the sample.
Emitting one signal and returning is what keeps that promise cheap; anything
that formats, filters, or stores belongs on the receiving side of the queued
connection, where it is on the GUI thread and no publisher is waiting for it.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal, Slot

from sieve.bench.metrics import METRICS, MetricBus, Sample


class ExecutorAdapter(QObject):
    """Subscribes to a `MetricBus`, emits its samples on the GUI thread.

    Construct on the GUI thread — the queued connection delivers to the thread
    the object lives on, so an adapter built anywhere else would relay to that
    thread instead and defeat the whole point.

    Subscribes for its whole life. There is no lazy connect-on-first-listener,
    because the samples this drops while nobody is listening are exactly the
    ones that answer "how long did the first thing take", and a HUD constructed
    a moment after the first render would find that interval already gone.
    """

    #: One measured interval, on the GUI thread. Carries the `Sample` whole
    #: rather than `(key, ms)`: it already holds the `Budget` and the verdict,
    #: and a consumer that had to look the ceiling up again would be a second
    #: reader of the table `bench/metrics.py` reads once at publish.
    sample = Signal(Sample)

    #: The same sample, but only when it missed its ceiling. A separate signal
    #: rather than a flag on the one above, because the consumers differ: a HUD
    #: plots every sample and a status bar or a toast wants only the misses, and
    #: the filtering being here means neither of them writes `if not
    #: sample.within_budget` and gets it subtly different.
    missed = Signal(Sample)

    #: Internal. Emitted on the publishing thread, delivered on ours.
    _relayed = Signal(Sample)

    def __init__(self, bus: MetricBus | None = None, parent: QObject | None = None) -> None:
        """Relay everything `bus` publishes. Defaults to the process-wide bus.

        Args:
            bus: Where samples come from. Injectable for the reason
                `gui/transport/player.py` takes one: a test asserting on what arrived must
                not hear another test's publisher, and `METRICS` is shared by
                construction.
            parent: Owner. Giving one is what ties `close` below to the
                lifetime of the window rather than to a garbage collection.
        """
        super().__init__(parent)
        self._relayed.connect(self._on_relayed, Qt.ConnectionType.QueuedConnection)
        self._unsubscribe = (METRICS if bus is None else bus).subscribe(self._receive)

    def close(self) -> None:
        """Stop listening. Idempotent, and safe to call from teardown.

        Worth calling explicitly rather than leaving to destruction: the bus
        holds the subscription, so an adapter that is merely dropped keeps its
        `_receive` alive on a `QObject` Qt may already have deleted, and the
        next publish reaches a wrapper around nothing.
        """
        self._unsubscribe()

    # ---- the publishing thread -------------------------------------------

    def _receive(self, sample: Sample) -> None:
        """Bus subscriber. Runs on whatever thread published — never assume ours."""
        self._relayed.emit(sample)

    # ---- the GUI thread ---------------------------------------------------

    @Slot(Sample)
    def _on_relayed(self, sample: Sample) -> None:
        """Queued arrival. Everything connected downstream of here is on our thread."""
        self.sample.emit(sample)
        if not sample.within_budget:
            self.missed.emit(sample)
