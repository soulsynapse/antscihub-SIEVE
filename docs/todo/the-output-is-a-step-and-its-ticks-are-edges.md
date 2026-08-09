---
title: The output is a step, and its ticks are edges
step: "09.2"
status: done
gated_on: nothing
done_when: "uv run pytest tests -q -k ticks_are_edges && uv run pytest tests/gui -q -k names_do_not_collide"
opened: 2026-08-09
---

# The output is a step, and its ticks are edges

What leaves the chain is a card at the foot of it, not a screen beside it:
the write list is the output step's param, ticking a product makes the step
that emits it an input of the output node — derived, so the picture cannot
disagree with the writes — the edges into the card are labeled by product,
and Run sits on the output's form. The save screen dissolves into it; its
pane was one step's form, so it is that step's form. MOCKUP-MAP.md row
"Output is a step" — `WRITES`, `refresh_output_inputs`, `_write_list`,
`_port_name`'s output branch and `_run_row` in the referent; VISION's
`output-1` guidance paragraph carries the argument. The map's review also
bounds it: the `into` folder and format combo on the referent's form are
*not* settled — the settled part is the shape. This spans layers by design —
an output tool on the shelf, the tick-to-edge derivation beside the graph,
the GUI rendering both — and the ticked list is what 07.9's checkoff becomes,
entering as the output node's param through the ordinary command path.

One edge per ticked product means this is the step where a node first has more
than one input, so it is the step that spends the extension ADR-2 anticipated:
`window` grows the port-keyed form [VISION.md](../VISION.md)'s scene calls for,
in the contract and the executor, not improvised tool-side by whatever tool
happens to be first to want two upstreams. That is also the event that gives
[a-merge-keys-its-inputs-by-port.md](a-merge-keys-its-inputs-by-port.md) the
subject it is deferred for — `a - b` versus `b - a` becomes crossable the
moment two labeled edges land on one node — so the run that builds this should
expect that item to come off its gate behind it, and should not reach the same
shape by a private route that leaves the deferral standing.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests -q -k ticks_are_edges
    1000 deselected in 0.93s
    exit: 5

## 2026-08-09 (review): the one-input posture is hardened at five sites, not one

Folded in rather than minted, because it is the same work this item already
owns. "The contract and the executor" is where the port-keyed form goes, but
the shape it replaces is not a default that a wider one quietly supersedes —
it is a refusal, installed deliberately and in five places.
`Pipeline._check` raises `two edges feed {node}` before any of the rest sees a
graph (`core/pipeline_model.py`); `Dag.node_keys`, `Dag._elements` and
`Dag._element_names` each unpack `(parent,) = fed` (`pipeline/dag.py`), and
`executor.py` does the same. `dag.py`'s own header cites the `Pipeline`
refusal as the reason it may assume one, and the last three of those unpacks
were *put there* by
[a-nodes-inputs-are-labeled-and-variadic.md](a-nodes-inputs-are-labeled-and-variadic.md),
now `done`, on the argument that silently keying on the first of two is the
failure being prevented. So the first ticked second product is a raise at
graph-construction time, well before anything can draw it, and unwinding the
five is inside this step rather than discovered by it. What replaces each is
the port-keyed read, not a drop of the check: the invariant that survives is
that an unlabeled second edge is still refused.

## 2026-08-09 (work): the output node is a shape the contract has no word for

Read before picking this up again: the run that measured this did not build,
and what stopped it is not size.

Every other clause here has a home in the tree already. `Edge` grows a port and
`Pipeline` keys its refusal on `(downstream, port)`; the five one-input sites
unwind against that; `window` grows the port-keyed form, which
[adr/no-kernel-apparatus.md](../adr/no-kernel-apparatus.md) names in advance as
"a contract-plus-executor change" and therefore licenses. The output *node* is
the clause with nothing behind it. It consumes one stream per ticked product
and emits none, and `ToolSpec` has no way to say that: `emits` is required and
typed, `_edge_faults` reads it, `Dag.elements` folds it, `ArraySpec.matches`
offers on it, and `executor._unrunnable_reason` refuses a spec that emits rows
because "a run returns a frame". A node that returns nothing is a member of the
declarable shape space that no ADR admits and this item does not rule on —
`adr/declared-means-verified.md` and the repo's ADR succession both put that
ruling ahead of the commit that spends it, not inside it.

The item is also not separable ahead of that ruling, which is worth stating
because the obvious split is the one that is closed.
[a-nodes-inputs-are-labeled-and-variadic.md](a-nodes-inputs-are-labeled-and-variadic.md)
argues that the schema may not grow a port field before a tool has ports — "the
distinction-nothing-can-make that `Edge` refuses" — so ports cannot land first.
And the five folds cannot unwind first either: what `_elements` reads once a
node has two upstreams is the merge semantics
[a-merge-keys-its-inputs-by-port.md](a-merge-keys-its-inputs-by-port.md) is
deferred on, and the only thing that dissolves the question is a node with no
element meaning to fold — the sink again. Every route in runs through the one
declaration nobody has made.

So the order is: rule on the sink shape, then this item builds in one piece —
ports, the five sites, the tool, the tick-to-edge derivation — with the GUI half
(the card at the foot of the stack, Run on its form, `gui/save_screen.py`
dissolving into it) a second job behind it. `done_when` is untouched and still
covers the whole; nothing here narrows it.

## 2026-08-09 (review): the gate is in the frontmatter now, and the fork is wider than the sink

The work run's reading holds — I re-ran `done_when` on its commit and got the
same red, and every citation above checks out against the tree. What it left in
prose is the field the loop actually reads: it concluded the item cannot be
taken until a ruling exists and then left `status: open`, `gated_on: nothing`,
so `--next` handed 09.2 straight back and the next work run would have stalled
at the same sentence. That is
[findings/loop/2026.08.07-an-item-states-its-gate-in-prose-and-ungated-in-frontmatter-so-the-selector-runs-it-first.md](../findings/loop/2026.08.07-an-item-states-its-gate-in-prose-and-ungated-in-frontmatter-so-the-selector-runs-it-first.md)
a second time, from the other end — there the gate was derived at minting, here
at the first attempt to build. This review sets `deferred_for: decision`.

The ruling is also wider than "does `ToolSpec` admit a sink". Writing already
happens in this tree, and it happens *outside the graph*:
`storage/checkpoint_writer.py` writes `<node>.<emission>.npy` and a manifest,
called by the run rather than declared on the shelf, and `tools/checkpoint.py`
is only the read side of it — a source tool, wired in by
[adr/a-users-file-wires-in-like-any-other-input.md](../adr/a-users-file-wires-in-like-any-other-input.md).
So the fork Kendrick is owed is not only what a sink may declare but whether
writing is a node at all: MOCKUP-MAP's "Output is a step" row presumes it is,
and the only writer the tree has says it is not. Answering the narrow question
without that one would admit a shape into the contract that the existing writer
did not need.

## 2026-08-09 (review): the arrowhead's port name is now this item's, in the picture as well as the form

Folded in rather than minted, because it is the same clause this item already
owns from the other end. 09.7 built the chain's edges and closed
([the-outputs-reach-down-behind-the-cards.md](the-outputs-reach-down-behind-the-cards.md))
with one clause of its body unbuilt: *a port is named at the arrowhead only
where the destination has more than one input.* Nothing in the tree produces a
name for a port — `Edge` has no port field and `Pipeline._check` refuses the
second inbound edge — so an implementation would have invented both the fan-in
and the word beside it. This item is where the two arrive together: "the edges
into the card are labeled by product" is that name, and it has to be drawn at
the arrowhead in `gui/chain_stack.py`'s painter, not only listed on the output
form. The painter's seams for it are `arrowhead` and `ChainColumn._paint_edge`,
both module-level or public for that reason.

`done_when` is unchanged. The reviewer that closes this should check that
`-k ticks_are_edges` reaches the drawn label and not only the derivation — a
case that asserts the tick-to-edge mapping and never renders the stack would
leave the picture's half of this clause exactly as unheld as it is today.

## Ruled 2026-08-09 (Kendrick): the output card is drawn, not modeled

[adr/the-output-card-is-a-picture-of-the-write-list.md](../adr/the-output-card-is-a-picture-of-the-write-list.md)
answers both widths of the fork the reviews above opened: no sink node
enters the contract, and writing is not a node at all — the card is the
GUI's picture of `Project.outputs`, its edges derived from the ticks as view
state, consistent with the one writer the tree already has. The deferral
lifts on that ruling, which is why the frontmatter reads open again.

What this closes inside the item: the port-keyed `window` extension, the
five one-input sites, and the fan-in do **not** ride this step — no schema
node gains a second input from a tick, so the paragraph above expecting
[a-merge-keys-its-inputs-by-port.md](a-merge-keys-its-inputs-by-port.md) to
come off its gate behind this work no longer holds; that item stays deferred
on a genuinely multi-input tool. What remains is the GUI half plus the
derivation: the card at the foot of the stack over `Project.outputs`, ticks
becoming drawn edges with the product name at the arrowhead
(`chain_stack.py`'s painter, per the review above), Run on its form,
`gui/save_screen.py` dissolving into it. `done_when` still covers exactly
that; the sentences it no longer covers are the ones the ADR removed from
scope rather than left undone.

## 2026-08-09 (work): the card is drawn, the ticks are its edges, and Run is on its form

Built to the ruling's scope and no wider. `gui/save_screen.kept_products` derives
what the run keeps from the document — `Project.checkpoints` and
`Project.outputs` together, each named by the product that node's own parameters
select, so the name on an edge moves when the knob does. `chain_stack.Outputs`
carries those to the pane as positions, which is `Step.reads`' form; the card
lands at the foot of the stack as a card of `ChainColumn` and not of the walk,
because the walk stands only where a node is. `ChainColumn` grows the labels the
09.7 review handed over: `port_labels` is the derivation, `port_label_origin`
the placement, and `_paint_edge` writes the name beside the arrowhead — only
where the destination has more than one input, which in this stack is the output
card and nothing else.

The tick redraws the picture rather than updating it: `SaveScreen.checked` says
a box moved and `app._outputs` derives the edges again from the document, so
there is no second copy of the write list to go stale. No cache key moves and the
graph is untouched — the pane's `Outputs` never reaches `session/`.

The save pane is that card's form: the card's arrow opens it, `save_screen.py`'s
header now says so, and Run is where it already was. What was *not* done is
folding the fourth position of the track away — `control.py` argues at length
(07.11, from VISION) for save being a position rather than a dialog, the
referent's three-position row is about a mockup with no save screen at all, and
neither this item nor ADR 25 rules on the track. So the form is reachable both
from the card and from the end of the walk, which is the same pane either way.

One thing measured that outlives the item is folded into
[a-checkpoint-does-not-record-which-product-it-holds.md](a-checkpoint-does-not-record-which-product-it-holds.md):
the card draws both of the document's write lists and the form ticks only one of
them, so a sink draws an edge no box is ticked for.

## 2026-08-09 (review): the names are painted, and painted over each other

The derivation holds and is proved rather than asserted. Six mutants over the two
files the work landed in were all killed by `-k ticks_are_edges` alone: reading
`checkpoints` without `outputs`, returning the emission's bare name instead of the
tool's label, dropping `checked.emit()`, widening the name rule to `fan_in > 0`,
deleting the `drawText`, and collapsing `port_label_origin` onto the arrowhead.
So the 09.7 handover's condition is met — the criterion reaches the drawn label
and not only the mapping, and the pixel assertion is what kills the `drawText`
mutant.

What it does not reach is the two names *together*, and that is where the clause
fails. Both edges into the card land on its top edge, so `port_label_origin`
gives both labels the same baseline, and the origins are one lane apart while the
names are several lanes wide. Measured on the same fixture the tests use
(`cropped` and `downsampled`, into a 420-wide pane): baseline y 145 for both,
origins at x 34 and x 68, advances 132 and 84, so the two run to x 166 and x 152
and the shorter name is painted through the middle of the longer one. `EDGE_LANE`
is 34; no product name in the tree is that narrow. The one case the whole clause
exists for — more than one input, so the arrowheads need naming — is the case
that renders unreadable.

The tests pass over it because both look at one lane: `_ink` is asserted in a
14-pixel window at one origin, and the absence assertion sits in the three pixels
between an arrowhead's shoulder and its own label. Neither window is anywhere the
neighbouring name's glyphs land. That is the `_NAME_WINDOW` comment's own
reasoning applied one step short — it bounds the window so the *neighbouring
arrowhead* is not read as this name, having established that the neighbour is
close enough to be confused for it, and the neighbour's *name* is closer still.

`done_when` gains a second command rather than a widened `-k`, for
[the reason 09.5.1's review gives](the-library-mints-a-project-and-the-selected-card-opens-its-folder.md):
a disjunction is green for whatever it names and does not have. The new leg is
`-k names_do_not_collide`, red today at exit 5. What it has to hold is that two
named arrowheads on one card produce two readable names — the placement rule is
the work run's to choose (stagger the baselines by lane, right-align each name
into the gap its own lane owns, elide against the next lane's origin), and this
review does not pick one. The rest of the item stands as built; the status goes
back to `open` for this clause and nothing else.

## 2026-08-09 (work): the second name is a second line, and the gap opens for it

Of the three placements the review offered, the two horizontal ones both spend
the lane pitch, and the lane pitch is the measurement that fails: right-aligning
into 34px or eliding against the next origin leaves three or four characters of a
product name, which is a different way of being unreadable rather than an answer
to it. So the names are staggered — `port_label_origin` takes a `lift`, and
`ChainColumn._lifts` gives each named edge a rank among the card's names, ordered
by lane, times the font's own `lineSpacing`. Two names over one card are set the
way any two lines of text are, which is why no constant of this module's was
minted for the gap between them. Outer lanes ride higher, so the names read
top-to-bottom in the order their cards do.

Neither name has room to rise into on its own: the layout's gap is one line tall,
the column paints its edges before its children, and a name lifted past the card
above is drawn under it — which is the same as not being drawn, and is the second
collision the criterion now names. `ChainColumn.label_headroom` is what the pane
reserves for it, so the gap over the output card is opened by exactly as much as
the stacking spends. `label_rect` is the box a name occupies, and it is the
instrument the criterion reads: the boxes are asserted disjoint, each wider than
`EDGE_LANE` (a box narrower than the pitch would clear its neighbour by
arithmetic rather than by placement), and both above the card above, with the
pixel probe still saying each was drawn.

One mutant of the five swept survives and is argued rather than fixed:
`origin.y() - self._metrics.ascent() ==> origin.y()` moves both boxes down
together, and a clause about two names not colliding is invariant to a
transformation applied to both. What the criterion holds is relative placement;
the box's own vertical origin is only how it is expressed.

## 2026-08-09 (review): done — the clause has a geometric referent and mutants die on it

Criterion re-run on the committed tree: both legs green (7 passed / 1 passed),
`done_when` untouched, and the worker left `status` at `awaiting-review`. Three
mutants run independently of the worker's sweep: the lift zeroed
(`rank * lineSpacing() ==> rank * 0.0`) is KILLED on the disjointness assertion,
at exactly the two boxes the prior review measured; `label_headroom ==> 0.0` is
KILLED on the clear-of-the-card-above assertion; the lane ordering reversed is
KILLED, though by the older bare-arrowhead case rather than by the new one — with
two names the only permutation is the one that lifts the wrong lane, so the
ordering clause has an oracle only for this arity. A shrunk `label_rect` width is
KILLED by the wider-than-`EDGE_LANE` guard, which is what stops the disjointness
claim being arithmetic.

Not a defect, recorded because it is the shape a later caller would meet:
`_lifts` ranks across all of `self._labels` and `label_headroom` is the max over
all of them, while `PipelinePane` reserves that headroom above the output card
alone. Today every label is an edge into the foot, so the two agree; a caller
that named an edge into a mid-stack card would stack the names by a global rank
and open the gap in the wrong place. Nothing in the tree can reach it and the
item did not ask for it.
