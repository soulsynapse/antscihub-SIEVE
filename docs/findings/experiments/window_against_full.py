"""The one-off of docs/findings/window-against-full.md: every registered tool on the shortest chain
that feeds it from synthetic footage, walked over the whole clip and over two windows inside it,
each node's rows compared against the whole clip's.

    .venv\\Scripts\\python -X utf8 docs\\findings\\experiments\\window_against_full.py

The footage is COUNT rows of bright squares drifting over seeded noise, a row's pixels a function of
its row alone. Each walk is walk._Walk driven by its turns on this thread, as bare.py drives one, on
a Graph of its own; a chain below a cut in time is walked leg by leg as the worker's lanes walk it,
the clip's over each cut whole and the window's over walk.window_legs. A frame tool is read through
a series probe below it, so the walk stacks its rows. Rows are compared by tests/stepping.same:
exact for integers, tables and object rows, NaN equal to NaN for floats, dtype for dtype. The
driving is tests/windowing.py's, shared with tests/test_window_against_full.py.
"""
import os
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from sieve_player import decoder as decmod, store  # noqa: E402
from sieve_player.registry import discover  # noqa: E402
from tests.windowing import COUNT, PROBE, WINDOWS, CHAIN, against_full, offsets  # noqa: E402

TMP = tempfile.mkdtemp(prefix="window-against-full-")


def main():
    decmod.QUIET = True
    decmod.read_frame_times_ahead = lambda path, then=None: None
    decmod.STORE = None
    store.CHOICE = os.path.join(TMP, "store.txt")
    os.environ[store.STORE_ENV] = os.path.join(TMP, "store")
    tools = {**{e.name: e.module for e in discover(os.path.join(ROOT, "tools")) if e.ok}, "probe": PROBE}
    counts = {"HOLDS": 0, "BREAKS": 0, "SKIPPED": 0}
    print(f"{COUNT} rows; windows {WINDOWS}; a differing row as +k from the window's first row or -k from its last")
    for name in sorted(set(tools) - {"probe"}):
        said, why, nid, found = against_full(name, tools, TMP)
        if why is not None:
            counts["SKIPPED"] += 1
            print(f"{name:<14} {str(said):<13} SKIPPED  {why}")
            continue
        verdict, parts = "HOLDS", []
        for a, b, node, reach, planned, bad, over, _ in found:
            if reach != planned:
                parts.append(f"{node} summed {reach}, the plan says {planned}")
            if node == nid or over or node in CHAIN.get(name, ()):
                parts.append(f"[{a},{b}) {node} {reach}: {offsets(bad, a, b)}" + (f" PAST AT {offsets(over, a, b)}" if over else ""))
            verdict = "BREAKS" if over else verdict
        counts[verdict] += 1
        print(f"{name:<14} {str(said):<13} {verdict:<8} " + "; ".join(parts))
    print(" ".join(f"{k} {v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
