---
title: A gap is a position, and the box fills it
step: "09.9"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k 'add_box or splices'"
opened: 2026-08-09
---

# A gap is a position, and the box fills it

ADD STEP on the project card — and `A` on the pipeline — opens a box in the
chain: card-shaped, card-numbered, dashed on the edges it would be spliced
onto, holding what could stand in the gap it is in. ↑/↓ move it through the
gaps and the offer rewrites with it, ←/→ walk the offer, enter takes one, esc
closes having written nothing. MOCKUP-MAP.md row "Adding a step";
`_AddBox`, `_add_box`, `Control.add_here` and `_ChainColumn.hold_box` in the
referent, and
[adr/a-position-is-asked-for-in-the-chain.md](../adr/a-position-is-asked-for-in-the-chain.md)
is why it stands in the chain rather than in a popup.

**The box never writes on opening.** It is a picker: one mutation is issued
when an offer is taken, and esc is free because there was nothing to undo.
That is what makes the same widget safe to open over a card in
[09.10](swap-opens-the-same-box-and-keeps-the-node.md), and it is a property
of this item, not of that one.

This is the surface `AddNode` arrives with — PLAN Phase 7's command list has
"AddNode and RemoveNode arriving with the surfaces that emit them", and 09.4
brought the other half. The splice is `without_node` run backwards and wants
its counterpart on `Pipeline`/`Project`: the new node reads what the gap's step
emits, and whatever read past the gap now reads the new node. `RemoveNode`'s
read-past closes a chain over a step; this opens one, and the two being exact
inverses is the check that the semantics are right rather than merely
symmetrical-looking.

The offer is `offered_tools` (`core/tool_registry.py`), which is built and
tested — the surface renders a shortlist it is handed and computes nothing
(`gui-computes-nothing`,
[adr/gui-knows-kinds-not-tools.md](../adr/gui-knows-kinds-not-tools.md)). Two
things about it are this item's to face rather than that function's:

- **The empty offer is the first case, not an edge.** `matches` is true at 0 of
  10 positions for eight of the ten tools on the shelf today
  ([findings/2026.08.09-the-shelf-declares-too-little-for-eight-of-ten-positions-to-offer-anything.md](../findings/2026.08.09-the-shelf-declares-too-little-for-eight-of-ten-positions-to-offer-anything.md)),
  so the box under `crop` is empty and crop is the first tool in every
  pipeline. The referent cannot draw this — its sample shelf always has
  entries — so what an empty box says, and whether it opens at all, is decided
  here and is the case to write a test for first.
- **The offer is asked of a gap, which holds no tool.** `offered_tools` takes
  the upstream's `emits` and the folded element meaning, neither of which is a
  fact about the tool standing at the position, so nothing new is needed —
  but the call site is a position rather than a node, and naming it that way
  is what keeps 09.10 from growing a second predicate.

One thing the referent gets wrong for the tree, and a worker reading it will
copy: the mockup models the output as a node, so "the gap under the output is
not a position" falls out of the node list. In the tree the output card is
drawn and not modeled
([adr/the-output-card-is-a-picture-of-the-write-list.md](../adr/the-output-card-is-a-picture-of-the-write-list.md)),
so the last gap is under the last real node and the refusal has nothing to
refuse. The rule that survives the difference is that a gap exists between two
positions the chain has; the referent's extra card is a mock artifact.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k 'add_box or splices'
    181 deselected in 0.69s
    exit: 5
