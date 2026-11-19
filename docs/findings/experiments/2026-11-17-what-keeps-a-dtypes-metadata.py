"""Which numpy operations on a structured array keep its dtype's metadata, where a table's plane rides.
Run: .venv/Scripts/python.exe -X utf8 docs/findings/experiments/2026-11-17-what-keeps-a-dtypes-metadata.py"""
import pickle

import numpy as np

FIELDS = [("x", "i4"), ("cx", "f4")]
one = np.dtype(FIELDS, metadata={"plane": (10, 20)})
other = np.dtype(FIELDS, metadata={"plane": (5, 5)})
a, b = np.zeros(3, one), np.zeros(2, one)

print("numpy", np.__version__)
print("two dtypes of other metadata are equal:", one == other, "and hash alike:", hash(one) == hash(other))
for name, made in [("slice", a[1:]), ("mask", a[a["x"] == 0]), ("take", a[[0, 1]]), ("copy", a.copy()),
                   ("sort", np.sort(a, order="x")), ("pickle", pickle.loads(pickle.dumps(a))),
                   ("concatenate, one metadata", np.concatenate([a, b])),
                   ("concatenate, two metadata", np.concatenate([a, np.zeros(2, other)])),
                   ("several fields, a[['x']]", a[["x"]]),
                   ("a dtype made of descr", np.zeros(1, np.dtype(one.descr)))]:
    print(f"{name}: {made.dtype.metadata}")
