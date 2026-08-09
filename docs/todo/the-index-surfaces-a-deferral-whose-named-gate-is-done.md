---
title: The index surfaces a deferral whose named gate is done
status: awaiting-review
priority: normal
phase: 0
gated_on: nothing
done_when: "uv run pytest tests/docs/test_doc_index.py -q -k named_gate"
opened: 2026-08-09
---

# The index surfaces a deferral whose named gate is done

A deferred item names its trigger in `gated_on`, and nothing goes red when
the trigger fires: the swap-menu item sat deferred on "the offering predicate
landing" after the predicate was ruled, reviewed done, and standing in the
tree (`matches`, `core/tool_base.py`), because noticing depended on someone
happening to look. The noticing belongs to machinery, not to a reviewer's
diligence — the review prompt's jurisdiction is the run under review, and a
standing scan duty in a prompt produces no difference between a reviewer that
scanned and one that forgot.

Three pieces, one commit's worth:

1. `doc_index.py`: when collecting, for each `deferred` item scan its
   `gated_on` for any substring that is an existing item's filename; if that
   item's status is `done`, the deferral is flagged. The generated index
   gains a table — deferrals whose named gate is done — beside "Waiting on a
   person", so it regenerates every session. The flag **informs and never
   fails**: not a `--check` failure and not an auto-flip, because the right
   response may be "re-argue, don't build" rather than "open", and a status
   move is a ruling. Prose gates ("the first multi-input tool") contain no
   filename and are invisible to the scan — by design, not as a gap: a
   functionally-never deferral must not get nagged open, and its home when
   recognized is PLAN's revival table, which is a ruling too.

2. `docs/todo/_TEMPLATE.md`: one sentence on `gated_on` — when a deferral's
   trigger is another item, cite that item's filename, so the scan can see
   it. Prose triggers stay legal.

3. `tests/docs/test_doc_index.py`: an item deferred on a slug whose item is
   done is flagged; the same wording as prose (no matching filename) is not;
   a slug cited whose item is not done is not. The `done_when` names these
   cases.

Out of scope, because each is a ruling and not work: flipping the swap-menu
item (its gate has lifted and it would be this table's first row), and
whether a-merge-keys-its-inputs-by-port is a blocker or a PLAN revival row.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests/docs/test_doc_index.py -q -k named_gate
    95 deselected in 0.04s
    exit: 5

Green, with the fourth case the outcome asked for beside the three the item
named — the flag informs, so a run of `--check` over a tree holding a flagged
deferral exits 0 and leaves its status where it was:

    $ uv run pytest tests/docs/test_doc_index.py -q -k named_gate
    4 passed, 95 deselected in 0.95s

The table renders empty against this tree: all three live deferrals state
prose triggers, and the two dispositions that would fill it (the swap-menu
item — since flipped to `open` by another hand — and a-merge's) were out of
scope here because each is a ruling.
