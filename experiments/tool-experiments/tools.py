"""What a tool declares about itself before anything schedules or draws it.

A tool, to everything in this folder, is five declarations and two
functions. The declarations are what the scheduler and the overlay need in
order to decide anything without running the tool first; the functions are
the work.

**The form it requires.** Not a fixed form — the crop is drawn by the user,
so a tool declares how to build its form from whatever the crop currently
is. This is what lets the store answer "does anything on hand satisfy the
tool" (`forms.grade`) rather than "is the tool's frame cached".

**Which frames it still needs**, as an explicit set of offsets from the
frame being computed rather than a reach. A pointwise op declares `(0,)`,
frame differencing and dense flow `(-1, 0)`, and a motion-history image
sampled at fixed lags `(-30, -20, -10, 0)` — four frames, not thirty-one,
which is the whole reason this is a set and not an integer. What must be
*fetched* and how far a sweep must decode *through* are then different
numbers, and only the second one is `reach`.

A declaration is a correctness specification, not a request. Evicting a
frame a tool declared does not make the tool slower — it makes the tool
decode again, which is the whole inefficiency the declaration exists to
prevent. So the store's job is to honour it, and the tool's job is to
declare what it actually needs; neither is planning against the other being
wrong.

**Retention is the union over a horizon, not `needs` at a point.** This is
the trap, and declaring sparsely is what springs it. `needs(row)` is exactly
right for one evaluation at one row. As a retention policy for a moving
playhead it is pathological: a lag-(30, 20, 10) tool at row 500 holds
{470, 480, 490, 500} and at row 501 needs {471, 481, 491, 501}, four
entirely new frames, so honouring the sparse set literally costs four
decodes per displayed frame instead of one. What is correct is the union of
`needs(r)` over the positions about to be served — sparse and small for a
still playhead or a random hop, dense for forward playback, and in both
cases computed from the declaration rather than assumed. One expression,
evaluated over the horizon the transport implies.

So the declaration does three jobs: unioned over the horizon it is what
eviction may not take, read one row ahead it is the prefetch list, and read
across a span it is what a sweep must decode. It is a pure function of
position rather than a pin/release protocol, deliberately — nothing to leak
when a tool is switched off or the playhead jumps, and the store asks what
the active set needs now instead of remembering what it was told.

What the declaration is *not* worth is a memory argument. During playback
the union over the horizon is dense anyway, so retention collapses to what a
window around the playhead would have held; where it stays sparse the
playhead is stationary and nothing is under pressure. The declaration earns
its keep as a **fetch plan**: a hop to a row whose lags sit thirty frames
back needs three specific old frames that no locality rule would ever
predict, and without the declaration they are discovered at display time and
paid for inside one frame budget. Eviction could stay crude. Fetching could
not. (An execution-strategy router keyed on how much a tool pins was drafted
here and cut: it answered a question — interactive against ordered pass —
that nothing in this tree asks yet. `docs/decode/ideas.md` keeps the general
form, that unbounded extent is unschedulable rather than slow.)

**Whether it is a map or a fold**, which is a different axis from the one
above and is easily confused with it. A map-shaped tool is evaluable at any
frame given its offsets, so a sweep can be split, resumed, reordered, or
skipped over ground nobody visits. A fold-shaped tool — a progressive
background, a continuous background subtractor, an MHI carrying a decayed
accumulator — has a *bounded* memory requirement, one accumulator rather
than a window of frames, and an *ordering* requirement instead: it must be
fed in sequence from a start or a checkpoint, and a jump costs a replay. So
a fold declares `sequential=True` with offsets `(0,)`; declaring frame
retention for it would pin gigabytes to avoid re-fetching frames it never
wanted. An MHI sampled at fixed lags and an MHI carrying an accumulator are
the same name and opposite costs, and only the first one is about memory.
The reset/step/checkpoint protocol a fold owes is not implemented yet,
because the two tools this folder starts with are both maps.

**Its cost class — which a tool does not get to declare.** The three classes
are cut where product behaviour changes:

- `FREE` — in the noise beside the decode that produced the frame. Its
  series fills as a byproduct of the user watching, and a sweep is only ever
  needed for ground nobody looked at.
- `BUDGETED` — real time, but fits a frame period once decode and paint are
  taken out of it. It can preview live and it can never be free.
- `COMMIT` — does not fit. Live preview is unavailable; the overlay shows
  what has been computed and says so where nothing has.

This was originally a field on the tool, declared by its author and checked
by an experiment. `03-free-while-hot` checked it and falsified the idea
rather than the declarations: on this machine *every* tool changed class
between the two regimes the loop runs in, because `FREE` is a ratio against
a decode and the decodes differ by a factor of forty between an intra chunk
and the uncut source. Frame differencing is genuinely free beside a 5.3K
decode and genuinely is not beside a chunk, at the same size, in the same
session, ten seconds apart. A class is a property of a *pairing*, so a tool
carrying one was a tool asserting something it cannot know.

What replaces it is `classify`, applied to measurements taken where the tool
is actually running. That follows the tree's existing habit rather than
inventing one: seek routing is probed at first open and cached per machine
and source shape, for the same reason — the alternative is shipping one
machine's answer to every other.

**The field, and the reduction.** A tool produces two things per frame and
they have completely different economics. The field is image-sized — the
difference image, the flow magnitude — and it is what the overlay draws. The
reduction is a scalar (or a few), and it is what the graphs read and the
series tier stores. Fields are never stored: a stored field is another
video's worth of bytes per tool per parameter setting, which is the whole
reason tier 4 holds series. So a field is computed when it is drawn and
discarded, and the frame it was computed on was hot anyway — which is how a
tool's series gets written by the act of looking at it.

Both tools here reduce a scalar field the same way, so only `field`
differs. Drawing one is `surfaces.py`'s job, not a tool's: a tool that
carried its own painter would carry its own paint cost, and paint cost is a
thing this folder measures rather than distributes.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable

import cv2
import numpy as np

from forms import Form

FREE = "free"          #: noise beside decode; the series fills by watching
BUDGETED = "budgeted"  #: fits the residual frame period; previews live
COMMIT = "commit"      #: cannot preview live; shows what exists, says so

#: at most this many decodes' worth of work to count as free. A cut, not a
#: fact: it is exposed so a caller can move it, and every classification
#: reports the ratio it was applied to so the cut can be argued with.
FREE_RATIO = 2.0


def classify(field_ms: float, decode_ms: float, period_ms: float,
             paint_ms: float, free_ratio: float = FREE_RATIO) -> str:
    """Which class a tool falls in *against this decode*, from measurement.

    Not a property of the tool. `FREE` is a ratio against the decode that
    produced the frame, and the same op lands either side of it depending
    on whether the frame came from the uncut source or an intra chunk —
    which is why nothing here is declared. `BUDGETED` is measured against
    the residual period, decode and paint removed, because a tool that fits
    the frame alone and not beside the drawing of it does not fit.
    """
    if decode_ms > 0 and field_ms <= free_ratio * decode_ms:
        return FREE
    return BUDGETED if field_ms <= period_ms - decode_ms - paint_ms else COMMIT


@dataclass
class Tool:
    """One tool's declarations and its work."""

    name: str
    #: crop rect in source pixels -> the form the tool wants its frames in
    form_for: Callable[[tuple[int, int, int, int]], Form]
    #: offsets from the frame being computed; non-positive, 0 included
    offsets: tuple[int, ...]
    #: {row: array} for exactly `needs(row)`, and the row -> a scalar field
    field: Callable[[dict[int, np.ndarray], int], np.ndarray]
    #: a scalar field -> the number the series stores
    reduce: Callable[[np.ndarray], float] = staticmethod(
        lambda f: float(np.mean(f)))
    #: a fold: bounded state, but must be fed in order from a checkpoint
    sequential: bool = False
    params: dict | None = None

    def needs(self, row: int) -> tuple[int, ...]:
        """The rows that must be resident to compute `row`.

        One evaluation, one row. For what to *hold* while the playhead is
        moving, use `residency` over the horizon — the sparse set at a
        point is not the working set of a sequence, and mistaking the two
        is how a sparse declaration turns into extra decodes per frame.
        """
        return tuple(row + off for off in self.offsets)

    @property
    def reach(self) -> int:
        """How far back the oldest requirement sits.

        What a sweep must decode *through* to produce an honest value,
        which is wider than what it must *hold* whenever the offsets are
        sparse. The two being one number is the thing a scalar extent got
        wrong.
        """
        return -min(self.offsets)

    def key(self) -> str:
        """The durable spelling, folding only what changes the stored value.

        Parameters that live *downstream* of the series — a threshold read
        off it, a smoothing window applied at display — are deliberately not
        here: folding them would invalidate work whose own inputs never
        changed, which is the cache-key failure `docs/decode/ideas.md`
        records. What belongs in a tool's params is what the field depends
        on.
        """
        if not self.params:
            return self.name
        bits = ",".join(f"{k}={self.params[k]}" for k in sorted(self.params))
        return f"{self.name}({bits})"


def analysis_form(pix: str = "gray") -> Callable[[tuple[int, int, int, int]], Form]:
    """The crop at source sampling — the default a tool wants.

    Native sampling because a form that has already been resampled can only
    be derived from approximately (`forms.EXACT`), and an approximate frame
    may not be recorded. A tool that genuinely wants less resolution says so
    with its own `form_for` and accepts that its series is about a different
    picture than the full-resolution one, which is a real answer to a real
    question and not the same answer cheaper.
    """
    def build(rect: tuple[int, int, int, int]) -> Form:
        x, y, w, h = rect
        return Form((x, y, w, h), (w, h), pix)
    return build


# ── the two this folder starts with ──────────────────────────────────────
# Chosen as a pair because they straddle the boundary the whole design keys
# on: one is in the noise beside decode and one is roughly forty times it,
# so every fork that reads the cost class fires at least once.

# A field stays in the narrowest type that carries its answer. Neither
# consumer wants float for its own sake — `surfaces.overlay` scales through
# `convertScaleAbs` and the reduction is a mean — so an `astype(np.float32)`
# on a difference image buys nothing and costs a full pass over a megabyte,
# which 03-free-while-hot measured at roughly two thirds of the op itself.

def _absdiff(frames: dict[int, np.ndarray], row: int) -> np.ndarray:
    return cv2.absdiff(frames[row], frames[row - 1])


def _dis_flow_factory(preset: int):
    #: per-thread, not per-tool. A tool object is shared by every consumer
    #: that wants it — that is the point of this folder — and the overlay
    #: calling `field` on the GUI thread while a sweep calls it on a worker
    #: is the normal case, not the exotic one. An op holding solver state
    #: across calls therefore holds it per thread or corrupts it; the
    #: alternative, a lock, would serialise the two consumers this folder
    #: exists to measure running at once.
    local = threading.local()

    def field(frames: dict[int, np.ndarray], row: int) -> np.ndarray:
        dis = getattr(local, "dis", None)
        if dis is None:
            dis = local.dis = cv2.DISOpticalFlow_create(preset)
        flow = dis.calc(frames[row - 1], frames[row], None)
        # cv2.magnitude, not np.linalg.norm(axis=2): the numpy route builds
        # intermediates over a two-channel megapixel field and measured
        # slower than the flow solve it was reducing.
        return cv2.magnitude(flow[..., 0], flow[..., 1])
    return field


def absdiff() -> Tool:
    return Tool(
        name="absdiff", form_for=analysis_form("gray"), offsets=(-1, 0),
        field=_absdiff)


def dis_flow(preset: int = cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST) -> Tool:
    names = {cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST: "ultrafast",
             cv2.DISOPTICAL_FLOW_PRESET_FAST: "fast",
             cv2.DISOPTICAL_FLOW_PRESET_MEDIUM: "medium"}
    return Tool(
        name="dis", form_for=analysis_form("gray"), offsets=(-1, 0),
        field=_dis_flow_factory(preset),
        params={"preset": names.get(preset, str(preset))})


def lag_mhi(lags: tuple[int, ...] = (30, 20, 10)) -> Tool:
    """Motion history sampled at fixed lags — the sparse-retention case.

    Here as the third tool rather than as a hypothetical, because it is the
    only one of the three whose retention set is not its reach: it holds
    four frames and spans thirty-one. An MHI that instead carried a decayed
    accumulator would be `sequential=True` with offsets `(0,)` — same
    picture, bounded memory, and a replay cost on every jump. Which of the
    two a user wants is a question about their footage, not an
    implementation detail.
    """
    offsets = tuple(sorted(-lag for lag in lags) + [0])

    def field(frames: dict[int, np.ndarray], row: int) -> np.ndarray:
        cur = frames[row]
        out = None
        for rank, off in enumerate(offsets[:-1]):
            # `* weight` on a uint8 difference promotes the whole megapixel
            # to float64 — a Python float is a double, and the promotion is
            # silent. convertScaleAbs stays in uint8 and does the scale in
            # the same pass as the subtraction's output.
            weight = (rank + 1) / len(lags)
            aged = cv2.convertScaleAbs(cv2.absdiff(cur, frames[row + off]),
                                       alpha=weight)
            out = aged if out is None else cv2.max(out, aged)
        return out

    return Tool(name="mhi-lag", form_for=analysis_form("gray"),
                offsets=offsets, field=field,
                params={"lags": "-".join(str(lag) for lag in sorted(lags))})


def residency(active: list[tuple[Tool, Form]], rows) -> set[tuple[int, str]]:
    """What the active tools need held to serve `rows`, as (row, form) pairs.

    `rows` is the horizon the transport implies — one row while paused or
    hopping, the run ahead of the playhead while playing, a whole span for
    a sweep. Taking a horizon rather than a position is the difference
    between a retention policy and a per-frame lookup: the union over the
    rows about to be served is the working set, and `needs` at a single row
    is only its degenerate case.

    Pairs, not rows, because a pin is on a frame *in a form*: two tools at
    different forms need different arrays of the same instant, and a store
    unioning by row alone would think one satisfied the other. Everything
    outside this set is the store's to evict however it likes.
    """
    if isinstance(rows, int):
        rows = (rows,)
    return {(need, form.key())
            for tool, form in active
            for row in rows for need in tool.needs(row)}
