---
title: The read-back shape check has no case
priority: normal
phase: 5
status: open
gated_on: nothing
opened: 2026-08-07
---

# The read-back shape check has no case

`_verify` refuses on three things — a frame count, a shape, and content — and
05.1 landed a case for the first and the third. Deleting the shape branch
outright leaves `tests/integration/test_materialize.py` green, 9 passed, which
is how this was found.

It is not a redundant branch. If a read-back frame comes back at a different
shape the digest misses, and the tolerance path then compares `mean()` and
`std()` of two differently-shaped arrays — both perfectly computable, and for a
crop that was padded rather than corrupted both land well inside
`MAX_STATISTIC_DRIFT`. So without the shape check the padded file registers,
and the failure mode is the one `ARENA`'s odd origin in the test module was
chosen to expose: an encoder re-aligning a crop to a macroblock grid.

The case wants a writer that pads rather than one that inverts — monkeypatch
`write_ffv1` the way the two refusal cases already do, feeding frames grown by
a row and a column, and assert the `reads back as` message and that no `.mkv`
survives anywhere under the project folder.
