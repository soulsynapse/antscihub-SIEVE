# What leaves the player is in the footage's rows and pixels

Read with `docs/spec/pieces-of-footage.md`, whose record this lifts by; with `tools/csv.py` and
`tools/_table.py`, which write a table and say its plane.

## How to read this

As `docs/spec/monitor.md`'s How to read this.

## Why

A table written below a cut is laid beside the tables of other cuts and drawn over the footage,
so its rows and positions are the footage's, whatever piece and plane it was found in.

## A table in the footage's rows and pixels

Assumes: `docs/spec/pieces-of-footage.md`'s A cut's record.

Facts to weigh. A csv written below a region is in the cut clip's pixels, so two regions' tables
cannot be laid side by side or drawn over the footage. `rescale` and `coarsegrain` hand out a plane
of another size than the piece's, and a table's dtype carries the plane it was found in
(`tools/_table.py:plane`). `attach`'s area is in the mark's plane. A column's unit is said where it
is minted and carried on the dtype; one the dtype says nothing of may have lost its unit
(`docs/findings/2026-11-17-what-keeps-a-dtypes-metadata.md`). `csv.py:default_name` is the
footage's stem and the rows, so two regions of one video that serve no clip name one file.

Open: whether a table's positions are moved to the footage's pixels where it is written, or are
minted in them. Recommended, and a session may build on it: where it is written, the table
carrying its piece and plane.

- [ ] A csv's rows are the footage's, and each column that says a unit is in the footage's pixels,
  scaled along its axis by its plane against the piece's size and, a position, moved by the record;
  a column that says none is written as it is. Its name and key line say the piece, the plate where
  there is no cut.
  Check: a one-off: a csv below a region and one below a region and a `rescale`, positions read
  back against the plate; one below an `attach`, its mark's area against the mark's plane; two
  regions of one video, two files.
- [ ] A table with a numeric column its dtype says nothing of is not written: the write raises,
  naming the column.
  Check: `tests/test_csv.py`, a seam.
