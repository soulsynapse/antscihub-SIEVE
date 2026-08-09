---
title: A word has one home
adr: 27
position: "03.06"
status: settled
decided: 2026-08-09
---

An **output** is what the user persists, an **emission** what a spec
declares it can produce, a **result** what a node computes; "product" is
dead, "write" is a verb, "checkpoint" its own noun.

The homes, spelled once: output is `Project.outputs`, the save scene's
list, and the drawn output card; emission is `emits`; result is the
per-frame data the cache holds and a checkpoint writes. A synonym is not a
second word — a checkpoint is a persisted result chosen on
`Project.checkpoints`, never an output, because the two lists persist
different things and neither may reach a cache key.

This binds what is written from now on; it mints no migration and no gate.
A spelling already in the tree is not made wrong by it — a session that
touches one anyway brings it to the ruling in passing, and cites here. What
would widen this into a gate row is the evidence the repo always waits for:
a run that does the wrong thing because the word meant two things to it.

Why: "output" was doing four jobs — a node's per-frame array, a spec's
declared producibles, the user's Sink records, and the GUI card — and the
overload produced a real misparse the day this was ruled: "inherit from
prior tools and outputs," meant as upstream emissions, reads as the canvas
inheriting from the write list. The repo has ruled on words twice before
(`tools-not-filters.md`, `the-product-owns-the-word-tools.md`); this one
differs only in ruling ahead of any enforcement, deliberately, because the
failure count in the tree is zero and a guard is proportionate to that
where machinery is not. VISION's usage is the unmarked one on purpose: it
is the document that gets reread, and its save scene already says
"outputs" for exactly the meaning this ADR frees the word to keep.
