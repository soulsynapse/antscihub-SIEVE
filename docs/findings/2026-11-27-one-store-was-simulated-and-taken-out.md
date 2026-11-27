# One store was simulated, built and taken out

2026-11-27, on v5-playground-one-store at `bd076ec3`, read from the 86 commits of `v5..HEAD` and
the files they deleted (`git show <commit>^:<path>`). Nothing was run for it. "The journal" is
`docs/playground/JOURNAL.md` as the named commit has it; its long form ends at `c93c0133^`.

## What was built, and what each was checked by

The journal (`bbf29887`) set four stages: an inventory (`b0561936`), a contract, a simulated
store, and slices into `sieve_player` "one of the inventory's holders at a time". The contract
and its code, `sim/store.py` and `sim/sim.py`, are `13883428`: a memory tier over a disk tier
under budgets, checkpoints as manifests, and seeded sequences of a user's doings on a simulated
disk and clock with O1, O3, O5 and O6 checked after each. The contract's scheme broke none over
150 seeds; code left out of the key, the footage print of size and ends, and entries written in
place each broke O1 in three or four doings. `sim/folder.py`, the store's disk over real files, is
`bb0c6da0`: `folder_check.py` played two stores over one folder against a dict for 40 seeds and
found nothing, at about 9 ms a doing. Both became `sieve_player/result_store.py` and
`result_folder.py` in `5d7582bf`, "importing nothing of the player and called by nothing yet".
`result_keeper.py` (`e7503afe`) kept a bare walk's frame rows that are no image, in chunks of
256, pinned by a test of a second walk running detect for no row; three bare walks of the
crossings clip over one folder took 2.5 s, 0.9 s and 0.9 s with equal results, and the journal
adds that ten seconds of clip is too short to price (`e0efa3a6`). The player's Graph was handed a
Keeper in `acde8df9`, and `81bf3151` wrote its chunks and the document's form into
`<document>.checkpoint` beside the held runs. Beside the store, as slices: `budget.py`
(`12e8e0e0`), display proxies (`e1e63ba8`), the reach test (`3eca29de`).

## What the figures said

From earlier findings gathered in `figures.md` (`22da1957`), as the journal reads them
(`189a9cc9`): a seek is 80 to 140 ms at 1080p against 1.1 to 2.8 ms for a row in order, fifty to
a hundred rows; threads flatten at about four, 7.03 ms a row at one worker and 2.05 at four and
at eight; holding more made a walk slower, 515 rows a second under a 64 MB memo and 151 to 316
under 4 GB; a plane is about 2 ms and 2 MB a row, ten times dearer to write to a 100 MB/s disk
than to make again, and a track step 0.6 to 0.9 ms for 1.2 KB. The priced simulation (`6b1dea61`,
its disk rates and laptop and HPC profiles guesses) has a first walk of 392 s against 1049 s
under one recency order, and the journal's sentence is "One store with one recency order is
worse than today's separate holders. The policy is the design, not a tuning." A scrub is one seek
and one row, 103 ms, and "The store cannot make that less". A 1280x720 jpeg of a frame is 70 KB
and 2 ms, a ten second loop at 5.3K 0.02 GB of proxies against 13.8 GB of planes (`0953c136`).
What kept rows saved a second clip walk after an edit (`73c64db7`, 40 cuts): "The keeper answered
nothing in any cell", the rows there being images. In the miniature detect ran 0 times with the
checkpoint's chunks lent and 319 withheld (`81bf3151`), and a cut in time cost the keeper one
durable write of about 670 bytes at 200 cuts as at 800 (`5df1794a`).

## What the adversaries proved, and what was mended

Against the contract, `store.py` and `sim.py` (`69cb7ec3`, the deleted `adversary.md`), eight
breaks proved in scratch copies: a second writer's checkpoint lost to this one's letting go; the
chunk grid not in the key and unseen by O1; `Ask.flight` holding 10.4 GB alive under a 3 GB
budget; `_make_room` run zero times in 150 seeds, so mutants ignoring the budget or the manifests
passed; a restore after a code edit bringing nothing back with O3 silent; a checkpoint refused
only after filling; torn parts counted used for good; a plane taken to disk at once at 5.3K. It
found too that the price table supports not writing planes on first make and not GreedyDual-Size
over recency. `eb4aa1fd` and `1c61f78d` answer them; the journal before `c93c0133` has "Not
rechecked: its other mutants". Against `folder.py` with real processes (`dcae353a`,
`adversary-2.md`), twelve items, eleven proved: calls raising under two processes, a returned
checkpoint left pending and swept, a foreign file breaking every room-making put, two holders of
one lock under clock skew, the budget passed by 1.90, a put of 1 KB 6 ms. `f6f0c660` mends them.
Its journal has nine items no longer coming out, item 3's held-open case showing "nothing either
way", item 9 "not seen to finish" and `made-*.log` growing without end; `c93c0133`'s message says
"every item of them mended".

## How it came out

- `2d5702da`: the held file is not moved first, being "already the range-aware holder, small,
  beside the document and leaned on at twenty places, and what costs is planes". It never moved.
- `b2872d98`, after 850 periods hung the player (`d9313e6b`): "the simulation models the store and
  nothing of what the scheduler pays a cut, so no oracle here could have seen it".
- `c93c0133`: the journal's long form, the inventory ("a reading of the tree many commits old"),
  both adversary reports and the claims list are deleted; `claims.py` went in `3046cde6`.
- `930423ce`: `sim.py`, `loop.py` and `figures.md` go: "the model shared no code with the player
  and found none of its defects." `a4c39356` folds `result_folder` into `result_store`.
- `d535451c`, after the miniature's O13 failed (`67825c7d`, a bare walk's rows not reaching the
  checkpoint): `result_store.py`, the results folder, `folder_check.py` and `diskrate.py` go and
  kept rows lie on disk only in the checkpoint. The message gives no reason for taking the store
  out beyond the arrangement that replaces it. Its journal: "O1 to O6 were written of a
  machine-wide store of results, which is gone; none is shown to hold."
- `d9efb79e`: the keeper holds no row. `tests/test_budget.py` had failed, 2427.7 MB planned
  against 2048 at 4 GB, the excess two Keepers of 512 MB, the window's runs and bare's stacks.
- `a15a9d27`: a tool's code leaves the key, "the owner having ruled \"Mark stale.\"". It had gone
  in at `69c9743b`, out at `ef7ac712` and in again at `828783a4`.
- `c61ffdfc`: the checkpoint holds held runs alone, "the owner having ruled \"if the user did a
  full run and hit save, it opens on that too\""; `result_keeper.py`, its test, the Graph's keeper
  and the memo's lent rows go, and `graph.py` is v5's.
- `99d2f759`: the footage print is v5's, "the owner having ruled it"; his words are not quoted.

## What was never asked

No commit compares the store with the existing holders on whether adding a tool touches the back
end. The journal before `c93c0133` says O4 "is not a simulation's to show and is counted at stage
4 by what a slice lets a new tool leave alone"; no commit holds that count, no holder the
inventory lists was moved onto the store, and nothing of the player called `result_store` but the
keeper. "Which of the places results are held in are apart for no reason, and can be one" was
first of the journal's Next from `930423ce` to `d1198622` and is absent at `bd076ec3`; no commit
between answers it. The journal at `bd076ec3`: "The earlier runs tested a store and never the
thing he asked for". That commit is the first to add a tool, a cutter at two widths and a `period` under a `period`
driven through the miniature with no store and no edit of the player.

## What remains in the tree

`budget.py` and `tests/test_budget.py`; display proxies and `sim/proxyrate.py`; the reach test
(`tests/windowing.py`, `tests/test_window_against_full.py`, `docs/findings/window-against-full.md`);
the checkpoint of held runs; a bare walk walking cuts in time (`a1834d56`); a window's runs held
apart (`930423ce`); the 850 periods' fix; provisional cuts (`89ad62f9`); `sim/miniature.py` and
`sim/cutters/pad.py`; `contract.md`, which the journal says describes what was taken out. Two
one-offs under `docs/findings/experiments/`, `bare_walk_thrice.py` and
`2026-11-21-what-walked-rows-save-a-rewalk.py`, set `SIEVE_RESULTS`, and the second imports
`result_keeper`; the tree has neither the variable's reader nor the module.
