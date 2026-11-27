# What an adversary proved against the plan to finish the one-store branch

Assumption throughout: the plan is completed exactly as written, so the miniature prints "holds"
for O7 to O11 and O14 under period, pad1, pad3 and nested, the rulings are made, the playground is
gone. Each finding below survives that.

Reproduction. Everything ran in a detached scratch worktree of ed8c4fd3, offscreen, one thread, by
`docs/playground/sim/adversary.py` (experiments named A, B, C, Dm, E, F, R, V, H, H2, called exp in what
follows) and one more cutter, `docs/playground/sim/cutters/gainpad.py`. Run from the tree:
`MINIATURE_CUTTER=period .venv/Scripts/python.exe -X utf8 docs/playground/sim/adversary.py A B Dm`.
It execs the miniature's own text up to its `failed = False` line, so the player, the turns and
`holds`/`apart` are the miniature's. It has not been run from where it now lies. No crash occurred in
any run; nothing was rerun for flakiness. Written by an adversary told to assume the plan done and
prove what would still make him think of the back end; finding 4's cause was reread by the
session that asked, gainpad declaring no key_params.

## Proven, ranked by what each costs him

1. The mark of other code never reaches a node below a cut in time. His ruling is "Mark stale";
   O14 is its oracle. Under a `period`, after a clip walk, with `reduce`'s code said changed
   (exp Dm): `marked: {'gate': True, 'below': False, 'smooth': False}` while `runs held of below
   under its key: 40`. Under nested: `{'gate': True, 'gate2': False, 'below': False, 'smooth': False}`.
   Cause: `window._show_held` hands `_show_stale` `self._chain()` (window.py:1414, 1432), which is
   `g.chain`, the untimed chain (window.py:1503); `held.marked` looks only at results of that chain's
   nodes (held.py:435-436). Every node whose walk is a `timed` one is outside it. The journal lists
   this as "unread" under Known open and Done-when does not carry it. Cost: he edits a tool's code,
   which is his daily work, and every result below a period is served, drawn and cuts further
   periods with no mark at all. Silent staleness, goal 2.

2. O11 and O14 are blind to the cutter, so item 1's "holds O7 to O11 and O14 under period, pad1,
   pad3 and nested" is the same check four times for two of the six. Both use `tables_home`'s
   document, gray, threshold, detect, size (miniature.py:286-293, 316, 360); MINIATURE_CUTTER never
   reaches it. That is why O14 prints "holds" under all four while finding 1 stands. O11 asked of
   the cutter's own document does hold (exp E: period `held 81; the copy serves 81 before a turn,
   apart 0 ... gray ran at 0 rows besides the playhead's`; nested the same with 121), so that half
   is only unpinned, not broken.

3. A cutting tool that raises in `cut_extents`, or a CUT_BY cutter without PATHS whose gate is
   unwired, passes the whole footage through and nothing says so. `pad` with no gate wire (exp B):
   `cutn: fed=True cuts=1 first=[None] standing=''`, `below: fed=True ... standing='' line_rows=300`,
   and a clip walk holds `[(None, 0, 320)]`: one run over every row as if no cutter were there.
   Unwiring the gate after a clip walk gives the same state, the 40 cuts gone, no standing.
   `period` in the same position says `'neither periods nor gate is wired'`, but only because it
   has PATHS: the refusal is `by and gate is None and not filed and paths(tool)` (plan.py:323).
   Otherwise `made[nid]` is preset to what the node reads (plan.py:316) and the tool's ValueError,
   whose text here is "no gate; wire a series node into gate", is swallowed (plan.py:340-341).
   Goal 2, and goal 1: the author of a cutter must know that raising means "cut nothing, silently".
   The plan's four cutters never unwire a gate and never raise.

4. A cut in time enters no key below it, so a cutter whose `run` is not the identity serves stale
   and wrong results. `gainpad` multiplies the frame by `gain` and cuts by a gate (exp A). After a
   clip walk at gain 1, gain set to 0 through `_params_changed`: `below key moved=False`, held
   below still 200.0, the line drawn after the edit `[200.0, 200.0, 200.0, 200.0]`; a fresh player
   at gain 0 holds 0.0 under the same key, and `edited player differs from fresh at 40 of 41 held
   results`. Cause: `read_key` skips every node `in_time_alone` (plan.py:254-267), stated only in
   plan's docstring (plan.py:188), not in registry/README.md. This is O1 failing; the journal says
   O1 "reads on as a claim nothing checks" and Done-when leaves it so. The same key for two values
   means a checkpoint carried to a colleague would serve them too; that step I infer and did not run.
   Goal 1: a rule about keys the README does not give. pad1, pad3 and nested all have identity `run`.

5. What one edit costs the window's own thread grows with the cuts held, and O7 does not ask it.
   O7 counts a clip walk and a window moved. With 100 and 400 cuts held, no worker turn taken
   (exp H2): `edit below the cuts: 63426 steps ... 193926 with 400: 3.06x`; the same edit again
   `68915 ... 220123: 3.19x`; `band edit on the gate: 15974 ... 34874: 2.18x`. Most steps at 400:
   `cut.py:reading 34488, cut.py:read 21044, held.py:_serving 19282, held.py:walked_rows 14000`,
   which is `_show_held` with `moved=None` asking `held_periods` of every cut (heldwalks.py:60-69).
   Each tick of a dragged param pays it. With turns taken the edit below re-walks every cut at a
   flat 21000 steps a cut (exp H: 2142914 and 8771409, 4.09x), which is work owed, not growth.
   Held up in the same run: a scrub is 580 steps at both counts.

6. Item 4 removes the instrument item 1 rests on. After it the miniature is "a one-off under
   docs/findings/experiments/ or deleted"; `tests/` mentions CUT_BY in one file (tests/test_cut.py)
   and no cutter but `period`. Nothing run by `pytest -q` would then hold O8 to O10 for a cutter
   that is not `period`, which is the thing the branch says it tested. CLAUDE.md's own line is that
   tests hold "what a later change elsewhere could break without anyone looking".

7. Mis-specified or mis-ordered items.
   - Item 1's fourth bullet waits on item 2's ruling, so item 1 cannot be finished before item 2;
     the order is inverted. Confirmed still failing: pad1 `below draws 0 of its 1 rows of periods`,
     pad3 `0 of its 3`, exit 1.
   - Item 1's second bullet has no bound ("Not an oracle yet; the miniature counts it first"): no
     count it could print would fail it.
   - Item 2's second option, "a window says best effort wherever a cutter may read past it", with
     no declared reach marks every provisional cut of every cutter, `period` included, since the
     player cannot tell which reads past; the first option adds a facet a tool author must learn.
     Either is a rule for goal 1 and neither names the README as where it is said.
   - Done-when names no check of goal 1 itself. O4 ("adding a tool changes no file of the store, the
     walk or the monitor") is listed as unchecked and stays so; findings 3 and 4 are what it would
     have caught. O5, the memory budget on a weak machine, likewise.
   - "Known open, mine" (five tools of unbounded reach unmeasured, footage told by size and two
     slices, the mark under a cut) is in no Done-when item; finding 1 is one of them and is a defect.

8. Claims about the tree that are false or loose.
   - "No module of sieve_player names a tool that cuts": `document.py:25` has
     `CUT_TOOL, REGION_TOOL = "crop2", "region"`. And the standing every cutter's readers get says
     "walked over each of N periods alone" (plan.py:421); under `pad` it read `40 periods` (exp B).
   - The miniature's docstring and the journal's "says which of O7 to O11 and O14 hold" under a
     cutter: for O11 and O14 it does not, finding 2.

## Tried and held up

- A gate fed a `tracks` result (exp C): `track`'s result carries `signal` and `gate`; the period is
  provisional, then cut, with standings said at each stage.
- Three cuts in time, each under the last (exp F): the miniature's O8, O9 and O10 all hold.
- `region` above a `period` and below one, params set, no clip served (exp R): O8, O9, O10 hold.
- Values drawn before a clip walk and not marked best effort, compared with what the clip walk then
  holds, over five windows (exp V): 0 of 72 differ under period and nested, 0 of 94 under pad1 and
  pad3. O10 itself compares rows and flags only, never a value (miniature.py:233-257), so this is
  unpinned rather than broken.
- `period` with its gate unwired says so and feeds nothing below (exp B).
- A stepped tool below a nested cut is the miniature's own `reduce` and `smooth`; nothing new found.
- The miniature's print matches the journal for the O8 to O14 half: period and nested exit 0, pad1
  and pad3 fail O10 only at "between two of the gate's runs".

## Unproven

- That finding 4's wrong result travels in a checkpoint: inferred from the equal keys, not run.
- A tool of unbounded reach below a cut, reopening with the checkpoint deleted, footage replaced
  at the same size, overlapping periods from a file, a served region clip beside a period: not tried.
- The O7 pass at 200/800 was not run; the journal's nested and pad1 O7 figures are unchecked by me.
- Whether finding 5's steps are felt: 220000 line steps a tick at 400 cuts is a count, not a time.
