"""What a step declares about itself before anything schedules or runs it.

A step, here, is a form it wants its inputs in, a set of offsets naming which
inputs it admits, a flag saying whether it can be evaluated anywhere or only
in sequence, the parameters its answer depends on, a version saying which
definition of the step those parameters were fed to, and two functions: one
producing a field and one reducing that field to the number a series stores.

**The form.** Not a fixed one — the crop is drawn by the user, so a step says
how to build its form from whatever the crop currently is. That is what lets
a store answer "does anything on hand satisfy this" (`forms.grade`) rather
than "is this step's frame cached".

**The offsets**, as an explicit set relative to the position being computed
rather than as a single reach. Frame differencing admits `(-1, 0)`; a motion
history sampled at fixed lags admits those lags and the current position,
which is a handful of inputs spanning many — and the span and the set are
different numbers, only the second of which is `reach`. What that declaration
is *for* is scheduling fetches rather than saving memory, and the reasoning
is ADR-0006 rather than repeated here.

Two readings of the same declaration, and confusing them is the trap that
sparse offsets set. `needs(row)` is what must be resident to evaluate one
position. `residency` over a run of positions is what may not be evicted
while serving them — the union, not the point set, because honouring the
point set for a moving playhead costs a fetch per offset per position.

**Sequential** distinguishes a step evaluable at any position from one
evaluable only in order from a start or a checkpoint. The first can be split,
resumed, reordered, or skipped over ground nobody visits; the second can only
be fed by a producer able to promise order and completeness. Nothing in this
tree is sequential yet, so the reset/step/checkpoint protocol such a step
would owe is named and unimplemented, and should stay that way until
something real needs it.

**Cost class is not among the declarations**, and `classify` computes it from
measurement instead. It was a declared field until `03-free-while-hot`
falsified the idea rather than any particular declaration — every step
measured landed in a different class against the two input regimes the loop
runs over, because the cheapest class is a ratio against a fetch and those
fetches differ by more than an order of magnitude. ADR-0007 carries the
decision; the result files carry the numbers.

**The field and the reduction** have different economics and different fates.
A field is image-sized — a difference image, a flow magnitude — and it exists
to be drawn. It is computed where it is drawn and discarded there, because
storing fields means another recording's worth of bytes per step per
parameter setting. A reduction is a scalar, and it is what a series stores,
written where the inputs it was computed from were admitted and never by
anything that draws (ADR-0005).

Drawing a field is `surfaces.py`'s job rather than a step's. A step that
carried its own painter would carry its own paint cost into a place this
folder measures paint separately on purpose.

A field stays in the narrowest type that carries its answer. Neither consumer
wants a float for its own sake — the overlay rescales on its way to a colour
map and the reduction is a mean — so widening one costs a full pass over an
image and buys nothing. `03-free-while-hot` prices what that costs when it is
done by accident.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable

import cv2
import numpy as np

from forms import Form

FREE = "free"          #: in the noise beside the fetch that produced its input
BUDGETED = "budgeted"  #: fits the period once fetch and paint are removed
COMMIT = "commit"      #: does not fit; shows what exists and says where none

#: at most this many fetches' worth of work to count as free. A cut rather
#: than a fact, exposed so a caller can move it — every experiment that
#: applies it records the ratio alongside, so the cut can be argued with
#: without anything being re-run.
FREE_RATIO = 2.0


def classify(field_ms: float, fetch_ms: float, period_ms: float,
             paint_ms: float, free_ratio: float = FREE_RATIO) -> str:
    """Which class a step falls in *against this fetch*, from measurement.

    Never a property of the step alone. `FREE` is a ratio against whatever
    produced the input, so the same arithmetic lands either side of the line
    depending on where the input came from. `BUDGETED` is measured against
    what is left of the period once the fetch and the drawing are taken out,
    because a step that fits the period alone and not beside the drawing of
    it does not fit.
    """
    if fetch_ms > 0 and field_ms <= free_ratio * fetch_ms:
        return FREE
    return BUDGETED if field_ms <= period_ms - fetch_ms - paint_ms else COMMIT


@dataclass
class Tool:
    """One step's declarations and its work."""

    name: str
    #: crop rect in source pixels -> the form this step wants its inputs in
    form_for: Callable[[tuple[int, int, int, int]], Form]
    #: offsets from the position being computed; non-positive, 0 included
    offsets: tuple[int, ...]
    #: {row: array} for exactly `needs(row)`, and the row -> a scalar field
    field: Callable[[dict[int, np.ndarray], int], np.ndarray]
    #: a scalar field -> the number a series stores
    reduce: Callable[[np.ndarray], float] = staticmethod(
        lambda f: float(np.mean(f)))
    #: evaluable only in order, from a start or a checkpoint
    sequential: bool = False
    #: what the field's answer depends on, and nothing downstream of it
    params: dict | None = None
    #: bumped where `field` or `reduce` changes what it answers — see `key`
    version: int = 1

    def needs(self, row: int) -> tuple[int, ...]:
        """The rows that must be resident to evaluate `row`.

        One position. For what to *hold* while the playhead moves, ask
        `residency` over the run about to be served: the set at a point is
        not the working set of a sequence, and treating it as one turns a
        sparse declaration into extra fetches per position.
        """
        return tuple(row + off for off in self.offsets)

    @property
    def reach(self) -> int:
        """How far back the oldest admitted input sits.

        What an ordered pass must work *through* to produce an honest value,
        which is wider than what it must *hold* whenever the offsets are
        sparse. Collapsing the two into one number is what a scalar extent
        got wrong.
        """
        return -min(self.offsets)

    def key(self) -> str:
        """The durable spelling, folding only what changes the stored value.

        Parameters downstream of the series — a threshold read off it, a
        smoothing applied at display — are deliberately absent: folding them
        would invalidate work whose own inputs never changed, which is the
        cache-key failure `docs/decode/ideas.md` records.

        `version` is folded because `params` cannot see the code. Two runs
        either side of an edit to `field` are different answers under one
        name, and a series the first wrote is handed to the second with
        nothing anywhere in a position to notice — the same silent reuse the
        downstream-parameter rule refuses, arrived at from the other side.
        So it is folded unconditionally, including for a step declaring no
        parameters at all, and bumping it is the author's act at the moment
        the answer changes rather than anything derived: a hash over the
        function's bytecode would invalidate a rename and still miss the
        case below.

        It spells this tree's code and not what that code calls. A step
        whose answer comes out of a third-party solver depends on that
        solver's identity too, and the field for that is `params` — which
        is what the answer depends on, and not only what a user set.
        """
        stem = f"{self.name}@{self.version}"
        if not self.params:
            return stem
        bits = ",".join(f"{k}={self.params[k]}" for k in sorted(self.params))
        return f"{stem}({bits})"


def analysis_form(pix: str = "gray") -> Callable[[tuple[int, int, int, int]], Form]:
    """The crop at source sampling — the default a step wants.

    Native sampling because a form that has already been resampled can only
    be derived from approximately, and an approximate input may not be
    recorded (`forms.py`). A step that genuinely wants less resolution says
    so with its own `form_for`, and accepts that its answer is about a
    different picture rather than the same one cheaper.
    """
    def build(rect: tuple[int, int, int, int]) -> Form:
        x, y, w, h = rect
        return Form((x, y, w, h), (w, h), pix)
    return build


# ── the steps this folder measures against ───────────────────────────────
# Loads, not proposals. `absdiff` and `dis_flow` sit either side of the
# free/not-free line so every fork reading a cost class fires; `lag_mhi` is
# the one whose admitted set is not its reach, which keeps that distinction
# tested rather than merely described.

def _absdiff(frames: dict[int, np.ndarray], row: int) -> np.ndarray:
    # returned as it comes out, uint8: widening it here would cost a pass
    # over the image and neither consumer asked for a float
    return cv2.absdiff(frames[row], frames[row - 1])


def _dis_flow_factory(preset: int):
    #: solver state per thread, not per step. A step object is shared by
    #: every consumer that wants it, and one calling `field` on the GUI
    #: thread while another calls it on a worker is the normal case here.
    #: A lock would serialise exactly the two consumers this folder exists
    #: to watch run at once.
    local = threading.local()

    def field(frames: dict[int, np.ndarray], row: int) -> np.ndarray:
        dis = getattr(local, "dis", None)
        if dis is None:
            dis = local.dis = cv2.DISOpticalFlow_create(preset)
        flow = dis.calc(frames[row - 1], frames[row], None)
        # cv2.magnitude rather than a numpy norm over the channel axis: the
        # numpy route builds intermediates across the whole two-channel
        # field and measured slower than the solve it was reducing
        return cv2.magnitude(flow[..., 0], flow[..., 1])
    return field


def absdiff() -> Tool:
    return Tool(name="absdiff", form_for=analysis_form("gray"),
                offsets=(-1, 0), field=_absdiff, version=1)


def dis_flow(preset: int = cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST) -> Tool:
    names = {cv2.DISOPTICAL_FLOW_PRESET_ULTRAFAST: "ultrafast",
             cv2.DISOPTICAL_FLOW_PRESET_FAST: "fast",
             cv2.DISOPTICAL_FLOW_PRESET_MEDIUM: "medium"}
    return Tool(name="dis", form_for=analysis_form("gray"), offsets=(-1, 0),
                field=_dis_flow_factory(preset), version=1,
                params={"preset": names.get(preset, str(preset))})


def lag_mhi(lags: tuple[int, ...] = (30, 20, 10)) -> Tool:
    """Motion history sampled at fixed lags — the sparse-admission case.

    Present as a third load because it is the only one whose admitted set is
    not its reach: it holds a handful of inputs and spans many. A motion
    history carrying a decayed accumulator instead would be `sequential`
    with offsets `(0,)` — the same picture, bounded state, and a replay on
    every jump.
    """
    offsets = tuple(sorted(-lag for lag in lags) + [0])

    def field(frames: dict[int, np.ndarray], row: int) -> np.ndarray:
        cur = frames[row]
        out = None
        for rank, off in enumerate(offsets[:-1]):
            # convertScaleAbs, not `* weight`: a Python float is a double,
            # so multiplying a uint8 image by one silently promotes the
            # whole thing. This scales in the same pass and stays uint8.
            weight = (rank + 1) / len(lags)
            aged = cv2.convertScaleAbs(cv2.absdiff(cur, frames[row + off]),
                                       alpha=weight)
            out = aged if out is None else cv2.max(out, aged)
        return out

    return Tool(name="mhi-lag", form_for=analysis_form("gray"),
                offsets=offsets, field=field, version=1,
                params={"lags": "-".join(str(lag) for lag in sorted(lags))})


def residency(active: list[tuple[Tool, Form]], rows) -> set[tuple[int, str]]:
    """What the active steps need held to serve `rows`, as (row, form) pairs.

    `rows` is the horizon the transport implies: one position while paused
    or hopping, the run ahead of the playhead while playing, a whole span
    for an ordered pass. Taking a horizon rather than a position is the
    difference between a retention policy and a per-position lookup.

    Pairs rather than rows, because what is held is an input *in a form*:
    two steps at different forms need different arrays of one instant, and
    a store unioning by row alone would think one satisfied the other.
    Everything outside this set is the store's to evict as it likes.
    """
    if isinstance(rows, int):
        rows = (rows,)
    return {(need, form.key())
            for tool, form in active
            for row in rows for need in tool.needs(row)}
