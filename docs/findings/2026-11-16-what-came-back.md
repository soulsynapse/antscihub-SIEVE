# What came back

2026-11-16, on v5-systems-review. This is the friction ledger of docs/spec/systems-review.md: each
commit whose message tells of a fix, a rework or a second attempt, filed under the kind of problem
it tells of. It is named for what it holds and not `ledger`, which is `sieve_player/ledger.py`'s
word. Experiment: `docs/findings/experiments/2026-11-16-what-came-back.py`, which reads the classes
and their hashes from this file and counts them off the log; a class struck or a hash moved here is
recounted by running it. Its total is of the log as it stands when run, so it counts past the 405
read here by the commits made since.

    412 commits; 227 filed, 55%; came back 105, 25%; settling 120, 29%; touched no earlier line 2

## What was read, and how

The log of v5 and the twenty-five branches off it, every commit that is no merge, from `1f9c35fc`
of 2026-10-11 to `324df5c1`. v5 is an orphan root, so the branches of the generations before it
that this repository also holds (v2, v2.5, v3, v3.1, v4 and the scratch branches, some 1700
commits) are other programs' and are not read. The spec says every branch; this is the reading
taken of it, and a fix there lands in no module of this tree.

Only messages were read, never a diff. The first 210 commits were read by the session that wrote
this and the last 195 by three readers, each handed a stretch of the log and asked for one row a
problem in the message's own words, with no remedy; the classes were then drawn over all the rows
by the one session.

Every filing was then read back by one session, each commit's whole message against the sentence
of each class it was filed under: 457 filings, of which 39 did not tell of their class. Six had
been drawn first, three by hand and three at random, and three of those were wrong and taken out
(`3619919f` from F01, `0746a141` from F06, `02911112` from F21), a rate the whole reading puts at
one in twelve. Of the other 36, twenty-nine were taken out and seven moved to the class the
message does tell of:

- F01: `b3d122f7`, `202471a9`, `020ccd0a` and `36e3565e` out, each a rule or a routine in two
  places and so F10's, where each already was; `27fb7e04` to F10.
- F02 and F21: `cd6c579c` out of both, a record the ledger kept and not the worker's state.
- F05: `0b36a987` and `d89260a5` out; `7f0a645d` and `25b5c3da` to F08.
- F06: `d324df23` and `c0b417f4` out, a count made cheaper and not a wrong one; `a2ee454f`, a
  limit raised, to F08.
- F07 and F13: `25b5c3da` out of both.
- F08: `e9bf30f4` out; `50d07ce7` to F05.
- F10: `c14271d9` out, a copy made and not one found. F11: `c4788dcf`. F12: `09094ef1`, a rename
  cancelled before any file met it. F15: `0ff1baea`. F17: `701f7d2a`, `5ca908c5`.
- F14: `2b172f94` out; `e394db53`, a figure the stream left out, to F20.
- F18: `be59a820`, a file read once and never again, to F05.
- F19: `ad588e9f`, `7a31e181`, `a6289fee`, `1fc793e0`, `822aaabd`, `d39b4ca6` and `eb973068` out,
  each a test made easier to write, fewer, or kept off the user's files, none one that passed or
  failed for another reason.
- F24: `6320bc37`, line endings, and `49396edc`.

Five commits so left the ledger, filed under no class: `6320bc37`, `701f7d2a`, `a6289fee`,
`822aaabd` and `0ff1baea`. The errors were of a commit filed one class too many, or under the
neighbouring class, and none of a class invented. The reading was of messages, as the filing was,
and lenient where a message tells of the class without telling of a fix: `3bd2d8d1` and `6530136d`
are findings that changed no code, `46899a83` and `5ceb287a` build what their class lacked, and
`e88a7bdb` and `02911112` stand in F09 on a dependency untangled inside one module. Those six are
the nearest to wrong of what is left.

The classes were then read with Kendrick, which is the last section's. Three were made of four:
F01 took F09, and F05 and F08 were cut again between them. Ten filings were taken out and each
is said under its class; no commit left the ledger by it. The figures here are of the classes as
they stand after.

A commit is filed under every class one of its problems belongs to, so the classes' counts sum
past the commits filed. A class is a kind of problem and names no remedy. Where a sentence names a
part of SIEVE or Qt it names where the problem was.

## Settling and coming back

The spec's settling is a fix to a change of the same branch within a day of it. Which change a
commit fixes is a judgement, so it is measured instead by where the lines the commit removed were
written: each removed line of code is blamed at the commit's parent, and the commit is settling
when more of them were written on its own branch within the day before it than were not, and came
back otherwise. A commit that removed no code is told by the lines its additions sit beside, and
one that touched no code by its other files. Three things bend the figure. The 117 commits made on
v5 itself share one branch, so there only the day tells. A commit is one unit, so a fix that rides
in a large build is told as the build is. And a branch a week long (v5-blob-detection, seventy
commits) settles less than its fixes were felt to, since its second day's fixes to its first day's
work came back by this rule.

## The classes at a glance

Sorted by the commits that came back.

| class | the problem | commits | came back | settling | first to last |
| --- | --- | --- | --- | --- | --- |
| F20 | A report of where the time went was not what had happened: a figure, a sighting, a clearing, or the reporting's own cost. | 29 | 19 | 9 | 10-31 to 11-15 |
| F11 | A thing was built and then taken out, reversed or replaced. | 31 | 18 | 13 | 10-29 to 11-15 |
| F04 | A failure was not shown, was shown as something else, or was charged to the wrong party. | 27 | 13 | 14 | 10-11 to 11-15 |
| F13 | Prose said what the code no longer did: a comment, a docstring, the README, a spec's facts. | 36 | 12 | 24 | 10-26 to 11-15 |
| F17 | A kind on a wire, a facet or a name met code that took it for another. | 20 | 12 | 8 | 10-25 to 11-15 |
| F10 | The same machinery stood in more than one place, and was made one or found to differ. | 22 | 11 | 11 | 11-07 to 11-15 |
| F12 | A saved file met a program that had moved on: a document, held results, a dump, a history, a store. | 16 | 11 | 5 | 11-01 to 11-15 |
| F05 | What a result depends on was said too narrowly, so a stale one was served, or too broadly, so the work was done again. | 23 | 10 | 13 | 10-14 to 11-15 |
| F16 | A look, a default or a gesture's rule was set and then set again. | 20 | 10 | 10 | 10-13 to 11-15 |
| F07 | The footage was not what its container or the plugin said of it: its count, its rate, its range, where a seek lands. | 16 | 8 | 8 | 10-31 to 11-15 |
| F01 | It was not settled which module a responsibility was, a value's or a job's, and it lay in two or in the wrong one. | 21 | 7 | 14 | 10-11 to 11-15 |
| F08 | Work was done that nothing asked for, or not done for something that did; or a result was kept that nothing would ask for, or let go that something would. | 13 | 7 | 5 | 10-31 to 11-14 |
| F14 | A spec was rewritten after a review or a reading, or held a check that could not be met as written. | 30 | 7 | 23 | 10-31 to 11-16 |
| F15 | Qt did other than the code took it to. | 14 | 7 | 7 | 10-25 to 11-15 |
| F19 | A test passed or failed for a reason other than its subject. | 13 | 6 | 7 | 10-26 to 11-15 |
| F21 | What the walking thread was doing was inferred from flags and counts, by itself or by a reader, and the inference could be wrong. | 10 | 5 | 5 | 11-01 to 11-15 |
| F25 | A one-off script a finding cites stopped running when the code under it moved. | 8 | 5 | 3 | 11-12 to 11-15 |
| F02 | One thread read or wrote what another was in the middle of changing. | 13 | 4 | 9 | 10-26 to 11-15 |
| F03 | The GUI thread or the worker waited, spun, hung or died, and nothing said so. | 15 | 4 | 11 | 10-31 to 11-15 |
| F06 | A store counted other than what it held. | 6 | 4 | 1 | 10-31 to 11-15 |
| F18 | A file was written, replaced or deleted while something held it, or was left part-written. | 13 | 4 | 9 | 11-04 to 11-15 |
| F23 | A tool was slow once it was measured. | 7 | 2 | 5 | 10-31 to 11-15 |
| F24 | A commit carried what was not its own, or did not stand alone. | 4 | 2 | 2 | 11-14 to 11-15 |
| F22 | A long job could not be stopped, or was stopped by what did not concern it. | 4 | 0 | 4 | 10-31 to 11-15 |

## The classes

### F01. It was not settled which module a responsibility was, a value's or a job's, and it lay in two or in the wrong one.

21 commits: 7 came back, 14 settling. 10-11 to 11-15, 35 days. Largest: `07dd9830`, +706 -2438. Landed in: sieve_player/window.py 14, sieve_player/graph.py 9, sieve_player/pane.py 8, sieve_player/worker.py 7, sieve_player/dev/simulations.py 5, sieve_player/ledger.py 5.

In the messages' words: the document named the second video and the player had the first open (8a08c367); the container's count stood in the graph after the decoder had corrected its own (9666dbd1, ee31097e); the density fold ran in the worker's loop (aaca3f7e); the Tab menu lived in the canvas though it knows no document and no tool (cd7fac9f); the walk was in worker.py beside the QThread, so a process with no interface imported Qt to reach it (87c598cf).

Came back: `8a08c367` `aaca3f7e` `5db29f34` `cce26bfe` `c0ec2e20` `07dd9830` `87c598cf`

Settling: `484eec32` `9666dbd1` `64ce8f59` `d39b4ca6` `ee31097e` `e88a7bdb` `bc0aaeb4` `02911112` `cd7fac9f` `d5381dad` `8ed3439f` `e000301f` `020ccd0a` `e4c08b3a`

This is two classes of the first filing made one at the walk: a value held in two places that
disagreed, and a job in a module that did not own it, which was F09, a number not used again. Where
a value lay in two, the modules it lay between:

| commit | the value | lay between |
| --- | --- | --- |
| `8a08c367` | which video is open | the document and the window |
| `9666dbd1` | the count of frames | the decoder and the graph |
| `ee31097e` | the count of frames | the plate's decoder, a served reader, the window and `bare.py` |
| `64ce8f59` | a bake's range, increment and quality | the tool, the worker, the document and the graph |
| `484eec32` | a node's params | the document and its settings widget |
| `d39b4ca6` | the list of recent files | the launcher and the window |

The fourteen told as settling are a job or a value put where it belongs within a day of being
felt, which is the class working as Kendrick means it to. The seven that came back are what it
costs when that waits, by the commit's whole diff, whatever else it carried:

| commit | what moved | lines | code files |
| --- | --- | --- | --- |
| `8a08c367` | which video is open, the document's before the window opens it | +29 -2 | 1 |
| `aaca3f7e` | the density fold, from the worker to the graph | +60 -10 | 4 |
| `5db29f34` | the probe of a video, from the pane to the decoder | +76 -38 | 4 |
| `cce26bfe` | the player's diagnostics, from the package root to `dev/console.py` | +139 -126 | 3 |
| `c0ec2e20` | the stream, to a module of its own | +696 -243 | 9 |
| `07dd9830` | bake retired whole | +706 -2438 | 28 |
| `87c598cf` | the walk, out of the worker's module | +388 -362 | 4 |

Taken out at the walk: `590ead81`, whose message tells of a plot built and of no responsibility
moved; `46060680` and `0746a141`, the monitor's figures, which are F20's; `ccb805a4`, the worker's
wait against its ladder, which is F21's.

Kendrick, at the walk: this one is felt, and the word he uses for it is seams though it is more
responsibilities. "When I'm working on one thing, sometimes it seems like a module should just do
it itself. Usually not a problem, until it is." Moving the job is how it is meant to be solved,
"but when it gets built upon itself, it becomes hellish to undo." A seam is muddy when it costs
something. Tools hold a good deal that is independent by design, and he does not like
bureaucracy. SIEVE is doing well enough that this is no statement of what needs building, "*yet*";
that he feels one is most of the time the sign he needs to go and fix it.

### F02. One thread read or wrote what another was in the middle of changing.

13 commits: 4 came back, 9 settling. 10-26 to 11-15, 20 days. Largest: `ef20ba50`, +1401 -249. Landed in: sieve_player/graph.py 11, sieve_player/window.py 8, sieve_player/worker.py 8, sieve_player/pane.py 4, sieve_player/plan.py 3, sieve_player/store.py 3.

In the messages' words: a sync landing between a node's run and its read memoized the new upstream under the old key (54ad1445); the worker wrote the document (e2a0191d); a scrub's turn and a walk's fold could span two plans (b33be8d5, 6bf747b6).

Came back: `ef20ba50` `6bf747b6` `687f37b0` `b33be8d5`

Settling: `54ad1445` `84d53ce1` `e2a0191d` `a603747b` `64ce8f59` `a573babc` `3ca27e22` `8ed3439f` `e4c08b3a`

How each was found, where its message says: `ef20ba50` by a TypeError raised, `687f37b0` by a
monitor report that read 17.1 GB against 6.1 GB in the stores, `84d53ce1` by a review, and
`e4c08b3a` by a reading, its message saying two processes landing one key was not run. The other
nine do not say. Two are fixes of the class and not of a case, by their messages and not checked on
every path that writes: `6bf747b6`, the worker reading one Plan a turn, and `b33be8d5`, the graph
computing for a job under the job's Plan.

What a message cannot tell of is the silent kind: a wrong value put under a key that is itself
right, as `54ad1445` was before it was read. Nothing raises and nothing waits, so the monitor,
which times what the threads do, has no way to see it, and no count here holds one that was never
found. Kendrick, at the walk: it "seems like the kind of mistake that could become very bad and
largely unnoticed". What would see one is a clip walked bare compared with what the player holds
for the same keys and rows; the same comparison would see a key that holds less than its run reads
(F05) and a tool whose result depends on where its walk began (F07), and would also name every
tool that keeps state across rows, rightly. It is not built.

### F03. The GUI thread or the worker waited, spun, hung or died, and nothing said so.

15 commits: 4 came back, 11 settling. 10-31 to 11-15, 15 days. Largest: `bfb0d3a0`, +596 -496. Landed in: sieve_player/worker.py 7, sieve_player/decoder.py 5, sieve_player/graph.py 4, sieve_player/window.py 4, sieve_player/__init__.py 2, sieve_player/document.py 2.

In the messages' words: a reflag on the GUI thread sat until the worker's read came back (ce9e6b0b); close joined a worker inside a composite build (18c2010a); the loop spun through the lock until an ask changed the answer (ccb805a4); a second raise killed the worker thread (f3746e02).

Came back: `75212615` `e9bf30f4` `6bf747b6` `bfb0d3a0`

Settling: `efd1fe10` `18c2010a` `1161c8b2` `cd887844` `ce9e6b0b` `f3746e02` `119391c9` `ccb805a4` `46899a83` `25b5c3da` `00fd8c19`

Kendrick, at the walk: a hang is what he sees most of the time, and the monitor is built for it.
The class is of the tree before the monitor of `docs/spec/monitor.md` said so; the monitor names
what it does not time, as `unprobed`.

### F04. A failure was not shown, was shown as something else, or was charged to the wrong party.

27 commits: 13 came back, 14 settling. 10-11 to 11-15, 35 days. Largest: `d5381dad`, +1334 -363. Landed in: sieve_player/window.py 13, sieve_player/graph.py 11, sieve_player/worker.py 10, sieve_player/pane.py 5, sieve_player/__init__.py 4, sieve_player/catalogue.py 3.

In the messages' words: a second series head was left unrun with nothing in the GUI to say so (c6de1d12); the worker read every IndexError as the stream ending (e9142899); a bake's refusal went to the window walk and vanished (b588358c).

Came back: `35d3b85f` `8d088b32` `c6de1d12` `94cfb5da` `59ec9351` `e9142899` `e9bf30f4` `d0fd3492` `81854fd6` `cadf84d1` `202471a9` `6bf747b6` `bfb0d3a0`

Settling: `3216eb59` `19a3981b` `d0df30e1` `a603747b` `6e72a872` `64ce8f59` `a573babc` `b588358c` `50d07ce7` `d5381dad` `988d2530` `4042a82a` `ee31097e` `e4c08b3a`

Felt at the walk itself: the player died on a click while this class was being read, and
`2026-11-16-the-player-died-on-a-click.md` has what it left. What the class's commits do not
reach is a process that ends: the player says nothing as it dies, and the next launch says nothing
of the last having died.

### F05. What a result depends on was said too narrowly, so a stale one was served, or too broadly, so the work was done again.

23 commits: 10 came back, 13 settling. 10-14 to 11-15, 32 days. Largest: `eb973068`, +934 -203. Landed in: sieve_player/window.py 11, sieve_player/graph.py 8, sieve_player/decoder.py 5, tools/region.py 5, sieve_player/plan.py 4, sieve_player/store.py 4.

In the messages' words: the fold cache was keyed by the address of a freed buffer and handed back the previous graph's folding (e9bf30f4); a node served whichever quality was cut last (eb973068); a nudge to one shape keyed anew everything below every region (d30bd9f0); a walk was begun again at every change to a param, whether or not a key moved (36e3565e).

Came back: `4079a72d` `e9bf30f4` `be59a820` `391bddd9` `d30bd9f0` `aaca3f7e` `7f0a645d` `13b54ce7` `1a1e39db` `d89260a5`

Settling: `a603747b` `88a413f1` `50d07ce7` `eb973068` `00fd8c19` `a532015d` `6530136d` `9b11f9c8` `4042a82a` `36e3565e` `27fb7e04` `e4c08b3a` `25b5c3da`

Made at the walk of the first filing's F05, a held result answering for what it was not of, and
the half of its F08 that was work done again where nothing had changed: Kendrick took the two for
one class, and they are the two ways of one mistake. By the side each commit tells of:

- Too narrowly, a stale or a wrong result served: `e9bf30f4`, `be59a820`, `391bddd9` (a path, where
  the footage was meant), `50d07ce7`, `eb973068`, `00fd8c19`, `88a413f1` (read stale with nothing
  changed, by a key it was never made under).
- Too broadly, the work done again: `4079a72d` and `7f0a645d` (the row, of a node whose output is
  the same at every row), `d30bd9f0`, `a603747b`, `36e3565e`, `e4c08b3a`, `27fb7e04`, `a532015d`.
- Said nowhere, so done at every asking: `aaca3f7e`, `25b5c3da`, `9b11f9c8`, `13b54ce7`,
  `4042a82a`, and of a result that grows by a row, the whole of it again: `6530136d`, `d89260a5`,
  `1a1e39db`.

Taken out at the walk: `54ad1445`, whose key was right and whose value was not, which is F02's.
The rule a store keeps or lets go by is F08's.

Kendrick, at the walk: with F08 the most felt class of the ledger. "Not being deliberate about
keys has been an issue." Of a setting changed: whether something upstream is invalidated is
"seemingly random and the tree has leaned towards just invalidating as the default. A bunch of
settings functionally don't change the results and that doesn't always get caught until I get
annoyed by a cache getting invalidated for no reason. That one I feel all the time and don't have
a good system (which should probably be built?) in place for it." He would not have a key stated
as a contract, a thing so stated having bitten before. Old documents migrated on load and their
caches invalidated is fine by him, and no document was lost to it (F12).

Three things the class's commits leave as they are, each bearing on the tool he means to build
next, period, which cuts bouts out of a clip for further work and leans on keys being right:

- A tool that keeps state across rows gives a result that depends on where its walk began, and
  where a walk began is in no key. `held.py:Runs.over` serves a range by cutting it from the run
  that began earliest. Whether a bout walked alone is to equal the same rows cut from a walk of
  the whole clip is a decision of design, and his.
- `key_params` lets a tool say what of its params its run reads, and one tool says:
  `tools/region.py`. For every other tool the key holds every param, so a param that changes
  nothing in the result changes the key.
- A key covers the tools' code, by `held.py:tools_print`, and the player's own only by
  `held.VERSION`, which a hand raises.

The monitor's catalogue has no class for work done again whose result came out the same as
before; such a run shows in its figures and is named by nothing.

### F06. A store counted other than what it held.

6 commits: 4 came back, 1 settling, 1 touched no earlier line. 10-31 to 11-15, 15 days. Largest: `e9142899`, +519 -106. Landed in: sieve_player/decoder.py 4, sieve_player/graph.py 3, sieve_player/worker.py 3, sieve_player/pane.py 2, bench.py 1, sieve_player/__init__.py 1.

In the messages' words: 256 rows of 5K BGR was 12 GB (75212615); the memo counted a table at its pointers, 389 MB on paper and 6.6 GB real (e9142899); the memo counted the cache's frame under each passing node (a639e63e).

Came back: `75212615` `e9142899` `982ea14d` `a639e63e`

Settling: `020ccd0a`

Touched no earlier line: `fdb02081`

Kendrick, at the walk: an accurate description, and he takes it for largely handled, the fixes
live or watched by the monitor. Three of the six are of 11-15, `a639e63e` the last, so it is
handled of late and not long since. Whether the monitor would say a store claiming other than the
memory the process holds was not checked.

### F07. The footage was not what its container or the plugin said of it: its count, its rate, its range, where a seek lands.

16 commits: 8 came back, 8 settling. 10-31 to 11-15, 15 days. Largest: `023c46ce`, +500 -222. Landed in: sieve_player/decoder.py 12, sieve_player/__init__.py 5, sieve_player/pane.py 5, sieve_player/window.py 5, sieve_player/graph.py 4, sieve_player/document.py 3.

In the messages' words: a raw stream reported a count of -192153584101141 (925f03fa); a container that seeks inexactly landed past the target (d0fd3492); on 00000.MTS no seek lands in the first thirty rows and cv2 says it did (27fb7e04, fcddc126).

Came back: `5db29f34` `e9142899` `e9bf30f4` `d0fd3492` `80462761` `fcddc126` `c4788dcf` `023c46ce`

Settling: `9666dbd1` `925f03fa` `f0b66582` `ee31097e` `020ccd0a` `27fb7e04` `250bc61f` `00fd8c19`

Kendrick, at the walk: largely fixed for what he was able to catch, and it could be latent in the
tree. For footage there are standard answers. For a tool's result there is none in the tree: his
case is a window inherited from a partial walk, in which a rolling average over merged blobs
makes a new identity where a walk from the top would have continued an old one. Nothing catches
that, and catching such things one at a time would be "whack-a-mole". The comparison under F02 is
the one check that would see that case with the rest.

### F08. Work was done that nothing asked for, or not done for something that did; or a result was kept that nothing would ask for, or let go that something would.

13 commits: 7 came back, 5 settling, 1 touched no earlier line. 10-31 to 11-14, 14 days. Largest: `e9142899`, +519 -106. Landed in: sieve_player/graph.py 7, sieve_player/worker.py 5, sieve_player/window.py 4, sieve_player/held.py 3, sieve_player/catalogue.py 2, sieve_player/decoder.py 2.

In the messages' words: the window walk folded a density for every fed frame node, shown or not (98e65cac); the clip walk ran the series chain over its whole prefix every 30 rows (e9142899); a series rerun asked for while a row request was pending was dropped with the row (fbf4fab7); a whole-clip run under keys since left outlasted the fresh one of the same length (b390c121).

Came back: `c194f9d4` `a2ee454f` `fbf4fab7` `e9142899` `0746a141` `98e65cac` `5c095255`

Settling: `0a52b97d` `e6e0b8a9` `b390c121` `988d2530` `7a31e181`

Touched no earlier line: `3bd2d8d1`

What is left of the first filing's F08 once the work done again where nothing had changed went to
F05, with the rule a store keeps or lets go by, which was F05's second half. The first clause is
Kendrick's at the walk; the second is this session's, a store's rule being a guess at what will
be asked for. By the side each tells of:

- Done for nothing that asked: `98e65cac`, `3bd2d8d1`, `0746a141`, `7a31e181`, and oftener than
  anything read it, `e9142899` and `5c095255`.
- Not done for something that asked: `fbf4fab7`.
- Kept or let go by the wrong rule: `c194f9d4`, `0a52b97d`, `e6e0b8a9`, `b390c121`, `988d2530`,
  `a2ee454f`.

Taken out at the walk: `f410e9a1`, in whose message no such work is told, and `0fab7f4c`, a
search made slow by how a dict empties, which is F20's.

Kendrick, at the walk: with F05 the most felt, and why "pull is probably one of the most important
things to build out." What counts as read "can get read wrong I think, currently. Sometimes I
want a draw on the video that is hard to surface as something needing it." The tree bears him
out: what the plot asks for is said, by `graph.py:Graph.watch`, the selection and the pinned;
what the frame's overlay asks for is taken, by `graph.py:Graph.drawing`, to be every fed frame
node whose tool has a `draw`.

### F10. The same machinery stood in more than one place, and was made one or found to differ.

22 commits: 11 came back, 11 settling. 11-07 to 11-15, 8 days. Largest: `d324df23`, +1129 -181. Landed in: sieve_player/window.py 6, sieve_player/worker.py 5, tools/_table.py 5, tools/region.py 5, tools/_csvfile.py 4, tools/csv.py 4.

In the messages' words: tools reached the table kind through one another (32bbc5a6); the window walk and the clip walk were two copies, seven private names beside a twin (59ce234f); file.py and region.py each carried the same forty lines of list set-up (50d07ce7).

Came back: `32bbc5a6` `02da4f03` `982ea14d` `929f1614` `59ce234f` `b99d9d3e` `e2809773` `cce7cb8e` `46060680` `b3d122f7` `202471a9`

Settling: `d113c8bb` `ad588e9f` `fe462c3b` `50d07ce7` `d8613261` `d324df23` `d39b4ca6` `e000301f` `020ccd0a` `36e3565e` `27fb7e04`

Kendrick, at the walk: a statement of fact, and the copies are by design, since he waits until he
has felt a thing a few times before he makes it general and SIEVE has been built fast. He
remembers no copy that bit by differing: "it usually gets surfaced right away."

### F11. A thing was built and then taken out, reversed or replaced.

31 commits: 18 came back, 13 settling. 10-29 to 11-15, 17 days. Largest: `f410e9a1`, +3603 -1095. Landed in: sieve_player/graph.py 14, sieve_player/window.py 12, sieve_player/worker.py 9, sieve_player/pane.py 8, sieve_player/decoder.py 7, sieve_player/registry/__init__.py 7.

In the messages' words: the series chain went and returned in thirty minutes (b929028e, bc0aaeb4); bake was retired whole (07dd9830) and the store came back eleven hours later (eb973068); four fixes to a seek's numbering in an afternoon, then the plugin itself replaced (fcddc126 to 023c46ce).

Came back: `295ac684` `5db29f34` `4d8f513e` `e9142899` `051f1c87` `7e32b819` `590ead81` `f410e9a1` `c0b417f4` `f8b1afbd` `6bf747b6` `07dd9830` `bfb0d3a0` `b33be8d5` `023c46ce` `39ef92ba` `9d161825` `75616e2d`

Settling: `f6ed3f91` `b929028e` `bc0aaeb4` `5ca908c5` `7658707b` `09094ef1` `efc13e2f` `8ed3439f` `49396edc` `c7320fa9` `eb973068` `250bc61f` `1d8e0107`

Kendrick, at the walk: by design. He builds on separate trees so as to see what a change did and
whether he wants it, and several such stand in the code now, harmless. The seek's numbering was
him trying things.

### F12. A saved file met a program that had moved on: a document, held results, a dump, a history, a store.

16 commits: 11 came back, 5 settling. 11-01 to 11-15, 14 days. Largest: `f410e9a1`, +3603 -1095. Landed in: sieve_player/document.py 9, sieve_player/window.py 9, sieve_player/graph.py 8, sieve_player/plan.py 7, sieve_player/catalogue.py 6, sieve_player/dev/timeview.py 6.

In the messages' words: a document saved before a tool gained a param raised KeyError at the tool's first row (9db14898); every key changes, and a held file made before this is found by nothing (391bddd9); a file holding a crop2 node must load as a region under its id (bfb0d3a0).

Came back: `9db14898` `7e32b819` `590ead81` `f410e9a1` `f8b1afbd` `45a0323f` `391bddd9` `07dd9830` `bfb0d3a0` `b33be8d5` `d30bd9f0`

Settling: `64ce8f59` `3f1cca54` `799753a6` `8ed3439f` `61b852d9`

Kendrick, at the walk: an old document migrated on load and its caches invalidated is fine, and
none was lost or built again. What he feels of this class is the cache gone for no reason, which
is F05's. Met in the reading: three tools carry their own fallback for a param a saved document
lacks, `tools/box_bandpass.py`, `tools/track.py` and `tools/region.py`.

### F13. Prose said what the code no longer did: a comment, a docstring, the README, a spec's facts.

36 commits: 12 came back, 24 settling. 10-26 to 11-15, 20 days. Largest: `87c598cf`, +388 -362. Landed in: sieve_player/window.py 12, sieve_player/graph.py 9, sieve_player/pane.py 8, sieve_player/worker.py 7, sieve_player/document.py 6, sieve_player/canvas.py 5.

In the messages' words: module headers had grown a sentence per commit, and a read found twenty-six sentences the code contradicts (f85239e5); four docstrings left saying "the head" by the commit that made heads plural (76369920); the spec said the Decoder opens the plugin (023c46ce).

Came back: `09c8b48e` `f85239e5` `fbf4fab7` `7d4de31f` `2712d0d3` `373dbe36` `447aa471` `e2809773` `28415b4c` `0f2c2eb6` `023c46ce` `87c598cf`

Settling: `79f58b6e` `76369920` `c03538dd` `a2a6afc9` `a603747b` `64ce8f59` `6530136d` `b588358c` `119391c9` `435e363c` `50d07ce7` `4203efbc` `fd3183d4` `01baa096` `f9d64e86` `9b11f9c8` `3f1cca54` `46899a83` `4042a82a` `e000301f` `020ccd0a` `36e3565e` `27fb7e04` `e4c08b3a`

### F14. A spec was rewritten after a review or a reading, or held a check that could not be met as written.

30 commits: 7 came back, 23 settling. 10-31 to 11-16, 16 days. Largest: `8ed3439f`, +704 -473. Landed in: sieve_player/graph.py 4, sieve_player/ledger.py 4, utilities/geometry/editor.py 4, utilities/geometry/window.py 3, sieve_player/catalogue.py 2, sieve_player/dev/simulations.py 2.

In the messages' words: the bake spec after an architecture review against plan.py, document.py and worker.py (87b970d3); the geometry spec's first draft rewritten nineteen minutes later (9f3ea91a); a check wanting every line a search finds rewritten, three of them ticked assertions a session never rewrites (e2809773).

Came back: `87b970d3` `a6db20de` `ba71e6f5` `7d4de31f` `e2809773` `8b1da7ab` `28900372`

Settling: `d42f0f45` `8dbc11c5` `a2a6afc9` `1b544de7` `119391c9` `af8a6019` `94000248` `09094ef1` `d8613261` `9f3ea91a` `255909dd` `ff0e16ef` `01b898e7` `4c1b311e` `96529ae8` `1e4840b2` `cd6c579c` `8fcd3c5e` `8ed3439f` `271d1ca9` `1d8e0107` `9f635d70` `324df5c1`

Kendrick, at the walk, of F13 and of this: felt and no problem, a review doing its job. A spec
used to be deleted once built, so those in the tree are history or under revision, and he no
longer rereads a document until he has it by heart. Both are kept as fact and traced to no system.

### F15. Qt did other than the code took it to.

14 commits: 7 came back, 7 settling. 10-25 to 11-15, 21 days. Largest: `c14271d9`, +499 -103. Landed in: sieve_player/window.py 7, sieve_player/theme.py 5, sieve_player/canvas.py 4, sieve_player/pane.py 3, sieve_player/widgets.py 2, sieve_player/__init__.py 1.

In the messages' words: a QLabel in a column is as wide as the column, so the whole row took the click (b6da7c94); Escape called QLineEdit.undo, which goes back only as far as Qt's last undo separator (e000301f); a signal connected to a lambda holding the worker kept it for the life of the process (9d161825).

Came back: `b6da7c94` `9306b6a8` `8d088b32` `3619919f` `687f37b0` `1a1e39db` `9d161825`

Settling: `39b82a6e` `bde2fa23` `f9d64e86` `b2fa56ae` `c14271d9` `61b852d9` `e000301f`

Two are of how long an object lives and not of how a widget behaves: `9d161825` and `687f37b0`,
a signal's connection keeping a worker, and with it a video's stores, for the life of the
process. Kendrick, at the walk: fine as it stands, and F16 too.

### F16. A look, a default or a gesture's rule was set and then set again.

20 commits: 10 came back, 10 settling. 10-13 to 11-15, 33 days. Largest: `590ead81`, +1442 -543. Landed in: sieve_player/window.py 9, sieve_player/theme.py 7, sieve_player/canvas.py 6, sieve_player/timeline.py 5, sieve_player/plot.py 3, sieve_player/pane.py 2.

In the messages' words: the playhead pulls the window, is never outside it, is clamped and never pulls it, in ten minutes (67b057e2 to 6632e9cf); 30px overshot (112fa664); tried and taken out, in no commit (15b3f90e, 0d1abcec, 3619919f, 5c095255).

Came back: `9c493ae5` `19bbb67d` `590ead81` `5c095255` `23dc00cc` `202dde4f` `b1981c61` `15b3f90e` `0d1abcec` `c4239ace`

Settling: `6632e9cf` `7fc8ef00` `112fa664` `6847d0b1` `b2fa56ae` `cd7fac9f` `c14271d9` `efc13e2f` `61b852d9` `22886796`

### F17. A kind on a wire, a facet or a name met code that took it for another.

20 commits: 12 came back, 8 settling. 10-25 to 11-15, 21 days. Largest: `d5381dad`, +1334 -363. Landed in: sieve_player/catalogue.py 5, sieve_player/dev/timeview.py 4, sieve_player/registry/__init__.py 4, sieve_player/canvas.py 3, sieve_player/document.py 3, sieve_player/graph.py 3.

In the messages' words: a table's rows of differing length read as the graph changing shape, and the walk started over forever (cd887844); bg_subtract's own MODES constant was read as the facet (64ce8f59); what the pane looks for on a settings widget was found by hasattr at ten sites and written nowhere (997700a3).

Came back: `ed6d5f8c` `31c455ac` `a9c33cc3` `ba71e6f5` `e2809773` `cce7cb8e` `0f2c2eb6` `ef20ba50` `b3d122f7` `c7c4d7d9` `f8b1afbd` `fb49ff6e`

Settling: `1dac19f0` `cd887844` `2216f272` `64ce8f59` `94000248` `d5381dad` `799753a6` `997700a3`

Three things are under the one sentence, divided here by each message's opening lines and not its
whole:

- What is on a wire, eleven: `ed6d5f8c`, `31c455ac`, `a9c33cc3`, `fb49ff6e`, `1dac19f0`,
  `cd887844`, `2216f272`, `e2809773`, `cce7cb8e`, `ef20ba50`, `94000248`.
- How a tool's declarations are read, three: `64ce8f59`, `997700a3`, `ba71e6f5`.
- The kinds and names of the stream's records, six: `0f2c2eb6`, `b3d122f7`, `c7c4d7d9`,
  `f8b1afbd`, `d5381dad`, `799753a6`.

Kendrick, at the walk: felt once in a while and not too painful; he sees these as they are made.
The first two read to him as clear things to build.

### F18. A file was written, replaced or deleted while something held it, or was left part-written.

13 commits: 4 came back, 9 settling. 11-04 to 11-15, 11 days. Largest: `07dd9830`, +706 -2438. Landed in: sieve_player/window.py 9, sieve_player/document.py 5, sieve_player/graph.py 5, sieve_player/pane.py 5, sieve_player/__init__.py 4, sieve_player/worker.py 4.

In the messages' words: a write that fails left a .part, in document.save and _csvfile.replace both (929f1614); on Windows a clip open in cv2 refuses the replace that lands a bake (a603747b); the replace over a clip another region had open was refused and the whole encode lost (eb973068).

Came back: `e9142899` `e9bf30f4` `929f1614` `07dd9830`

Settling: `2060fbfe` `a603747b` `6e72a872` `50d07ce7` `988d2530` `d39b4ca6` `eb973068` `27fb7e04` `e4c08b3a`

Kendrick, at the walk: a good system and an easy one, and any write should probably go through
it. Of the tree's own files what he lost to this class is the encode of `eb973068`.

### F19. A test passed or failed for a reason other than its subject.

13 commits: 6 came back, 7 settling. 10-26 to 11-15, 20 days. Largest: `d324df23`, +1129 -181. Landed in: sieve_player/graph.py 5, sieve_player/window.py 4, sieve_player/decoder.py 3, sieve_player/catalogue.py 2, sieve_player/dev/simulations.py 2, sieve_player/ledger.py 2.

In the messages' words: one test ran to its 10 s timeout every run and passed on what happened to be there (6e72a872); a test connected its slot after asking and missed a fast worker about one run in eight (ccb805a4); no test read the three off a Frames, so the suite passed over a break (c29bfc45).

Came back: `5fb537e6` `28900372` `c0b417f4` `bfb0d3a0` `023c46ce` `c29bfc45`

Settling: `1482ba65` `847628c7` `6e72a872` `ccb805a4` `0b36a987` `d324df23` `25b5c3da`

Three kinds are under the sentence: a test whose answer turns on which thread ran first
(`ccb805a4`), a test that passes whatever the code does (`6e72a872`), and no test where one was
taken to be (`c29bfc45`), which fits the sentence least. The thirteen were not divided among them.
`CLAUDE.md` took its rule for the first kind in `c0b417f4`, one of the thirteen; four are after
it, and `023c46ce` among them tells of a test of the ledger failing once in some twelve runs,
seen and not settled. Kendrick, at the walk: trust in the suite matters.

### F20. A report of where the time went was not what had happened: a figure, a sighting, a clearing, or the reporting's own cost.

29 commits: 19 came back, 9 settling, 1 touched no earlier line. 10-31 to 11-15, 15 days. Largest: `8ed3439f`, +704 -473. Landed in: sieve_player/catalogue.py 16, sieve_player/ledger.py 14, sieve_player/dev/timeview.py 12, sieve_player/graph.py 8, sieve_player/dev/simulations.py 6, sieve_player/report.py 6.

In the messages' words: it read 3 h off a 32 s build (4079a72d); a problem cleared in one lane read as cleared while another's last walk still showed it (13b54ce7); a slowdown that stayed cleared itself once the fast walk was dropped (202471a9).

Came back: `4079a72d` `7f0a645d` `8b1da7ab` `28900372` `46060680` `0746a141` `cadf84d1` `13b54ce7` `1fc793e0` `57b3d362` `b3d122f7` `202471a9` `c7c4d7d9` `f8b1afbd` `45a0323f` `023c46ce` `e22531a0` `0fab7f4c` `b5c5e8f5`

Settling: `e394db53` `efd1fe10` `378ba876` `cd6c579c` `0b36a987` `799753a6` `3ca27e22` `8ed3439f` `46899a83`

Touched no earlier line: `3bd2d8d1`

The monitor of `docs/spec/monitor.md`, a stream, a ledger and a catalogue, was specified in
`f96a9d77` on 11-12. Five of the twenty-nine are before it and twenty-four from that day to
11-15, so the class is that monitor being built and driven on real documents over three days,
an instrument being set, and its count says nothing of how far the monitor is to be trusted now.
What sets it is in the tree: the simulations of `sieve_player/dev/simulations.py`, each a fault
made on purpose that the catalogue is to name. Kendrick, at the walk: the monitor is extremely
helpful, a hang is found by it, and it may not yet catch all it needs to. What this walk met that
it does not see: a wrong value under a right key (F02), work done again to the same result (F05),
and a process that ends (F04).

### F21. What the walking thread was doing was inferred from flags and counts, by itself or by a reader, and the inference could be wrong.

10 commits: 5 came back, 5 settling. 11-01 to 11-15, 14 days. Largest: `8ed3439f`, +704 -473. Landed in: sieve_player/worker.py 9, sieve_player/dev/simulations.py 3, sieve_player/window.py 3, sieve_player/catalogue.py 2, sieve_player/dev/timeview.py 2, sieve_player/graph.py 2.

In the messages' words: the failure handler guessed which walk it was stepping from whether rows were left (fbf4fab7); _serve had three exception arms guessing the job (770a0889); a walk of held rows was read as the old walk going on (b5c5e8f5).

Came back: `fbf4fab7` `59ce234f` `770a0889` `5ceb287a` `b5c5e8f5`

Settling: `fe462c3b` `b588358c` `ccb805a4` `8ed3439f` `ce86e5a3`

By who inferred: the worker of itself, six (`fbf4fab7`, and the five of 11-08 that
`docs/spec/solver.md` asked for, `59ce234f`, `fe462c3b`, `770a0889`, `b588358c`, `ccb805a4`,
after which each job holds its own state and none of this kind is told again); the figure of
`sieve_player/pace.py` of the worker, two (`5ceb287a`, `b5c5e8f5`); the monitor of the worker,
two (`8ed3439f`, `ce86e5a3`, the worker now saying when it rests and wakes). One case stands:
`pace.py` opens a walk on a count that falls or a range that grows, the worker beginning one over
with no signal of its own, and its docstring names the walk it still reads as the last going on.
Kendrick, at the walk: this reads to him as next to the keys. It is, in that a walk's identity is
made out from beside it where a result's is carried; it is no key, nothing being kept under it.

### F22. A long job could not be stopped, or was stopped by what did not concern it.

4 commits: 0 came back, 4 settling. 10-31 to 11-15, 15 days. Largest: `020ccd0a`, +363 -254. Landed in: sieve_player/graph.py 4, sieve_player/window.py 3, sieve_player/decoder.py 2, sieve_player/worker.py 2, tools/_cutfile.py 2, sieve_player/dev/simulations.py 1.

In the messages' words: a run of fifty seeks finished work nothing would take (18c2010a); a knob downstream or on another branch killed an hour's encode (a603747b); closing the player mid-cut left ffmpeg running (020ccd0a).

Settling: `18c2010a` `a603747b` `020ccd0a` `36e3565e`

Three of the four were settled by one question, whether the job's own key had moved: a read
after it has is cancelled (`18c2010a`), a bake is abandoned only then (`a603747b`), a walk is
begun again only then (`36e3565e`). So a key that holds more than its run reads (F05) stops a job
for what did not concern it. A cancel is met at a read; a tool's one long call and a child
process are not reached by it, and which tools have such a stretch was not looked for. Kendrick,
at the walk: what is stopped on him now is the bare walk, "because something in the tree updated
all the time", and little else. `window.py:PlayerWindow._bare_said` drops a bare walk's results
where the whole document is other than the one the walk began under, no key being asked; what of
a document so counts was not read.

### F23. A tool was slow once it was measured.

7 commits: 2 came back, 5 settling. 10-31 to 11-15, 15 days. Largest: `d324df23`, +1129 -181. Landed in: sieve_player/graph.py 2, sieve_player/window.py 2, tools/_table.py 2, tools/crop.py 2, sieve_player/decoder.py 1, sieve_player/widgets.py 1.

In the messages' words: blobs ran its feature pass over the whole plane for 136 components of which one survived (896113f7); crop's rect scanned the full plate at every row, in three forms in eighty minutes (07a5a0a4).

Came back: `5f2bf254` `c0b417f4`

Settling: `896113f7` `50d07ce7` `07a5a0a4` `d324df23` `4685285c`

A tool written the plain way, measured and written again, which is the monitor and the bare walk
doing what they are for; Kendrick, at the walk: a slow tool shows in the monitor just fine. Two
shapes come twice: the whole plane worked where a box would do (`896113f7`, `07a5a0a4`), and a
thing built at every row that no row changes (`c0b417f4`, `d324df23`). `STATIC` says a whole
tool's output is the same at every row; nothing says it of a part of one. Taken out at the walk:
`e9142899`, the clip walk's chain, which is the player's and F08's.

### F24. A commit carried what was not its own, or did not stand alone.

4 commits: 2 came back, 2 settling. 11-14 to 11-15, 1 days. Largest: `46899a83`, +594 -98. Landed in: sieve_player/catalogue.py 1, sieve_player/dev/simulations.py 1, sieve_player/graph.py 1, sieve_player/ledger.py 1, sieve_player/machine.py 1, sieve_player/plan.py 1.

In the messages' words: two sessions' work in one commit, their hunks being in the same files (46899a83); a move rode in by a slip, unsaid, and a test did not import at that commit (39ef92ba).

Came back: `b33be8d5` `39ef92ba`

Settling: `46899a83` `2b172f94`

Taken out at the walk: `391bddd9` and `fcddc126`, in whose messages nothing is told that was not
the commit's own. Kendrick, at the walk: he does not mind it; it began about when `CLAUDE.md` took
its line on committing and pushing, and it saves on tokens. That line is of `fcddc126`, 11-15,
and the class begins the day before. What it costs this finding is under What the classes'
figures are and are not.

### F25. A one-off script a finding cites stopped running when the code under it moved.

8 commits: 5 came back, 3 settling. 11-12 to 11-15, 3 days. Largest: `f410e9a1`, +3603 -1095. Landed in: sieve_player/catalogue.py 4, sieve_player/ledger.py 4, sieve_player/dev/simulations.py 3, sieve_player/dev/timeview.py 3, sieve_player/window.py 3, sieve_player/worker.py 3.

In the messages' words: eight one-offs that read a view into a Log no longer run (8ed3439f); nine others that no longer run stay because a finding or a ticked box cites each (b05608af).

Came back: `f410e9a1` `c0ec2e20` `023c46ce` `39ef92ba` `87c598cf`

Settling: `8ed3439f` `4042a82a` `b05608af`

Seven one-offs of 11-12 and 11-13 call `Log.read`, gone since `8ed3439f`, and stand. Kendrick, at
the walk: he does not as a rule run an old experiment again. A one-off is the record of what was
run on its day, and by the rule of `CLAUDE.md` that keeps it out of `tests/` nothing keeps it
running.

## What the classes' figures are and are not

The span is the days from a class's first commit to its last and the largest change is the commit
with the most lines added and removed, whatever else that commit carried; the log shows no other
cost. Hours are not in it: a commit's time is when it landed, and several sessions ran at once on
some days, so the time between two commits is no measure of the work in the second. `Landed in`
counts, a code file, the class's commits that touched it, so `sieve_player/window.py` and
`graph.py` lead most classes partly because most commits touch them. A commit that carries two
things (F24) is told as settling or as coming back by all its lines, so it bends the figure of
every class it is in.

## What this could not see

Work that left no commit, where a message happens to say so. Four commits tell of something built
and taken out again before the commit: a pace control in the transport's row and one outlined look
for every button (`15b3f90e`), the play button as a bare glyph (`0d1abcec`), the close mark as a
glyph Qt drew ragged (`3619919f`), and two faster ways of drawing an envelope dropped for how they
looked (`5c095255`). `4d8f513e` tells of a day of linker variants, none justifiable without ground
truth and all dropped. `09094ef1` cancels two renames before they were built. v5-runs is parked
with two commits no branch has merged (`7bc71e00`, `d324df23`), per `c0b417f4`. What was tried and
dropped with no message to say so is in no count here.

Changes nobody saw. From 11-01 to 11-15, 59 commits say something was not run, 49 of them the
player on screen. What Kendrick then saw in the player, and which of the looks set again in F16
came of it, the log does not tie together.

Gaps named and left. Of the last 195 commits, 92 name something left open or not fixed. Those are
not filed: a gap left is not yet a fix. Four tests or simulations are told failing some runs and
left unsettled (`5c095255`, `023c46ce`, `07dd9830`, `6bf747b6`).

Reviews. Several of the largest reworks follow a review a message names (`e9142899`, `84d53ce1`,
`87b970d3`, `64ce8f59`, `119391c9`, `c0ec2e20`, `590ead81`). What the review cost, and what it
found that was judged not worth a change, is not in the log.

Friction Kendrick has named that the log does not show. A session holds of his words only what an
earlier session wrote down, so this part is the thinnest and is his to add to at the gate.

- The spec's Why, a session's wording of his ask, whose own text he removed in `324df5c1`:
  "Modules hold things that are not theirs, and the same small machinery keeps being written again
  beside the last copy." In the log these are F09 and F10.
- Names. On 2026-11-09, of renaming `mask` and `inside`, a session's note records him saying "we
  need to talk about it first" and "a bunch of things already have weird names". The log shows
  only the renames cancelled in `09094ef1`.
- The gap. On 2026-11-14 he named running a sub-pipeline over pieces of footage, replicates cut in
  space and bouts cut in time, as the largest thing missing, with "Periods to bouts follows
  regions to crop." It is a thing SIEVE cannot do and not a thing that came back, so it is in no
  class; the spec enters it among the candidates on his word.
- What `46899a83` records of his word of 11-14, that the monitor spec's reading of the log is
  dated and the log largely not needed, is of one thing among several that go by that name. What
  went is `Log.read`, a reader that judged the ledger's view at a poll, as
  `docs/spec/monitor.md` says where it was reordered that day; `catalogue.py:Log`, the problems
  the catalogue has found, is what the monitor's window, `report.py` and the simulations read.
  He, at the walk: the log was a stand-in for something else and was mostly retired, and some of
  it may be left. Left of it, as found: the seven one-offs of F25, the spec's earlier sections,
  and the fields of `Log` the spec lists, which are not the fields the class has; whether any
  field is unused was not read.
- Who writes the code. He, at the walk: sessions building it and helping him assess it is how
  SIEVE got where it is, "a non issue", and he asks enough as it goes to bring a fault up. No
  class here is to be read as a cost of that.

## Read with Kendrick

On 2026-11-16 the classes were read to him one at a time and what he said of each is under it,
as his. He stated the friction; a session does not infer it. By what he said, the classes stand
so:

- Felt, and the most: F05 and F08, which he takes for one matter, what a result depends on and
  what is asked for.
- Felt when it costs: F01. Felt once in a while: F17. Felt that day: F04.
- A system he would have: F18, every write through one place. Of F22, that the standard move, a
  job told to stop, is no bad idea.
- Could be bad and go unseen: F02. Fixed for what was caught and maybe latent: F07.
- Handled, or the monitor's to find: F03, F06, F20, F21 but for one case, F23.
- Fact, by design or no problem: F10, F11, F12, F13, F14, F15, F16, F19 with trust in the suite
  mattering, F24, F25.

One thing recurs in F05, F08, F17 and F21, and is this session's reading: what settled a case was
its owner saying a thing that a reader had been making out for itself, what a run reads, what is
asked for, what kind is on a wire, which walk this is. Each of those is a fact of one run of one
tool or one walk of one range, and the tree keeps such facts in separate places: the key by
`plan.py`, the time by the graph's probe, the failure by `graph.py:Graph.note`, the bytes by
`graph.py:nbytes`.

Not all of it is to be acted on, and he said so: this is to bring up what could be. What the
reading put forward for the review's list of candidates, none of it agreed to be built:

- The reads of a run recorded: the player hands `run` its params through a mapping that notes
  which were read, and the key holds those. He: "probably the clearest system to deliberately
  build so far." It belongs in what already runs a tool and keeps its result,
  `graph.py:Graph._compute` with `plan.py`, a key now being made before anything runs. What it
  would save is counted first by a one-off that runs each tool so and lists the params no `run`
  read. F05; F22 by way of it.
- A clip walked bare compared with what the player holds, a one-off: F02, F05, F07.
- What kind is on a wire, and one reader of what a tool declares, `registry:probe` having no
  caller outside its package: F17's first two parts, small and apart.
- What is asked for said by a flag a user sets, where the frame's overlay now takes it: F08.
- One function that writes a file whole or not at all, every write through it: F18, and the
  review's A1.
- One place a failure is said, and a mark left at launch and taken away at a clean close, so
  that a launch after a death can say so: F04, and the review's A3.
- A job told to stop when its own key moves and at no other time, a long call and a child process
  having a way to be told: F22.
- The walk named on each progress signal: F21's one case.
- To watch and not to move: what the review's part 4 lists a module as holding for another, F01.

Fixes and no system: five tools draw by an `outline` param nothing declares; `recent.py:note`
leaves its part file; the geometry file is written where it lies.
