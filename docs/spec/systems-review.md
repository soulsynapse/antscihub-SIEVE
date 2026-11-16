# Systems review: what SIEVE wants to be, the systems that would deliver it, and which of them it has

On v5-systems-review, branched from v5. This spec builds one document over several sessions,
`docs/systems-review.md`, and one finding it argues from, the friction ledger. Nothing in the tree
under `sieve_player/`, `tools/` or `utilities/` changes on this branch: the review proposes, and
what is built of it is decided after it is read.

## The ask

Kendrick's two messages, as he wrote them. Where a line below reads otherwise, these stand.

> lets do a systems review of SIEVE as a whole. I think there are a few things some modules are
> holding that they probably should not be, and there is a lot of opportunity to put dedicated
> systems in place to alieviate things that keep getting reinvented

> Actually, hold on. Lets do this systematically. Open a branch and make a spec for this, for
> reviewing specific things. You should compare architectures to mature software, houdini, blender,
> nuke, raven, bonsai, sleap, imagej, vaporsynth, and other tracking and editing software, and see
> where I'm clearly feeling development friction. You should assess what SIEVE wants to be and what
> systems are likely to be in place, and check if they are or have earned their place yet. You
> should not look at the tests or the other specs during the review, many of the specs are very
> stale and were only used during development. The spec for the systems should have sections with
> checklist deliverables in chunks that can reasonably be investigated. The final deliverable
> should be what sieve wants to be, then a list of what a seasoned user from other platforms would
> expect as features, what the systems in place to deliver these things would be, citing how other
> platforms do it (comparison tables at the end of those will be helpful). You shouldn't just stick
> to a single list of other programs, every time you do a comparison, you should figure out what
> the *best* example of that system is that applies here and include it so I can learn from it.
> Then you should look at the systems that are actually in place for SIEVE, and look at which
> things were built by attrition and a dedicated system or something similar would fit well and
> save future work, rooted in how other reference projects handle what that system does. The spec
> should be built such that it can be done in chunks and the final product should finish with a
> useful assessment of the high level systems present currently, and a list of opportunities and
> frictions with three columns: importance to the user, out of 10, importance to speed and
> reliability of development, out of 10, number of times it would have solved problems for me, and
> one other column of your choosing that you think would be useful. Again the spec will build this
> document over sessions. It shouldn't be overly wordy, it should be written to be convincing and
> clear. A useful heuristic to use is "what would a senior developer of ___ think here?"

## Why

Modules hold things that are not theirs, and the same small machinery keeps being written again
beside the last copy. Both are what a tree looks like when a system was needed before it was named:
each feature paid for its own piece of it. Mature programs in the same family met every one of
these needs years ago and settled on a dedicated system for each, and their answers are public. A
review that reads SIEVE against those answers says which systems SIEVE already has, which it has
in pieces, which it lacks, and which it built ahead of any need.

## How to read this

Each `##` below the rules is a deliverable, sized for one session: an `Assumes:` line, a sentence
of why, then done-when assertions, each a box with a `Check:`. A check here is a reading of the
document against the assertion, a one-off by the Tests section of CLAUDE.md; no test is written
for this branch. A box is ticked by a session once the document meets it; a session never unticks
or rewrites an assertion, and before writing toward an unticked box checks whether the document
already meets it. A `Worth a look:` line says what is worth Kendrick's eye before the next
deliverable leans on it; it is not a gate. Nothing here says how. Any deliverable whose `Assumes:`
are all done is available; among those the earlier one in the file first. The branch is done when
every box is ticked.

Words. A *system* is one named owner of one job, with a data structure and a surface the rest of
the program goes through: an undo stack, a parameter declaration, a cache with a key. A *reference*
is the program whose system for that job fits SIEVE's case best. *Attrition* is a job done in
several places by code written for each place, with no owner. A *friction* is a class of problem
that came back, as the ledger counts it.

## What the review reads, and what it does not

- The code under `sieve_player/`, `tools/`, `utilities/` and the launchers, `README.md`, the
  registry's README, `docs/findings/`, and `git log` on every branch are read. `tests/` and every
  other file under `docs/spec/` are not: the specs are scaffolds of builds since finished and many
  are stale, and a seam is read off the imports as they are, not off what a test allows.
- A claim about SIEVE cites `file:name`. A claim about another program cites its documentation or
  its source, fetched in the session that writes it; one written from memory and not fetched says
  so in the sentence. A reference chosen without a source read is not chosen.
- The reference for a system is chosen per system, and the sentence that names it says why it is
  the best fit and not merely a known one. Houdini, Blender, Nuke, Raven, Bonsai, SLEAP, ImageJ
  and VapourSynth are where the search starts, never where it ends: a tracker, an editor, an
  annotation tool, a database or a build system is the reference wherever its system for the job
  is the best one that applies.
- Each verdict is tested by one question, asked of the reference by name: what would a senior
  developer of it think, reading SIEVE's code for this job? The answer is one sentence in the
  entry.
- A system has earned its place when the tree does its job by hand in three places or more, or
  when ledger entries trace to its absence. One a seasoned user expects and neither holds for is
  written as not yet. The same test runs the other way on what SIEVE has: a system the tree holds
  whose job the ledger and the code's own callers do not show being needed is written as ahead of
  need.
- The document is short. A claim is made once, an entry fits a screen, and a table carries what is
  enumerable. It is written to convince a reader who knows SIEVE and does not know the reference.

## The document

`docs/systems-review.md`, in six parts in this order, each built by the deliverables below:

1. What SIEVE wants to be.
2. What a seasoned user of the neighbouring programs expects to find.
3. The systems that deliver those, each with its reference and a comparison table.
4. The systems SIEVE has, and what each module holds.
5. What was built by attrition.
6. The assessment, and the table of opportunities and frictions.

An entry of part 3 has one form: the job in a sentence; the reference, why it is the best fit, and
its mechanism, meaning the data structure, who owns it and what goes through it; a table whose
rows are the reference, two to four other programs including one that does it differently or not
at all, and SIEVE last, under columns chosen for that job; where the job is done in SIEVE; the
verdict, one of dedicated, by attrition, absent and earned, absent and not yet, ahead of need; and
the senior developer's sentence.

## The friction ledger

Assumes: nothing.

The count of times a system would have helped is evidence or it is a guess, and the evidence is
in the commit messages, which say what each change fixed and why.

- [ ] `docs/findings/` holds a finding, the ledger, that groups the commits of every branch whose
  message tells of a fix, a rework or a second attempt into classes of problem, each class with an
  id, a sentence, its commits by hash and its count.
  Check: three hashes drawn from three classes, read with `git show`, tell of the class they are
  filed under.
- [ ] A class says where its fixes landed, by module, so a class whose fixes span several modules
  is told from one that kept coming back in the same place.
  Check: every class has the line.
- [ ] The ledger says what it could not see: work that left no commit, and what Kendrick has named
  as friction in conversation that the log does not show.
  Check: the section is there and is not empty.

Worth a look: the classes, before anything is scored against them. A class Kendrick does not
recognise as friction, or one he feels and the ledger lacks, changes every count below.

Open: Raven is read as Raven Pro, the Cornell bioacoustics program, whose selection tables and
band-limited detectors are the nearest thing among the eight to SIEVE's band and gate. If another
Raven was meant, the entries that lean on it change.

## What SIEVE wants to be

Assumes: nothing.

Every later verdict is a fit to an aim, so the aim is written first and written from the tree.

- [ ] Part 1 says, in a page or less, what SIEVE is for, who uses it and on what footage, what a
  session of work with it produces, and what it has declined to be, each read off the README, the
  tools as they stand, the findings and the direction of the log.
  Check: each of the four is there, and each cites what it was read off.
- [ ] It places SIEVE among its neighbours by the three or four choices that most separate them:
  pull or push evaluation, interactive or batch first, frames or tables as the thing on a wire, a
  file or a session as the unit of work. One table.
  Check: the table has a row for SIEVE and one for each program named in the rules.
- [ ] It says where SIEVE is headed that the tree does not yet show, marked as direction and not
  as fact.
  Check: the paragraph cites the commit, finding or conversation each direction is read from.

Worth a look: all of part 1. It is the premise.

## What a seasoned user expects

Assumes: What SIEVE wants to be.

A system is owed to a feature somebody expects; the list of features is what bounds the list of
systems.

- [ ] Part 2 lists what a user arriving from each neighbouring program would reach for in their
  first week, one line a feature, each with the program it is expected from and whether SIEVE has
  it, has part of it, or has none.
  Check: every program named in the rules has at least one line, and no line is a system.
- [ ] The features SIEVE's aim puts out of scope are listed apart, a clause each for why.
  Check: the list is there and each line cites part 1.
- [ ] Each feature names the system or systems of part 3 that would deliver it, so the list of
  systems the later deliverables write up is fixed here, each filed under one of the groups below.
  Check: no feature is without a system and no system is in two groups.

## Systems of the editing core

Assumes: What a seasoned user expects; the friction ledger.

The document, its nodes' parameters and every change made to them: what is saved, how a saved form
of an older shape is read, how a parameter is declared and what is derived from the declaration,
and whether a change can be taken back.

- [ ] Part 3 has an entry, in the form above, for each system of this group.
  Check: each entry has every element of the form, and each reference's mechanism cites a source.
- [ ] Part 4 says, for each module that does a job of this group, what it holds, and of that what
  is another system's.
  Check: each line cites `file:name`.
- [ ] Each verdict of earned, by attrition or ahead of need cites the ledger classes or the places
  in the tree it rests on.
  Check: none is bare.

## Systems of evaluation

Assumes: as the editing core.

What decides which node runs for which row, under what key, on which thread, held where and for
how long, and how a run that no longer matters is stopped.

- [ ] As the three boxes of the editing core, for this group.
  Check: as theirs.

## Systems of footage

Assumes: as the editing core.

Decoding, the row and its time, seeking, the frame cache, the files cut from a video and the store
they lie in.

- [ ] As the three boxes of the editing core, for this group.
  Check: as theirs.

## Systems of results

Assumes: as the editing core.

What a wire carries that is not a frame: signals, tables, tracks, intervals; how each is typed,
held between sessions, stamped with what made it, and written out.

- [ ] As the three boxes of the editing core, for this group.
  Check: as theirs.

## Systems of the tool surface

Assumes: as the editing core.

How a tool is found, what it declares, what it is handed, what tools share, and how its settings
come to be on screen.

- [ ] As the three boxes of the editing core, for this group.
  Check: as theirs.
- [ ] The entry on settings counts, over every tool under `tools/`, the lines that build a widget
  against the lines that compute, and names what a declaration would have derived.
  Check: the count is in the document with the command that made it.

## Systems of the shell

Assumes: as the editing core.

The window and what it composes: commands, keys and menus, selection, the viewer with its overlays
and picks, the canvas, the plot and timeline, the look, and where the player's own state is kept.

- [ ] As the three boxes of the editing core, for this group.
  Check: as theirs.
- [ ] Part 4 lists what `sieve_player/window.py` holds by job, each job with the lines it takes.
  Check: the lines sum to the file, within what is plainly composition.

## Systems of observation

Assumes: as the editing core.

What says what the player did and why: the stream, the ledger and catalogue over it, the monitor,
the log, a node's standing, an error's path to the user.

- [ ] As the three boxes of the editing core, for this group.
  Check: as theirs.
- [ ] The entry weighs the lines this group takes in the tree against the ledger classes it found
  or would have found, and says which parts that weighing carries and which it does not.
  Check: the lines and the classes are both cited.

## Systems of the run

Assumes: as the editing core.

Work with no window: a document run over a whole file, over many files, over pieces of one, and
what brings the results back.

- [ ] As the three boxes of the editing core, for this group.
  Check: as theirs.

## What was built by attrition

Assumes: every group above.

The groups read down each job; this reads across them, for the machinery that is nobody's job and
so is in every module.

- [ ] Part 5 lists each thing the tree writes more than twice, a sentence for what it is, every
  place by `file:name`, and the system of part 3 that would own it, or a new entry there if none
  does.
  Check: two of the listed things, drawn and read in the tree, are in every place cited and in no
  place uncited.
- [ ] It lists each thing a module holds for another, drawn from part 4, with where it would lie.
  Check: each line cites its line of part 4.

## The assessment

Assumes: What was built by attrition.

- [ ] Part 6 opens with the systems SIEVE has, a line each: what it is, how sound, and whether it
  was built as a system or arrived at.
  Check: every dedicated and ahead-of-need verdict of part 3 has its line.
- [ ] One table lists every opportunity and friction, a row each, sorted, with: importance to the
  user out of 10, where 10 is work lost or a user leaving and 1 is unnoticed; importance to the
  speed and reliability of development out of 10, where 10 is paid by every new tool or feature
  and 1 is cosmetic; the times it would have solved a problem, the count of the ledger classes it
  answers, cited; and what its cost grows with while it waits, the tools written, the documents
  saved, the wires' types, or nothing.
  Check: no count is without its classes, and each score has a clause of why in the row or under
  the table.
- [ ] It closes with an order: what to do first and what to leave, argued from the table in a
  paragraph, and what it would take to be wrong about the first.
  Check: the paragraph names a first, a not yet, and the evidence that would reverse the first.

Worth a look: the whole document.

## Not here

Building any system the review argues for; renaming; the specs under `docs/spec/` and whether they
are kept; the tests and whether they are the right ones.
