---
title: The field that names footage leaves the schema, and every reader reaches it through the graph
priority: high
phase: 11
status: awaiting-review
gated_on: nothing
done_when: 'uv run pytest tests/unit/test_pipeline_model.py tests/unit/test_source_tool.py -q -k a_document_carrying_a_source_key_is_refused && uv run pytest tests/unit/test_pipeline_model.py tests/unit/test_source_tool.py -q -k relocating_rewrites_the_source_nodes_path_param && uv run pytest tests/unit/test_pipeline_model.py tests/unit/test_source_tool.py -q -k a_relative_source_param_anchors_on_the_project_directory && uv run pytest tests/integration/test_cli_run.py -q -k a_project_whose_graph_has_no_source_root_refuses_by_name && uv run pytest "tests/gui/test_project_cards.py::test_the_library_line_reads_footage_through_the_graph" -q && uv run pytest tests/unit/test_pipeline_model.py -q -k the_version_a_document_declares_after_the_removal'
opened: 2026-08-10
---

# The field that names footage leaves the schema

[adr/a-document-names-footage-only-through-a-tool.md](../adr/a-document-names-footage-only-through-a-tool.md)
(34) settles that `Project.source` and `SourceRef` leave schema v1 — a document
names footage only in a source tool's path param, stored relative to the project
file, and every reader reaches it through the graph — and then closes without
naming an item. This is that referent, exactly as
[the-first-source-tool-moves-the-three-single-root-assumptions](the-first-source-tool-moves-the-three-single-root-assumptions.md)
is ADR 18's; the same discharge onto a referent that did not exist, one ADR
later. The ADR is the decision and nothing here reopens it.

The tree still holds all of it. `core/pipeline_model.py` defines `SourceRef`,
`Project.source`, `source_path`, `for_video` and `relocated`'s source branch;
`cli/run_cmd.footage_of` is the one reader of `source_path` and `run`, `preview`
and `materialize` all reach footage through it; `gui/app.py` opens the player on
`project.source` directly and `gui/project_select.py` reads it for the card's
"no footage yet" label. Those two GUI readers are the ones the ADR's "every
reader reaches it through the graph" costs most, because neither is going
through `source_path`'s gate today.

## The two source tools anchor against the wrong directory, and that is this migration's

`tools/pick.py` and `tools/footage.py` both resolve a relative path against the
process's directory, and `pick` says so deliberately — "that is what a file
picker hands over and it is deliberately not the project directory", deferring
the project-relative question to
[whether-an-external-input-carries-a-portable-identity](whether-an-external-input-carries-a-portable-identity.md).
ADR 34 answers it the other way and answers `pick`'s own reason with it:
resolution happens before the key, so the rule that resolution policy stays out
of the key survives untouched, and what is hashed is still the resolved file's
identity. So this is a docstring written under the old anchoring rather than a
live disagreement with the decision — and it belongs here, with the field whose
relative-to-the-project property is moving onto the param, rather than in a
second item beside it. `relocated` is the same fact from the other end: it keeps
rebasing outputs and crops and rebases the source as a param rewrite on the node
that holds it, which is what the third `-k` clause above pins.

## 11.1 runs first, and this is the case its rule is written against

[a-load-restamps-the-version-it-read](a-load-restamps-the-version-it-read.md)
(11.1) is where the rule for a bump lands; the ADR names it as such, and this
item cites it rather than carrying a second copy. The queue already orders them
— same phase, and a step outranks a pool item in its own phase — so nothing here
needs a `gated_on`.

What the session on 11.1 has to see before it writes that ADR: this is a
*removing* bump, and 11.1's body proposes a rule that "a bump adds fields and
never repurposes or removes one". Written flat, that rule is violated by the
first thing queued behind it. Either the rule states the terms on which a
removal is paid for — the ADR's "the cost is charged once, at the version" is
the direction, not the wording — or it is additive-only and this migration
contradicts a rule one item old. That is 11.1's call and not this item's; what
this item owes 11.1 is that the case exists.

## Folded 2026-08-10: the library card's two lines are both wrong now the mint writes a node

`the-source-is-a-card-in-the-walk` landed `project_select.mint` writing an
unchosen source node, so an ordinary project reaches `_holds` with the field
still empty and a graph that holds the answer. Both halves of the line say the
wrong thing for it: the footage half reads `project.source` and so says "no
footage yet" for every project the user has ever picked a file for, and the chain
half counts nodes and so says "1 step" for a project whose chain is empty and
whose one node is the picker. That is the same reader this item already names —
it is now wrong on the common case rather than the empty one, and asserted at
`tests/gui/test_project_cards.py::test_new_project_mints_an_unchosen_source_the_library_lists`,
which pins today's answer and will need the migration's.

`done_when` gains a third leg for it, red today because the case does not exist
(exit 4): the two schema legs and the CLI leg could all go green over a card
still reading `project.source`, which is what the fold above says is now wrong
on every project rather than only the empty one.

    $ uv run pytest "tests/gui/test_project_cards.py::test_the_library_line_reads_footage_through_the_graph" -q
    ERROR: not found: …::test_the_library_line_reads_footage_through_the_graph
    exit: 4

## Folded 2026-08-10: 11.1 ruled, and it leaves this item the question of whether the number moves

[adr/a-bump-adds-and-a-removal-is-paid-at-the-version.md](../adr/a-bump-adds-and-a-removal-is-paid-at-the-version.md)
(38) is 11.1's answer, and it rules the way the section above hoped: a removal is
allowed and paid at the version, which for this migration is `extra="forbid"`
refusing every document still carrying `source:` by name — the first `-k` clause
is that price, written as a case. What the ADR does not decide, because it is
this bump's and not the rule's, is whether `SCHEMA_VERSION` becomes 2 here at
all. The stamp rises when a build writes content the declared version does not
have, and this bump writes none: it takes a key away, and a v1 document that
still carries the key does not open under either number. So a v1 document
written after this lands is the same bytes as one written before it, minus a
key, and there is no build the number would tell anything a refusal by name does
not already say. The argument for moving it anyway is that a removal is exactly
the change a stamp exists to record; the argument against is that a number
nothing reads differently is a number that lies about being load-bearing. This
item's session picks one and says which in the commit.

## Review 2026-08-10: the branch is measured, and the criterion pins whichever one is taken

The section above is right that the number is this item's to move or not, and
wrong that ADR 38 leaves it open: "the stamp rises only when a build writes into
it something the declared version does not have" decides it, and a removal
writes nothing new. What that decision costs is
[a-removals-price-is-charged-only-to-the-old-document](../findings/2026.08.10-a-removals-price-is-charged-only-to-the-old-document.md)
— the document this migration produces loads clean on the pre-removal build,
which then tells the user to add footage to a project that already names it in a
node param. The ADR prices the old document under the new build and is silent on
the new document under the old one, which is the direction the stamp exists for.

So the pick is between a misreading with a measured message and a successor ADR
saying a removal moves the number too. That is a ruling rather than an
implementation detail, and a worker taking either branch without one records the
decision nowhere. `done_when` now ends in a case that pins the version a
post-removal document declares — red until it exists, and satisfiable under
either branch, since what is missing today is not a number but any assertion at
all about which number a document written after the removal carries.

## What stays where it is

`footage_of` dies with the field, and the case it is owed on
[the-second-failing-command-moves-the-shared-refusals](the-second-failing-command-moves-the-shared-refusals.md)
dies with it — see that item's dated section, which is where the `cli/common.py`
question stays. The refusal itself does not go: a run still owes the user a
sentence naming the document rather than an `AttributeError`, and the ADR moves
it to where the graph can be seen, which is what the fourth `-k` clause pins on
one command.

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/unit/test_pipeline_model.py tests/unit/test_source_tool.py -q -k "a_document_carrying_a_source_key_is_refused or relocating_rewrites_the_source_nodes_path_param or a_relative_source_param_anchors_on_the_project_directory"
    70 deselected in 0.31s
    exit: 5

    $ uv run pytest tests/integration/test_cli_run.py -q -k a_project_whose_graph_has_no_source_root_refuses_by_name
    8 deselected in 0.33s
    exit: 5

## Folded 2026-08-10: the anchoring clause is discharged, and the four that remain are counted

The section above headed "The two source tools anchor against the wrong
directory" is done. `pipeline/resolve_source.anchored` rewrites every
`ToolSpec.path_params` entry that is relative against the project file's
directory, before `Dag.build` and therefore before any key —
`tests/unit/test_source_tool.py::TestASourceParamIsAnchoredOnTheProject::
test_a_relative_source_param_anchors_on_the_project_directory` is the third
`-k` clause and it passes. It lives in `pipeline/` rather than in the two tools
because a tool is handed a pattern and never a document, which is the same
reason `pick`'s own header gave for deferring the question; both tool headers
and `tool_base.named_files`' Args now cite the rewrite instead of stating the
process's directory as the rule. `sieve run`, `sieve materialize`, `sieve
preview` and the window's two readers all call it, so the answer does not
depend on which front end asked.

What this session did **not** do, and the measurement of why. The remaining
five `-k` clauses are one atomic schema removal, and its cost is not the four
source files this item inventories — it is the corpus that names the field.
`Project.for_video` has 23 call sites in `tests/`, `SourceRef` 71 mentions
across roughly twenty more, and the two shapes are not one edit:

- A test that carries `source=SourceRef(path="clip.mp4")` as ceremony and never
  decodes — most of `tests/gui/` — loses the line and nothing else. Cheap.
- A test built as `Project.for_video(video, dir).with_pipeline(graph())` has to
  grow a `footage` root feeding what was a reader-fed root, which moves the node
  count in every `"N node outputs computed"` assertion and the walk position in
  every GUI layout assertion. `tests/integration/test_cli_run.py::_project` is
  the shape, and there are twenty-odd of it.

Which is to say the `done_when` above is five jobs behind one criterion:
the anchoring (done), the field's removal, `relocated`'s rewrite, the CLI's
graph-side refusal, the library card, and the version. A review widening or
splitting it is the edit this needs, and this session may not make it. The
version clause in particular is answerable on its own — ADR 38 already decides
it, per the "Review 2026-08-10" section above — and needs none of the removal
to land.

`relocated` is worth naming separately because it cannot stay where it is:
rebasing a source node's path param means knowing which param is a path, which
is a registry question, and `core/pipeline_model.py` is registry-blind by its
own header. Either the caller hands it `ToolSpec.path_params` or the method
leaves `Project`. Nothing calls `relocated` today and nothing tests it, so the
signature is free.

## Folded 2026-08-10: an addition landed and nothing decided whether the stamp rose

11.2 put `Edge.port` into the document — the first field added since ADR 38
settled that a bump adds and a load keeps the version it read — and it landed
without touching `SCHEMA_VERSION`. What made that defensible is a serializer:
`Edge` writes `port` only when it has one, so a document over a graph with no
fan-in is byte-for-byte what it was, and a v1 stamp on it is true. What it does
not answer is the document that *does* carry a port. Under ADR 38 the stamp
"rises only when a build writes into it something the declared version does not
have", and nothing in the tree implements a conditional rise: a project loaded at
1, given a merge, and saved is stamped 1 and carries a field 1 does not have.

It lands here rather than as its own item because this is the item that pays a
removal at a version, so it is the one that has to decide what a version *is* on
the way in as well as on the way out — and its `done_when` already names
`the_version_a_document_declares_after_the_removal`, which is the case the
addition's answer would sit beside. That criterion covers the removal only; the
addition half may want widening.

## Review 2026-08-10: the anchoring lands in the cache key, and `relocated` is not free

The anchoring clause the fold above discharges is correct about the file it
resolves and wrong about what that costs in keys.
[anchoring-puts-the-project-directory-into-the-node-key](../findings/2026.08.10-anchoring-puts-the-project-directory-into-the-node-key.md)
measures it: `anchored` rewrites the param before `Dag.build`, `node_key` digests
the resolved params, and so the project's own directory is inside every key below
a source node. One `pick` node with the same picked identity keys three different
ways as held, anchored on one folder, and anchored on another. That is the first
of the two rules
[adr/a-users-file-wires-in-like-any-other-input.md](../adr/a-users-file-wires-in-like-any-other-input.md)
forbids by name — "neither 'this exact path' nor 'the folder of this name beside
the project'" — and the commit's claim that "the pattern still never enters a
key" is contradicted by `cache_key.picked_key`'s own docstring, which says the
pattern reaches the node key through `params`. The ADR's *ordering* clause was
satisfied and its *exclusion* clause was not; the run checked one and cited both.

This belongs here rather than beside the cache key because it is this migration
that makes it universal. ADR 34 requires the stored path to be relative to the
project file, so relative stops being the spelling a few documents happen to use
and becomes the only one — and relative was the one spelling whose key did not
move when the folder did. What a user sees after moving a project is a document
that opens, every file resolving, and every node below the source recomputing.

The fix is a fork this item has to take rather than inherit: either a source-tool
node's `ToolSpec.path_params` are excluded from `node_key`'s digest — defensible
without a new ruling, since the file the param resolved to is already in the key
as the `picked_key` on the node's `upstream` pair — or the cost is accepted and a
successor ADR says so. Nothing in the tree pins key stability across a project's
location either way, so whichever branch is taken owes a case that would go red
if the other were built.

Correcting the fold above on one point: "Nothing calls `relocated` today and
nothing tests it, so the signature is free" is false.
`tests/unit/test_pipeline_model.py` calls it twice, at
`test_relocating_rebases_every_stored_path` and
`test_relocating_with_no_footage_rebases_what_it_does_name`, and the first
asserts on `moved.source` — the field this item removes. So the session that
takes the second `-k` clause rewrites both cases rather than writing one against
a free signature, and the first of them is what that clause replaces.

## Folded 2026-08-10: the first leg is green today, on one clause of three

`-k "A or B or C"` selects the union and exits 0 as soon as *any* selected case
passes, so the first leg went green the moment 11.3's anchoring case landed and
says nothing at all about the two clauses beside it, neither of which exists:

    $ uv run pytest tests/unit/test_pipeline_model.py tests/unit/test_source_tool.py -q -k "a_document_carrying_a_source_key_is_refused or relocating_rewrites_the_source_nodes_path_param or a_relative_source_param_anchors_on_the_project_directory"
    1 passed, 72 deselected in 0.84s
    exit: 0

Only the chained `&&` keeps the criterion red, and it is red on the second leg.
A worker reading the first leg's exit code as its baseline is reading a green
that two thirds of the removal cannot move. Whatever a review does with the
splitting question, the union is the wrong connective for a criterion whose
clauses are meant to land together — three legs asserting three cases would go
red per clause and green per clause, which is what a criterion is for.

The measurement of what the removal costs is
[the-footage-field-removal-is-atomic-across-forty-test-modules](../findings/2026.08.10-the-footage-field-removal-is-atomic-across-forty-test-modules.md).

## Review 2026-08-10: the union became three legs, and the item did not split

The criterion now spells the first leg as three `&&` invocations of one name
each, so each clause reports for itself — clauses one and two exit 5 for their
own absence and the anchoring clause exits 0 for its own case, where the union
exited 0 for all three. Nothing else in the criterion moved: the connective was
the defect, not the clause list. The three names keep their order, so the
sections above that number them ("the first `-k` clause", "the third") still
point where they did; what is stale is prose numbering *legs* — the card's fold
calls its own the third, and the command now has six.

The item is not split, and the measurement is why. The finding this item cites
found no clause satisfiable alone — the corpus encodes the reader-fed root's
absence, so any stage that leaves the tree runnable is the whole removal — and a
split into halves that cannot land separately would put two items where one job
is. What the criterion can now do is say which clause a session is short of;
what it cannot do is make the job smaller.

`the_version_a_document_declares_after_the_removal` (the last leg) stays as it
is, and the finding's `closed` entry is the warning that goes with it: the case
will pass against a tree that has not removed the key, so its red has to come
from the removal being in place, not from writing the case first.

## 2026-08-10: the removal landed whole, and it cost three rulings the item did not name

Every clause is green and the corpus is migrated in one commit — `1296 passed`,
which is the suite plus the two cases the criterion's fourth and fifth legs were
waiting for. What is worth recording is not the diff but the three questions the
removal forced, because none of them is in the sections above.

**`SCHEMA_VERSION` stays 1**, on ADR 38's plain words: the stamp "rises only when
a build writes into it something the declared version does not have", and a
removal writes nothing new. `test_the_version_a_document_declares_after_the_removal`
pins it — the stamp, the absence of the key, and that a document written after
the removal reads back at 1. The "Review 2026-08-10" section above is right that
this leaves
[a-removals-price-is-charged-only-to-the-old-document](../findings/2026.08.10-a-removals-price-is-charged-only-to-the-old-document.md)
unpaid: a post-removal document still opens clean on a pre-removal build, which
then tells the user to add footage to a project that names it in a node param.
That is a successor ADR's to overturn, and the criterion is satisfiable under
either branch, so it stays pinned at what this build actually writes.

**Which decoded root is "the footage" is `resolve_source.footage_root`, and the
tie-break is the first decoded source root in document order.** Decoded rather
than any source root, because the readers that ask are the ones that decode — a
`pick` over a background is not the video. Document order rather than the
topological one, because a root has no ancestors to sort behind and document
order is available to a caller holding a graph that will not build, which the
library card is. `footage_file` then resolves that root's param under the
baseline first and the replicates in order, because a path param is an ordinary
param and a folder of already-cut files deviates it per arena and leaves the
node's own empty.

**Crop serving would have died with the field, and did not.** `crop_roots`
recognised a crop of the footage as *a root* crop node; under the ADR the
footage is a node, so every such crop is fed by it and the mechanism found
nothing. It now matches a crop node whose upstream is empty or is exactly the
footage root, and `_wired` cuts the edge into a node it turns into a source tool
— a source tool with an upstream reads a file and a stream at once. `_uncut`
puts that edge back, which is what keeps the pair an edit and its undo.

Two things this leaves behind, neither of them this item's:

- The parent footage root survives a serving edit with nothing reading it, and
  the executor computes every node the graph holds, so a fully served run still
  decodes the parent once per frame. Keeping it is deliberate — it is where
  `source_end` comes from, and dropping it would make a default-span run over a
  served project cover the crop file's length in the source's numbering — so the
  fix is on the executor's side, not the document's.
  `tests/integration/test_crop_serving.py::test_the_served_graph_holds_no_crop_node`
  says so in its own words rather than claiming a saving it no longer makes.
- `run_cmd`'s reader is now unreachable for any document. Every root of every
  graph opens its own file once the footage is a source node, so
  `_reads_the_footage` is false for everything a front end can write and
  `frame_source`, `PrefetchFrameSource`'s use here and `_UNFED` are reached only
  by a graph rooted on a plain tool — which is the state the CLI refuses by name
  one line earlier.
