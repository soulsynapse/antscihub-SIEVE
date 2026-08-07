---
title: A checkpoint writes its node's output to the project folder
step: "05.3"
status: open
gated_on: nothing
done_when: "uv run pytest tests/integration/test_checkpoints.py -q"
opened: 2026-08-07
---

# A checkpoint writes its node's output to the project folder

The one item here with no v2 code under it. v2 declared `Project.checkpoints`
and `Project.outputs`, validated both, and then only *printed* the sink list
from `run_cmd` — nothing ever wrote one. v3 does not carry a field nothing
consumes (`adr/declared-means-verified.md`), so either schema v1 loses two
fields or this gets built, and VISION's user checking off the outputs they
want persisted before pressing process settles which.

What lands: a run writes each checkpointed node's per-frame output into the
project folder, and a sink record says where and in what format. The format
is this item's decision and it is recorded as one — a file per checkpoint,
readable without SIEVE, is the default the revival table's zarr row is
measured against later. The writer lives in `storage/` beside `crop_writer`,
which is the second output format VISION's never-line holds against "before
someone asks"; this is the ask.

Two claims the test must make, because they are what the fields are shaped
for. Changing the checkpoint list between two runs moves no cache key —
`checkpoints` is on `Project` for exactly that reason, and a cluster run that
turns them off must be the same run. And a checkpointed run and an
unpersisted one produce identical results, so a checkpoint only ever changes
how much is recomputed.

There is no v2 test file to port, so the criterion is a new one and the
case table does not apply. What replaces it: each claim above is a named
test, and the item says so before the code exists.
