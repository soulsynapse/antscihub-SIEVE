"""The monitor's Problems over a log whose entry changes in place, offscreen: the rows repaint when
an entry's figures change and not when nothing did, and the foot names the latest cleared entries
and counts the rest. Prints each and exits 1 where one is not so.

    .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-13-the-problems-rows-repaint-what-the-log-changed.py
"""
import os
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from sieve_player.catalogue import Entry, Log, Problem  # noqa: E402
from sieve_player.dev.timeview import CLEARED, Problems  # noqa: E402
from sieve_player.ledger import WalkId  # noqa: E402

app = QApplication.instance() or QApplication([])
walk = WalkId(*([0] * len(WalkId._fields)))
problem = Problem("thrash", "memo", "line", 1.0, 0.5, (), "src", walk, 0.0, "says", "target")
log = Log()
entry = log.entries["thrash", "memo"] = Entry(problem, 0.0, count=1)
window = SimpleNamespace(log=log, picked=None, now=100.0, view=object())

part, updates, checks = Problems(), [], {}
part.lines.update = lambda *a: updates.append(1)
part.refresh(window)
part.refresh(window)
checks["a poll that changed nothing repaints no row"] = len(updates) == 1
entry.count += 1
entry.problem = replace(problem, ms_row=9.0, share=0.9)
part.refresh(window)
checks["an entry changed in place repaints its row"] = len(updates) == 2 and part.lines.written[0][1][3] == "9.00 ms a row"

for i in range(CLEARED + 2):
    log.entries["seeks", f"n{i}"] = Entry(replace(problem, kind="seeks", subject=f"n{i}", t=float(i)), 0.0, holds=False)
part.refresh(window)
foot = part.foot.text()
checks["the foot names the latest cleared and counts the rest"] = (
    f"n{CLEARED + 1}" in foot and "n0," not in foot and "and 2 earlier" in foot)

for said, ok in checks.items():
    print(f"{'ok ' if ok else 'NOT'} {said}")
print(" ", foot)
sys.exit(0 if all(checks.values()) else 1)
