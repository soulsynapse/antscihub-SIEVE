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
both turned out to be ruled, and ruled outright an hour after that. The sequence
is worth keeping because the answer is not either of the things the question
offered.

**Neither axis carries it.** A fourth `ElementKind` member is closed by
[adr/an-outputs-kind-is-the-picture-it-makes.md](../adr/an-outputs-kind-is-the-picture-it-makes.md)
— "no member is ever added for a tool" — on the reasoning that `ElementKind`
answers what a node's output *is*, and a scene description is not an answer to
that. Emission-name keying is refused by the 2026-08-09 ruling on
[the-offering-predicate-is-not-the-edge-legality-check.md](the-offering-predicate-is-not-the-edge-legality-check.md),
which answers by derivation: the offer is computed from what the position's
input resolved to.

**Ruled 2026-08-09 (Kendrick): the meaning is the wiring, and the user states
it.** VISION's "select what type of output it should broadcast as" survives, and
what it describes is neither a declaration on the spec nor a derivation — it is
the user saying what their file wires to. A file the user brought is precisely
the case where nothing can be derived: a background and a mask resolve
identically, one `PIXEL` file of the same extension class, so there is no fact in
hand to compute an answer from. Derivation is how candidates are *offered*, and
an offer is a suggestion; a file from outside the project is the case where the
system has no basis to suggest and the user has to be able to say. So the answer
is asked for rather than inferred, and where it lands is the edge.

That is consistent with everything already settled rather than a new axis beside
them:
[adr/a-users-file-wires-in-like-any-other-input.md](../adr/a-users-file-wires-in-like-any-other-input.md)
already says choosing among sources is moving an edge, and the
substitution-not-comparison ruling in
[whether-vision-states-the-background-ab.md](whether-vision-states-the-background-ab.md)
already says one background is live at a time. What this adds is that the move is
the user's to make explicitly, by name, rather than something a swap performs
silently on their behalf.

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
