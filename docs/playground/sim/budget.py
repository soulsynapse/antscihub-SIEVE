"""A clip walk under a limit on the held runs smaller than what the walk holds, on the miniature's
player: whether the worker comes to rest, whether the runs kept pass the limit, and whether a
result kept is the one a walk under no limit holds. Run: python -X utf8 budget.py,
MINIATURE_CUTTER as the miniature takes it. It prints a line a limit and exits 1 where one fails.
"""
import faulthandler
import os
import sys
from pathlib import Path

faulthandler.dump_traceback_later(600, exit=True)

HERE = Path(__file__).resolve().parent
sys.argv = ["miniature.py", str(HERE.parents[2]), "0", "0"]
G = {"__file__": str(HERE / "miniature.py"), "__name__": "mini"}
exec(compile((HERE / "miniature.py").read_text(encoding="utf-8").split("\nfailed = False")[0], "miniature.py", "exec"), G)
opened, settled, holds, app, np = (G[n] for n in ("opened", "settled", "holds", "app", "np"))
TURNS = 200000     # more worker turns than any walk here takes: past it the worker is taken as never resting


def rested(win):
    """The worker's turns taken until none is due, counted; None past TURNS."""
    taken = 0
    for _ in range(8):
        while True:
            with win.worker._cv:
                turn = win.worker._turn()
            if turn is None and win._whole_due.isActive():
                win._show_held_whole()
                continue
            if turn is None:
                break
            for job, act in turn[1]:
                win.graph.serving(turn[0], job.name)
                act()
            taken += 1
            if taken > TURNS:
                return None
        app.processEvents()
    return taken


def size(win):
    return win.runs._indexed()[3]


whole = opened("whole")
whole._toggle_clip()
at_rest = rested(whole)
want, full = holds(whole), size(whole)
print(f"cut by {G['CUTTER']}; under no limit {len(want)} results held in {full} bytes, {at_rest} turns")
failed = False
for part in (2, 8, 64):
    win = opened(f"limit-{part}")
    win.runs.limit = full // part
    win._toggle_clip()
    taken = rested(win)
    again = None if taken is None else rested(win)
    got = holds(win)
    wrong = [k for k in got if k not in want or not np.array_equal(got[k], want[k], equal_nan=True)]
    over = size(win) > win.runs.limit and len(win.runs) > 1
    waits = sorted(nid for n in win.doc.nodes if "waits" in (win.graph.standing(nid := n.id) or ""))
    said = [f"never rests in {TURNS} turns"] * (taken is None) + [f"{again} turns more once at rest"] * bool(again) \
        + [f"{len(wrong)} results kept differ, the first {w}" for w in wrong[:1]] + [f"{size(win)} bytes kept over the limit"] * over
    failed |= bool(said)
    print(f"limit a {part}th, {win.runs.limit} bytes: {taken} turns, {len(got)} of {len(want)} results kept in {size(win)} bytes, "
          f"{len(win.runs)} runs, waiting: {waits or 'none'}; " + ("; ".join(said) or "ok"))
    sys.stdout.flush()
sys.stdout.flush()
os._exit(1 if failed else 0)
