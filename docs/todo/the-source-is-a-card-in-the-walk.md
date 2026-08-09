---
title: The source is a card in the walk
status: deferred
deferred_for: subject
gated_on: the first source tool landing (the-first-source-tool-moves-the-three-single-root-assumptions.md) — until every input is a node, a source card would be a picture of an edge the graph does not hold
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
