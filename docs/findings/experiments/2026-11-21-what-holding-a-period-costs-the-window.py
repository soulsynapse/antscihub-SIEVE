"""What the window does on its own thread each time one period's run is held, with N periods held.
A `period` of N equal periods over 38100 rows, three stepped series nodes below it, each period's
run held in a held.Runs with made-up signals; then one pass of what `PlayerWindow._hold_run` asks
of them, timed: the plan, heldwalks.held_periods, heldwalks.window_periods, and held.Runs.listed
for three cards. No player, no window, no video.
Run: .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-21-what-holding-a-period-costs-the-window.py"""
import os
import sys
import time
from types import SimpleNamespace as Tool

import numpy as np

sys.path.insert(0, os.getcwd())

from sieve_player import document as D  # noqa: E402
from sieve_player import held  # noqa: E402
from sieve_player.heldwalks import held_chain, held_periods, window_periods  # noqa: E402
from sieve_player.plan import plan  # noqa: E402
from tests.test_graph import gray  # noqa: E402

COUNT = 38100
COUNTS = (100, 300, 1000)
BUDGET = 45.0       # s: no count is begun past it
BEGAN = time.perf_counter()


def series(name, expects):
    return Tool(NAME=name, KIND="series", EXPECTS=expects, PRODUCES="signal", PARAMS={},
                step=lambda state, row, i, params: (None, {"signal": 0.0}), run=lambda s, params: None,
                reach_in_rows=lambda params: (None, 0))


def ms(f):
    t = time.perf_counter()
    f()
    return (time.perf_counter() - t) * 1e3


for n in COUNTS:
    if time.perf_counter() - BEGAN > BUDGET:
        print(f"N={n}: not begun, {BUDGET:.0f} s spent")
        break
    each = COUNT // n
    periods = [(i * each, i * each + each) for i in range(n)]
    period = Tool(NAME="period", KIND="frame", EXPECTS="gray", PRODUCES="gray", PARAMS={},
                  run=lambda frames, row, params: frames(row), cut_extents=lambda params, result, periods=periods: [{"rows": r} for r in periods])
    tools = {t.NAME: t for t in (gray, period, series("a", "gray"), series("b", "signal"), series("c", "signal"))}
    doc = D.from_tools(list(tools.values()))
    made = []
    t_plan = ms(lambda: made.append(plan(doc, tools, "base", footage="print", count=COUNT)))
    p = made[0]
    (w,) = p.timed
    chain = held_chain(p, w.chain)
    runs = held.Runs(1 << 40, lambda nid, r: 0)
    for s, e in periods:
        runs.hold(s, e - s, {nid: {"signal": np.zeros(e - s), "key": p.entries[nid].key} for nid in w.chain}, chain, (s, e))
    t_held = ms(lambda: held_periods(p, runs))
    t_window = ms(lambda: window_periods(p, runs, 0, 300))
    t_listed = ms(lambda: [runs.listed(nid, chain, cut, COUNT) for nid in w.chain for cut in p.entries[nid].cuts])
    print(f"N={n}, {len(runs)} runs held, ms: plan {t_plan:.0f}, held_periods {t_held:.0f}, window_periods {t_window:.0f}, listed for 3 cards {t_listed:.0f}")
