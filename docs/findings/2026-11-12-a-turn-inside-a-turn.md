# A turn with a span inside it is put in the wrong bucket by the span's length, and the player opens no span inside a turn

2026-11-12, on v5-monitor over c0ec2e20 with the working tree of `docs/spec/stream-seams.md`'s deliverables
through The catalogue's parts, by `docs/findings/experiments/2026-11-12-a-turn-inside-a-turn.py`, offscreen.
It is the observation of the Fork under A span's place in time is the emitter's to say.

## The ledger's placing of a turn, as the Fork words it

A "slot" was opened 10 ms before a bucket's edge on an `Emitter`, did 5 ms of its own work, opened a
"monitor" turn of 500 ms, and did 100 ms of its own work after; both events went to a `Ledger` of 250 ms
buckets. Buckets are numbered from the one the slot began in.

| | bucket 0 | bucket 1 | bucket 2 | bucket 3 |
|---|---|---|---|---|
| the slot ran in | 5.0 ms | none | 7.0 ms | 93.1 ms |
| the ledger put it in | 12.0 ms | 93.1 ms | none | none |

93.1 of the slot's 105.1 ms are in a bucket the slot did not run in, and 100.0 are in another bucket than
the one they were spent in. The ledger spreads a turn's `ms` from its `t`, so what the slot did after the
turn inside it is drawn where the inner turn was, earlier by the inner turn's length. The figure a walk's
`gui` share is made of, a sum over the walk's buckets, moves only where the displacement crosses the walk's
first or last bucket.

## What is inside a turn in the player

The player was opened on a clip of 500 rows at 640 by 480 with gray and a series head, its monitor opened by
the header's control, and then left to walk the window, played for three seconds, walked a window of 100
rows and walked the clip, some eleven seconds in all with the monitor polling and painting.

Two runs gave 2487 and 2508 slots and paints. None had a span inside it, and the thread they are on emitted
no other span at all: no run, no read, no "monitor" of the ledger's. A turn's event is emitted after the
turn has closed, so a fold of the ledger's that the emit sets off is beside the turn and not inside it; the
display's rows are computed on the worker; and a paint is queued by Qt and not entered from a slot.

## What it does not show

The session was offscreen and short. A slot that calls `repaint()` and not `update()`, a tool run from a
slot, or a turn added later around something that emits would each put a span inside a turn, and nothing
would go red: the ledger would misplace the turn's own time as the first table shows. The stream as it is
does say which turn is inside which, a span emitted later on a thread with an earlier `t` enclosing those
since, which is how `Ledger._span` places a run. What a turn lacks is the `reader` by which the ledger
knows a span is waited on by an encloser still to emit: with none it would keep every turn, for an
encloser that in the sessions above never came. `docs/spec/stream-seams.md` has the two ways out as an Open.
