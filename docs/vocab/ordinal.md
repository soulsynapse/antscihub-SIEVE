---
title: ordinal
group: Substrate
position: 4
gloss: What row a listed position is, inside one store's snapshot of one listing. A coordinate, valid only beside the table that produced it, and never a frame's identity.
origin: emergent
defined: 2026-08-30
---

What row a listed [position](position.md) is, inside one snapshot of one
listing. An ordinal is a coordinate and not a name: it is valid only beside the
table that produced it, and the same frame is a different ordinal in a
different listing. It exists because grids have to be filed somewhere fixed and
distances have to be measured in something even — the two jobs a position
cannot do.

## Where it lives

`ordinals.py`. `Ordinals.rank` maps a position to its row, `listed` is the
snapshot it maps against, `around` returns the rows within a radius. It lived
in `serve.py` until the pipeline needed it too, and depends on nothing.

The snapshot is the point, and it is deliberately not on `Store`, which holds
that an extent is asked and never stored: a grid that renumbered itself when a
still landed would file the next chunk over the last one. That also names the
bug — a source still being written into grows past the snapshot and nothing
re-takes it, which `docs/vertical-slice.md` carries as untested rather than
fixed.

Distance is measured in rows and never in pts: at 90 kHz over 23.976 fps one
frame is 3753.75 ticks, so a pts difference compared against a count of frames
reads every ordinary step as a jump. ADR-0004 admits an ordinal only as a
per-store coordinate carried beside a table.
