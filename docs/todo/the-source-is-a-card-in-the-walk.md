---
title: The source is a card in the walk
status: awaiting-review
gated_on: nothing
priority: high
phase: "9"
done_when: 'uv run pytest "tests/gui/test_source_card.py::test_a_minted_project_opens_on_a_source_card_with_nothing_chosen" "tests/gui/test_source_card.py::test_the_root_position_offers_the_source_tools" -q'
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

## 2026-08-10, review of `adc0756`: the two lines landed and the root did not

`adc0756` built the card's two lines — `param_form.PathChooser` for the value the
document holds, `chain_stack.Step.sources` for what the window resolved it to —
and dropped `PATH` from `STEREOTYPES_WITHOUT_EDITOR`. That is the chooser clause
and the "two files now show in the source tool" clause, and `done_when` reached
exactly those, which is why it went green over a body that still holds two
subjects nobody has built:

- **The mint writes the source node.** `project_select.mint` still writes
  `Project()`, and its docstring still says "Empty is the whole of it: no
  sources, no chain" — so VISION's minted project opens on an empty stack, not
  on "the source picker with nothing chosen". The card that draws it now exists,
  which is what the section above was waiting for.
- **The root's own offer.** `app.MainWindow._offer_over` still returns `()` at
  the root, and its docstring still gives the accepts-side reason ("needs their
  count and extension class") that the fold above replaced — the question is
  source-ness, not what accepts the stream, and the docstring goes with the
  build.

`done_when` is now those two by nodeid rather than a `-k` over the file, so it
cannot go green on the half that already shipped
([[2026.08.09-a-k-disjunction-is-green-for-the-disjunct-that-names-nothing]]).

**Append-on-browse is struck.** The item reserved MOCKUP-MAP's "browsing
*appends*" row for confirmation in review rather than treating it as licence;
this is that review, and it does not translate. The row describes the mockup's
module-level `SOURCES` list, and a v3 source node holds one `path` parameter
with no set behind it — appending would need a second document shape nothing
else asks for. VISION line 96 is the clause that does translate ("pick a video
out of a folder, change their mind, and swap the source to the folder itself"),
and the two asks `adc0756` built are it.

**The two rulings leave.** Whether the resolution is narrowed by extension and
whether `sorted` is the order a concatenating chain should read are both now
visible on screen and neither is this card's to settle; they move to
[a-folders-resolution-is-unnarrowed-and-lexicographic.md](a-folders-resolution-is-unnarrowed-and-lexicographic.md),
which also carries the fixture note that
`test_the_source_card_lists_what_its_path_resolved_to` pins the list against
reversal and against nothing finer.
