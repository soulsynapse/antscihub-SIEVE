---
title: A node id reaches the filesystem with no spelling rule
status: awaiting-review
priority: normal
phase: 2
gated_on: nothing
done_when: "uv run pytest tests/unit/test_pipeline_model.py -q -k a_node_id_the_filesystem_cannot_hold_is_refused_at_load"
opened: 2026-08-07
---

# A node id reaches the filesystem with no spelling rule

`Node.node_id` is validated for uniqueness and for nothing else. `tool_id` and
`version` both carry a pattern, and the reason given for `tool_id`'s is exactly
the one that now applies to `node_id`: it "appears in paths and CLI arguments
where case folding and shell quoting are not to be relied on". A checkpoint
writes `<node_id>.npy`, so a hand-edited document naming a node `../escape`
aims a write outside the folder it was meant for.

`storage/checkpoint_writer.py` refuses such an id at the point it would become
a file name, which closes the hole for the one writer that exists. What it does
not close is the next one: the guard lives with the consumer rather than with
the field, so a second writer, an `inspect` output path, or a GUI that names a
folder after a node gets to rediscover it. The question this item answers is
whether the pattern belongs on the field — which would make it schema v1's
rule and refuse the document at load rather than at write — or whether a
document is allowed to hold ids a filesystem cannot, with each consumer
sanitising or refusing on its own terms.

Not decided here because it is a schema change with a migration shape to it:
`SCHEMA_VERSION` is 1 and there is no importer, so tightening the field now is
free, and tightening it after a project exists in the wild is not.

The recommendation, since the decision is what this now waits on: put the
pattern on the field. `node_id` defaults to `uuid4().hex`, so nothing SIEVE
generates can fail it, and the ids it would refuse are the ones only a
hand-edited document produces today. The reversibility runs one way — a wider
pattern admits every document a narrower one did, so loosening stays free
after there are projects in the wild, and tightening does not.

What the choice actually costs sits in a surface nothing has scoped. `Node`
carries no label, so `node_id` is the only handle a rename would have to
write on, and a pattern on the field is then a rule about what a user may type
into a GUI — the alternative being a second field that holds the readable name
and leaves the id machine-spelled. That is the half only Kendrick can settle,
and it is why no `done_when` is written here: the command would assert the
answer.

Review fold, 2026-08-07: the reversibility argument above is one-directional
at the schema layer and not at the consumer's. Loosening the pattern later
still admits every document, but the reason to put it on the field is so the
next writer does not carry its own guard — so every consumer written while
the pattern held has to get one back the day it is widened. The freedom to
loosen is bought from the consumers, not free, and that is the half of the
asymmetry the recommendation does not price.

## Ruled 2026-08-08 — the pattern goes on the field

Schema v1 refuses at load. Node ids reach the filesystem through the
checkpoint writer, the manifest, and crop artifacts, and per-consumer
sanitisation mints N mappings that can collide — two ids sanitising to one
file is a rename the record does not survive, which quietly breaks the
reviewer-rerun promise. One pattern on the model, refusal naming the node,
in the `extra=forbid` culture; the checkpoint writer's own guard stays (a
defense at the write is not wrong for existing at the load too), and the
review-fold's price is accepted knowingly: loosening later is bought back
from the consumers.

The GUI half settles the other way than a second field: no label field now.
Nothing displays one — when a Phase 7 surface wants a readable name, the
field arrives with that surface (`adr/declared-means-verified.md`), and until
then the pattern is simply the rule for what may be typed where an id is
typed. Phase 7's AddNode needs a spelling rule from somewhere regardless, and
it should be the schema's, not the widget's.

## Reopened 2026-08-08 — the pattern is anchored one character too loosely

`e0da6ca` implements the ruling and its criterion passes, but the pattern it
landed ends `$` where the writer's deleted `_SAFE_NODE_ID` ended `\Z`. Python's
`$` matches before a final newline, so `node_id: "abc\n"` is refused by the tree
before the commit and accepted by both the schema and the writer after it — a
document that loads clean and reaches `open_memmap` with a newline in the file
name. Measured in
`findings/loop/2026.08.08-consolidating-two-guards-onto-one-constant-narrows-the-stricter-one.md`,
which also records that the suite, the criterion, and three mutation sweeps are
all green either way.

The fix is `\Z` and a trailing-newline id added to the case the `done_when`
already selects, so the criterion is unchanged. `TOOL_ID_PATTERN` and
`SEMVER_PATTERN` anchor with `$` for the same reason and were the precedent
followed here; whether either is reachable by a value with a trailing newline is
a separate question and not this item's.

Worker note, 2026-08-08: `\Z` landed and the criterion's case gained the newline
id by both routes — a direct `Node` and a `from_yaml` whose quoted scalar carries
it. The criterion was green on the unchanged tree and is green now; what changed
is that it can go red. Mutating the constant back to `$` against
`tests/unit/test_pipeline_model.py` and `tests/integration/test_checkpoints.py`
is KILLED, which is the mutant the finding was written because nothing could
kill. The separate question above is now measured and answered yes — both
anchors are reachable by a hand-edited document — and is carried by
`two-ids-anchored-with-dollar-take-a-trailing-newline-from-a-document.md`.
