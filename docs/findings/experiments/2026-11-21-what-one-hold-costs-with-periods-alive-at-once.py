"""What one more period's run held costs the window's thread when K periods are alive at a row.
A `period` of N periods of LENGTH rows, one beginning every LENGTH // K rows, three stepped series
nodes below it and every period's run held but one; then that one is held and what
`PlayerWindow._show_held` asks after it is timed: heldwalks.held_periods and, for one card,
heldwalks.listed_cuts, each handed what it last answered and what the hold moved. Made-up signals;
no player, no window, no video.
Run: .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-21-what-one-hold-costs-with-periods-alive-at-once.py"""
import os
import sys
import time
from types import SimpleNamespace as Tool

import numpy as np

sys.path.insert(0, os.getcwd())

from sieve_player import document as D  # noqa: E402
from sieve_player import held  # noqa: E402
from sieve_player.heldwalks import held_chain, held_periods, listed_cuts  # noqa: E402
from sieve_player.plan import plan  # noqa: E402
from tests.test_graph import gray  # noqa: E402

LENGTH = 1800
CASES = ((1000, 1), (1000, 12), (1000, 36), (1000, 72), (3000, 36))     # (periods, alive at a row)
BUDGET = 40.0       # s: no case is begun past it
BEGAN = time.perf_counter()


def series(name, expects):
    return Tool(NAME=name, KIND="series", EXPECTS=expects, PRODUCES="signal", PARAMS={},
                step=lambda state, row, i, params: (None, {"signal": 0.0}), run=lambda s, params: None,
                reach_in_rows=lambda params: (None, 0))


def ms(f):
    t = time.perf_counter()
    f()
    return (time.perf_counter() - t) * 1e3


for n, k in CASES:
    if time.perf_counter() - BEGAN > BUDGET:
        print(f"N={n}, {k} alive: not begun, {BUDGET:.0f} s spent")
        break
    step = LENGTH // k
    periods = [(i * step, i * step + LENGTH) for i in range(n)]
    count = periods[-1][1]
    period = Tool(NAME="period", KIND="frame", EXPECTS="gray", PRODUCES="gray", PARAMS={},
                  run=lambda frames, row, params: frames(row), cut_extents=lambda params, result, count, periods=periods: [{"rows": r} for r in periods])
    tools = {t.NAME: t for t in (gray, period, series("a", "gray"), series("b", "signal"), series("c", "signal"))}
    p = plan(D.from_tools(list(tools.values())), tools, "base", footage="print", count=count)
    (w,) = p.timed
    chain = held_chain(p, w.chain)
    runs = held.Runs(1 << 40, lambda nid, r: 0)
    sig = np.zeros(LENGTH)
    hold = lambda s, e: runs.hold(s, e - s, {nid: {"signal": sig, "key": p.entries[nid].key} for nid in w.chain}, chain, (s, e))
    mid = n // 2
    for i, (s, e) in enumerate(periods):
        if i != mid:
            hold(s, e)
    was, lists = held_periods(p, runs), listed_cuts(runs, "a", chain, w.cuts, count)
    moved = hold(*periods[mid])
    t_held = ms(lambda: held_periods(p, runs, was, moved))
    t_listed = ms(lambda: listed_cuts(runs, "a", chain, w.cuts, count, lists, moved))
    print(f"N={n}, {k} alive at once, {len(runs)} runs: one hold, held_periods {t_held:.1f} ms, listed for one card {t_listed:.1f} ms")
    sys.stdout.flush()
