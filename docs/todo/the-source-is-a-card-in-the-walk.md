---
title: The source is a card in the walk
status: awaiting-review
gated_on: nothing
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

## 2026-08-09: the gate lifted

`44b6456` landed `pick`, so a project can hold an input that is a node and a
source card is a picture of something the graph carries. `gui/param_form.py`
already builds a `PATH` field as the value the document holds, which is the
placeholder this card replaces with a chooser. `status` and `gated_on` moved on
that; the work below is unchanged, including the append-on-browse row that is
still Kendrick's to confirm in review.

## 2026-08-09: the mint writes the node this card draws

A minted project holds `nodes: []`, and nothing in the GUI can give it a first
one. `add_step` returns early on an empty `_order` — a gap is between two
positions the chain has — and `AddNode` issues only from `take_offer`, so the
add box is the sole writer and it cannot open. The card cannot be a picture of
something the graph carries while the graph carries nothing, so the mint writes
the source node with no file chosen and this card draws it: VISION's last
scenario has the new project put the user "straight into it, where the only
pipeline item is the source picker with nothing chosen".

The chooser's answer is *which reading*, not only which file. VISION has two
files in a folder match both a concatenating tool and a folder of pre-cropped
videos, and offers both "with the tool picker display: the user decides how the
input is interpreted" — one input, two interpretations, which is a different
shape from the add box's one entry per spec. What the source resolves to is
[the-stream-a-position-produces-is-resolved-not-declared](the-stream-a-position-produces-is-resolved-not-declared.md);
what the user does with an ambiguous resolution is this card.

## Folded 2026-08-09: the root is now the only position that offers nothing

`the-stream-a-position-produces-is-resolved-not-declared` landed the fold, so
every position below the source resolves and offers what takes its stream. The
root did not, and `_offer_over` still returns `()` there — that item's body says
it should stop doing so, and stopping needs an argument `offered_tools` cannot be
handed: there is no stream flowing into a root, so the accepts-side match is
vacuous and what actually distinguishes the candidates is that they are sources
at all. That is the chooser's question rather than the add box's, which is the
distinction the paragraph above already draws — "one input, two interpretations
… a different shape from the add box's one entry per spec" — so the shape the
root offer takes is settled here.

## Folded 2026-08-09: the files the card lists are computed, and nothing paints them

`a-source-param-names-a-folder-and-several-files-are-an-ordering` landed
`MainWindow.resolved_sources` — per source root, the ordered files its path
parameter names, re-read when the window becomes the active one again. That is
what "two files now show in the source tool" is read off, and today nothing
reads it: the map is held and painted by nothing, which is this card's job and
was left here rather than given a placeholder consumer.

It also leaves the card a question that could not be answered without it. A
folder resolves to *every* file in it, flat and unfiltered, because narrowing by
extension is a declaration no tool carries — so a folder holding a README
resolves to the README, and what the user sees is a list with something in it
they did not mean. Whether the chooser narrows the list, the tool declares what
it can read, or nobody does because a reader refuses it one step later, is a
question this card is the first to have a reason to ask.

## Folded 2026-08-09 at that item's review: the order the card lists in is a ruling too

Beside the extension question, and reaching the card the same way. `named_files`
orders a folder lexicographically and argues for it against the alternative it
was rejecting — the sequence the directory happened to be written in — which is
the right rejection and not yet an answer. Lexicographic over unpadded numbering
is the failure the ordering was made deliberate to avoid: `clip_10.mp4` before
`clip_2.mp4`, which for anything that concatenates is a silent wrong answer
rather than a failed run. Whether SIEVE reads the number inside a name, or lists
what `sorted` gives and lets the user see it is wrong, is undecidable until a
list is drawn — and this card is what draws it, so the choice is visible here
first and nowhere earlier.

Two facts it can build on. `offered_tools` now refuses a tool declaring `source`,
because a root cannot be what goes *after* something; the root's offer is that
refusal read the other way. And the swap button's dead tooltip on the source card
is asserted in `tests/gui/test_swap_box.py`, so whatever this card does to the
root position has a test standing on the current answer.
