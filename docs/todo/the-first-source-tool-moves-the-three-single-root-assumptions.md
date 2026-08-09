---
title: The first source tool moves the three places one root is assumed
status: open
gated_on: nothing
priority: normal
phase: 8
done_when: 'uv run pytest tests/unit/test_source_tool.py -k "two_roots_order_and_execute or swapping_the_picked_file_moves_only_its_own_key or a_pattern_matching_several_files_is_refused or the_picker_emits_a_concrete_stream_type" -q && uv run pytest tests/integration/test_crop_serving.py -k a_second_root_beside_the_crop_is_not_one_the_artifact_can_serve -q'
opened: 2026-08-07
---

# The first source tool moves the three places one root is assumed

[adr/a-users-file-wires-in-like-any-other-input.md](../adr/a-users-file-wires-in-like-any-other-input.md)
settles that a picked file enters as a source tool — a node with no upstream
keying from its own file — and closes by saying "That migration is an item."
It was not one: nothing under `docs/todo/` and no line of `PLAN.md` mentions a
source tool, a picker, or a second root, so the ADR discharged its own
unfinished half onto a referent that does not exist. This is that referent.
The ADR is the decision; what is owed here is the first tool that exercises it.

Three sites assume the single root, and all three are real today rather than
predicted. `dag.linear_order` raises `expected one root, found N` — that is
the tool stack's redraw, so a two-root project cannot be *drawn* before it
fails to run. `cache_key.source_key` is "the ancestor of every root", one
value the whole graph folds in, which is the wrong shape the moment two roots
have different content identities. And the executor binds a node with no
upstream to the reader (`executor.py`, the root-is-the-reader comment), which
is the binding a source tool replaces rather than shares.

The ADR names two more consequences that land with the tool and not before. A
new `ParamStereotype` for a path: `ParamStereotype`'s own docstring says the
vocabulary is closed and a new member is a deliberate decision forced by a tool
that cannot be expressed in the existing ones — ADR-18 is that decision, so the
tool is what spends it, and `ToolSpec` refusing an unknown kind is what would
otherwise stop it. Not the *sixth*, which this item said until the two claims on
that seat were read together:
[a-band-has-no-stereotype-of-its-own.md](a-band-has-no-stereotype-of-its-own.md)
is ruled, is phase 1, and drains first, so `BAND` is sixth and a path is
seventh. Nothing in the argument here depends on which — the closure rule is
what the ADR spends, and that item is the one that restates the rule without an
ordinal in it. Read it before writing the picker's spec, since it also carries
the `SPAN`/`BAND` split and the picker declares neither. And the resolution policy stays out of the key: a pattern resolving to
nothing is a run that cannot happen, one resolving to several is refused rather
than ordered, and what is hashed is the file each replicate resolved to and
never the rule that found it.

The two VISION scenarios that wait on this are the picker and the folder
([VISION.md](../VISION.md)), and whether VISION also states an A/B of two
backgrounds is
[a separate question for Kendrick](whether-vision-states-the-background-ab.md).

## The picker's `emits` names one concrete stream type

Settled, and the alternative is refused. The alternative was a wildcard —
`ArraySpec()` with neither dtype nor channel layout stated — on the reading that
a node whose file the user chooses cannot know what it will be handed.
`StreamSpec.admits` is permissive by construction, and its own docstring is the
argument against: a wildcard on either side admits, because the static check
exists to reject graphs that *cannot* work rather than ones that cannot be
proven to. So an unconstrained `emits` passes against every `accepts` on the
shelf, and `dag.py`'s edge check is retired for every graph that contains the
picker. A node whose whole purpose is to let a user substitute an arbitrary file
is the last node that should switch that check off; the permissiveness that
makes a wildcard cheap everywhere else is exactly what makes it expensive here.

`crop` and `span` do emit `ArraySpec()` and are not the precedent this looks
like. Both are wildcards on *both* sides of a pass-through: what they emit is
whatever arrived, so the unstated pair is a statement of preservation and the
edge check still runs against the real upstream. A source tool has no upstream
to preserve from, so the same two empty tuples would be a claim of ignorance
standing where a claim about frames belongs.

What the picker declares is what its frames *are* — the dtype and channel layout
a decoded frame carries, which it can state because a picked file reaches the
graph through the decode boundary the project's own video reaches it through.
What its frames *mean* — that this one is a background rather than a plate — is
not a question a stream type asks, and naming it there would be smuggling a
scene description into a dtype. That meaning goes through the products: an
`Emission` is something a user picks and saves, and `selected_by` names the
parameter that picks it.

`done_when` above carries a fourth case for this,
`the_picker_emits_a_concrete_stream_type`, added by review after the working
session declined to edit its own criterion. It has to assert both tuples
non-empty: `emits.dtypes` and `emits.channels`. Asserting one leaves the other
a wildcard, and one unstated tuple is enough for `admits` to pass against every
`accepts` on the shelf, which is the whole failure this section refuses.

### Open: which axis carries a meaning like "generated background"

Not decided here, and not to be decided by the session that lands the tool.

The conversation that settled the paragraph above leaned on `ElementKind`'s
promise that "a third member arrives with the tool that needs it". That premise
is gone: the enum already has three members — `PIXEL`, `BLOCK` and `FRAME`, all
three present in the commit that wrote the sentence — and `detect` declares
`FRAME`. So the question stands on its own terms with two live readings. An
`Emission` name puts the meaning where the user's choice already is, per tool,
and says nothing to a consumer asking what it was handed. A fourth `ElementKind`
member puts it on the type, where it propagates through `node_element` and
reaches every downstream — but `ElementKind`'s own docstring says it answers what
one value *is a value of*, and a scene description is not an answer to that
question: a background frame's values are pixels, whatever produced them.

Which axis is Kendrick's call. Name it before the picker's spec is written,
because the spec is where the answer is spent.

### Noted, not owed here

`ElementKind`'s docstring miscounted its own members and promised a third that
had already landed, which is what the reading above leaned on until the enum was
checked. That was a defect independent of everything above and it survived
whichever way the axis question goes; it was fixed on its own reason in
[its own item](elementkind-counts-two-members-over-three.md), not here. The axis
question is untouched by that fix.

## 2026-08-08: a fourth site, and it is the one that fails silently

08.2 landed `resolve_source.crop_bound`, which answers which root a written crop
could stand for, and `cli/run_cmd._route`, which drops that node and points the
whole run at the artifact. `crop_bound` declines when there are two crop roots,
because two boxes are two answers — but it says nothing about a *non-crop* root
standing beside the crop. Checked at this review on a graph of `crop -> down`
plus a second unattached `downsample`: two roots, and `crop_bound` still returns
the crop's box. The run is then served, the artifact is the invocation's only
reader, and `executor` binds every node with no upstream to that reader — so the
second root, which asked for whole frames, is handed the cut ones. No refusal,
no message, and the printed counts are the counts a correct run prints.

The other three sites announce themselves: `linear_order` raises, `source_key`
folds a shape that is visibly wrong, the executor's binding is the one the tool
replaces. This one is the same assumption with no symptom, and it is worth
noting that it arrived *after* the three were written down — a plan-time route
that reads "the root" is the shape this assumption keeps taking. Whether the
tool moves it or `crop_bound` simply declines a graph with more than one root is
this item's call; either way the case named in `done_when` is what pins it, and
it is writable today rather than waiting on the picker.

[crop-serving-and-checkpoint-read-back-become-source-tools.md](crop-serving-and-checkpoint-read-back-become-source-tools.md)
is where `_route` is unwound, and unwinding it retires this site with the rest
of the plan-time route — but that migration is gated on this item, so the site
is live until this one lands.
