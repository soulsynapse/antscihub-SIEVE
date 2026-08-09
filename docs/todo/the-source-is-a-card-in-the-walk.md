---
title: The source is a card in the walk
status: open
gated_on: nothing
priority: high
phase: "9"
done_when: "uv run pytest tests/gui -q -k source_card"
opened: 2026-08-09
---

# The source is a card in the walk

The video the chain reads is chosen on the first card of the stack — a stage
of one, never removable, its chooser listing the project's sources with
browsing *appending* rather than replacing — instead of on a screen before
the pipeline or a strip above it. MOCKUP-MAP.md row "Source is a step";
`_source_chooser`, `_browse_for_source` and the `STAGES` comment in the
referent; VISION's first scenario ("the project names no video of its own,
and every input including this one is a tool"). Deferred on the subject, not
a decision: ADR-18 already rules that a user's file enters as a source tool,
and four Phase 3/5 items wait on the same landing. When it lifts, this card
is the GUI half of what they build — the chooser's value is the source
node's param, entering through the ordinary command path.

The append-on-browse behaviour is in the map's settled table but was never
explicitly Kendrick's; the session that builds this confirms it in review
rather than treating the map row as licence.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/gui -q -k source_card
    119 deselected in 0.68s
    exit: 5

## 2026-08-09: the gate lifted

`44b6456` landed `pick`, so a project can hold an input that is a node and a
source card is a picture of something the graph carries. `gui/param_form.py`
already builds a `PATH` field as the value the document holds, which is the
placeholder this card replaces with a chooser. `status` and `gated_on` moved on
that; the work below is unchanged, including the append-on-browse row that is
still Kendrick's to confirm in review.
