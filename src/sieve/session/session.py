"""The running thing: what is open, what is filling, and what answered.

Everything below this module is a part that can be checked alone. This is where
they are wired together, and its job is almost entirely *not* deciding: the
ladder says what to try, the schedules say in what order, `form.grade` says what
may be kept, and the session executes. What it owns is state — which source,
which crop, which window, which steps are active — and one rule.

**The rule: a decode of the original never runs on the thread that draws,
unless the user just released a control.** It is enforced here rather than
remembered, by knowing which thread constructed the session and refusing. Every
version of this tree that has felt frozen has felt that way for this reason, and
the finding is unambiguous that the symptom is not slowness but a window that
has stopped answering.

**No module-level state, and that is the substantive change.** In the explorers
the source, the crop rect, the window length and the chunk directory are module
globals, and `_crop` reads a mutable one from three threads. The threading is
the lesser half of that defect. The greater half is that a crop nobody can name
in a key produces values not reproducible from the key they are filed under,
which is the single invariant `05-provenance.py` exists to check — so the crop
is a step's parameters here, passed to `form_for`, and never read from the air.

**The crop is a tool, and the window stores its form.** A crop change is a form
change: the resident store simply misses, the old picture stays until eviction
takes it, and the window refills. That is what `02-form-derivation.py` measured
and it is not made cheap here.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from sieve.analysis.record import Recorder
from sieve.analysis.tool import Tool, residency
from sieve.decode.hybrid import HybridRoute
from sieve.decode.route import Route
from sieve.frame.form import Form, build, derive
from sieve.frame.shape import Shape
from sieve.frame.table import FrameTable
from sieve.session import ladder as ladder_mod
from sieve.session.frontier import Frontier
from sieve.session.ladder import (
    CHUNK,
    DECODE,
    DERIVE,
    HOLD,
    KEYFRAME,
    NEAR,
    PROXY,
    RESIDENT,
    Request,
    Situation,
    admissible,
)
from sieve.session.ledger import DOUBLE_DECODE, PLACEHOLDER, Ledger
from sieve.store.chunks import CHUNK_ROWS, ChunkStore
from sieve.store.resident import NEAR_RADIUS, ResidentStore
from sieve.store.spans import SpanStore

#: The tuning window, in rows. Ten seconds of the footage this tree runs on,
#: which is the gesture the product is built around rather than a tuning knob.
WINDOW_ROWS = 300

#: What the resident store may hold. A default rather than a fact: the right
#: figure depends on the machine and on how large the crop is, and a session
#: that wants a different one says so.
BUDGET_BYTES = 1_500_000_000


class BlockedTheDrawingThread(RuntimeError):
    """Raised where a decode would have run on the thread that draws.

    An exception rather than a log line, because the failure it guards is one
    that reads as the application hanging: by the time somebody notices, the
    information about which request did it is gone. Better to fail loudly in
    the place with the answer.
    """


@dataclass(frozen=True)
class Served:
    """What a request got, and where it came from."""

    row: int
    image: np.ndarray | None     #: `None` means hold: show what is already up
    tier: str
    ms: float
    admitted: bool = False
    stood_in_for: int | None = None   #: the row actually shown, if not `row`

    @property
    def exact_pixels(self) -> bool:
        return self.image is not None and self.stood_in_for is None


class Session:
    """One source, its stores, its producers, and what answered."""

    def __init__(self, source: Path, derived: Path, *,
                 route: Route | None = None,
                 proxy: SpanStore | None = None,
                 budget_bytes: int = BUDGET_BYTES,
                 window_rows: int = WINDOW_ROWS,
                 rows_per_chunk: int = CHUNK_ROWS,
                 ledger: Ledger | None = None):
        self.source = source
        self.derived = derived
        self.shape = Shape.read(source) if route is None else None
        self.table = FrameTable.cached(source) if route is None else route.table
        self.ledger = ledger or Ledger()

        self.route = route or HybridRoute(source, self.table, self.shape)
        self.source_form: Form = self.route.form
        self.resident = ResidentStore(budget_bytes=budget_bytes)
        self.chunks = ChunkStore(derived / "chunks", self.table,
                                 rows_per_chunk=rows_per_chunk)
        self.proxy = proxy
        self.proxy_form: Form | None = None

        self.window: tuple[int, int] | None = None
        #: How long a landing opens by default. Held, because it arrives
        #: as a constructor argument and a version of this took it and
        #: never stored it — so every caller that passed one was ignored,
        #: silently, and got the module default instead.
        self.window_rows = window_rows
        self.anchor = 0
        self.tools: list[Tool] = []
        self.crop: tuple[int, int, int, int] = (
            0, 0, self.source_form.rect[2], self.source_form.rect[3])

        #: where values go. Given the project's derived directory, so a
        #: series is written beside the chunks it was computed from.
        self.recorder = Recorder(source.name, self.table,
                                 root=derived / "series")
        self.frontier: Frontier | None = None
        self.encode_queue: queue.Queue = queue.Queue()
        self._encoder = threading.Thread(target=self._encode_loop, daemon=True)
        self._closing = threading.Event()
        self._encoder.start()

        #: whichever thread built the session is taken to be the one that
        #: draws. Recorded rather than passed, so no caller has to remember to
        #: say which thread it is on and none can lie about it by forgetting.
        self.drawing_thread = threading.get_ident()

    # ── what a step wants ────────────────────────────────────────────────
    def form_for(self, tool: Tool | None = None) -> Form:
        """The form the active step wants its inputs in, at the current crop."""
        if tool is not None:
            return tool.form_for(self.crop)
        if self.tools:
            return self.tools[0].form_for(self.crop)
        x, y, w, h = self.crop
        return Form((x, y, w, h), (w, h), self.source_form.pix)

    def set_crop(self, rect: tuple[int, int, int, int]) -> Form:
        """Draw a new crop. A form change, and nothing is wiped.

        The store simply stops having what is asked for. The previous crop's
        frames remain until eviction reaches them, so returning to it is a hit
        rather than a refill — which is all that form keying buys, and is not
        the same as a crop change becoming cheap.
        """
        self.crop = rect
        return self.form_for()

    def set_proxy(self, store: SpanStore | None,
                  form: Form | None = None) -> None:
        """Attach or detach the display proxy, closing whatever was there.

        A setter rather than two assignments because the store holds open file
        handles: replacing it by assignment drops the reference without closing
        them, and on Windows the first symptom is a directory that will not
        delete. The store and the form move together for the same reason the
        form exists — a store whose form nobody recorded cannot say what its
        frames are pictures of.
        """
        if self.proxy is not None and self.proxy is not store:
            self.proxy.close()
        self.proxy = store
        self.proxy_form = form if store is not None else None

    def active(self) -> list[tuple[Tool, Form]]:
        """The steps that are running, each with the form it wants, read once.

        Handed to a producer rather than reached for by one. A producer that
        reads the current step to decide which inputs to gather and reads it
        again to decide where to file the answer writes a value computed with
        one step under the key of another when the two reads straddle a change
        — which is the defect `05-provenance.py` exists to catch, and which no
        instrument that measures time can see.
        """
        return [(tool, tool.form_for(self.crop)) for tool in self.tools]

    def residency(self, horizon: range | int) -> set[tuple[int, str]]:
        """What the active steps need held over the positions about to run."""
        if not self.tools:
            return set()
        return residency(self.active(), horizon)

    # ── serving ──────────────────────────────────────────────────────────
    def situation(self, row: int) -> Situation:
        low, high = self.window or (0, 0)
        return Situation(
            in_window=low <= row < high,
            source_form=self.source_form,
            proxy_form=self.proxy_form,
            have_chunks=bool(self.chunks.coverage),
        )

    def serve(self, row: int, want: Form | None = None, *,
              exact: bool = False, task: str = "step") -> Served:
        """Answer one request by walking the ladder until something does.

        The ladder decides what to try; this decides nothing except when to
        stop. A tier that produces something admissible is admitted here rather
        than by the tier, so there is one place where `grade` is honoured and
        one place to look when something is in a store that should not be.
        """
        row = max(0, min(len(self.table) - 1, row))
        want = want or self.form_for()
        request = Request(row=row, want=want, exact=exact, task=task)
        started = time.perf_counter()

        for attempt in ladder_mod.choose(request, self.situation(row),
                                         near_radius=NEAR_RADIUS):
            if attempt.blocking:
                self._refuse_if_drawing(request, attempt.tier)
            served = self._attempt(attempt, request)
            if served is None:
                continue
            image, stood_in_for = served
            ms = (time.perf_counter() - started) * 1000
            admitted = False
            if attempt.admit and stood_in_for is None:
                self.resident.put(want.key(), row, image,
                                  protected=self.residency(row))
                admitted = True
            self.ledger.serve(task, attempt.tier, ms, row=row)
            return Served(row=row, image=image, tier=attempt.tier, ms=ms,
                          admitted=admitted, stood_in_for=stood_in_for)

        ms = (time.perf_counter() - started) * 1000
        self.ledger.serve(task, HOLD, ms, row=row)
        return Served(row=row, image=None, tier=HOLD, ms=ms)

    def _refuse_if_drawing(self, request: Request, tier: str) -> None:
        """Catch a ladder that offered a wait nobody is owed.

        The rule is narrower than "no blocking on the drawing thread", and the
        difference matters. What the freeze finding prices at two to four
        hundred milliseconds is a *miss* inside the window — an exact seek and
        roll-forward for a frame the fill has not reached yet — and that is
        what `DECODE` is. The keyframe route outside the window is a different
        thing: one decode, no roll-forward, and the only way to see anything at
        all before a proxy has been built. It is a cost somebody chose, priced
        in the explorer logs, and refusing it would leave the hunt with nothing
        to show on a fresh project.

        So this refuses `DECODE` for a request nobody released, which is a
        ladder that has gone wrong rather than a caller that has. The guard's
        job is to catch the broken ladder, not to second-guess a correct one.
        """
        if tier == DECODE and not ladder_mod.blocking_allowed(request):
            raise BlockedTheDrawingThread(
                f"tier {tier!r} would seek and roll forward for a "
                f"{request.task!r} request nobody released")
        if tier == KEYFRAME and threading.get_ident() == self.drawing_thread:
            # a chosen cost, not waste: an approximate answer now beats the
            # true one later, and counting it as waste would bury the count
            self.ledger.chosen(PLACEHOLDER)

    def _attempt(self, attempt, request: Request):
        """Try one rung. Returns `(image, stood_in_for)` or `None`."""
        row, want = request.row, request.want
        tier = attempt.tier

        if tier == RESIDENT:
            frame = self.resident.get(want.key(), row)
            return None if frame is None else (frame, None)

        if tier == CHUNK:
            frame = self.chunks.fetch(want.key(), row)
            return None if frame is None else (frame, None)

        if tier == DERIVE:
            held = self.resident.get(self.source_form.key(), row)
            if held is None:
                return None
            produced, _ = derive(held, self.source_form, want)
            return produced, None

        if tier == NEAR:
            found = self.resident.nearest(want.key(), row, attempt.radius)
            return None if found is None else (found[1], found[0])

        if tier == PROXY:
            if self.proxy is None or self.proxy_form is None:
                return None
            frame = self.proxy.fetch(self.proxy_form.key(), row)
            if frame is None:
                return None
            produced, _ = derive(frame, self.proxy_form, want)
            return produced, row if not attempt.admit else None

        if tier == KEYFRAME:
            answer = self.route.keyframe_at(row)
            if answer is None:
                return None
            full, landed, _ = answer
            produced = build(full, want)
            if landed != row:
                # the crop of a real decode is worth keeping even though it is
                # not the row asked for: it is exact for the row it *is*
                if admissible(self.source_form, want):
                    self.resident.put(want.key(), landed, produced,
                                      protected=self.residency(row))
                return produced, landed
            return produced, None

        if tier == DECODE:
            self._count_double_decode(row, want)
            answer = self.route.at(row)
            if answer is None:
                return None
            return build(answer[0], want), None

        return None

    def _count_double_decode(self, row: int, want: Form) -> None:
        """A decode of something a held form could have produced exactly.

        The ladder offers `DERIVE` before `DECODE`, so reaching a decode with
        a dominating form resident means the derivation was skipped or the
        store lost it between the two — either way work is being done twice
        for an output one of the consumers could have served (ADR-0008).
        """
        held = self.resident.get(self.source_form.key(), row)
        if held is not None and admissible(self.source_form, want):
            self.ledger.waste(DOUBLE_DECODE,
                              f"row {row} decoded with {self.source_form.key()}"
                              f" resident and exact for {want.key()}")

    # ── landing ──────────────────────────────────────────────────────────
    def land(self, row: int, *,
             window_rows: int | None = None) -> tuple[int, int]:
        """Start a window here and fill it, anchored on where somebody clicked.

        The window snaps to the chunk grid so that two landings over the same
        ground share chunks rather than each writing its own copy of the
        overlap. The anchor does not snap: it is where attention actually is,
        and the fill order is built from it.
        """
        rows = self.window_rows if window_rows is None else window_rows
        start = self.chunks.chunk_start(max(0, row - rows // 2))
        end = min(len(self.table), start + rows)
        self.stop_fill(wait=False)

        self.window = (start, end)
        self.anchor = row
        form = self.form_for()
        # read once, here, and closed over for the life of this fill. A crop
        # change stops this fill and starts another, so the set a producer is
        # working against cannot move underneath it.
        active = self.active()
        self.frontier = Frontier(self.route, form, self.resident, self.chunks,
                                 encode_queue=self.encode_queue,
                                 ledger=self.ledger,
                                 protected=self.residency(range(row, end)),
                                 on_admitted=lambda landed: self.recorder.admitted(
                                     active, landed, self.resident))
        self.frontier.launch(start, end, row)
        return self.window

    def stop_fill(self, wait: bool = True) -> None:
        if self.frontier is not None:
            self.frontier.stop(wait=wait)
            self.frontier = None

    def pause_fill(self, paused: bool = True) -> None:
        """Hand the decoder to something the user is waiting on, or take it back."""
        if self.frontier is None:
            return
        if paused:
            self.frontier.pause.set()
        else:
            self.frontier.pause.clear()

    # ── the encoder ──────────────────────────────────────────────────────
    def _encode_loop(self) -> None:
        """Write completed chunks behind the fill, off every other thread.

        Its own thread because encoding holds the interpreter for long
        stretches and because `Coverage.record` rewrites its whole document —
        neither belongs anywhere near the one that draws.
        """
        while not self._closing.is_set():
            try:
                form, start, frames = self.encode_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            activity = self.ledger.begin("encode", f"chunk at {start}")
            try:
                self.chunks.encode(form, start, frames)
            finally:
                self.ledger.end(activity)

    def close(self) -> None:
        self._closing.set()
        self.stop_fill(wait=False)
        self._encoder.join(timeout=2)
        self.chunks.close()
        if self.proxy is not None:
            self.proxy.close()
        self.route.close()
