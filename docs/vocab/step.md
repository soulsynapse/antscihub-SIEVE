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
the role and never the tool — "the step tools" names what those modules are
filling, not what they are. See [node](node.md) for the role a step is one of
and [edge](edge.md) for what it offers.

What a step is is fixed by what it may not say: its form follows the crop it is
handed, its timebase and origin are its input's, and its access belongs to
wherever its output is kept, so the [binding](binding.md) supplies all of it.
What it does declare is its reach into the past.

## Where it lives

`Tool.role` holds a `Step` the way it holds a `Source`, `ROLES` is the table of
both, and `role_kind` answers which one a tool is —
`gui/frame/window.py` collects the step tools with `Tools.of_kind`.

`contract/nodes.py` is where the constraint lives. A step declares `Produced`
and not `Edge` — a name, a kind and a dtype. `offsets` is non-positive and
contains 0, checked four ways in `__post_init__`, because a value about a
position computed without that position is a value about a different one and
nothing in the tree trims a tail. Output positions are the input's, one for
one. `session.step_inputs` resolves offsets against the listing and hands over
`(step, frames, ordinal)`; `run_step` is deliberately static and touches no
tier, which is what lets `gui/frame/stepwork.py` run it off the drawing thread.
The chain draws every step it has loaded and evaluates the first — one card is
doing arithmetic today and the rest are declarations on screen.

Nothing coordinated the word, and the ADRs were using it before the class
existed. ADR-0005 makes a *step* the thing whose value is recorded where its
inputs landed, ADR-0006 makes it the thing that declares offsets, ADR-0007
makes a cost class a property of a step paired with what feeds it, and
`contract/__init__.py` promises "a `nodes.Source` today and a step tomorrow" in
the same slot as the reason nothing subclasses anything.
`experiments/tool-experiments/tools.py` is named for what a step declares about
itself before anything runs it; `experiments/chain-experiments/bind.py` is
named for what it is not allowed to. `lk_flow` and `lag_mhi` were written weeks
apart, and both spell the same pair — a field drawn and discarded, a reduction
offered as the one product.

The verb is the ordinary English one and is left alone: `transport`, `swipe`,
`nav` and `segmented` all have a `step` that means advance by one, and
ADR-0003's "the walked step" is the screen named for what it shows. One noun is
not this word — the local `step` in `chunks.py`'s pts helpers is the tick
distance between two frames, which the rest of the tree measures in rows or
states in ticks and never calls a step.
