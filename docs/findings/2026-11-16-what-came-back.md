# What came back

2026-11-16, on v5-systems-review. This is the friction ledger of docs/spec/systems-review.md: each
commit whose message tells of a fix, a rework or a second attempt, filed under the kind of problem
it tells of. It is named for what it holds and not `ledger`, which is `sieve_player/ledger.py`'s
word. Experiment: `docs/findings/experiments/2026-11-16-what-came-back.py`, which reads the classes
and their hashes from this file and counts them off the log; a class struck or a hash moved here is
recounted by running it.

    405 commits; 232 filed, 57%; came back 107, 26%; settling 122, 30%; touched no earlier line 3

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

Six filings were drawn and read back with `git show`, three by hand and three at random. Three
told of the class they were filed under (`b390c121` in F05, `f0b66582` in F07, `119391c9` in
F13). Three did not and were taken out: `3619919f` from F01, `0746a141` from F06 and
`02911112` from F21, each a commit that belongs to another class it is also filed under. So a
filing is wrong at a rate six draws put near a half and cannot put well, the errors seen are of a
commit filed one class too many and not of a class invented, and the spec's first box is left
unticked until the filings are read back whole.

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
| F11 | A thing was built and then taken out, reversed or replaced. | 32 | 19 | 13 | 10-29 to 11-15 |
| F20 | A report of where the time went was not what had happened: a figure, a sighting, a clearing, or the reporting's own cost. | 28 | 19 | 8 | 10-31 to 11-15 |
| F04 | A failure was not shown, was shown as something else, or was charged to the wrong party. | 27 | 13 | 14 | 10-11 to 11-15 |
| F08 | Work was done again where nothing had changed, or done where nothing read it. | 23 | 12 | 10 | 10-14 to 11-15 |
| F13 | Prose said what the code no longer did: a comment, a docstring, the README, a spec's facts. | 37 | 12 | 25 | 10-26 to 11-15 |
| F17 | A kind on a wire, a facet or a name met code that took it for another. | 22 | 12 | 10 | 10-25 to 11-15 |
| F10 | The same machinery stood in more than one place, and was made one or found to differ. | 22 | 11 | 11 | 11-07 to 11-15 |
| F12 | A saved file met a program that had moved on: a document, held results, a dump, a history, a store. | 17 | 11 | 6 | 11-01 to 11-15 |
| F16 | A look, a default or a gesture's rule was set and then set again. | 20 | 10 | 10 | 10-13 to 11-15 |
| F07 | The footage was not what its container or the plugin said of it: its count, its rate, its range, where a seek lands. | 17 | 8 | 9 | 10-31 to 11-15 |
| F15 | Qt did other than the code took it to. | 15 | 8 | 7 | 10-25 to 11-15 |
| F19 | A test passed or failed for a reason other than its subject. | 20 | 8 | 12 | 10-26 to 11-15 |
| F05 | A held result answered for what it was not of, or was kept or let go by the wrong rule. | 18 | 7 | 11 | 10-26 to 11-15 |
| F09 | A job lay in a module that did not own it, and was moved. | 18 | 7 | 11 | 10-11 to 11-15 |
| F14 | A spec was rewritten after a review or a reading, or held a check that could not be met as written. | 32 | 7 | 25 | 10-31 to 11-16 |
| F01 | One fact was held in two places, and the two disagreed. | 15 | 6 | 9 | 10-26 to 11-15 |
| F06 | A store counted other than what it held. | 9 | 6 | 2 | 10-31 to 11-15 |
| F18 | A file was written, replaced or deleted while something held it, or was left part-written. | 14 | 5 | 9 | 11-04 to 11-15 |
| F21 | The thread that walks told what it was doing by flags and counts that could disagree. | 11 | 5 | 6 | 11-01 to 11-15 |
| F25 | A one-off script a finding cites stopped running when the code under it moved. | 8 | 5 | 3 | 11-12 to 11-15 |
| F02 | One thread read or wrote what another was in the middle of changing. | 14 | 4 | 10 | 10-26 to 11-15 |
| F03 | The GUI thread or the worker waited, spun, hung or died, and nothing said so. | 15 | 4 | 11 | 10-31 to 11-15 |
| F24 | A commit carried what was not its own, or did not stand alone. | 8 | 4 | 3 | 10-26 to 11-15 |
| F23 | A tool was slow once it was measured. | 8 | 3 | 5 | 10-31 to 11-15 |
| F22 | A long job could not be stopped, or was stopped by what did not concern it. | 4 | 0 | 4 | 10-31 to 11-15 |

## The classes

### F01. One fact was held in two places, and the two disagreed.

15 commits: 6 came back, 9 settling. 10-26 to 11-15, 20 days. Largest: `590ead81`, +1442 -543. Landed in: sieve_player/window.py 8, sieve_player/graph.py 5, sieve_player/pane.py 5, sieve_player/catalogue.py 4, sieve_player/dev/timeview.py 4, sieve_player/document.py 4.

In the log's words: the document named the second video and the player had the first open (8a08c367); the container's count stood in the graph after the decoder had corrected its own (9666dbd1, ee31097e); the serving rule was in `Graph.cut_files` and `plan.file_of` both (020ccd0a).

Came back: `8a08c367` `590ead81` `46060680` `0746a141` `b3d122f7` `202471a9`

Settling: `484eec32` `9666dbd1` `64ce8f59` `ccb805a4` `d39b4ca6` `ee31097e` `020ccd0a` `36e3565e` `27fb7e04`

### F02. One thread read or wrote what another was in the middle of changing.

14 commits: 4 came back, 10 settling. 10-26 to 11-15, 20 days. Largest: `ef20ba50`, +1401 -249. Landed in: sieve_player/graph.py 12, sieve_player/window.py 8, sieve_player/worker.py 8, sieve_player/pane.py 4, sieve_player/plan.py 3, sieve_player/store.py 3.

In the log's words: a sync landing between a node's run and its read memoized the new upstream under the old key (54ad1445); the worker wrote the document (e2a0191d); a scrub's turn and a walk's fold could span two plans (b33be8d5, 6bf747b6).

Came back: `ef20ba50` `6bf747b6` `687f37b0` `b33be8d5`

Settling: `54ad1445` `84d53ce1` `e2a0191d` `a603747b` `64ce8f59` `a573babc` `cd6c579c` `3ca27e22` `8ed3439f` `e4c08b3a`

### F03. The GUI thread or the worker waited, spun, hung or died, and nothing said so.

15 commits: 4 came back, 11 settling. 10-31 to 11-15, 15 days. Largest: `bfb0d3a0`, +596 -496. Landed in: sieve_player/worker.py 7, sieve_player/decoder.py 5, sieve_player/graph.py 4, sieve_player/window.py 4, sieve_player/__init__.py 2, sieve_player/document.py 2.

In the log's words: a reflag on the GUI thread sat until the worker's read came back (ce9e6b0b); close joined a worker inside a composite build (18c2010a); the loop spun through the lock until an ask changed the answer (ccb805a4); a second raise killed the worker thread (f3746e02).

Came back: `75212615` `e9bf30f4` `6bf747b6` `bfb0d3a0`

Settling: `efd1fe10` `18c2010a` `1161c8b2` `cd887844` `ce9e6b0b` `f3746e02` `119391c9` `ccb805a4` `46899a83` `25b5c3da` `00fd8c19`

### F04. A failure was not shown, was shown as something else, or was charged to the wrong party.

27 commits: 13 came back, 14 settling. 10-11 to 11-15, 35 days. Largest: `d5381dad`, +1334 -363. Landed in: sieve_player/window.py 13, sieve_player/graph.py 11, sieve_player/worker.py 10, sieve_player/pane.py 5, sieve_player/__init__.py 4, sieve_player/catalogue.py 3.

In the log's words: a second series head was left unrun with nothing in the GUI to say so (c6de1d12); the worker read every IndexError as the stream ending (e9142899); a bake's refusal went to the window walk and vanished (b588358c).

Came back: `35d3b85f` `8d088b32` `c6de1d12` `94cfb5da` `59ec9351` `e9142899` `e9bf30f4` `d0fd3492` `81854fd6` `cadf84d1` `202471a9` `6bf747b6` `bfb0d3a0`

Settling: `3216eb59` `19a3981b` `d0df30e1` `a603747b` `6e72a872` `64ce8f59` `a573babc` `b588358c` `50d07ce7` `d5381dad` `988d2530` `4042a82a` `ee31097e` `e4c08b3a`

### F05. A held result answered for what it was not of, or was kept or let go by the wrong rule.

18 commits: 7 came back, 11 settling. 10-26 to 11-15, 20 days. Largest: `eb973068`, +934 -203. Landed in: sieve_player/graph.py 8, sieve_player/window.py 6, sieve_player/decoder.py 4, sieve_player/held.py 4, sieve_player/plan.py 4, sieve_player/registry/__init__.py 3.

In the log's words: the fold cache was keyed by the address of a freed buffer and handed back the previous graph's folding (e9bf30f4); a node served whichever quality was cut last (eb973068); a nudge to one shape keyed anew everything below every region (d30bd9f0).

Came back: `4079a72d` `e9bf30f4` `c194f9d4` `7f0a645d` `391bddd9` `d30bd9f0` `d89260a5`

Settling: `54ad1445` `0a52b97d` `a603747b` `88a413f1` `0b36a987` `e6e0b8a9` `b390c121` `988d2530` `eb973068` `25b5c3da` `00fd8c19`

### F06. A store counted other than what it held.

9 commits: 6 came back, 2 settling, 1 touched no earlier line. 10-31 to 11-15, 15 days. Largest: `d324df23`, +1129 -181. Landed in: sieve_player/decoder.py 6, sieve_player/graph.py 6, sieve_player/worker.py 4, sieve_player/pane.py 2, tools/_table.py 2, bench.py 1.

In the log's words: 256 rows of 5K BGR was 12 GB (75212615); the memo counted a table at its pointers, 389 MB on paper and 6.6 GB real (e9142899); the memo counted the cache's frame under each passing node (a639e63e).

Came back: `75212615` `a2ee454f` `e9142899` `982ea14d` `c0b417f4` `a639e63e`

Settling: `d324df23` `020ccd0a`

Touched no earlier line: `fdb02081`

### F07. The footage was not what its container or the plugin said of it: its count, its rate, its range, where a seek lands.

17 commits: 8 came back, 9 settling. 10-31 to 11-15, 15 days. Largest: `023c46ce`, +500 -222. Landed in: sieve_player/decoder.py 13, sieve_player/window.py 6, sieve_player/__init__.py 5, sieve_player/pane.py 5, sieve_player/graph.py 4, sieve_player/document.py 3.

In the log's words: a raw stream reported a count of -192153584101141 (925f03fa); a container that seeks inexactly landed past the target (d0fd3492); on 00000.MTS no seek lands in the first thirty rows and cv2 says it did (27fb7e04, fcddc126).

Came back: `5db29f34` `e9142899` `e9bf30f4` `d0fd3492` `80462761` `fcddc126` `c4788dcf` `023c46ce`

Settling: `9666dbd1` `925f03fa` `f0b66582` `ee31097e` `020ccd0a` `27fb7e04` `250bc61f` `25b5c3da` `00fd8c19`

### F08. Work was done again where nothing had changed, or done where nothing read it.

23 commits: 12 came back, 10 settling, 1 touched no earlier line. 10-14 to 11-15, 32 days. Largest: `f410e9a1`, +3603 -1095. Landed in: sieve_player/window.py 11, sieve_player/graph.py 10, sieve_player/worker.py 9, sieve_player/catalogue.py 5, sieve_player/decoder.py 4, sieve_player/ledger.py 4.

In the log's words: the clip walk ran the series chain over its whole prefix every 30 rows (e9142899); the window walk folded a density for every fed frame node, shown or not (98e65cac); the strip drew the whole clip's signal at each clipReady (1a1e39db).

Came back: `aaca3f7e` `fbf4fab7` `e9142899` `e9bf30f4` `f410e9a1` `0746a141` `13b54ce7` `98e65cac` `5c095255` `1a1e39db` `0fab7f4c` `d89260a5`

Settling: `a532015d` `a603747b` `7a31e181` `6530136d` `50d07ce7` `9b11f9c8` `4042a82a` `36e3565e` `27fb7e04` `e4c08b3a`

Touched no earlier line: `3bd2d8d1`

### F09. A job lay in a module that did not own it, and was moved.

18 commits: 7 came back, 11 settling. 10-11 to 11-15, 35 days. Largest: `07dd9830`, +706 -2438. Landed in: sieve_player/window.py 13, sieve_player/pane.py 8, sieve_player/graph.py 7, sieve_player/worker.py 7, sieve_player/canvas.py 5, sieve_player/dev/simulations.py 5.

In the log's words: the density fold ran in the worker's loop (aaca3f7e); the Tab menu lived in the canvas though it knows no document and no tool (cd7fac9f); the walk was in worker.py beside the QThread, so a process with no interface imported Qt to reach it (87c598cf).

Came back: `aaca3f7e` `5db29f34` `cce26bfe` `590ead81` `c0ec2e20` `07dd9830` `87c598cf`

Settling: `e88a7bdb` `bc0aaeb4` `64ce8f59` `02911112` `cd7fac9f` `d5381dad` `8ed3439f` `d39b4ca6` `e000301f` `020ccd0a` `e4c08b3a`

### F10. The same machinery stood in more than one place, and was made one or found to differ.

22 commits: 11 came back, 11 settling. 11-07 to 11-15, 8 days. Largest: `d324df23`, +1129 -181. Landed in: sieve_player/window.py 5, sieve_player/worker.py 5, tools/_table.py 5, tools/_csvfile.py 4, tools/csv.py 4, tools/region.py 4.

In the log's words: tools reached the table kind through one another (32bbc5a6); the window walk and the clip walk were two copies, seven private names beside a twin (59ce234f); file.py and region.py each carried the same forty lines of list set-up (50d07ce7).

Came back: `32bbc5a6` `02da4f03` `982ea14d` `929f1614` `59ce234f` `b99d9d3e` `e2809773` `cce7cb8e` `46060680` `b3d122f7` `202471a9`

Settling: `d113c8bb` `ad588e9f` `fe462c3b` `50d07ce7` `d8613261` `c14271d9` `d324df23` `d39b4ca6` `e000301f` `020ccd0a` `36e3565e`

### F11. A thing was built and then taken out, reversed or replaced.

32 commits: 19 came back, 13 settling. 10-29 to 11-15, 17 days. Largest: `f410e9a1`, +3603 -1095. Landed in: sieve_player/graph.py 14, sieve_player/window.py 12, sieve_player/worker.py 9, sieve_player/decoder.py 8, sieve_player/pane.py 8, sieve_player/registry/__init__.py 7.

In the log's words: the series chain went and returned in thirty minutes (b929028e, bc0aaeb4); bake was retired whole (07dd9830) and the store came back eleven hours later (eb973068); four fixes to a seek's numbering in an afternoon, then the plugin itself replaced (fcddc126 to 023c46ce).

Came back: `295ac684` `5db29f34` `4d8f513e` `e9142899` `051f1c87` `7e32b819` `590ead81` `f410e9a1` `c0b417f4` `f8b1afbd` `6bf747b6` `07dd9830` `bfb0d3a0` `c4788dcf` `b33be8d5` `023c46ce` `39ef92ba` `9d161825` `75616e2d`

Settling: `f6ed3f91` `b929028e` `bc0aaeb4` `5ca908c5` `7658707b` `09094ef1` `efc13e2f` `8ed3439f` `49396edc` `c7320fa9` `eb973068` `250bc61f` `1d8e0107`

### F12. A saved file met a program that had moved on: a document, held results, a dump, a history, a store.

17 commits: 11 came back, 6 settling. 11-01 to 11-15, 14 days. Largest: `f410e9a1`, +3603 -1095. Landed in: sieve_player/document.py 9, sieve_player/window.py 9, sieve_player/graph.py 8, sieve_player/plan.py 7, sieve_player/catalogue.py 6, sieve_player/dev/timeview.py 6.

In the log's words: a document saved before a tool gained a param raised KeyError at the tool's first row (9db14898); every key changes, and a held file made before this is found by nothing (391bddd9); a file holding a crop2 node must load as a region under its id (bfb0d3a0).

Came back: `9db14898` `7e32b819` `590ead81` `f410e9a1` `f8b1afbd` `45a0323f` `391bddd9` `07dd9830` `bfb0d3a0` `b33be8d5` `d30bd9f0`

Settling: `64ce8f59` `09094ef1` `3f1cca54` `799753a6` `8ed3439f` `61b852d9`

### F13. Prose said what the code no longer did: a comment, a docstring, the README, a spec's facts.

37 commits: 12 came back, 25 settling. 10-26 to 11-15, 20 days. Largest: `87c598cf`, +388 -362. Landed in: sieve_player/window.py 13, sieve_player/graph.py 9, sieve_player/pane.py 8, sieve_player/worker.py 7, sieve_player/document.py 6, sieve_player/canvas.py 5.

In the log's words: module headers had grown a sentence per commit, and a read found twenty-six sentences the code contradicts (f85239e5); four docstrings left saying "the head" by the commit that made heads plural (76369920); the spec said the Decoder opens the plugin (023c46ce).

Came back: `09c8b48e` `f85239e5` `fbf4fab7` `7d4de31f` `2712d0d3` `373dbe36` `447aa471` `e2809773` `28415b4c` `0f2c2eb6` `023c46ce` `87c598cf`

Settling: `79f58b6e` `76369920` `c03538dd` `a2a6afc9` `a603747b` `64ce8f59` `6530136d` `b588358c` `119391c9` `435e363c` `50d07ce7` `4203efbc` `fd3183d4` `01baa096` `f9d64e86` `9b11f9c8` `3f1cca54` `46899a83` `4042a82a` `e000301f` `020ccd0a` `36e3565e` `27fb7e04` `e4c08b3a` `25b5c3da`

### F14. A spec was rewritten after a review or a reading, or held a check that could not be met as written.

32 commits: 7 came back, 25 settling. 10-31 to 11-16, 16 days. Largest: `8ed3439f`, +704 -473. Landed in: sieve_player/graph.py 4, sieve_player/ledger.py 4, utilities/geometry/editor.py 4, sieve_player/worker.py 3, utilities/geometry/window.py 3, sieve_player/catalogue.py 2.

In the log's words: the bake spec after an architecture review against plan.py, document.py and worker.py (87b970d3); the geometry spec's first draft rewritten nineteen minutes later (9f3ea91a); a check wanting every line a search finds rewritten, three of them ticked assertions a session never rewrites (e2809773).

Came back: `87b970d3` `a6db20de` `ba71e6f5` `7d4de31f` `e2809773` `8b1da7ab` `28900372`

Settling: `e394db53` `d42f0f45` `8dbc11c5` `a2a6afc9` `1b544de7` `119391c9` `af8a6019` `94000248` `09094ef1` `d8613261` `9f3ea91a` `255909dd` `ff0e16ef` `01b898e7` `4c1b311e` `96529ae8` `1e4840b2` `cd6c579c` `8fcd3c5e` `8ed3439f` `2b172f94` `271d1ca9` `1d8e0107` `9f635d70` `324df5c1`

### F15. Qt did other than the code took it to.

15 commits: 8 came back, 7 settling. 10-25 to 11-15, 21 days. Largest: `c14271d9`, +499 -103. Landed in: sieve_player/window.py 7, sieve_player/theme.py 6, sieve_player/canvas.py 4, sieve_player/pane.py 3, sieve_player/widgets.py 3, sieve_player/__init__.py 1.

In the log's words: a QLabel in a column is as wide as the column, so the whole row took the click (b6da7c94); Escape called QLineEdit.undo, which goes back only as far as Qt's last undo separator (e000301f); a signal connected to a lambda holding the worker kept it for the life of the process (9d161825).

Came back: `b6da7c94` `9306b6a8` `8d088b32` `0ff1baea` `3619919f` `687f37b0` `1a1e39db` `9d161825`

Settling: `39b82a6e` `bde2fa23` `f9d64e86` `b2fa56ae` `c14271d9` `61b852d9` `e000301f`

### F16. A look, a default or a gesture's rule was set and then set again.

20 commits: 10 came back, 10 settling. 10-13 to 11-15, 33 days. Largest: `590ead81`, +1442 -543. Landed in: sieve_player/window.py 9, sieve_player/theme.py 7, sieve_player/canvas.py 6, sieve_player/timeline.py 5, sieve_player/plot.py 3, sieve_player/pane.py 2.

In the log's words: the playhead pulls the window, is never outside it, is clamped and never pulls it, in ten minutes (67b057e2 to 6632e9cf); 30px overshot (112fa664); tried and taken out, in no commit (15b3f90e, 0d1abcec, 3619919f, 5c095255).

Came back: `9c493ae5` `19bbb67d` `590ead81` `5c095255` `23dc00cc` `202dde4f` `b1981c61` `15b3f90e` `0d1abcec` `c4239ace`

Settling: `6632e9cf` `7fc8ef00` `112fa664` `6847d0b1` `b2fa56ae` `cd7fac9f` `c14271d9` `efc13e2f` `61b852d9` `22886796`

### F17. A kind on a wire, a facet or a name met code that took it for another.

22 commits: 12 came back, 10 settling. 10-25 to 11-15, 21 days. Largest: `d5381dad`, +1334 -363. Landed in: sieve_player/catalogue.py 5, sieve_player/canvas.py 4, sieve_player/dev/timeview.py 4, sieve_player/graph.py 4, sieve_player/registry/__init__.py 4, sieve_player/trace.py 4.

In the log's words: a table's rows of differing length read as the graph changing shape, and the walk started over forever (cd887844); bg_subtract's own MODES constant was read as the facet (64ce8f59); what the pane looks for on a settings widget was found by hasattr at ten sites and written nowhere (997700a3).

Came back: `ed6d5f8c` `31c455ac` `a9c33cc3` `ba71e6f5` `e2809773` `cce7cb8e` `0f2c2eb6` `ef20ba50` `b3d122f7` `c7c4d7d9` `f8b1afbd` `fb49ff6e`

Settling: `701f7d2a` `1dac19f0` `cd887844` `2216f272` `64ce8f59` `5ca908c5` `94000248` `d5381dad` `799753a6` `997700a3`

### F18. A file was written, replaced or deleted while something held it, or was left part-written.

14 commits: 5 came back, 9 settling. 11-04 to 11-15, 11 days. Largest: `07dd9830`, +706 -2438. Landed in: sieve_player/window.py 10, sieve_player/document.py 5, sieve_player/graph.py 5, sieve_player/pane.py 5, sieve_player/__init__.py 4, sieve_player/worker.py 4.

In the log's words: a write that fails left a .part, in document.save and _csvfile.replace both (929f1614); on Windows a clip open in cv2 refuses the replace that lands a bake (a603747b); the replace over a clip another region had open was refused and the whole encode lost (eb973068).

Came back: `e9142899` `e9bf30f4` `929f1614` `be59a820` `07dd9830`

Settling: `2060fbfe` `a603747b` `6e72a872` `50d07ce7` `988d2530` `d39b4ca6` `eb973068` `27fb7e04` `e4c08b3a`

### F19. A test passed or failed for a reason other than its subject.

20 commits: 8 came back, 12 settling. 10-26 to 11-15, 20 days. Largest: `d324df23`, +1129 -181. Landed in: sieve_player/window.py 8, sieve_player/graph.py 7, sieve_player/worker.py 4, sieve_player/catalogue.py 3, sieve_player/decoder.py 3, sieve_player/ledger.py 3.

In the log's words: one test ran to its 10 s timeout every run and passed on what happened to be there (6e72a872); a test connected its slot after asking and missed a fast worker about one run in eight (ccb805a4); no test read the three off a Frames, so the suite passed over a break (c29bfc45).

Came back: `5fb537e6` `28900372` `c0b417f4` `1fc793e0` `822aaabd` `bfb0d3a0` `023c46ce` `c29bfc45`

Settling: `1482ba65` `847628c7` `ad588e9f` `6e72a872` `7a31e181` `ccb805a4` `a6289fee` `0b36a987` `d324df23` `d39b4ca6` `eb973068` `25b5c3da`

### F20. A report of where the time went was not what had happened: a figure, a sighting, a clearing, or the reporting's own cost.

28 commits: 19 came back, 8 settling, 1 touched no earlier line. 10-31 to 11-15, 15 days. Largest: `8ed3439f`, +704 -473. Landed in: sieve_player/catalogue.py 16, sieve_player/ledger.py 14, sieve_player/dev/timeview.py 12, sieve_player/graph.py 8, sieve_player/dev/simulations.py 6, sieve_player/report.py 6.

In the log's words: it read 3 h off a 32 s build (4079a72d); a problem cleared in one lane read as cleared while another's last walk still showed it (13b54ce7); a slowdown that stayed cleared itself once the fast walk was dropped (202471a9).

Came back: `4079a72d` `7f0a645d` `8b1da7ab` `28900372` `46060680` `0746a141` `cadf84d1` `13b54ce7` `1fc793e0` `57b3d362` `b3d122f7` `202471a9` `c7c4d7d9` `f8b1afbd` `45a0323f` `023c46ce` `e22531a0` `0fab7f4c` `b5c5e8f5`

Settling: `efd1fe10` `378ba876` `cd6c579c` `0b36a987` `799753a6` `3ca27e22` `8ed3439f` `46899a83`

Touched no earlier line: `3bd2d8d1`

### F21. The thread that walks told what it was doing by flags and counts that could disagree.

11 commits: 5 came back, 6 settling. 11-01 to 11-15, 14 days. Largest: `8ed3439f`, +704 -473. Landed in: sieve_player/worker.py 9, sieve_player/dev/simulations.py 3, sieve_player/graph.py 3, sieve_player/ledger.py 3, sieve_player/window.py 3, sieve_player/catalogue.py 2.

In the log's words: the failure handler guessed which walk it was stepping from whether rows were left (fbf4fab7); _serve had three exception arms guessing the job (770a0889); a walk of held rows was read as the old walk going on (b5c5e8f5).

Came back: `fbf4fab7` `59ce234f` `770a0889` `5ceb287a` `b5c5e8f5`

Settling: `fe462c3b` `b588358c` `ccb805a4` `cd6c579c` `8ed3439f` `ce86e5a3`

### F22. A long job could not be stopped, or was stopped by what did not concern it.

4 commits: 0 came back, 4 settling. 10-31 to 11-15, 15 days. Largest: `020ccd0a`, +363 -254. Landed in: sieve_player/graph.py 4, sieve_player/window.py 3, sieve_player/decoder.py 2, sieve_player/worker.py 2, tools/_cutfile.py 2, sieve_player/dev/simulations.py 1.

In the log's words: a run of fifty seeks finished work nothing would take (18c2010a); a knob downstream or on another branch killed an hour's encode (a603747b); closing the player mid-cut left ffmpeg running (020ccd0a).

Settling: `18c2010a` `a603747b` `020ccd0a` `36e3565e`

### F23. A tool was slow once it was measured.

8 commits: 3 came back, 5 settling. 10-31 to 11-15, 15 days. Largest: `d324df23`, +1129 -181. Landed in: sieve_player/graph.py 3, sieve_player/decoder.py 2, sieve_player/window.py 2, sieve_player/worker.py 2, tools/_table.py 2, tools/crop.py 2.

In the log's words: blobs ran its feature pass over the whole plane for 136 components of which one survived (896113f7); crop's rect scanned the full plate at every row, in three forms in eighty minutes (07a5a0a4).

Came back: `5f2bf254` `e9142899` `c0b417f4`

Settling: `896113f7` `50d07ce7` `07a5a0a4` `d324df23` `4685285c`

### F24. A commit carried what was not its own, or did not stand alone.

8 commits: 4 came back, 3 settling, 1 touched no earlier line. 10-26 to 11-15, 20 days. Largest: `46899a83`, +594 -98. Landed in: sieve_player/decoder.py 3, sieve_player/graph.py 3, sieve_player/window.py 3, sieve_player/plan.py 2, sieve_player/__main__.py 1, sieve_player/bare.py 1.

In the log's words: two sessions' work in one commit, their hunks being in the same files (46899a83); a move rode in by a slip, unsaid, and a test did not import at that commit (39ef92ba).

Came back: `391bddd9` `fcddc126` `b33be8d5` `39ef92ba`

Settling: `46899a83` `49396edc` `2b172f94`

Touched no earlier line: `6320bc37`

### F25. A one-off script a finding cites stopped running when the code under it moved.

8 commits: 5 came back, 3 settling. 11-12 to 11-15, 3 days. Largest: `f410e9a1`, +3603 -1095. Landed in: sieve_player/catalogue.py 4, sieve_player/ledger.py 4, sieve_player/dev/simulations.py 3, sieve_player/dev/timeview.py 3, sieve_player/window.py 3, sieve_player/worker.py 3.

In the log's words: eight one-offs that read a view into a Log no longer run (8ed3439f); nine others that no longer run stay because a finding or a ticked box cites each (b05608af).

Came back: `f410e9a1` `c0ec2e20` `023c46ce` `39ef92ba` `87c598cf`

Settling: `8ed3439f` `4042a82a` `b05608af`

## What the classes' figures are and are not

The span is the days from a class's first commit to its last and the largest change is the commit
with the most lines added and removed, whatever else that commit carried; the log shows no other
cost. Hours are not in it: a commit's time is when it landed, and several sessions ran at once on
some days, so the time between two commits is no measure of the work in the second. `Landed in`
counts, a code file, the class's commits that touched it, so `sieve_player/window.py` and
`graph.py` lead most classes partly because most commits touch them.

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
- The monitor's log. `46899a83` records his word of that day, that the spec's reading of the log
  is dated and the log largely not needed, and that the machine he was using chugged under the
  runs that were to measure it. F20's commits are in large part that log's.
