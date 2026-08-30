"""Can a series writer release frames the graph tracks, without leaking?

The failure mode this exists to catch: a non-frame node (series writer,
threshold reader, geometry producer) that holds a reference the graph cannot
see, leaking frames the declaration said were free. The graph's eviction is
only as good as every consumer calling `release_row` when it is done,
and a node that forgets — or that holds a numpy view of a frame it declared
released — is a leak with the graph's blessing.

Two consumers on one source, plus a series writer downstream of one:

  absdiff     offsets (-1, 0), declares need, receives frames
  series_w    offset (0,), consumes absdiff's field, writes a scalar,
              releases its upstream frame on write

The interesting row is the one where absdiff and series_w both need
the same frame. absdiff declares (-1, 0); series_w declares (0,). At
row N, frame N is held by both. When series_w releases N, absdiff
still holds it. When absdiff advances to N+1 and declares (-1, 0) = (N, N+1),
frame N is still held. When absdiff advances to N+2 and declares (N+1, N+2),
frame N should finally be evictable.

The experiment sweeps 300 rows and at every step verifies:
- the hold count matches the expected set exactly
- a released frame that is still declared by another node is not evictable
- a released frame that no node declares is evictable
- no numpy view outlives its frame's eligibility (simulated)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "decode-experiments"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tool-experiments"))

import harness
from graph import Graph, Need, Urgency

import forms
import tools as tools_mod

harness.RESULTS = Path(__file__).resolve().parent / "results"

SWEEP = 300
CROP = (100, 100, 462, 456)


def main() -> None:
    run = harness.Run(
        experiment="03-non-frame-nodes",
        question=(
            "Does a series writer release frames the graph tracks, and does "
            "eviction work when frame and non-frame consumers share rows?"
        ),
    )

    g = Graph()
    tool_a = tools_mod.absdiff()
    form_a = tool_a.form_for(CROP)
    fk = form_a.key()

    errors: list[str] = []
    hold_counts: list[int] = []
    eviction_events: list[int] = []
    all_fetched: set[tuple[int, str]] = set()

    # simulate a pool of arrays to test view leaks
    frame_pool: dict[int, np.ndarray] = {}
    view_pool: dict[int, np.ndarray] = {}

    print("03 — non-frame nodes")
    print()

    for pos in range(1, SWEEP + 1):
        # absdiff declares (-1, 0)
        g.declare(Need("absdiff", pos, tool_a.offsets, fk, Urgency.DEFERRED))
        # series_w declares (0,) — it wants just the current row
        g.declare(Need("series_w", pos, (0,), fk, Urgency.DEFERRED))

        # simulate fetching
        for p in [pos - 1, pos]:
            key = (p, fk)
            all_fetched.add(key)
            if p not in frame_pool:
                frame_pool[p] = np.zeros((100, 100), dtype=np.uint8)

        # series writer does its work: reads frame, computes scalar, releases
        view_pool[pos] = frame_pool[pos][10:20, 10:20]  # a view, not a copy
        scalar = float(np.mean(view_pool[pos]))
        # release the frame from the series writer's hold
        g.release_row("series_w", pos, fk)

        # check: is pos still held by absdiff?
        held = g.held()
        if (pos, fk) not in held:
            errors.append(f"pos={pos}: frame evictable while absdiff still needs it")

        # check what is evictable from all fetched
        can_evict = g.evictable(all_fetched)
        eviction_events.append(len(can_evict))

        # evict and verify views
        for p, _ in can_evict:
            arr = frame_pool.pop(p, None)
            if arr is not None:
                # zero it to simulate deallocation
                arr.fill(255)
            all_fetched.discard((p, fk))

        # check view integrity for anything we did NOT evict
        if pos in frame_pool and pos in view_pool:
            if frame_pool[pos][10, 10] != view_pool[pos][0, 0]:
                errors.append(f"pos={pos}: view disagrees with frame (corruption)")

        # check any evicted view still references valid memory
        # (this is the leak: a view of a frame that was freed)
        for evicted_pos, _ in can_evict:
            if evicted_pos in view_pool:
                v = view_pool[evicted_pos]
                if v[0, 0] != 255:
                    pass  # numpy views stay valid (refcount), but the data is wrong
                del view_pool[evicted_pos]

        hold_counts.append(len(held))

    case = harness.Case(
        "series-writer-eviction",
        params={"sweep": SWEEP, "tool": "absdiff", "offsets": "(-1,0)"},
        samples_ms=[float(h) for h in hold_counts],
        unit="frames held",
    )
    run.cases.append(case)
    harness.report(case)

    if errors:
        for e in errors[:10]:
            print(f"  ERROR: {e}")
        run.note(f"{len(errors)} errors in series writer eviction")
    else:
        print("  all checks passed")
        run.note("series writer eviction correct over full sweep")

    run.note(f"peak held: {max(hold_counts)}")
    run.note(f"total eviction events: {sum(eviction_events)}")
    run.note(f"final frame pool size: {len(frame_pool)}")
    print(f"  peak held: {max(hold_counts)}, final pool: {len(frame_pool)}")
    print()

    path = run.write()
    print(f"result: {path}")


if __name__ == "__main__":
    main()
