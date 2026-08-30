---
title: step
group: Substrate
position: 9
gloss: The role a tool fills to process frames — an arithmetic over a fixed set of listed positions, run once per position, producing an image-sized field and the scalar it reduces to.
origin: emergent
defined: 2026-08-30
---

The role a tool fills to process frames: an arithmetic over a fixed set of
listed [positions](position.md), run once per position, producing an
image-sized [field](field.md) and the scalar that field reduces to. A step is
the role and never the tool — "the step tools" names what those modules fill,
not what they are. What a step is is fixed by what it may not say: its form
follows the crop it is handed, its timebase and origin are its input's, and its
access belongs to wherever its output is kept, so the [binding](binding.md)
supplies all of it. What it does declare is its reach into the past.

## Where it lives

`contract/nodes.py` holds the constraint. A step declares `Produced` and not
`Edge` — a name, a kind, a dtype. `offsets` is non-positive and contains 0,
checked four ways in `__post_init__`, because a value about a position computed
without that position is a value about a different one and nothing in the tree
trims a tail. Output positions are the input's, one for one.

`Tool.role` holds a `Step` the way it holds a `Source`; `role_kind` answers
which. `session.step_inputs` resolves offsets against the listing; `run_step`
is static and touches no tier, which is what lets `gui/frame/stepwork.py` run
it off the drawing thread. The chain draws every step it has loaded and
evaluates the first.

The ADRs used the word before the class existed: ADR-0005 records a step's
value where its inputs landed, ADR-0006 makes it the thing that declares
offsets, ADR-0007 makes a cost class a property of a step paired with what
feeds it. `lk_flow` and `lag_mhi`, written weeks apart, spell the same pair — a
field drawn and discarded, a reduction offered as the one product.

The verb is ordinary English and left alone: `transport`, `swipe` and `nav`
each have a `step` meaning advance by one, and the local `step` in
`chunks.py`'s pts helpers is a tick distance.
