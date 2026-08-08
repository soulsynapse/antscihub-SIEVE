---
title: Two crops of one name and span write the same file
step: "08.3"
status: open
gated_on: nothing
done_when: "uv run pytest tests/integration/test_materialize.py -q -k collide && uv run pytest tests/integration/test_materialize.py -q"
opened: 2026-08-07
---

# Two crops of one name and span write the same file

`artifact_filename(name, fmt, span)` does not take the region, and
`materialize_crop` writes to whatever it returns. Two records that
`CropRecord.identity()` calls distinct therefore land on one path: the second
`part.replace(final)` clobbers the first, and the first record — still in the
project, still resolving — answers `backs()` with True over a file holding a
different region's pixels. Measured in
`findings/2026.08.07-two-crops-of-one-name-and-span-write-one-file-and-backs-still-says-yes.md`.

The verification pass cannot see this. At the moment `_verify` runs the file is
exactly what was fed to it; the lie appears in the older record, which nothing
re-checks. So the fix is in the naming or in the write, not in the guard.

Two shapes, and the item is the choice as much as the change. A region-derived
component in the name makes the collision impossible and keeps the path a pure
function of the record, at the cost of a stem nobody can read. A uniquifying
suffix before `part.replace(final)` keeps names readable but makes the write
able to fail on a race and needs the record to carry whichever name won.
Whichever lands, `artifact_filename`'s docstring sentence about the name being
"disambiguated on the way out" has to go or become true — it currently
describes neither v2's shape nor v3's.

Numbered before 05.12 rather than filed beside it, because "gates" was a
relation the pool could not express: nothing calls `materialize_crop` today, so
the corruption is unreachable until that command exists and it must not still
be here then, and within a phase's pool the only ordering is the priority tier
and then the filename — which put this one *after* the item it gates. The
case belongs beside 05.1's refusal cases in
`tests/integration/test_materialize.py` — two cuts, one name, one span,
different regions, and both records still describing their own files.
