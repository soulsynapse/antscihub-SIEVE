"""The resource side of the HUD wiring: what the session holds and what the pools do.

`main_window.py` has carried a live path from a measurement to something on
screen since the bus met the HUD; what never existed was anything publishing on
the resource side of it. This is that publisher. Once a second it reads the
three pool meters, asks the sampler thread for the session's RSS, judges the
reading against `shares.ledger_ceiling`, and emits one `ResourceSample`
on the GUI thread — the standing version of the measurement that was, twice,
a scratch script attached by PID.

**The expensive read happens off the GUI thread.** `process_memory_bytes`
walks the child-process list, which on Windows snapshots the process table —
milliseconds, on the thread every latency budget in `bench/budgets.py` is
about. So the tick runs on the GUI thread only long enough to read the meters
(a lock and two ints each) and the mode, and hands off to a worker for the
memory read, exactly the division `bench/metrics.py` states as "subscription
may not cost the thing it measures". A tick that arrives while the worker is
still out is skipped rather than queued: a sampler that fell behind must thin,
not backlog.

**Every sample carries the mode that produced it**, because the recorded
session of 2026-07-28 proved the confound: ordinary playback scored zero ring
hits at every capacity and the split had nothing to do with it — the ring was
not in play by design. A consumer that summed a render-fed sample with a plain
playback sample would average two regimes that do not compare, so the tag is
on the sample, not left to the reader's memory of what the app was doing.

**Utilisation is busy time over wall time times workers**, differenced between
consecutive ticks. "Time spent with work in flight" and "average worker
utilisation" diverge for a pool wider than one; the denominator uses the
resolved worker count so a two-worker pool with one worker saturated reads
0.5, which is the number that answers whether the *declared width* fits.

Rule 6 governs the memory reading: a sampler that cannot read a child process
refuses (`MemoryUnreadableError`), and the refusal is published as `rss_bytes =
None` rather than by silence — absent must not render as zero, and a probe
that went quiet would read as a session with nothing to report.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from time import perf_counter_ns

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, Slot

from sieve.gui.concurrency import resolve_worker_split
from sieve.mutual.machine import MemoryUnreadableError, process_memory_bytes
from sieve.mutual.pool_meter import PoolMeter
from sieve.mutual.shares import WorkerSplit, ledger_ceiling

#: One reading per second. Fast enough that the ledger item's "30-second
#: reading on small hardware" is thirty samples, slow enough that the GUI-side
#: half of a tick — six ints and a string — is nothing.
SAMPLE_INTERVAL_MS = 1000

#: The modes a sample may carry. Strings rather than an enum because the HUD
#: prints them verbatim and nothing branches on them — they exist to keep two
#: series apart, not to drive behaviour.
MODE_RENDER_FED_PLAYBACK = "render-fed playback"
MODE_PLAYBACK = "playback"
MODE_RENDER = "render"
MODE_IDLE = "idle"


@dataclass(frozen=True, slots=True)
class PoolReading:
    """One pool's interval, as resolved for this machine."""

    #: The row in `shares.SENSED` this reading is evidence about.
    name: str
    #: The resolved pool width the utilisation is denominated in.
    workers: int
    #: Busy time over `workers x wall`, clamped to [0, 1].
    utilisation: float
    #: Work waiting on the pool when the tick fired — an instantaneous gauge.
    depth: int


@dataclass(frozen=True, slots=True)
class ResourceSample:
    """One tick's readings, already judged against the ledger."""

    #: What the session was doing. Samples with different modes must never be
    #: summed or averaged together — see the module docstring's confound.
    mode: str
    #: Session RSS including children, or None when the reading was refused.
    #: None is a published refusal, not an absence of data (rule 6).
    rss_bytes: int | None
    #: `shares.ledger_ceiling()` for this machine at this tick.
    ledger_bytes: int
    pools: tuple[PoolReading, ...]

    @property
    def over_ledger(self) -> bool | None:
        """Whether the session holds more than the ledger accounts for.

        None when the reading was refused — an unreadable session is not
        within its ledger, it is unexamined, and the two must render apart.
        """
        if self.rss_bytes is None:
            return None
        return self.rss_bytes > self.ledger_bytes


class _MemoryWorker(QObject):
    """Lives on the sampler thread; the only place the expensive read runs."""

    sampled = Signal(object)

    def __init__(self, read_memory: Callable[[], int]) -> None:
        super().__init__()
        self._read_memory = read_memory

    @Slot(str, object)
    def complete(self, mode: str, pools: tuple[PoolReading, ...]) -> None:
        """Finish the tick: the memory read, the ceiling, one sample out."""
        try:
            rss: int | None = self._read_memory()
        except MemoryUnreadableError:
            rss = None
        self.sampled.emit(
            ResourceSample(mode=mode, rss_bytes=rss, ledger_bytes=ledger_ceiling(), pools=pools)
        )


class ResourceProbe(QObject):
    """Samples the session's resources once a second and publishes on the GUI thread.

    Construct on the GUI thread, after the objects whose meters it reads.
    Owns the sampler thread for its whole life, so `shutdown` is required
    before the application exits — the obligation every thread owner in
    `gui/` carries.
    """

    #: One `ResourceSample`, on the GUI thread. The HUD's slot connects here.
    sample = Signal(object)

    _requested = Signal(str, object)

    def __init__(
        self,
        meters: Mapping[str, PoolMeter],
        mode: Callable[[], str],
        parent: QObject | None = None,
        *,
        interval_ms: int = SAMPLE_INTERVAL_MS,
        read_memory: Callable[[], int] = process_memory_bytes,
        split: WorkerSplit | None = None,
    ) -> None:
        """Start sampling.

        Args:
            meters: One `PoolMeter` per pool row, keyed by the names in
                `shares.SENSED`. A mapping rather than three parameters
                so the reconciliation test and this signature cannot disagree
                about what the rows are.
            mode: What the session is doing right now. Called on the GUI
                thread at every tick, so it may read widget-owned state; it
                must be cheap, because it sits inside the tick the interval
                budget above assumes is nothing.
            parent: Owner.
            interval_ms: Tick period. A test passes something small; the
                application takes the default.
            read_memory: The RSS reading. Injectable so a test can pin the
                refusal path without arranging an unreadable process.
            split: The resolved pool widths utilisation is denominated in.
                `None` asks `resolve_worker_split`, which is the application's
                case; a test that fakes meters passes the split its fakes
                assume.
        """
        super().__init__(parent)
        self._meters = dict(meters)
        self._mode = mode
        resolved = resolve_worker_split() if split is None else split
        self._workers = {
            "player": resolved.player,
            "preview": resolved.preview,
            "detector": resolved.detector,
        }
        self._last_busy = {name: meter.busy_ns for name, meter in self._meters.items()}
        self._last_tick_ns = perf_counter_ns()
        self._awaiting = False

        self._thread = QThread()
        self._thread.setObjectName("sieve-resource-probe")
        self._worker = _MemoryWorker(read_memory)
        self._worker.moveToThread(self._thread)
        self._requested.connect(self._worker.complete)
        # Queued explicitly for `executor_adapter.py`'s reason: one rule, one
        # delivery order, whatever thread the sample was assembled on.
        self._worker.sampled.connect(self._on_sampled, Qt.ConnectionType.QueuedConnection)
        self._thread.start()

        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    def shutdown(self) -> None:
        """Stop the timer and the sampler thread. Call before the app exits."""
        self._timer.stop()
        self._thread.quit()
        self._thread.wait()

    # ---- the GUI thread ---------------------------------------------------

    @Slot()
    def _tick(self) -> None:
        """The cheap half: meters, mode, and a handoff. Skips if one is out."""
        if self._awaiting:
            return
        now = perf_counter_ns()
        wall = now - self._last_tick_ns
        self._last_tick_ns = now

        readings: list[PoolReading] = []
        for name, meter in self._meters.items():
            busy = meter.busy_ns
            workers = self._workers.get(name, 1)
            share = busy - self._last_busy[name]
            self._last_busy[name] = busy
            utilisation = min(max(share / (wall * workers), 0.0), 1.0) if wall > 0 else 0.0
            readings.append(
                PoolReading(name=name, workers=workers, utilisation=utilisation, depth=meter.depth)
            )

        self._awaiting = True
        self._requested.emit(self._mode(), tuple(readings))

    @Slot(object)
    def _on_sampled(self, sample: object) -> None:
        self._awaiting = False
        self.sample.emit(sample)
