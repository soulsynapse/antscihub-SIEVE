---
# ---- identity -------------------------------------------------------------
title: The seek is irreducible            # what was learned, not what was done
date: 2026-07-25                          # the day it was measured
status: closed                            # closed | open | superseded
commit: "4b2431a"                         # the commit that acted on it, or omit
tags: [decode, scrub]

# The one-line answer. This is the field the index table shows, so it has to
# stand alone: a reader who sees only this row should know whether to open the
# file. State the result, not the topic — "the seek is ~70% of the cost and has
# no knob", not "investigated seek cost".
verdict: >
  set(POS_FRAMES) is 46.7 ms of a 67.8 ms round trip and has no tunable knob.

question: >
  What was this measurement designed to decide?

# ---- how it was measured --------------------------------------------------
# Without this a number is not comparable to a later one, which makes it
# useless for the only thing findings are for: noticing a change.
source:
  footage: which file, format, frame count
  build: library versions that touch the number
  machine: specific enough to re-run

measurements:
  - probe: what was run
    result: what came back, with spread when it matters

# ---- what it changed ------------------------------------------------------
consequences:
  - what moved in the code or the plan because of this

closed:                                   # hypotheses this measurement killed
  - what: the alternative that was live before this
    why: the observation that killed it

open_questions:                           # what this deliberately did not settle
  - the follow-on, and what it is blocked on

files: []
supersedes: []                            # earlier findings this overturns
---

# The title again, as a heading

Body is free-form. Use it for the reasoning a table cannot carry: why a probe
was designed the way it was, why a negative result is trustworthy, what a
number would have to look like for the conclusion to flip.

A negative result with no stated prediction is indistinguishable from not
having looked — write down what the refuted mechanism *would* have produced.

---

## How to use this file

Copy to `docs/findings/YYYY.MM.DD-short-name.md` (or `findings/loop/` for a
truth about how the work loop fails rather than about the system), delete this
section and the example values, fill it in. One file per finding. Then run
`uv run python scripts/doc_index.py`; do not edit `.index.md` by hand —
`tests/docs/test_doc_index.py` fails when it is stale.

Required: `title`, `date`, `status`, `verdict`. Everything else is optional,
but `source` is close to mandatory in practice — a measurement whose hardware,
footage, and build are unrecorded cannot be compared to the next one, and
comparison is the entire reason to keep it.

### `status`

- `closed` — the question is settled and the code reflects it
- `open` — measured, but the consequence has not been acted on yet
- `superseded` — a later finding overturned it; name it in the later file's
  `supersedes` and leave this one in place. Findings are a record of what was
  believed and why, so deleting a wrong one destroys the reason the code took
  the shape it did.

### Findings vs. work items

A `docs/todo/` item says *what should be built* and, once done, what was. A
finding says *what is true about the system*, and outlives the code that
prompted it. When a measurement justified a decision, it belongs here and the
item links to it rather than restating the numbers.
