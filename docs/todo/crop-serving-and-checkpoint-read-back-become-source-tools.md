---
title: Crop serving and checkpoint read-back become source tools
status: awaiting-review
gated_on: nothing
priority: high
phase: "05"
done_when: 'uv run pytest tests/integration/test_crop_serving.py -k "the_served_graph_holds_no_crop_node or a_pre_cropped_folder_needs_no_crop_record or a_preview_is_served_by_the_written_crop or a_served_source_root_reaches_every_front_ends_plan_keyed" -q'
opened: 2026-08-07
---

# Crop serving and checkpoint read-back become source tools

[adr/a-users-file-wires-in-like-any-other-input.md](../adr/a-users-file-wires-in-like-any-other-input.md)
now says the two places a file already stands where a node stood are instances
of the source-tool mechanism rather than paths beside it. This is that
migration. Nothing here re-decides it; what is owed is the tree agreeing with
the ADR.

Two things move and a third dissolves. `resolve_source.resolve` currently
answers "which file does this run open, in whose frame numbering" by matching a
`CropRecord` against a region the caller derived from the graph — that match
survives, but its product becomes a document edit offered to whoever holds the
project, not a file handed to a run already planned. The checkpoint side has no
reader yet, which is the cheap half: it is written as a source tool the first
time rather than migrated into one. And
[a-served-run-elides-the-node-its-file-already-holds.md](a-served-run-elides-the-node-its-file-already-holds.md)
is the third — it is open, it is asked to settle whether a served run
neutralises the crop node at `WHOLE_FRAME` or drops it from `dag.order`, and
under the ADR neither happens because the executed graph does not contain the
node. **Those two items must not both land.** Whichever runs second is
re-deciding, so if 05.10 lands first this item is the one that unwinds it, and
if this one lands first 05.10 loses its subject and should be closed rather than
worked.

What must hold after, and is what the criterion is for: a run served by a
written crop executes a graph whose root is a source tool over that file and
which holds no crop node at all, and a folder of pre-cropped videos wires in
with no `CropRecord` anywhere — same mechanism, no crop node to hang one on,
which is the case that forced the ADR.

Cache keys are not one guard over both halves, and the ADR now says which is
which. The crop half moves no key *provided the crop node is dropped rather than
neutralised*: `dag.node_keys` folds `source_key(<file>, decode_format)` into
every root and schema v1 puts no region in it, so a root reading the written crop
already folds the string a source tool over that file folds — but a node left in
at `WHOLE_FRAME` stands between them and moves everything below. Assert that
equality directly, over the two key dicts; Phase 5's second gate does not cover
it, because it runs one project twice with only its checkpoint list changed and
never derives a key both ways.

The checkpoint half does move keys, off the checkpointed node's key and onto the
written file's identity, and that is owed here rather than discovered later: this
item re-states Phase 5's second gate in `PLAN.md` so it says what a read-back
that is a document edit can actually satisfy. Re-stating a gate is a change to
the plan, so it is proposed to Kendrick and not written past him.

**Only one front end serves a crop, and this is what makes that stop mattering.**
08.2 landed the plan-time route in `cli/run_cmd.py` and nowhere else, so a
preview session and a GUI render worker still decode the parent and re-cut a box
that is already on disk — which `resolve_source.py`'s opening paragraph has
claimed all three call, since before any of them did. Under the wired form there
is no call to add: the substitution is a mutation the project holds, so a front
end that reads the document is served without knowing artifacts exist. Unwinding
`_route` and its two-pass shape is this item's work either way; what the gap
says is that the alternative — teaching two more front ends the same plan-time
route — is work with the same known expiry and should not be done.

`done_when` gained `a_preview_is_served_by_the_written_crop` at the review that
read that fold, because the two cases it named are both about the graph and
neither would go red for a migration that served `sieve run` and left
`cli/preview_cmd.py` decoding the parent. The preview is named rather than the
GUI worker because it is the front end that exists as a command today; if the
worker is a distinct executable path when this lands, it wants a case of its own
and the criterion widens again.

Where the clause work goes is open and is this item's call.
`crop_binding.py`'s four states are facts about records and stay facts, but a
state that used to mean "this run will be served" now means "this edit is
offerable", and the reader that displays them is downstream of a decision
somebody makes rather than of one the planner already made.

## 2026-08-09: the gate lifted, and the site it unwinds grew a clause

`44b6456` landed the first source tool, so there is something to migrate onto:
`ToolSpec.source`, `ToolSource`, and `Dag.source_roots`, with `pick` as the
worked example of a root that opens its own file. `status` and `gated_on` moved
on that.

The plan-time route this item unwinds gained a clause in the same commit:
`resolve_source.crop_bound` now also declines when the footage feeds more than
one root, because serving replaces the whole reader and the second root asked
for whole frames. That clause is part of what retires here — a source tool
wired to the crop node's place needs no `_route` and no count of roots — so the
migration removes it rather than carrying it over.

## 2026-08-09: the one-front-end gap now costs a key as well as a decode

Folded from the run that landed the external-input walk at run start
(`todo/a-run-names-the-external-files-it-needs-before-it-starts.md`). That walk
resolves every source root's file and hands `ExecutionPlan.build` the `picked`
identities that key those roots, and it is in `cli/run_cmd.py` and nowhere else:
`pipeline/preview.py` and `cli/materialize_cmd.py` still build plans with no
`picked`, so a source root in either is left out of `Dag.node_keys` and takes its
whole subtree with it. That is the same "only one front end" gap the paragraph
above names about serving, one layer down — and under this migration it stops
being a gap about pickers and becomes one about crops, because a written crop
*is* a source root here. A preview whose crop root is unkeyed recomputes the
graph below it on every drag, which is the product constraint `CLAUDE.md` states
rather than an efficiency note.

Whether the fix is a shared run-start step the three front ends call or a
`picked` argument each threads is this item's to settle, since it is the item
that decides what a front end has to know about artifacts at all. Not minted
separately for that reason: an item for "preview passes `picked`" would be
answered by whichever shape this one picks.

### 2026-08-09 review: `done_when` widened for the paragraph above

The fold arrived with the criterion untouched, as CLAUDE.md requires, and its
author said so. Widened here to a fourth case —
`a_served_source_root_reaches_every_front_ends_plan_keyed` — which is the shape
the case has to take and not a spelling to obey: it must fail while any front
end builds a plan without `picked`, so it cannot be satisfied by asserting
`run_cmd`'s behaviour a second time. It deliberately does not prejudge which of
the two shapes the paragraph names is picked; a shared run-start step and a
threaded argument both pass it.

## 2026-08-09 review: the key paragraph's premise is gone, and the fork is Kendrick's

A work run selected this item, proved the criterion red for the right reason
(exit 5, none of the four cases exist), and stopped without touching the tree
rather than pick a reading. It was right to. The paragraph above that begins
"Cache keys are not one guard over both halves" rests on `dag.node_keys` folding
`source_key(<file>, decode_format)` into every root, and since `44b6456` it does
not: a root with a `source` spec folds `picked_key(identity)` instead —
different flavour literal, different arity, unequal digest for one file. Measured
in
[findings/2026.08.09-a-source-tool-root-keys-in-a-different-flavour-than-the-footage-it-replaces.md](../findings/2026.08.09-a-source-tool-root-keys-in-a-different-flavour-than-the-footage-it-replaces.md),
which also carries the two live readings and the argument for each.

So the criterion's first case is not merely unwritten — the equality it asks for
is unsatisfiable on this tree, and the item cannot be worked without settling a
question ADR-18 does not rule and that would otherwise ride along inside an
implementation. `status` is `deferred` on that ruling. `done_when` is left
untouched: which cases it should name depends on which way the fork goes, and
widening it now would prejudge it.

The same sentence sits in the ADR itself
([a-users-file-wires-in-like-any-other-input.md](../adr/a-users-file-wires-in-like-any-other-input.md),
under "The two halves pay differently in keys"). Amending a settled ADR is not a
reviewer's edit; the finding names the divergence and the ADR is Kendrick's to
correct or to re-decide.

One stale sentence while it is deferred, corrected here rather than in place:
the opening paragraph says
[a-served-run-elides-the-node-its-file-already-holds.md](a-served-run-elides-the-node-its-file-already-holds.md)
"is open". It is `done`. So the collision that paragraph guards against has
already resolved in the direction it anticipated — 05.10 landed first, and this
item is the one that unwinds it. Nothing about that is re-decided by the
deferral; it is what this item will do whenever the fork above is settled.

## 2026-08-09: the fork is ruled — the flavour follows the reader

Kendrick took the first fork in the reader-owned form, minted as
[adr/a-root-keys-by-its-reader.md](../adr/a-root-keys-by-its-reader.md) with
the finding above holding what decided it: a source tool whose file is read
through the shared decode stack folds `source_key`, and only an own-code
reader folds `picked_key`. `status` and `gated_on` moved on that.

For this item that means the artifact's source tool declares the shared-decoder
reading, `dag.node_keys` folds `source_key(identity, decode_format)` for such
roots, and the criterion's first case is satisfiable as written. `pick` keeps
`picked_key` and its keys do not move. The contract change lands here rather
than in an item of its own because this is the first work that needs it; the
review that closes this item should consider whether `done_when` wants a case
pinning the split itself — a decoder-read root keying source-flavoured while
`pick` stays bare — which is a widening and therefore the reviewer's.

## 2026-08-09: the checkpoint half's identity must say which product

A pointer, not a restatement:
[a-checkpoint-does-not-record-which-product-it-holds.md](a-checkpoint-does-not-record-which-product-it-holds.md)
holds the schema gap — neither the manifest nor `Project.checkpoints` can say
which emission of a multi-product node a checkpoint holds, and 07.9's save
screen could not fix it from its side. That item's own text says the read-back
path is where it is answered, "whichever arrives first" — and this item is the
read-back path, arriving first. The checkpoint half mints the written file's
key-bearing identity here; an identity minted without the product fact
hardwires the gap into keys and turns a schema field into a migration. So the
schema question is answered inside this work, not after it. The criterion does
not name the product fact; folded without touching `done_when`, so the review
decides whether it must.

## 2026-08-09: the crop half is wired; the checkpoint half is not started

What landed. `tools/footage.py` is the second source tool and the first
decoder-read one: it opens a video through `decode/reader.py` in the format
the graph derives, carries `first_index` so a file that is a window out of a
longer source answers in source numbering, and declares `ToolSource.decoded`,
which is the contract change ADR-24 needed and which `Dag.node_keys` is the
one reader of. `pipeline/crop_serving.serving_edit` is the match `resolve`
used to make per run, made once and returned as a `Project`:  each root crop
node becomes a `footage` node over the written file, every replicate's region
override becomes a path and an offset, and `sieve materialize` applies it on
the invocation that makes it offerable. `resolve`, `ResolvedSource`,
`OffsetFrameSource`, `crop_bound` and `elided` are gone, `_route` with them,
and `run_cmd` opens no container at all for a graph whose every root reads its
own file. `crop_binding`'s four states are untouched and now report whether an
edit is offerable.

Two rulings this item's prose left to it, taken here and stated so the review
can disagree with them rather than discover them. **The offer is whole-
document**: one pipeline serves every replicate, so a crop node cannot be a
`footage` node for the arena whose file exists and a crop for the arena whose
file does not, and `serving_edit` therefore answers `None` until every target
has a record. `sieve materialize` cuts one replicate per invocation, so that
is a real state and not a formality. **Coverage stops being a clause**: there
is no parent to decline back to once the file is the source, which is the
position a folder of already-cut files was always in, so a window past what
the file holds is a decode error naming it rather than a fallback. What
replaces the clause is that `materialize_cmd` cuts the whole video's read
range and the edit is reversible — the records survive it.

The key equality the paragraph beginning “Cache keys are not one guard over
both halves” asks for is **satisfied one hop up from where it is written**, and
no choice available under ADR-18 satisfies it as written. Measured and argued
in a dated amendment to
[findings/2026.08.09-a-source-tool-root-keys-in-a-different-flavour-than-the-footage-it-replaces.md](../findings/2026.08.09-a-source-tool-root-keys-in-a-different-flavour-than-the-footage-it-replaces.md):
the served root's upstream *is* `source_key(<file>, decode_format)`, the string
that file folds as footage; but a source tool is a node, so the nodes below it
fold its node key and not that string, and its key must carry `first_index` or
two windows out of one file collide. Taking the edit therefore re-keys the
subtree once. The criterion's first case is written against the root's flavour
and passes; whether ADR-18's key paragraph wants narrowing is Kendrick's.

**The checkpoint half is not begun, and the criterion does not cover it.** All
four cases are about the crop half. What the checkpoint half still owes is
unchanged: a read-back source tool, the key-bearing identity that must say
which product a checkpoint holds
([a-checkpoint-does-not-record-which-product-it-holds.md](a-checkpoint-does-not-record-which-product-it-holds.md)),
and the re-statement of Phase 5's second gate in `PLAN.md` — which this item's
own text says is proposed to Kendrick and not written past him, so it is not
written here. `tools/footage.py` is most of the mechanism the read-back needs;
what it is missing is the schema answer, which is a decision and not code.

Two things the review should weigh. The criterion may want a fifth case
pinning the flavour split itself — a decoder-read root keying `source_key`
while `pick` stays bare — which
`test_crop_serving.py::test_the_served_root_folds_the_key_its_file_would_fold_as_footage`
asserts one half of and `tests/unit/test_preview.py` the other; widening is the
reviewer's. And `_ReaderPool` in `tools/footage.py` holds its readers open past
the end of a run, because the executor has no lifecycle hook for a source tool
— bounded at two, closed on eviction, and named there rather than left as a
surprise.
Left untouched on purpose: `PLAN.md`'s two Phase 5 sentences describing
`resolve_source.py` as the module that answers “which file a run opens, in
whose frame numbering”. That is now `tools/footage.py` and
`pipeline/crop_serving.py`, so the sentences are stale — but editing the build
sequence is a change to the plan, which this item's own text rules is proposed
to Kendrick rather than written past him. Named here so it is a decision
someone takes rather than a line nobody notices.
