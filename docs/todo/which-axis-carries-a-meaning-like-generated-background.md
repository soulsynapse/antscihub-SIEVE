---
title: A picked file's meaning is the wiring, and the user is the one who states it
phase: 2
priority: normal
status: deferred
deferred_for: subject
gated_on: the-window-grows-a-port-keyed-form-and-the-executor-delays-each-port.md — a node with one input has one place a file can wire to, so there is nothing for the user to say yet
done_when: "uv run pytest tests/unit/test_intents.py -q -k a_picked_file_is_wired_to_a_named_port"
opened: 2026-08-09
---

# A picked file's meaning is the wiring, and the user is the one who states it

Minted the same day claiming two live readings, corrected within the hour when
both turned out to be already ruled, and ruled outright an hour after that. The
sequence is kept because it is the argument for the ADR: a question can read as
open while every part of its answer is already in the tree, if no ruling cites
the question by name.

**The decision is
[adr/a-picked-files-meaning-is-the-port-it-wires-to.md](../adr/a-picked-files-meaning-is-the-port-it-wires-to.md)**
(ADR 31, Kendrick, 2026-08-09), which is where the reasoning lives and what a
session reading the tool contract will find. It succeeds ADR 18 — that one made
choosing among sources a move of an edge, this one says who makes the move — and
it records why neither axis this item was named for can carry the meaning.
Nothing about the ruling is restated here; what remains below is only what this
item still owes.

**Deferred on a subject, not a decision.** The gesture has nothing to operate on
yet: every node in the tree takes one input, so a picked file has exactly one
place it can wire to and asking the user which is asking a question with one
answer. It becomes real with the port-keyed form
([the-window-grows-a-port-keyed-form-and-the-executor-delays-each-port.md](the-window-grows-a-port-keyed-form-and-the-executor-delays-each-port.md)),
where a subtraction has a plate port and a background port and "what does this
wire to" is a question with two answers. `PORT_NAMES` in the referent is already
the surface for it — the mockup names ports only where a step has more than one
input, which is the same condition as this gesture's.

Two constraints on whoever lifts this. The port a user names is a fact about the
graph, so it is on the edge and in the saved file, and it reaches the cache key
the way 11.2's ordered `(port, key)` pairs do — not a second identity beside it.
And the naming is a `SetParam`-shaped intent through the one command layer, not a
special path: an edge the user re-pointed is the same mutation kind as a value
they typed
([one-field-is-one-populated-value.md](../adr/one-field-is-one-populated-value.md)).

`done_when` at minting, red because nothing matches and red for as long as the
gate holds — a deferral on a subject still owes a criterion, and this one names
the gesture rather than the port machinery so it cannot be satisfied by 11.2
alone:

    $ uv run pytest tests/unit/test_intents.py -q -k a_picked_file_is_wired_to_a_named_port
    7 deselected in 0.13s
    exit: 5
