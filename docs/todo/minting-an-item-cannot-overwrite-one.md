---
title: Minting an item cannot overwrite one
priority: high
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/docs/test_doc_index.py -q"
opened: 2026-08-07
---

# Minting an item cannot overwrite one

A session mints an item by writing a slug, and 01.4's run wrote a slug an
existing tracked item already held — the body was replaced wholesale and
nothing went red, because the index is rebuilt from whatever files exist
(`findings/loop/2026.08.07-minting-an-item-is-a-write-to-a-slug-and-a-collision-deletes-the-item-it-hits.md`).
The repo's memory of noticed work has exactly one copy, and a collision
deletes it silently.

The check belongs where the index is built, since that is what every session
runs: `doc_index.py` fails when a tracked item's file is gone or when its
`opened` date moves backwards under an unchanged slug, and there is a
`--mint <slug>` that refuses an existing name outright. Refusing at mint time
is the one that fixes the class — a session that has to ask for a name
cannot take one by accident.

This is the same shape as the ADR identity rule already enforced here: `adr:`
is minted once and never reused, and `collect_adrs` raises when two files
claim one number. Items got the ordering half of that discipline and not the
identity half.

**Two things for the review, because one session did both roles here.** The
criterion above was written by the session that then met it, which is the
independence the open -> awaiting-review -> done protocol exists to keep, so
it is worth re-deriving rather than re-running.

And the text above says `opened` "moves backwards", which is the wrong
direction: a mint over an occupied slug stamps *today*, so the date it writes
goes forward, and a check reading only backwards would miss the accident the
finding recorded. What landed refuses a move either way, on the grounds that
`opened` is written once and never edited, so any move is the same evidence.
If the original wording meant something this reading loses, that is the thing
to say no to.
