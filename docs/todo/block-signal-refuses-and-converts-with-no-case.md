---
title: block_signal's refusal, its color path, and its auto label have no case
priority: normal
phase: 8
status: open
gated_on: nothing
opened: 2026-08-07
---

# block_signal's refusal, its color path, and its auto label have no case

Three branches of `tools/block_signal.py` are reached by nothing in
`tests/unit/test_block_signal.py`, and all three were already uncovered in v2's
file the port carried over — so this is a gap the porting discipline required
rather than one it introduced.

| Unreached | What it costs |
|---|---|
| the `prev.shape != gray.shape` raise | the declared refusal; deleting the branch leaves the grid mismatched and `_block_mean` reshaping garbage rather than a named error |
| `_to_gray`'s BGR/RGB branch | every case feeds `ChannelSpec.GRAY`, so the BT.601 projection that keeps this node's series on `normalize`'s scale is asserted nowhere — 04.3's review found the same blind spot in `normalize` and named it |
| `presentation_values`' `auto (N)` | the label a spinner shows for `block=0`; the only reader of `resolve_block(0, scale)` outside the kernel |

The first is `adr/declared-means-verified.md` on a docstring's `Raises:`. The
second is the one with a wrong-numbers failure rather than a missing-message
one: a color path that projected with the wrong weights would produce a block
series every downstream band was tuned against a different signal for.

Not folded into 04.4 because that item is one job and its criterion is the
ported file plus parity; these are cases v2 never wrote, which makes them a
decision about coverage rather than part of the port.
