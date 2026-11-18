"""The unit of every column of a table below blobs, sample, attach, track and kinematics, read back
off its dtype with tools/_table.py:unit_of; exits 1 where the dtype says nothing of a column. After
it, what a concatenate of two rows' tables, as held.py:_flat makes one, keeps of them.

    .venv/Scripts/python.exe docs/findings/experiments/2026-11-17-the-unit-of-every-column.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools import attach, blobs, kinematics, sample, track  # noqa: E402
from tools._table import plane, unit_of  # noqa: E402

PLANE, HALF = (60, 100), (30, 50)


def mask(at):
    m = np.zeros(PLANE, np.uint8)
    for x, y in at:
        m[y:y + 6, x:x + 8] = 255
    return m


def said(table):
    return {n: unit_of(table, n) for n in table.dtype.names}


rows = np.empty(4, object)
for r in range(4):
    m = mask([(10 + 2 * r, 20), (60, 10 + 3 * r)])
    found = blobs.find(m, 2, diff=m)
    found = sample.sample(found, m, "lit", "mean")
    found = sample.sample(found, m[::2, ::2], "set", "count")
    marks = blobs.find(mask([(12 + 2 * r, 22)])[::2, ::2], 1)
    rows[r] = attach.attach(found, marks, "dot", ["major"])
tracked, _ = track.link(rows, 10.0, 5, 1, 0.1)
moved = kinematics.kinematics(tracked)

last = moved[3]
print(f"plane {plane(last)}, {len(last)} records")
unsaid = []
for name, unit in said(last).items():
    print(f"  {name:10} {'unsaid' if unit is None else unit[0]:9} {'' if unit is None or unit[1] in (None, plane(last)) else 'of ' + str(unit[1])}")
    if unit is None:
        unsaid.append(name)
print("unsaid:", unsaid or "none")

one = np.concatenate([moved[2], moved[3]])
print("a concatenate of two rows' tables:", "says the same of every column" if said(one) == said(last) else
      "says nothing of any column" if not any(said(one).values()) else "says something else", "| plane", plane(one))
sys.exit(1 if unsaid else 0)
