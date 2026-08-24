"""One process-wide setting, and why it is not left at its default.

The fill thread and the encode thread churn the interpreter hard enough to
starve the thread that draws for a hundred to four hundred milliseconds at
CPython's default five-millisecond switch interval. That was measured with a
heartbeat probe during the freeze hunt
(`docs/findings/2026.08.22-what-froze-the-felt-loop.md`), and a shorter interval
trades a little throughput for the event loop staying alive.

**It is a whole-process setting and therefore not a session's to make.** A
`Session` built inside a check, a harness script or somebody's REPL has no event
loop to protect and no business changing how the interpreter schedules
everything else in that process. So it is applied by whatever is running an
application, once, at startup — and never as an import side effect, which is how
the explorers do it and is the one thing about their version worth changing.

**It is the tuned case, and a measurement taken without it is the untuned
one.** `experiments/tool-experiments/results/04-under-load-*.json` says so in
its own notes, because the difference reaches ratios and not only absolutes.
Anything comparing a number from here against a number from an explorer has to
know which side of this it was taken on; `apply()` reports what it changed so a
harness can record it rather than guess.
"""

from __future__ import annotations

import sys

#: Seconds the interpreter runs one thread before offering the others a turn.
#: CPython's default is 0.005. The figure is from the freeze hunt rather than
#: from theory, and moving it is a decision about the trade it names: shorter
#: keeps the event loop alive under a fill, longer lets the fill finish sooner.
SWITCH_INTERVAL_S = 0.002


def apply(interval: float = SWITCH_INTERVAL_S) -> tuple[float, float]:
    """Set the switch interval. Returns what it was and what it now is.

    Returned rather than logged so that a caller which records its conditions —
    a harness run, a parity comparison — can put both numbers in its result
    beside the timings they explain.
    """
    before = sys.getswitchinterval()
    sys.setswitchinterval(interval)
    return before, sys.getswitchinterval()
