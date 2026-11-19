# What keeps a dtype's metadata

2026-11-17, numpy 2.5.4 in `.venv`. A table's plane rides its dtype's metadata
(`tools/_table.py:plane`), and `docs/spec/what-a-node-declares.md` would have a column's unit ride
there too. `docs/findings/experiments/2026-11-17-what-keeps-a-dtypes-metadata.py` asks which
operations on a structured array keep it.

| operation | metadata after |
| --- | --- |
| a slice, a bool mask, a list of indices, `copy`, `np.sort` by a field, a pickle read back | kept |
| `np.concatenate` of arrays of one metadata | kept |
| `np.concatenate` of arrays whose metadata differ | None |
| several fields taken, `a[["x"]]` | None |
| a dtype made again of `descr` with no metadata handed | None |

Two dtypes that differ only in metadata are equal and hash alike, so nothing that compares dtypes
tells them apart: `held.py:_flat` takes a run's rows for one kind by their dtype and concatenates
them.

Read in `tools/` by grep, not run: `_table.py:with_column` hands the metadata on, and
`_table.py:_plane_dtype` makes a dtype of `descr` and the plane alone, so anything else the dtype
it is handed carried is left behind there. No tool takes several fields of a table.

So metadata is lost with no error wherever it is lost, and a reader cannot tell a dtype that never
had an entry from one that lost it. Not looked for: whether any path in the tree concatenates
tables of two planes.
