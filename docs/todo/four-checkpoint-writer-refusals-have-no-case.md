---
title: Four of the checkpoint writer's refusals have no case, and two have no caller
status: open
priority: normal
phase: 8
gated_on: nothing
opened: 2026-08-07
---

# Four of the checkpoint writer's refusals have no case, and two have no caller

`storage/checkpoint_writer.py` raises `CheckpointWriteError` in six places.
`tests/integration/test_checkpoints.py` reaches two of them — the short span and
the unusable node id. The other four are asserted by nothing:

- `__init__`, on an empty `keys` mapping. Unreachable from `run_cmd`, which
  returns `None` instead of building a writer when `project.checkpoints` is empty.
- `record`, on a frame arriving after `close`.
- `record`, on a frame whose shape or dtype disagrees with the file already
  opened for the node.
- `_output`, on a checkpointed node that produced no output for a frame.
  Unreachable as the executor stands: `_completed` yields a `FrameResult` only
  once every node has answered, so `outputs` is total by construction — and
  `Project` already refuses a checkpoint naming a node the pipeline does not
  hold, which closes the other way in.

Two of these are the good kind of defensive raise and two are dead. The item is
to decide which is which and act on it in both directions: a refusal a caller can
provoke gets a case, and a refusal nothing can reach gets deleted or gets the
caller that justifies it. `adr/declared-means-verified.md` is the same argument
one level down from a schema field — a message a user is promised and can never
see is a claim the code does not keep.

The out-of-order guard in `record` is the interesting one: it is unreachable
today only because `run_cmd` is the single caller and feeds it the executor's
stream directly. It is the guard that would fire the day something else drives a
writer, which is an argument for keeping it and giving it a unit case rather than
for cutting it.
