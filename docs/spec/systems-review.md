# Systems review: what SIEVE's own history says it needs, read against how the best programs do each thing

On v5-systems-review, branched from v5. This spec builds one document over several sessions,
`docs/systems-review.md`, and one finding it argues from, the friction ledger. Nothing in the tree
under `sieve_player/`, `tools/` or `utilities/` changes on this branch: the review proposes, and
what is built of it is decided after it is read.

## Why

Modules hold things that are not theirs, and the same small machinery keeps being written again
beside the last copy. Mature programs met each of these needs long ago and settled on a dedicated
system for it, and their answers are public. Reading SIEVE against them says where a system would
have saved work.

It also says, of any small program, that nearly everything is missing. So the review runs from
SIEVE's evidence outward and never from the references inward: what came back in the log and what
the tree wrote twice name the candidates, and only a candidate is read against a reference.

## What this guards against

Each is a way a review of this kind argues for more than its subject needs, and what here stands
against it.

- The references are survivors of hundreds of developers, thousands of users and decades of saved
  files. A system of theirs answers a pressure, and an entry says which and whether SIEVE is under
  it. Part 1 lists the pressures SIEVE is and is not under, once, for every entry to cite.
- A count of the times a system would have helped is a counterfactual made by whoever proposes
  the system. The ledger is written before any system is named, Kendrick strikes and adds classes
  before anything is counted against them, and a count is of commits by hash, told apart as
  prevented or made cheaper.
- Commits follow where building was, not where the design failed. A fix that settles a change of
  the same branch within a day of it is counted apart from one that came back later.
- A second copy is often cheaper than the wrong abstraction, and a tool is one file on purpose. A
  thing written more than once is attrition only where its copies have drifted apart or a fix in
  the ledger had to land in more than one of them.
- A form with a verdict slot fills every slot. Leave alone is a verdict, every entry carries the
  case for it, and the final table is capped.
- SIEVE has one user. What a seasoned user of another program would expect is a list to learn
  from; it scores nothing and makes nothing a candidate. Importance to the user is importance to
  Kendrick's work.
- A system has a price. An entry says what it would take to build, what it replaces, and what
  SIEVE gives up by having it, beside what waiting costs.
- A document written to convince hides what it rests on. This one is written so the reader can
  disagree: every score and verdict stands beside its evidence.

## How to read this

Each `##` from the friction ledger on is a deliverable, sized for one session unless it says
otherwise: an `Assumes:` line, a sentence of why, then done-when assertions, each a box with a
`Check:`. A check here is a reading of the document against the assertion, a one-off by the Tests
section of CLAUDE.md; no test is written for this branch. A box is ticked by a session once the
document meets it; a session never unticks or rewrites an assertion, and before writing toward an
unticked box checks whether the document already meets it. A box that begins `Kendrick:` is his to
tick and no session's: it is a gate, and a deliverable that assumes its deliverable is not
available until it is ticked. Nothing here says how. Any deliverable whose `Assumes:` are all done
is available; among those the earlier one in the file first. The branch is done when every box is
ticked.

Words. A *system* is one named owner of one job, with a data structure and a surface the rest of
the program goes through: an undo stack, a parameter declaration, a cache with a key. A *class* is
a kind of problem the ledger found more than once. *Settling* is a fix to a change of the same
branch within a day of it. *Attrition* is a job done in several places by code written for each
place, whose copies have drifted or were fixed apart. A *candidate* is a system the evidence
argues for or against: one whose absence a class or an attrition traces to, one Kendrick has
named, or one the tree holds that its evidence does not carry. A *reference* is the program whose
system for a candidate's job fits SIEVE's case best.

## What the review reads, and what it does not

- The code under `sieve_player/`, `tools/`, `utilities/` and the launchers, `README.md`, the
  registry's README, `docs/findings/`, and `git log` on every branch are read. `tests/` and every
  other file under `docs/spec/` are not: the specs are scaffolds of builds since finished and many
  are stale, and a seam is read off the imports as they are, not off what a test allows.
- A claim about SIEVE cites `file:name` or a commit's hash. A claim about another program cites
  its documentation or its source, fetched in the session that writes it; one written from memory
  and not fetched says so in the sentence. A reference chosen without a source read is not chosen.
- The reference is chosen per candidate, and the sentence that names it says why it is the best
  fit and not merely a known one. Houdini, Blender, Nuke, Raven, Bonsai, SLEAP, ImageJ and
  VapourSynth are where the search starts, never where it ends: a tracker, an editor, an
  annotation tool, a database or a build system is the reference wherever its system for the job
  is the best one that applies. A program of SIEVE's own size that does the job well outranks a
  large one that does it thoroughly.
- The question asked of each reference, by name, has two halves: what would a senior developer of
  it think, reading SIEVE's code for this job, and what of their own system would they not build
  again at SIEVE's size? Each half is a sentence in the entry.
- The document is short. A claim is made once, an entry fits a screen, and a table carries what is
  enumerable.

## The document

`docs/systems-review.md`, in six parts in this order. They are written in the order of the
deliverables below, which is not theirs.

1. What SIEVE wants to be, and the pressures it is and is not under.
2. What a seasoned user of the neighbouring programs expects to find.
3. The candidates, an entry each, with its reference and a comparison table.
4. The systems SIEVE has, and what each module holds.
5. What was built by attrition.
6. The assessment, and the table of opportunities and frictions.

An entry of part 3 has one form, in this order: the job in a sentence; the evidence, as ledger
classes and places in the tree; the reference, why it is the best fit, and its mechanism, meaning
the data structure, who owns it and what goes through it; the pressure that system answers and
whether SIEVE is under it, by part 1; a table whose rows are the reference, two to four other
programs including one that does the job differently or not at all, and SIEVE last, under columns
chosen for that job; the smallest thing that would answer the evidence, which is seldom the
reference's whole system; what that takes, what it replaces and what SIEVE gives up; the case for
leaving it alone; the verdict, one of build, watch, leave, or for what SIEVE already holds, keep,
shrink; under a watch, what would be seen in the tree or the log that turns it; and the senior
developer's two sentences.

## The friction ledger

Assumes: nothing. Two sessions if the log asks for them.

What came back is the evidence, and it is gathered before any system has a name to be gathered
for.

- [x] `docs/findings/` holds a finding, the ledger, that files each commit of every branch whose
  message tells of a fix, a rework or a second attempt under a class, each class with an id, a
  sentence in the words of the problem and of no remedy, its commits by hash, and the modules its
  fixes landed in.
  Check: three hashes drawn from three classes, read with `git show`, tell of the class they are
  filed under; no class's sentence names a system.
- [x] Each class's commits are told apart as settling or as coming back, and the ledger gives the
  share of all commits that each is.
  Check: both counts are on every class and the shares are at the top.
- [x] Each class says what its commits cost where the log shows it: the span from first to last,
  and the largest single change.
  Check: every class has the line or says the log does not show it.
- [x] The ledger says what it could not see: work that left no commit, and friction Kendrick has
  named in conversation that the log does not show, each entered as his and with his words.
  Check: the section is there and is not empty.
- [ ] Kendrick: the classes are read, the ones not felt as friction are struck, and the ones felt
  and missing are added.

Open: Raven is read as Raven Pro, the Cornell bioacoustics program, whose selection tables and
band-limited detectors are the nearest thing among the eight to SIEVE's band and gate. If another
Raven was meant, the entries that lean on it change.

## What SIEVE wants to be

Assumes: nothing.

Every verdict is a fit to an aim and to the pressures on it, so both are written first and from
the tree.

- [x] Part 1 says, in a page or less, what SIEVE is for, who uses it and on what footage, what a
  session of work with it produces, and what it has declined to be, each read off the README, the
  tools as they stand, the findings and the direction of the log.
  Check: each of the four is there, and each cites what it was read off.
- [x] It lists the pressures a program of this family can be under, each marked as one SIEVE is
  under, is not, or is headed for, with the evidence: users, authors of tools, saved documents
  that must still open, the length of footage, the count of files in a study, who writes the code.
  Check: one table; each row cites the tree, the log or Kendrick.
- [x] It places SIEVE among its neighbours by the three or four choices that most separate them:
  pull or push evaluation, interactive or batch first, frames or tables as the thing on a wire, a
  file or a session as the unit of work. One table.
  Check: the table has a row for SIEVE and one for each program named in the rules.
- [x] It says where SIEVE is headed that the tree does not yet show, marked as direction and not
  as fact.
  Check: the paragraph cites the commit, finding or conversation each direction is read from.
- [ ] Kendrick: part 1 is read and is the premise.

## What the tree holds

Assumes: nothing. Two sessions: the player, then the tools and the utilities.

The other half of the evidence, read off the code before any reference is opened, so that what is
found is what is there and not what a comparison went looking for.

- [ ] Part 4 names the systems the tree has, each with the modules that are it, its lines, and
  what goes through it, and lists for each module what it holds by job.
  Check: every module under `sieve_player/` is in one line or more, and each job cites
  `file:name`.
- [x] It lists what `sieve_player/window.py` holds by job, each with the lines it takes, and marks
  each job as composition, the window's own, or another owner's.
  Check: the lines sum to the file.
- [ ] Part 5 lists each thing the tree writes more than twice, with every place by `file:name`,
  and says of each whether its copies have drifted, whether a ledger fix landed in more than one,
  or neither. Only the first two are attrition; the rest are listed as copies left alone.
  Check: two of the listed things, drawn and read in the tree, are in every place cited and in no
  place uncited; every attrition cites the drift or the hashes.
- [ ] It lists each thing a module holds for another, with the ledger class, if any, that came of
  its lying there.
  Check: each line cites its line of part 4.
- [ ] Over every tool under `tools/`, it counts the lines that build a settings widget against the
  lines that compute.
  Check: the count is in the document with the command that made it.

## The candidates

Assumes: the friction ledger, with its gate; What SIEVE wants to be, with its gate; What the tree
holds.

The list of what is read against a reference is fixed here, from the evidence, and cut by Kendrick
before a session is spent on any of it.

- [ ] Part 3 opens with the candidates, a line each: the job, the classes and attritions that
  trace to it, and their commits as prevented or made cheaper had it been there, by hash.
  Check: no candidate is without evidence; three hashes drawn are filed as the line says.
- [ ] What Kendrick has named as a gap is a candidate on his word, cited as his: running a
  pipeline over pieces of footage is one.
  Check: the line is there.
- [ ] A system the tree holds is a candidate for shrinking where its lines are large beside the
  classes it found or the callers it has; each such line gives both figures.
  Check: the figures are there with the commands that made them.
- [ ] Classes and attritions that trace to no system are listed apart as traced to none.
  Check: every class of the ledger and every attrition of part 5 is in one list or the other.
- [ ] Kendrick: the list is cut to the candidates worth an entry.

## The entries

Assumes: the candidates, with its gate. One session takes one to three candidates; as many
sessions as the cut list asks for.

- [ ] Each candidate left on the list has an entry in part 3, in the form above.
  Check: each entry has every element of the form; each reference's mechanism cites a source
  fetched; each pressure cites its row of part 1.
- [ ] No entry's smallest thing is the reference's system by another name: each says what of the
  reference it leaves out and why SIEVE does not need it.
  Check: the sentence is in every entry with a verdict of build or watch.
- [ ] Part 4's line for each system an entry touches says the verdict.
  Check: the two agree.

## What a seasoned user expects

Assumes: the entries.

Written to learn from, after the candidates are settled, so that it adds none.

- [ ] Part 2 lists what a user arriving from each neighbouring program would reach for in their
  first week, one line a feature: the program it is expected from, the system that delivers it
  there in a clause, and where SIEVE stands, one of has it, an entry of part 3, not yet, out of
  scope.
  Check: every program named in the rules has a line or more; no line carries a score.
- [ ] A not yet says what would be seen in SIEVE's use that makes it a candidate; an out of scope
  cites part 1.
  Check: none is bare.

## The assessment

Assumes: What a seasoned user expects.

- [ ] Part 6 opens with the systems SIEVE has, a line each: what it is, how sound, whether it was
  built as a system or arrived at, and its verdict.
  Check: every system of part 4 has its line.
- [ ] One table lists the entries whose verdict is build or shrink, ten rows at most, sorted, with:
  importance to Kendrick's work out of 10, where 10 is a result he cannot get or work lost and 1
  is unnoticed; importance to the speed and reliability of development out of 10, where 10 is paid
  by every new tool or feature and 1 is cosmetic; the commits it would have prevented and the
  commits it would have made cheaper, coming back and settling apart; what it takes to build,
  against a part of the tree of like size; and what its cost grows with while it waits, the tools
  written, the documents saved, the wires' types, or nothing.
  Check: every count cites its hashes through part 3, and each score has a clause of why.
- [ ] Under it, the watches and the leaves, a line each with the reason, and for a watch what
  turns it.
  Check: every entry of part 3 is in the table or in this list.
- [ ] It closes with an order: what to do first and what to leave, argued from the table in a
  paragraph, with what would have to be true for the first to be the wrong one.
  Check: the paragraph names a first, a leave, and the evidence that would reverse the first.
- [ ] Kendrick: the document is read.

## Not here

Building anything the review argues for; renaming; the specs under `docs/spec/` and whether they
are kept; the tests and whether they are the right ones.
