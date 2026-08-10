---
title: The field that names footage leaves the schema, and every reader reaches it through the graph
priority: high
phase: 11
status: open
gated_on: nothing
done_when: 'uv run pytest tests/unit/test_pipeline_model.py tests/unit/test_source_tool.py -q -k "a_document_carrying_a_source_key_is_refused or relocating_rewrites_the_source_nodes_path_param or a_relative_source_param_anchors_on_the_project_directory" && uv run pytest tests/integration/test_cli_run.py -q -k a_project_whose_graph_has_no_source_root_refuses_by_name && uv run pytest "tests/gui/test_project_cards.py::test_the_library_line_reads_footage_through_the_graph" -q'
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
