---
title: Both axes for "generated background" are closed, so the question is whether VISION's sentence survives
phase: 2
priority: normal
status: deferred
deferred_for: decision
gated_on: Kendrick ruling on VISION's "select what type of output it should broadcast as" — a residual capability, or a sentence describing the swap
opened: 2026-08-09
---

# Both axes are closed, so the question is whether VISION's sentence survives

Minted the same day claiming two live readings, and corrected within the hour:
both were already ruled, by two rulings this item had not read together.

**A fourth `ElementKind` member is closed.**
[adr/an-outputs-kind-is-the-picture-it-makes.md](../adr/an-outputs-kind-is-the-picture-it-makes.md)
(settled 2026-08-09) says "no member is ever added for a tool", and that a
picture a tool wants shown over the footage is a `DisplaySurface` member and a
revision of that ADR, "never a fourth `ElementKind`". Its reason is the one the
source-tool item had already argued and could not settle alone: `ElementKind`
answers what a node's output *is*, and a scene description is not an answer to
that question.

**Emission-name keying is refused where it was going to be spent.** The
2026-08-09 ruling on
[the-offering-predicate-is-not-the-edge-legality-check.md](the-offering-predicate-is-not-the-edge-legality-check.md)
reads "no plausibility field, no new `ElementKind` member, no Emission-name
keying", and answers positively instead: the offer is derived from what the
position's input resolved to. That is scoped to the offer rather than to every
consumer, but the offer was one of the three scenarios the axis was said to
block, and the ruling's closing clause governs the rest — new vocabulary is
admitted only when a real offer proves inexpressible in the resolved facts.

So what is left is not a choice between two mechanisms. It is whether VISION's
sentence still describes a capability at all: "they do that and select what type
of output it should broadcast as. As soon as they select generated background,
the background subtraction step picks it up and displays it." Read against
[adr/a-users-file-wires-in-like-any-other-input.md](../adr/a-users-file-wires-in-like-any-other-input.md)
— a picked file is a node, so choosing among sources is moving an edge — and
against the substitution-not-comparison ruling in
[whether-vision-states-the-background-ab.md](whether-vision-states-the-background-ab.md),
the sentence may already be satisfied by the swap: the file means "background"
because of which position it was wired into, and there is nothing left to select.
The reading against that is that derivation genuinely cannot tell a background
PNG from a mask PNG — both resolve to one `PIXEL` file of the same extension
class — so if the user is ever to say which it is, an edge is the only place the
answer currently lives, and a graph where two source nodes feed one step has two
edges and no labels on them until Phase 11's ports exist.

That is the residual, and it is Kendrick's for the same reason the A/B was: it is
a VISION edit either way — the sentence stays and gains a mechanism, or it comes
out because the swap already does its work. What it is **not** is a blocker for
Phase 11. 11.3's subtraction knows which input is the background from the port it
arrives on, and ports are settled.

`pick.py` is stale on this and the fix rides with whichever way it goes: its
docstring and its spec comment both tell the reader the axis is open, written at
07:39 on 2026-08-09, eight hours before ADR 29 closed half of it.

No `done_when`, because what a command would assert is the thing being decided.
