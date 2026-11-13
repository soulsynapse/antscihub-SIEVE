"""The walk's measured rate: the rows between two of the worker's progress signals over a clock, as a
multiple of realtime, with what those rows were. The one definition the player's control and the
monitor's header read. It holds no graph, reaches no Qt and attaches nothing to the probe; `Pace.row`
and `Pace.figure` are one thread's."""
import time
from dataclasses import dataclass

COLD = 0.05     # a walk is cold while a store held no more than this share of its rows: the display's own row always is, computed before the walk reaches it

def clock(seconds):
    """`seconds` as m:ss, or h:mm:ss from an hour up."""
    s = round(seconds)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


@dataclass(frozen=True)
class Figure:
    """A walk as the control draws it. `what` says which time `seconds` is: "takes", the clip at this
    rate, given for a window walk only while it is cold, no row served and no more than COLD of them
    held; "left" and "took", the clip walk's own; "", and `seconds` is None."""
    lane: str               # "window" or "clip"
    done: int
    total: int
    ran: int                # of the rows done, those a store did not hold
    served: int             # and those that read a bake's file
    over: bool              # the walk reached its last row or was stopped
    multiple: float | None  # rows a second over the clip's rows a second; None until a second signal is in
    seconds: float | None
    what: str
    clip_s: float           # the clip's length

    @property
    def held(self):
        return self.done - self.ran - self.served

    def words(self):
        """The figure in words, for where the control's marks are not enough."""
        rate = "no rate yet" if self.multiple is None else f"{self.multiple:.1f}x realtime"
        lines = [f"{self.lane} walk, {self.done} of {self.total} rows, {rate}",
                 f"{self.ran} ran, {self.held} held by a store, {self.served} served from a bake"]
        if self.what == "takes":
            lines.append(f"the clip, {clock(self.clip_s)}, would take ~{clock(self.seconds)} at this rate")
        elif self.what:
            lines.append(f"the clip, {clock(self.clip_s)}: {clock(self.seconds)} {self.what}")
        elif self.lane == "window" and self.multiple is not None:
            lines.append("no time for the clip: the walk was not cold")
        return "\n".join(lines)


class _Walk:
    def __init__(self, t, done, total):
        self.began = self.t = t
        self.since = (t, done)      # where the rate counts from: the walk's first signal, or its first after the other lane's turn
        self.done, self.total, self.ran, self.served = done, total, 0, 0
        self.over, self.rate = False, None


class Pace:
    """Fed each progress signal of either lane as it lands; `figure` is the lane that signalled last,
    walking or finished. A lane's count at or below its last opens a new walk, the worker starting
    one over with no signal of its own, so a walk's first row is not in its rate: the signal that
    opens it is that row's end. The clock is the reader's, so the rate holds the turns the ladder
    gave other work and how late the signal was read."""

    def __init__(self, clock=time.perf_counter):
        self._clock, self._walks, self._lane = clock, {}, None

    def row(self, lane, done, total, ran=0, served=0):
        if not total:
            return      # a clip walk that was not asked for reports 0 of 0
        t, w = self._clock(), self._walks.get(lane)
        closing = w is not None and done == w.done and total == done    # a halt repeats the count with the range cut to it
        if w is None or done < w.done or (done == w.done and not closing):
            w = self._walks[lane] = _Walk(t, done, total)
        elif self._lane != lane:
            w.since = (t, w.done)
        if done > w.done and t > w.since[0]:
            w.rate = (done - w.since[1]) / (t - w.since[0])
        w.t, w.done, w.ran, w.served = t, done, ran, served
        w.over = done >= total
        self._lane = lane

    def figure(self, fps, count):
        """The Figure of the lane that signalled last, over a clip of `count` rows at `fps`; None before any signal."""
        w = self._walks.get(self._lane)
        if w is None:
            return None
        what, seconds = "", None
        if self._lane == "clip":
            if w.over:
                what, seconds = "took", w.t - w.began
            elif w.rate:
                what, seconds = "left", (w.total - w.done) / w.rate
        elif w.rate and not w.served and w.done - w.ran <= COLD * w.done:
            what, seconds = "takes", count / w.rate
        return Figure(self._lane, w.done, w.total, w.ran, w.served, w.over,
                      w.rate / fps if w.rate else None, seconds, what, count / fps)
