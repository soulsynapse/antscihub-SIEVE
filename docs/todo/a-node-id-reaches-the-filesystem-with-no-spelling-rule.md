---
title: A node id reaches the filesystem with no spelling rule
status: open
priority: normal
phase: 2
gated_on: nothing
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
