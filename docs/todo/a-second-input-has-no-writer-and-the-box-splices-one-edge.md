---
title: A merge has no way into a document — the box splices one edge and nothing writes a second
status: deferred
deferred_for: subject
gated_on: the-window-grows-a-port-keyed-form-and-the-executor-delays-each-port.md — until `Pipeline` accepts two edges into one node there is no second edge for a surface to write
priority: normal
phase: "11"
done_when: "uv run pytest tests/gui/test_add_box.py -q -k 'a_merge_is_offered_only_where_both_its_ports_can_be_fed or taking_a_merge_wires_both_of_its_ports'"
opened: 2026-08-10
---

# A merge has no way into a document

11.2 makes a fan-in expressible, 11.3 lands the tool that wants one, and
[a-fan-in-has-no-picture-and-no-rule-for-which-parent-holds-it.md](a-fan-in-has-no-picture-and-no-rule-for-which-parent-holds-it.md)
draws it. None of the three lets a user make one. Every `AddNode` in the tree
issues from `take_offer` on the add box (09.9), the box fills a *gap*, and a gap
is one producer: `Pipeline.with_node_after` writes exactly one inbound edge — the
gap's step — and rewires what read past it. Splice a subtraction into a gap and
it arrives holding a plate and nothing else, with no second gesture to reach for
and no ruling saying what the document is in the meantime.

**Nothing refuses the half-wired node, and nothing accepts it either.**
`Pipeline._referential_integrity` checks that edges name real nodes and (until
11.2) that no node is fed twice; it has never checked that a node's declared
inputs are all fed, because no tool declared two. Downstream, the four
`(parent,) = fed` unpacks 11.2 retires would meet an empty set, so today's
answer to a merge with one port wired is a `ValueError` out of a tuple unpack in
`dag.py`. Whether a half-wired merge is a legal document — a state the user is
legitimately halfway through, drawn with a dangling arrowhead, refused at that
node by the executor while the rest of the chain still previews — or a state the
writer never produces because the offer never opened, is the first thing this
item rules. The tuning loop is why it matters rather than being a taste
question: a document that cannot be saved mid-edit is a document the user cannot
leave, and a document that saves in a state the executor unpacks a `ValueError`
out of is one they cannot reopen.

**The offer is the other end of the same ruling.** `offered_tools(produced:
StreamSpec, element, shelf)` narrows the shelf by matching one flowing stream
against `accepts`; 11.2 retires `accepts`'s single form and the signature above
follows it, but what the *offer* should then mean is nobody's yet. Two readings,
and they are not the same product: a merge appears in any gap whose stream feeds
one of its ports, and taking it opens a second question about where the other
port comes from; or a merge is not a thing a gap offers at all, because a gap
names one producer and the box's whole contract is that taking an offer is one
mutation and esc is free (09.9). The second keeps the box's property and needs
the wiring gesture to exist first; the first breaks it, because a box that opens
a follow-up has written something esc must undo. Preferring the second is what
this item's `done_when` is written for — `offered_only_where_both_its_ports_can_be_fed`
is that reading — and a session that argues the first changes the criterion at
review rather than around it.

**The gesture lands here.**
[choosing-among-sources-is-a-move-no-intent-kind-makes.md](choosing-among-sources-is-a-move-no-intent-kind-makes.md)
owes the mutation and the eighth intent kind and explicitly leaves the surface to
"the fan-in item or whatever else first needs one" — the fan-in item draws a
picture and touches no input handling, so this is the whatever-else. One surface
for both writes, because the layer is keyed by the mutation and not by the widget
(`session/intents.py`): re-pointing an existing edge and completing an unfed port
are a move and an add of the same thing, and a second gesture for the second one
would be the bespoke path ADR 18 collapsed.

**There is nothing to copy, and that is the ruling to bring to Kendrick.** The
referent authors its fan-in as a literal — `INPUTS[6] = (4, 5)` beside `NODES`,
with a comment saying which steps a step reads is the graph's to say — and its
one edge-writing gesture is the output card's tick list, which ADR 25 ruled is
view state over `Project.outputs` and not a graph edge at all
([the-output-is-a-step-and-its-ticks-are-edges.md](the-output-is-a-step-and-its-ticks-are-edges.md)).
So the mockup holds no picture of a user wiring anything, and every candidate —
a drag from a card's edge to another card, a producer chooser on the unfed port's
label, the add box growing a second position to ask for — is a design decision
made here for the first time. It is Kendrick's, proposed before it is built.

`done_when` at minting, red because nothing matches — and red for as long as the
gate holds, since a merge is a tool no shelf can carry until 11.3:

    $ uv run pytest tests/gui/test_add_box.py -q -k 'a_merge_is_offered_only_where_both_its_ports_can_be_fed or taking_a_merge_wires_both_of_its_ports'
    12 deselected in 0.13s
    exit: 5
