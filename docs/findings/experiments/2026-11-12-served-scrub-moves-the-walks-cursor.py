"""Experiment behind docs/findings/2026-11-12-served-scrub-moves-the-walks-cursor.md: the simulations' graph
with its bake served, walked once plain and once with three scrubs asked during the walk, each thirty rows
ahead of it; per walk, what the bake node's reader did and what the catalogue's log holds.

    .venv\Scripts\python -X utf8 docs\findings\experiments\2026-11-12-served-scrub-moves-the-walks-cursor.py 2>NUL

Upstream of the bake is pinned, so the folds a served bake leaves running are read and the log is the scrub's alone.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from sieve_player.report import line  # noqa: E402
from sieve_player.dev import simulations as S  # noqa: E402

for scrub in (False, True):
    with tempfile.TemporaryDirectory() as tmp, S._Run(tmp, served=True, pinned=("gray", "work")) as r:
        if scrub:
            r.worker.walked.connect(lambda done, n: done in (8, 24, 40) and r.worker.request_row((done + 30) % S.ROWS))
        r.walk()
        seen = r.seen()
        runs = seen.view.walks[-1].nodes["bake"].runs
        print("scrubbed" if scrub else "plain", {f"{kind} under the {demand} of {asked}": v[0] for (kind, demand, asked), v in runs.items()})
        print("\n".join("  " + line(e) for e in seen.log.ordered()) or "  nothing found")
