---
title: Whether a verbatim port stays verbatim after its review, since nothing checks it
status: deferred
deferred_for: decision
gated_on: Kendrick deciding whether "verbatim" is a claim about a port's arrival that lapses on the next commit, or a property of the file that a gate holds — and if the second, which files carry it and what an intended edit does to the row
priority: normal
phase: "00"
opened: 2026-08-07
---

# Whether a verbatim port stays verbatim after its review

`core/types.py` stopped equalling v2's blob at 02.1, for a docstring naming two
schema fields schema v1 had deleted, and nothing went red
([findings/loop/2026.08.07-the-copy-verbatim-anchor-stopped-being-verbatim-two-commits-after-it-landed.md](../findings/loop/2026.08.07-the-copy-verbatim-anchor-stopped-being-verbatim-two-commits-after-it-landed.md)).
That edit was right. What it cost is that two todo items spent weeks deferring
to "the copy-verbatim anchor" as a live constraint, and by then it was a
description of a state that had ended.

`a-frame-count-does-not-enforce-its-own-int.md` settled the terms for its own
subject — verbatim is a rule about how a port lands, not a freeze afterwards —
and that ruling is what the anchor's remaining consumers spend. It does not
answer this: whether the *claim* should be checkable at all, for any of the
files PLAN.md calls verbatim.

The evidence that it could be is `tests/unit/test_tool_id_spelling.py`. ADR-1's
rename is the other property a port was supposed to carry by discipline plus
review, it did not, and a gate reading the tree rather than the diff found six
survivors on its first run
([findings/loop/2026.08.07-a-verbatim-port-carries-the-buried-vocabulary-past-review.md](../findings/loop/2026.08.07-a-verbatim-port-carries-the-buried-vocabulary-past-review.md)).
The check here is cheaper than that one — `git rev-parse` on both sides of a
table of paths, which 01.1's review already ran by hand and wrote into the item.

What makes it a decision rather than an afternoon is the second half. A blob
gate goes red on the *intended* edit too, so the table needs a way to say "this
file left verbatim on purpose, here is the item that spent it" — and that row is
either a second home for the ruling or the only home for it. Three shapes:

- The table pins the hash and an intended edit updates it, citing the item. The
  gate becomes the record of which ports are still recoverable from v2 and which
  are not, which is the fact `docs/V2-MAP.md` exists to answer.
- The table pins membership only: a file leaves the verbatim list by an explicit
  deletion, and the deletion is the visible widening the way the spelling gate's
  empty exception list is.
- Nothing is pinned, and PLAN.md's porting discipline says outright that
  verbatim is spent at the port — which costs nothing to write and makes every
  later item that wants to cite the anchor read the sentence that says it
  cannot.

Not urgent while the remaining verbatim ports are unlanded (`decode/` at Phase
3, `bench/` at Phase 6), and worth deciding before they are, since the third
shape is free only until somebody relies on the second again.
