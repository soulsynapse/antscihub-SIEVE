---
# ---- identity -------------------------------------------------------------
title: Scrub budget and Preferences        # the TODO item's name, verbatim
date: 2026-07-25                           # YYYY-MM-DD, the day it landed
commit: 4b2431a                            # see "Filling in `commit`" below
tags: [pre-pipeline, gui, budgets]         # free-form; grep handles the rest

summary: >
  One sentence, past tense, saying what the repo can do now that it could not
  before. Not a list of files — that is `files`.

# ---- what moved -----------------------------------------------------------
files:
  added:
    - src/sieve/gui/scrub_policy.py
    - src/sieve/gui/preferences.py
  changed:
    - src/sieve/gui/player.py
    - docs/ARCHITECTURE.md
  removed: []

tests:
  added: 47
  total: 181                               # suite size after the change
  gates: [lint, typecheck, imports, tests]  # nox sessions that passed

# ---- the load-bearing part ------------------------------------------------
# Why the code looks the way it does. This is the section that stops the same
# ground being re-argued in six months. Keep entries to one or two lines; the
# body below is where a decision that needs a paragraph goes.
decisions:
  - what: scrub_to_repaint moved 50 ms -> 100 ms
    why: 46.7 ms of the 67.8 ms round trip is the container seek, and it has no knob

rejected:
  - what: hardware-accelerated decode
    why: does not engage in this OpenCV build; measured, not assumed
  - what: keyframe-aligned seeking
    why: no sawtooth in seek cost across 150 consecutive targets — buys nothing

# Numbers that justified the above. Cheap to record, expensive to re-measure.
# Say what hardware/footage produced them or they are not comparable later.
measurements:
  source: 5312x2988 H.264 @ 59.94 fps, videos-testing/
  results:
    - seek (CAP_PROP_POS_FRAMES): 46.7 ms
    - full scrub round trip: 67.8 ms

# ---- consequences ---------------------------------------------------------
budgets: [scrub_to_repaint, scrub_settle]  # keys in bench/budgets.py touched
contracts: []                              # .importlinter contracts added/changed
docs: [docs/ARCHITECTURE.md]                # prose documents this rewrote

follow_ups:                                # TODO items this created
  - Drag existing boxes
supersedes: []                             # earlier entries this replaces
---

# Scrub budget and Preferences

Body is optional and free-form. Use it for what does not compress into a
frontmatter line: a decision that needed a paragraph, a bug the tests caught
along the way, a naming choice that will look arbitrary later.

Two things belong here specifically, because nothing else in the repo records
them:

**What was checked by mutation.** Which deliberate breakage failed which test.
A test suite that has never been proven to fail is a suite of unknown value,
and this is the only place that proof gets written down.

**What changed outside the item's scope.** The incidental fix, the renamed
method, the guard that turned out to be dead. These are the changes a future
reader finds in the diff and cannot explain from the title.

---

## How to use this file

Copy it to `docs/completed-todo/YYYY.MM.DD-short-name.md`, delete this section
and the example values, fill it in, and delete the corresponding section from
`docs/TODO.md`. One file per completed item, always — a file covering two items
cannot be superseded, cross-referenced, or deleted independently, which is the
whole reason these are atomic.

Every field is optional except `title`, `date`, `commit`, `summary`, and
`files`. Omit a key rather than writing `none` — an absent `rejected:` reads as
"nothing was seriously considered and dropped", which is usually true and
should not cost a line.

### Filling in `commit`

A file cannot contain the hash of the commit that introduces it. The
convention, which costs nothing:

```
# 1. write the entry with `commit: pending`, commit the work
git commit -m "…"

# 2. read the hash back and write it in
git rev-parse --short HEAD

# 3. let the fix ride along with the next commit
```

`commit: pending` in a committed file is therefore normal and self-correcting.
If it is still pending several commits later, `git log --oneline -- <the files
in this entry>` recovers it.

Use a range (`e09b8bf..4b2431a`) when the item genuinely landed across several
commits. Do not invent a squash that did not happen.
