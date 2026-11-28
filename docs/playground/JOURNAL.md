# Playground: a back end he does not think about

Branch `v5-playground-one-store`, cut from `v5`; the name is the question it was cut to ask,
answered no, and not what it builds. Notes to resume from, not rules: where the tree
or the work shows a line here wrong, the line goes. Deleted before anything merges. State is
verified with `git log --oneline v5..HEAD`, never taken from this file.

## What Kendrick asked for

He develops tools and runs experiments to publish, and wants to stop thinking about the back end:
the decode cache, the memo, the series, the checkpoint, what periods and other tools keep. A
collaborator's weak computer runs it and a strong one too; above all no worry as tools are added.

1. Windows are reliable and fast.
2. A saved file opens where the user left off, as the user expects.
3. Walk bare and walk clip keep working as tools are added.
4. What is likely to be revisited does not cost the user much.

Whether holding every result in one store would get him that was the branch's first question. It
would not: `docs/findings/2026-11-27-one-store-was-simulated-and-taken-out.md`. No store is built
here and none is argued for.

The goal, restated with him on 2026-11-27 so that each part can fail a check:

- G1. Adding a tool of a kind the player has, frame, series, stepped, cutting, cut by a result,
  serving a file, edits no file of `sieve_player/` and needs no rule of keys, held runs,
  checkpoints or what is computed again but those `sieve_player/registry/README.md` says a tool
  declares.
- G2. Ordinary work, a scrub, the window moved, a param edited, a wire made or broken, a clip
  walk or a bare one, a save, a reopen, the document handed to a colleague, never shows a result
  that is wrong, missing or of older code without saying so; where the player cannot show a
  thing yet it says that, and what will make it appear.
- G3. What an ordinary act costs does not grow with what was done before it, the cuts, runs and
  nodes there are; and nothing likely to be looked at again is computed again without need.

"Never thinks about the back end" whole is more than this branch. The branch is done by "Done
when" below, which is G1 to G3 for the kinds of tool the tree has now.

The branch is mine to build: forks are decided here with the reasoning said to him, specs are
historical referents and not rulings, and player-visible decisions are reported so he can
overrule them. His freeing me from a spec's decision endorses neither side of it.

## The oracles

Each oracle is of G1, G2 or G3. O2, O3 and O6 were of a store's entries and went with it.

- O1, of G2. What is held or shown under a key equals what a fresh player computes of the same
  document, after any edit. `sim/adversary.py A` asks it of a cutting tool whose `run` changes
  the frame, which failed it until such a tool was keyed; the miniature does not ask it yet.
- O4, of G1. A tool of a kind the player has is added with no edit of `sieve_player/`. Asked by
  the cutters of `sim/cutters/`; no check asks it of the other kinds.
- O5, of G3. Memory held stays under the budget given; a budget too small for one row's work is
  said. Nothing checks it.
- O7, from the 850 periods: what one more cut, run or node costs a turn of either thread does
  not grow with how many there are. The miniature asks it of a clip walk's steps a cut, and of a
  window moved, whose steps with 800 cuts held are not to pass 1.5 times those with 200. A window
  moved took 193630, 338240 and 980519 steps with 200, 800 and 3200 held while it asked
  `_show_held` of every cut and run, and took 131920, 145120 and 261610 after that. What then
  grew, `_restate` on each window result asking every cut its file and its rows in time, does
  not: `sim/audit.py`'s cell of a window moved with cuts held says what it takes now. O7 is two
  acts by one size; the audit is every act by every size, and a cost is judged there.

- O8, his: a bare walk and a clip walk leave the same held; bare is only the faster for having
  no window beside it.
- O9, his: nothing computed only for the window reaches a tool, a walk of the clip or the held
  file.
- O10, his: the window shows what is asked of it, every series node's line over its rows, whether
  or not a clip walk was made. The miniature asks it over a window inside a period, one over two
  whole periods and one cutting periods at both edges; before a clip walk the lines at a period
  cut off by the window's edge are to be best effort, and after one none is. By his ruling a
  cutting tool cut by a wire whose cuts of a part of the result are not its cuts of the whole
  shows no line below it before a clip walk and its node says it waits: the tool that says
  `CUT_BY_A_PART` is cut by what the window walked, `period` among them, and one that says
  nothing waits (`sieve_player/registry/README.md`).
- O11, his: a full run made and the document saved, the document and its checkpoint copied
  elsewhere and opened: every run the first player held is served without walking.
- O14, his ruling: a held run made under a tool's older code is served after the tool's code
  changes, and its node is marked as of other code.
- O12 and O13 were of a frame node's small rows in the checkpoint, which he ruled out of it.

## What checks the work

- `sim/miniature.py`, the player itself over a clip made for it, says which of O7 to O11 and O14 hold.
  It writes nothing outside a temp folder. It does not see real threads, decode or disk.
- What caught real defects: an adversary told to prove a break in a scratch copy; an unanchored
  reader tracing one path; a profile of the real document
  (`docs/findings/experiments/2026-11-21-the-gui-thread-while-the-clip-lane-walks-periods.py`).
- What did not: a ledger of my own beliefs rechecked on a file's change. A belief that bites is
  one never written down.
- `contract.md` is the design as assertions. Most of it is not built; a line of it is no
  evidence about the tree.

## Next

`sim/miniature.py` is the player's own window, worker, plan, held runs and tools over a clip made
for it, the worker's turns taken on one thread, and it says which of O7 to O11 and O14 hold. A defect
found on a real document is pinned there.

What follows is the record of what the cutters showed; the list of work is "Done when". The
question the branch was cut to answer was whether one store is needed at all. The earlier runs
tested a store and never the thing he asked for, a tool added without the back end being thought
of; the plan below tests that, by cutting tools that are not `period` driven through the miniature
(`MINIATURE_CUTTER`, the tools under `sim/cutters/`). The figures of a run are the miniature's to
print and a commit message's to hold, not this file's.

1. Done, to be verified by running it: a `pad` cutter, each of the gate's runs widened so a cut
   reads rows its gate does not keep, disjoint (`pad1`) and overlapping (`pad3`), and a `period`
   under a `period` (`nested`). No module of `sieve_player` asks a cutting tool's name to walk or hold what it cuts
   (`document.py` names `region` to read an older document, and `plan`'s standing says "periods"
   of any cutter's cuts); the player
   knows one by `cut_extents` and `CUT_BY` alone. What the cutters showed is items 2 to 4.
2. A cut reaching past its gate's run is not shown by a window that holds none of the run, and
   nothing says so: `cut_extents` declares no reach over the result it is handed, so a
   provisional cut is made of the window's rows of the gate as if they were all of it.
3. Done, to be verified by the miniature under `nested`: a gate inside a cut in time is answered
   by the window's walk of that cut (`heldwalks.window_gate_result` reads the window's
   `window_periods`), the cuts made again once a pass where a result moved (`cuts_alike`), and
   what the window walked of a cut kept when the plan moves under others (`walked_before`).
   Open under it, both seen in the miniature's steps a cut of a nested clip walk, which fails
   O7: each outer cut's run held makes the cuts again, and `plan` is made whole, asking
   `cut_result` of every cut, so a clip walk of nested cuts costs the square of them (the look
   through every held run inside each ask is gone, `held.Runs.of_cut`); and each of the window's
   cuts turning from provisional to held has the worker walk every cut of the window again, a
   cost of the window's size and not of the clip's, which nesting makes larger. The first is the
   ask being the whole document's and not one cut's.
4. A window moved grew past O7's bound under `pad1` and not under `pad3` or `period`: read, and
   the monitor's own ledger counted as the player's; "Done when" item 2 says it.
5. `registry.cut_by` answers a tool's first CUT_BY input and no other: a cutter of two gates has
   no way in. Unbuilt, and whether one is wanted is his.
6. The standing of a gate's held run, to be argued to him and not built unasked: it is read by
   `plan`'s `cut_result`, so letting it go changes results and not speed alone, where every other
   holder is a cache. The referent is an analysis written into the document (Nuke's CurveTool and
   Tracker write knobs), never let go for a budget; a provisional cut is its preview.
7. Done: `docs/findings/2026-11-27-one-store-was-simulated-and-taken-out.md`. Two one-offs it
   names read a module and a variable the tree no longer has; whether they go is his.
8. Done: `contract.md` is the address and the ask, without the store.
9. What is proven here and no part of the question, to be put to him as a merge of its own: the
   850 periods' fix, `budget.py`, the checkpoint, the display proxies.

## The audit of what each act costs

Asked for by him on 2026-11-27, the defects of cost having been found one at a time by whoever
picked a case: every act against every size that can grow, measured, and set against what the
act is to cost. It is G3 made a table. It is `sim/audit.py`, and a run of it is filed as
`docs/findings/2026-11-27-what-each-act-costs-against-each-size.md`: what it found, and the work
that follows of it, is there and in "Done when". A change meant to take a cost away is judged by
the cells of its column going to what they are to be, and by no other cell passing it.

The method is empirical growth, as Goldsmith, Aiken and Wilkerson's "Measuring Empirical
Computational Complexity" has it: one size is varied over three or four values spaced by
doubling with the others fixed, the steps of each function are counted, and the slope of log
steps on log size is the exponent, 0 flat, 1 linear, 2 quadratic. A cell is a finding where the
exponent measured passes the one expected by more than a quarter and the steps at the largest
size are more than noise; the finding lists the functions by how much of the growth is theirs.

How it is built, each a thing found while planning it:
- It execs the miniature's text up to `failed = False` as `sim/adversary.py` does, and sets the
  miniature's globals in that namespace before a player is opened: `PERIOD` and `KEPT` for the
  rows of a cut, `BELOW` lengthened by `smooth` nodes each reading the last for the chain,
  `opened(name, cuts)` for the cuts. `held.File.write` is put back to `WRITE` so a save writes.
- Two counts an act: the steps of the act alone, which is the window's thread at once, and the
  steps of `settled(win)` after it, the worker's turns and the slots they land in.
- The sizes: cuts 50, 100, 200, 400; rows a cut 4, 8, 16 (`KEPT`, `PERIOD` twice it); the
  window's length 1, 2, 4 times three cuts, so the longest lengthened ends inside the shortest
  clip, which the script asserts; nodes added to the chain 0, 2, 6. The base
  is 100 cuts, 4 rows, 1, 0. It is run under `MINIATURE_CUTTER` unset and `nested`, depth being
  two points and no slope.
- The acts, in this order on one player a size: a window moved with none held; a clip walk; a
  scrub; a window moved and a window lengthened with every cut held; the marks of other code
  (`_show_stale`); a save; a reopen (`player(folder)`, the new player settled); a param edited
  below the cuts (`smooth`'s `reach`); the gate's band edited to cut the same rows; let go.
- What each is to cost, the table the measures are set against, his to correct: a scrub by the
  chain alone; a window moved or lengthened by the window, the rows of a cut and the chain; a
  clip walk, a save and a reopen by cuts, rows and chain, once each; an edit at once by what the
  window shows, and until settled by all that it made stale and the window walked again; the
  marks by the chain alone, and let go at once by the chain. `EXPECTED` in the script is the
  table.
- Not measured by it: anything that is flat and dear, which a wall-time profile of the same acts
  on his GoPro document is for. A limit on the held runs is `sim/budget.py`'s, which asks whether
  a clip walk under one comes to rest and keeps no result other than a walk's under none.

## Done when

A proposal of mine, his to cut. The question the branch was cut for is answered, one store is
not needed, and the finding holds why. What is left is for the answer to stand on a tree that
passes its own checks, and for the playground to go.

An adversary was set on the first form of this list, told to assume it done; what it proved is
`docs/findings/2026-11-27-an-adversary-against-the-plan-to-finish.md`, its runs `sim/adversary.py`,
and the list below is the one it left. The order is the order of work.

1. His rulings first, each changing what is built below. The first is built as recommended, on
   his "fix the defects then": `registry.hands_down_what_it_reads`, a cutting tool with no `run`;
   `cut_extents` is handed the footage's rows third, where `period`'s check of its file's rows
   now is, `period` having no `run`. To be verified by `MINIATURE_CUTTER=norun1` holding what
   `pad1` holds and by `sim/adversary.py A` saying no held result differs from a fresh player's.
   Found on the way: a tool whose file does not import left its node not fed with no standing,
   the menu alone saying why; the plan's standing now names the tool that is not loaded, and
   the node below says it waits on that node.
   - how the player knows a cutting tool hands down what it reads. It takes any tool that cuts
     rows alone for one (`plan.py`'s `in_time_alone`) and leaves it out of the keys below, so one
     whose `run` changes the frame serves the old values after its param is edited. Mine to
     recommend: a cutting tool with no `run` hands down what it reads and no other does, a rule
     taken away and not one added; `period`'s check of its file's rows moves to `cut_extents`.
   - whether a cutting tool declares a reach over the result that cuts it. Without one the player
     cannot tell which cutter reads past a window's rows, and to say best effort it must say it
     of every provisional cut, `period`'s too.
   - whether a gate's held run is the document's and never let go for a budget.
   - whether a cutter of two gates is wanted at all.
2. Defects, each with a run in `sim/adversary.py` or the miniature that shows it. Done, to be
   verified by those runs: the first (`_show_stale` reads every walked node's chain; the
   miniature's O14 asks it below a cut) and the third (`plan` refuses a node whose `cut_extents`
   raised, its standing "cuts nothing:" and what was raised; `region` raises its "no geometry"
   there too, and a region of no geometry is no longer fed where its `run` used to raise, a
   change he can see; the registry README does not say the rule yet, item 4). The rest are open:
   - a result made under a tool's older code is not marked below a cut in time (`_show_stale` is
     handed the chain no cut in time is in). His "Mark stale." does not hold under a period.
   - the key, as ruled in item 1.
   - a cutting tool that raises in `cut_extents`, or one with no path input and its gate unwired,
     passes the whole footage and has no standing. The standing says what the tool raised.
   - a param edited costs the window's thread more the more cuts are held. Less than it did and
     not flat: `_show_held` answers of the window's cuts at once and of the rest when
     `_whole_due` runs out, the clip lane walking nothing meanwhile; `sim/adversary.py T` says
     the milliseconds by cuts held. What still grows is the plan made whole at each sync and
     `Runs.spans` over every run. A card's values in every cut and its mark of other code wait
     on the same timer, a change he can see.
   - nested: a plan made whole at each gate's run held; the cuts of one cut in time are made
     again without the others'.
   - the window's cuts walked again as each turns from provisional to held: the worker walks
     again the cut that moved and no other; the miniature counts walks of a cut unmoved, none.
   - `pad1`, O7 of a window moved: read, and holds. What grew was the monitor's ledger, a
     dataclass's `__init__` made from `ledger._span`, counted because generated code names no
     module; the miniature now leaves out the monitor's generated code with its modules. Why the
     ledger made more of them under `pad1` at the larger count and none more under `period` is
     unread, and is the monitor's cost, which the miniature does not ask (`sim/adversary.py W`).
   - `pad1` and `pad3`, O10 between two of the gate's runs. Done, to be verified by the
     miniature holding O10 under `pad1`, `pad3` and `norun1`: a cutting tool that does not say
     `CUT_BY_A_PART` waits for the clip walk and says so, where it was cut by what the window
     walked and a cut reaching in from a row the window did not walk was missing unsaid.
   - what the audit's finding lists, each a cell of `sim/audit.py` by cuts. Done, to be verified
     by the audit's cells of those acts: a window moved or lengthened with cuts held
     (`cut.first_served`, `cut.cuts_in_time`, the strip handed periods only where they are
     another list); the marks of other code (`Runs.made_under`); the gate's band edited at once
     (`Runs._holding`, the fewer of the runs with a result of the node and the runs near the
     rows); a param edited at once (`plan`'s `cuts_made`, which the graph keeps: a cutting node
     asked the same of the same cuts and results makes the tuple it made, where every sync made
     each cut again and everything known of the tuple by its identity with it). And `nested`'s clip
     walk: each outer cut's gate run held was a sync that made every inner cut again, and a run
     held now syncs only where a cutting node's cuts could be others for it
     (`window._could_cut_anew`, of the plan's `lacking`), which the ruling under "Standing words
     of his" makes the last run alone. Left as it is, his to say otherwise: a param edited at
     once under `nested`, each plan still asking `cut_result` of every outer cut, which
     `sim/adversary.py T` times and the finding holds, and which fewer asks would close only by
     a held answer kept across syncs and let go wherever a run or the window's walk moves. And,
     his to say
     whether they are defects, a reopen's one pass over every cut held and the decoder's packet
     times read on the first walk.
3. The miniature asks what it did not: O11 and O14 of the cutter's own document, which they are
   blind to; O1 as an edited player against a fresh one, with a cutter that changes the frame; O7
   of a param edited; a cutter that raises. Then it holds every oracle under every cutter.
4. `sieve_player/registry/README.md` says what a cutting tool declares and what the player does
   of it, every rule items 1 and 2 leave: adding a tool is to need that file and no other.
5. A seam test of a cutting tool that is not `period`, small, so what the miniature showed
   outlives it: `tests/` holds none.
6. The period spec's box the tree contradicts, the two one-offs that read what is gone, and what
   "Known open, mine" still lists are each settled or carried out of this file to where they bind.
7. The playground goes: this journal and `contract.md` deleted; `sim/` kept as one-offs under
   `docs/findings/experiments/` or deleted, his to say.
8. The branch reaches `v5` as he chooses, whole or the proven fixes first.

Not asked by any of it, and said so: O5, the budget on a weak machine; a tool of unbounded reach
below a cut; a checkpoint deleted or footage replaced before a reopen; periods of a file that
overlap.

Not to be done on this machine: long walks or timing runs for their own sake. He said no stress
testing, and a restart now and then is fine.

## Where things are

- In the player, to be verified in the tree: holders sized from the machine's RAM (`budget.py`);
  the window-against-full test over the registry; display proxies; a frame node's rows held by
  the graph's memo for a session and nowhere after it; the held runs and the window's own runs
  within `budget.py`'s "held", the window's held apart and never written; a bare walk walking the
  clip and its cuts in time and handing back their results; a checkpoint beside the document,
  `<document>.checkpoint`, one append-only file of its held runs and nothing else (`held.py`),
  written at a save where a run was held or the path changed. A tool's code is in no key: a run
  held under older code is served and its node marked (`held.marked`, the window's `_show_stale`).
  A cutting node whose gate no held run answers is cut provisionally of the gate's result as the
  window walked it (`plan.Provisional`, `cut.Record.provisional` and `cut_off`, `Plan.unheld`):
  those cuts are walked by the window lane alone, shown, best effort where cut off at the
  window's edge, and never held, written, baked or handed to a card; the cuts are made again as
  the window's walk hands the gate's result (the window's `_cut_again`).
- Not in the player: the memo, the decode cache, the held runs and cut files are each their own
  holder still; no one ask. Frame, series and stepped results are kept by nothing across sessions
  but the runs the series chain's results are held as.

## His rulings

- On a tool's code in the key: "Mark stale." A result made under older code is found by its key
  and marked; the code is not in the key. A trace on this branch (commit 16e54fe7, not reread
  since) found that such a result is drawn, feeds walks, cuts a `period` and is written to a csv
  whose card reads "on disk: this graph's", the `!` on its card the one mark.
- On the checkpoint: "if the user did a full run and hit save, it opens on that too." It holds the
  held runs, and not a frame node's small rows or the document's form.
- The footage print is v5's, size and the first and last `decoder.SLICE` bytes: sampling between
  them guarded a rare case and moved every key against v5.
- Findings of this branch: `docs/findings/2026-11-21-the-player-died-walking-856-periods.md`,
  `docs/findings/2026-11-21-bare-walk-crashes-on-the-full-file.md`,
  `docs/findings/window-against-full.md`.

## Known open, mine

- Five tools declare a reach without bound and no measurement stands behind it.
- A cut file served to a bare walk, and every key, are named by the footage print: footage
  changed only between its first and last `decoder.SLICE` bytes, at the same size, is taken for
  the one before.
- Whether the mark of other code reaches nodes under a cut in time is unread.
- A gate's band edited moves the cuts below it, and the runs held of the cuts that were stay
  held under keys still good: they serve nothing, are written with the document and count
  against the limit (`docs/findings/2026-11-27-the-nested-gopro-document-edited-against-walked-fresh.md`).
- The registry's types are unchecked for a set of periods as a value, a gate of two inputs, a
  matrix of time by scale.

## His to decide, none blocking

- Whether a csv written from a window's card says it is the window's.
- `docs/spec/a-cut-in-time.md`, the box of a `period` fed a series node's result: while no walk is
  held it "has no periods and says it waits"; the tree gives it provisional periods inside the
  window beside the waiting.
- The encoder's version is in no cut file's key.
- A test in `tests/test_graph.py` asserting wall time failed once and is not marked `simulation`.

## Standing words of his

- A failed check is a defect to find. The processor is a hypothesis, tested against the event
  logs, and never the assumed cause.
- He reopens the player mid-change: a change that orphans held results is said before it lands.
- A run is queued through the orchestrator, whose window he opens on this project.
- SIEVE is to have series tools whose result is set by a value inferred from the whole clip, a
  `period` below cut by it (`docs/spec/todo.md`), and a fix here leaves room for them. What that holds a
  fix to: a cutting node's cuts are of the results it was handed and nothing else, and stand
  while those results do, an edit below moving none (`plan`'s `cuts_made`); a node cut by held
  results alone is cut by all of them or waits, never by a part (`plan._waits`); a sync put off
  or left out is one whose answer could not have moved. His ruling on the
  node the window walked a result of: it is cut by what the window walked alone until every cut
  it reads has a held result, and then by those, never a held one beside the provisional
  (`plan._all_held_or_seen`). A cutting node whose gate, or a node above the gate, reads
  without bound a side is cut by no result of the window's and waits for the walk, the window's
  value of such a tool being another than the clip's (`plan`, where it asks `reach_of_node` of
  the gate). The window's own line of such a node, outside any cut in time, is drawn best
  effort where its rows stop short of the clip's edge on that side and are no clip walk's
  (`window._cut_short`), as `walk.window_legs` says it of one inside a cut. Under another cut a series node runs inside one outer cut at
  a time and never over all of them together.
