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

**Its cost class, as a claim that an experiment can falsify.** The three
classes are cut where product behaviour actually changes:

- `FREE` — in the noise beside the decode that produced the frame. Its
  series fills as a byproduct of the user watching, and a sweep is only ever
  needed for ground nobody looked at.
- `BUDGETED` — real time, but fits inside a frame period at the analysis
  form. It can preview live and it can never be free.
- `COMMIT` — cannot fit a frame period. Live preview is not available; the
  overlay shows what has been computed and says so where nothing has.

The class is *declared*, not measured, because a descriptor is written
before there is a measurement. The free-while-hot experiment's job is to
check the declarations against the machine and report the ones that are wrong — a claim nothing can
falsify would not be worth writing down.

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
BUDGETED = "budgeted"  #: fits a frame period at analysis form; previews live
COMMIT = "commit"      #: cannot preview live; shows what exists, says so


@dataclass
class Tool:
    """One tool's declarations and its work."""

    name: str
    #: crop rect in source pixels -> the form the tool wants its frames in
    form_for: Callable[[tuple[int, int, int, int]], Form]
    #: offsets from the frame being computed; non-positive, 0 included
    offsets: tuple[int, ...]
    claim: str
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

def _absdiff(frames: dict[int, np.ndarray], row: int) -> np.ndarray:
    return cv2.absdiff(frames[row], frames[row - 1]).astype(np.float32)


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
        return np.linalg.norm(flow, axis=2)
    return field


def absdiff() -> Tool:
    return Tool(
        name="absdiff", form_for=analysis_form("gray"), offsets=(-1, 0),
        claim=FREE, field=_absdiff)


def dis_flow(preset: int = cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST) -> Tool:
    names = {cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST: "ultrafast",
             cv2.DISOPTICAL_FLOW_PRESET_FAST: "fast",
             cv2.DISOPTICAL_FLOW_PRESET_MEDIUM: "medium"}
    return Tool(
        name="dis", form_for=analysis_form("gray"), offsets=(-1, 0),
        claim=BUDGETED, field=_dis_flow_factory(preset),
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
        out = np.zeros(cur.shape, dtype=np.float32)
        for rank, off in enumerate(offsets[:-1]):
            weight = (rank + 1) / len(lags)
            np.maximum(out, cv2.absdiff(cur, frames[row + off]) * weight,
                       out=out)
        return out

    return Tool(name="mhi-lag", form_for=analysis_form("gray"),
                offsets=offsets, claim=FREE, field=field,
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
