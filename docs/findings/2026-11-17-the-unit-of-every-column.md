# The unit of every column

2026-11-17, numpy 2.5.4 in `.venv`. `docs/spec/what-a-node-declares.md` has a column's unit said
where it is minted and carried on the table's dtype. `docs/findings/experiments/2026-11-17-the-unit-of-every-column.py`
builds a table through `blobs`, `sample` twice, `attach`, `track` and `kinematics` on a 60 by 100
plane, the second sample and the marks on a plane of half that, and reads every column back with
`tools/_table.py:unit_of`.

| column | unit | of |
| --- | --- | --- |
| `x`, `cx`, `dot_cx` | x | the table's plane |
| `y`, `cy`, `dot_cy` | y | the table's plane |
| `w`, `dx` | length x | the table's plane |
| `h`, `dy` | length y | the table's plane |
| `major`, `minor`, `speed` | length | the table's plane |
| `area`, `core` | area | the table's plane |
| `contour` | points | the table's plane |
| `set`, a sample's count | area | (30, 50), the sampled plane |
| `dot_area` | area | (30, 50), the marks' plane |
| `dot_major`, a column `attach` was asked to copy | length | (30, 50), the marks' plane |
| `angle`, `mean`, `peak`, `lit`, `dot_n`, `id`, `heading` | none | |

No column was unsaid.

The same run concatenates two rows' tables, as `held.py:_flat` does of a run's rows whose dtypes
are equal: the result's dtype says nothing of any column and carries no plane. Each row's table
came out of `with_column`, which makes a dtype of its own at every call, so the two rows' dtypes
are equal, with equal metadata, and are two objects. This sharpens the table in
`2026-11-17-what-keeps-a-dtypes-metadata.md`, whose "arrays of one metadata" were arrays of one
dtype object: metadata that is equal and not the same object is dropped. It was so of the plane
before a unit rode beside it, `with_column` having made a dtype a call then too.

Read in `held.py`, not run: `_flat` is how a held record writes a run's rows of tables, and it
leaves out a dtype with an object column, so a table with `contour` is written as it is and one
below `detect`, which has none, is concatenated. Not looked for: what a tool does of a table read
back from a held file with no plane on it.
