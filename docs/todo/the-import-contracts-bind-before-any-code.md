---
title: The import contracts bind before any code
step: "00.2"
status: open
gated_on: nothing
done_when: "uv run lint-imports"
opened: 2026-08-06
---

# The import contracts bind before any code

`.importlinter` adapted from v2, not copied: layers with `sieve.tools` and no
`detect` or `backend` layer; `core-purity` and `opencv-containment` (tools the
named exception) verbatim in intent; `headless` minus its detect entry;
`gui-computes-nothing` with an empty exception list and
`unmatched_ignore_imports_alerting = error`. Read v2's `.importlinter` for the
rationale comments above each contract — they are part of what ports.

Two placements v2 cannot answer: `compat` is `sieve.pipeline`'s sibling in
the layers list (`sieve.pipeline | sieve.compat` — neither may import the
other: the importer emits a schema-v1 artifact and hands it off, the executor
never learns v2 existed) and joins the `headless` source list, since a
cluster node must import a v2 project. `mutual` gets no layer line until
Phase 5 decides whether it ports.

Beyond `done_when`: a deliberate violation committed on a scratch branch must
turn each contract red. That proof is the item's real content; a contract that
has never failed is a contract nobody has tested.
