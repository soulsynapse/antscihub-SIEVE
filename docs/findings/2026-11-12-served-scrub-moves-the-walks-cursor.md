# A scrub of a served node moves the walk's cursor on its reader

2026-11-12, on v5-monitor at 0b36a987, through
`docs/findings/experiments/2026-11-12-served-scrub-moves-the-walks-cursor.py`: the simulations' graph of
`sieve_player/dev/simulations.py`, 64 rows of 64×48, its bake served on a fresh graph and the window walked
once plain and once with three scrubs asked while it walked, each thirty rows ahead of the walk. One run of
each; the counts are the walk's own, read off its record in the ledger.

| walk | the bake node's reader, in the walk's lane | the catalogue |
|---|---|---|
| plain | 64 decodes | nothing |
| three scrubs during it | 58 decodes, 2 seeks, 2 rows its cache held | seeks, subject bake, 2 seeks |

`_Scrub.turn` reads inside `Decoder.scrub()`, which puts the plate decoder's reads on its second cursor so
the display's jump never lands on the walk's. The call is on `g.decoder`, the plate's. A served node's rows
come from its reader's own `Decoder`, which nothing switches, so the scrub reads through that decoder's walk
cursor and the walk's next row finds the cursor ahead of it and seeks back. Two of the three scrubs cost the
walk a seek; the third landed within what the cursor reads through. The rows the scrub decoded are in the
reader's cache when the walk reaches them, which is the six decodes fewer.

On this clip a seek is nearly free, every frame of it a keyframe, and the entry reads 0.03 ms a row. On a
file with long groups of pictures each such seek decodes from the keyframe before it; not measured here, and
the purb bake was not driven.

Nothing in the spec's healthy walks covers it: the simulation's scrub during a walk is on a live document,
where the scrub has its own cursor and the walk reads no seek.

## The bug, for picking up after v5-monitor

Open; nothing on v5-monitor fixes it, the branch leaving the player as it is. Kendrick's reading of
2026-11-12 is that the fix is clear.

What is wrong: `_Scrub.turn` in `sieve_player/worker.py` reads inside `g.decoder.scrub()` alone. The shown
and the overlaid node may each sit at or behind a served frame node, whose rows come from the reader
`Graph._reader` opens, a `writers` clip reader holding its own `Decoder` as `.decoder`. That decoder has the
same two cursors and its `scrub()` is never entered.

What would fix it: the scrub's reads run on the scrub cursor of every decoder they can reach, the plate's
and each served clip reader's, so the walk's cursor on each stays where the walk left it. Whether that is
`_Scrub.turn` entering each held reader's `scrub()`, or the graph offering one context that does, is the
fix's to choose; a reader opened by the scrub itself, at its first read, must be covered too. A served series
node's reader holds no decoder and needs nothing.

What shows it fixed: the experiment beside this finding reads no seek on the bake node in the scrubbed walk,
and the catalogue nothing; as a test, the scrubbed walk of `tests/test_reading_back.py`'s served graph, or of
the simulations' with its bake served, reading no `seek` event in the window's lane. The second capture a
served reader then opens on its file is one more reader to close before a same-key rebake on Windows, which
`Readers.release` already does by closing the reader whole.
