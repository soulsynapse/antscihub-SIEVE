# The shape of an ADR

An ADR names one problem and says what solves it. It does not argue; the
title carries the decision and an experiment carries the proof, so a reader
who wants the reasoning opens the experiment rather than reading a case made
for them here.

Two states, and the title says which one an ADR is in.

**Unsettled.** `[problem] is solved by TBD`. Something has to be decided and
nothing has earned it yet. The file lists what might.

**Accepted.** `[problem] is solved with [prior art]'s [solution]`. An
experiment in this tree ran and the candidate survived it. The prior art is
named because borrowing a solved thing is the point — an ADR that says only
what this tree does, with no shoulders under it, is either an invention worth
being suspicious of or a citation somebody did not look for.

**The prior art is a named artifact, never a category.** "The container's
timestamp" and "a buffer pool's refcount" are descriptions of a family; what
goes in a title and a citation is the specific thing somebody built, with the
symbol, paper, or field you could go and open — `AVStream.time_base`,
`FFTW_MEASURE` and its wisdom file, `arInitial` / `arAllFramesReady`. A family
name cannot be checked, cannot be read for what else it decided, and hides
whether the writer found one instance or none.

An unsettled ADR becomes accepted by one edit: the candidate that won moves up,
the title is rewritten to name it, the filename follows the title. **The
number never changes**, because ADR-0013 is a permanent address for its
problem and stays so through every answer the problem gets.

## The file

```markdown
---
title: <the title, verbatim>
group: <shelf name — see docs/ADR.md's preamble>
position: <order along that shelf>
status: unsettled | settled
decided: <YYYY-MM-DD>
---

<One sentence stating the decision, or the problem an unsettled ADR has not
settled. This paragraph is quoted into docs/ADR.md, so it comes first and
carries no heading above it.>

## Accepted

<Accepted only.> [prior art]'s [solution] — <link to the experiment and to
any finding it produced>.

## Candidates

<Unsettled only.> [prior art]'s [solution] — <one line on what it would buy, and
what would have to be measured to accept it>.

## Rejected

[alternative] cautionary tale: <what goes wrong, and where that was seen —
an experiment in this tree that killed it, or the record of the system it
happened to>.
```

`scripts/doc_index.py` regenerates `docs/ADR.md` from the staged tree at
commit, and it quotes each ADR's first paragraph. So the decision sentence is
the first thing in the body and nothing precedes it — a heading in that
position becomes the index entry. `status` sends an ADR to one section of
that index or the other, tallied apart, so an unsettled ADR is never counted
as agreed; how the two sections read is `SHELVES` in that script.

`README.md` carries no front matter and so is placed on no shelf, which is
what keeps it off the index it describes.

## The three sections

**Accepted** holds exactly one entry and only in the accepted state, and that
entry says what settled it. Normally that is a link to an experiment in this
tree; a solution with no experiment behind it is a candidate however obvious
it looks, and moving it up without one is the failure this shape exists to
prevent — a later reader takes an untested guess for a decision somebody made.
The exception is a decision settled by adopting a solved thing where the
evidence is the alternatives' own record rather than a measurement here, and
that line says so in as many words, so nobody reads a citation as a result.

**Candidates** holds the solutions in the running, one line each, in the same
`[prior art]'s [solution]` grammar the title will use. More than one is the
normal case and is what makes the open state worth writing down: it says
somebody looked, and it says where to start. A candidates list is also the
brief for the experiment that will settle it.

**Rejected** holds what is out and why, in one grammar:
`[alternative] cautionary tale: [problems]`. Two things end up here and the
line says which: a candidate an experiment in this tree killed, which links
that experiment, and an alternative rejected on another system's record,
which names the system. Both are worth keeping — the second is usually why
the candidate list looks the way it does, and deleting it leaves the next
reader to rediscover a failure somebody already paid for.

Nothing leaves an ADR. A rejected candidate stays rejected in writing so the
same idea does not arrive again with no memory attached to it.

## What an ADR is not

Not a finding. A finding records a measurement — what, on what, and when — so
a later one supersedes it rather than argues with it. An ADR records what the
tree does about a measurement, cites the finding, and never restates its
numbers: a number copied into a decision is wrong the moment the measurement
moves and nothing goes red for it.

Not a place to explain the experiment. The link is the explanation. If the
experiment's own README does not make its result legible, that is a defect in
the experiment.

Not minted unprompted. Suggest one; the decision to have a decision is not
the writer's.
