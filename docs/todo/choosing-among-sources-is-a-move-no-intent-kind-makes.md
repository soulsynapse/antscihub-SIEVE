---
title: Choosing among sources is a move of an edge, and nothing in the tree moves one
status: open
gated_on: nothing
priority: normal
phase: "07"
done_when: "uv run pytest tests/unit/test_intents.py -q -k a_consumer_is_repointed_to_another_source"
opened: 2026-08-10
---

# Choosing among sources is a move of an edge, and nothing moves one

[adr/a-users-file-wires-in-like-any-other-input.md](../adr/a-users-file-wires-in-like-any-other-input.md)
rests its collapse of the two bespoke substitution paths on one sentence:
"adding a file is adding a node, choosing among sources is moving an edge, and
the command layer needs no intent kind it does not already have." The first
clause is `AddNode`. The second is nothing: `Pipeline` gains edges only through
`with_node_after` and loses them only through `without_node`, `Project` has no
edge mutation at all, and the seven kinds in `session/intents.py` splice, drop,
retool, set one param, set the outputs, and add or drop a replicate. A document
whose graph is to read a different producer cannot be written by any path a
front end is allowed to take.

The reading that would save the sentence — a remove and an add — is the one
`RetoolNode`'s own docstring refuses, for a reason that transfers unchanged: the
pair mints a new `node_id`, and `node_id` is what names the artifact on disk,
what the checkpoints and the sinks hold, and what `bench/` addresses. Re-pointing
a consumer must leave both endpoints where they are.

**The subject is here now, and it is not the merge.** A re-point needs two
candidate *producers*, not two ports, so this does not wait on
[11.2](the-window-grows-a-port-keyed-form-and-the-executor-delays-each-port.md).
`pick` landed, so a document can already hold a source tool beside the chain, and
VISION's background scenario — a background made outside the project standing
where a generated one stood — is one edge moving from the `background_ema` node
to that source, between two nodes that each emit once into a consumer that reads
once. Which *port* receives a picked file is the deferred question and stays with
[which-axis-carries-a-meaning-like-generated-background.md](which-axis-carries-a-meaning-like-generated-background.md);
which node it arrives from is deferred on nothing.

What it owes is the mutation and the kind: an edge move on `Pipeline`, whatever
`Project` needs over it, and the eighth kind. `INTENT_KINDS` notices the arrival
by construction and `KIND_NAMES` in `test_intents.py` goes red for it, which is
the claim `60f99fa` left standing — an eighth kind is a claim about what a
layout owes. One kind, not one per surface: the layer is keyed by the mutation
and not by the widget that emitted it (`session/intents.py`), so a chooser on the
source card, ADR 31's picker and any later drag are the same write.

**If the kind is needed, ADR 18's sentence stops being true, and that is a
succession rather than an edit** ([CLAUDE.md](../../CLAUDE.md)). Settle which it
is before building: either the move is expressible with what exists — in which
case say how, here, and this item is prose — or it is not, and the ADR's claim is
corrected where ADRs are corrected. A new kind landing quietly beside a settled
decision that says it was unnecessary is the state this item exists to prevent.

Two things it does not decide. Not the gesture: the referent draws its fan-in as
fixed geometry (`INPUTS`, `PORT_NAMES` in `mockup/mockup.py`) and its source
chooser is a combo writing a param, so the mockup holds no picture of a user
moving an edge and there is nothing to copy — the surface arrives with
[a-fan-in-has-no-picture-and-no-rule-for-which-parent-holds-it.md](a-fan-in-has-no-picture-and-no-rule-for-which-parent-holds-it.md)
or with whatever else first needs one. And not a third refusal: a re-point can
draw a cycle, and `Pipeline` refuses self-loops while `Dag` refuses cycles at
execution — the intent raises through one of those two rather than growing a
legality check beside them.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/unit/test_intents.py -q -k a_consumer_is_repointed_to_another_source
    12 deselected in 0.14s
    exit: 5
