---
# ---- identity -------------------------------------------------------------
title: The seek is irreducible            # what was learned, not what was done
date: 2026-07-25                          # the day it was measured
status: closed                            # closed | open | superseded
commit: 4b2431a                           # the commit that acted on it, or omit
tags: [decode, scrub, opencv]

# The one-line answer. This is the field the index table shows, so it has to
# stand alone: a reader who sees only this row should know whether to open the
# file. State the result, not the topic — "the seek is ~70% of the cost and has
# no knob", not "investigated seek cost".
verdict: >
  set(POS_FRAMES) is 46.7 ms of a 67.8 ms round trip and has no tunable knob;
  hardware acceleration does not engage and keyframe alignment buys nothing.

question: >
  Which of the escape hatches from the previous scrub measurement actually
  exists — hardware decode, skipping colour conversion, keyframe-only seeking?

# ---- how it was measured --------------------------------------------------
# Without this a number is not comparable to a later one, which makes it
# useless for the only thing findings are for: noticing a change.
source:
  footage: videos-testing/stab_GX010050c2_02_18_26.MP4
  format: 5312x2988 H.264 59.94 fps, 30579 frames
  build: OpenCV 4.13, Python 3.11, opencv-python-headless
  machine: reference workstation                # be specific enough to re-run

measurements:
  - probe: set(POS_FRAMES) alone, random far target
    result: 46.7 ms median (min 29, max 202)
  - probe: retrieve() (YUV -> BGR)
    result: 21.1 ms
  - probe: VIDEO_ACCELERATION_ANY
    result: backend reports HW_ACCELERATION = 0.0; timing unchanged

# ---- what it changed ------------------------------------------------------
consequences:
  - scrub_to_repaint moved 50 ms -> 100 ms, met by degrading rather than by decoding faster
  - added gui/scrub_policy.py and gui/frame_cache.py

closed:                                   # hypotheses this measurement killed
  - what: hardware-accelerated decode
    why: does not engage in this build
  - what: keyframe-aligned seeking
    why: no sawtooth across 150 consecutive targets — cost is 43-124 ms, aperiodic

open_questions:                           # what this deliberately did not settle
  - a sparse pre-decoded thumbnail track would make the first pass cheap too;
    blocked on where a project file lives

budgets: [scrub_to_repaint, scrub_settle]
files: [src/sieve/gui/scrub_policy.py, src/sieve/gui/player.py]
supersedes: []                            # earlier findings this overturns
---

# The seek is irreducible

Body is free-form. Use it for the reasoning a table cannot carry: why a probe
was designed the way it was, why a negative result is trustworthy, what a
number would have to look like for the conclusion to flip.

The sawtooth probe is the model. "No sawtooth across 150 consecutive targets"
is only meaningful if the reader knows a sawtooth is what
seek-to-keyframe-then-decode-forward *would* produce. Write that down — a
negative result with no stated prediction is indistinguishable from not having
looked.

---

## How to use this file

Copy to `docs/findings/YYYY.MM.DD-short-name.md`, delete this section and the
example values, fill it in. One file per finding. Then run:

```
uv run nox -s docs
```

which rewrites `.index.md` from the frontmatter of every file in this folder.
Do not edit `.index.md` by hand — `tests/docs/test_doc_index.py` fails when it
is stale, which is the same discipline `test_budget_table.py` applies to
`ARCHITECTURE.md`.

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

### Findings vs. completed-todo

A `completed-todo` entry says *what was built*. A finding says *what is true
about the system*, and outlives the code that prompted it. When a measurement
justified a decision, it belongs here and the completed-todo entry links to it
rather than restating the numbers.
