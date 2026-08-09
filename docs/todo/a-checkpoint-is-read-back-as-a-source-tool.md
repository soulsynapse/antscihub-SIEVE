---
title: A checkpoint is read back as a source tool
status: done
gated_on: nothing
priority: high
phase: "05"
done_when: 'uv run pytest tests/integration -k "a_checkpointed_stretch_is_read_back_as_a_source_tool or a_checkpoints_identity_names_the_product_it_holds or a_read_back_root_is_keyed_off_the_written_file" -q'
opened: 2026-08-09
---

# A checkpoint is read back as a source tool

The second half of
[crop-serving-and-checkpoint-read-back-become-source-tools.md](crop-serving-and-checkpoint-read-back-become-source-tools.md),
moved here rather than copied: that item's crop half landed at `b63f43f`, its
criterion covers only the crop half, and a `-k` criterion cannot be widened to
cover a case that does not exist yet
([findings/loop/2026.08.09-a-k-disjunction-is-green-for-the-disjunct-that-names-nothing.md](../findings/loop/2026.08.09-a-k-disjunction-is-green-for-the-disjunct-that-names-nothing.md)).
So the halves are two items. Nothing here re-decides
[adr/a-users-file-wires-in-like-any-other-input.md](../adr/a-users-file-wires-in-like-any-other-input.md)
or [adr/a-root-keys-by-its-reader.md](../adr/a-root-keys-by-its-reader.md);
what is owed is the checkpoint side of the tree agreeing with them.

This is the cheap half in one respect and the expensive half in another. Cheap:
there is no reader to migrate — the checkpoint side has never had one, so it is
written as a source tool the first time rather than unwound into one, and
`tools/footage.py` is most of the mechanism already. A checkpointed stretch on
disk is a file that stands where a node stood, read back at the node's place,
which is the same sentence a written crop answers to.

Expensive: **the identity a read-back root keys on must say which product it
holds, and minting one without that fact hardwires the gap into keys.**
[a-checkpoint-does-not-record-which-product-it-holds.md](a-checkpoint-does-not-record-which-product-it-holds.md)
holds the gap — neither the manifest nor `Project.checkpoints` can say which
emission of a multi-product node a checkpoint is, `ToolSpec.emissions` means a
node of `block_signal` has four candidates, and 07.9's save screen could not fix
it from its side. That item's own text says the read-back path is where it is
answered, "whichever arrives first", and this is that path. So the schema
question is answered inside this work rather than after it: a key-bearing
identity minted without the product fact turns a schema field into a migration.

**The keys move here, and that is the difference from the crop half.** ADR-24
rules the flavour off the reader, and the crop half's file is read through
`decode/` so it folds `source_key` and moves nothing below it. A checkpoint is
not a video — it is whatever the node emitted — so the reader is not `decode/`
and the flavour question has to be answered rather than inherited. What the key
comes off is the written file's identity rather than the checkpointed node's
key, which is a move, and it is owed here rather than discovered later.

**The Phase 5 gate re-statement is proposed, not written.** `PLAN.md`'s second
Phase 5 gate is stated in terms a plan-time read-back could satisfy and a
document edit cannot. Re-stating it is a change to the build sequence, so this
work proposes the wording to Kendrick and does not write past him — the same
rule the crop half followed for `PLAN.md`'s two now-stale sentences describing
`resolve_source.py` as the module that answers "which file a run opens, in whose
frame numbering". Those sentences are also still there and also his: the answer
is now `tools/footage.py` and `pipeline/crop_serving.py`.

## Folded 2026-08-09: `footage.py` claims a thread-safety it does not have

From the review that closed the crop half. `FootageFile`'s docstring says the
shared `_ReaderPool` means "two concurrent renders over one file share a reader
and neither can advance the other's position — `VideoReader.read` seeks per
call". `decode/reader.py` says the opposite twice: "nothing here is
thread-safe", and above the class, "one reader belongs to one thread. The GUI
keeps its reader on a dedicated decode thread for exactly this reason."
`_ReaderPool` takes no lock, so two threads missing together open two readers
and leak one, and an eviction can `close()` a reader another thread is mid-read
on. Nothing reaches it today — the GUI refills on a `QTimer` on the GUI thread
and the transport's `QThread` holds its own `PrefetchFrameSource` — so this is a
sentence that will be believed before it is tested.

It lands here because this is the next work in that file and the work that
decides whether a second source tool shares that pool at all. Either the claim
comes out or the lock goes in, and which depends on that decision.

`done_when` names three cases and none of them exists, so it is red because
nothing matches: `uv run pytest tests/integration -k "..." -q` exits 5 with 95
deselected on the tree at `b63f43f`. The file they live in is deliberately not
named — where a read-back case belongs depends on whether it joins
`test_checkpoints.py` or earns a file, and the criterion should not pick that.
