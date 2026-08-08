---
title: awaiting-review returns to the selection rule
priority: normal
status: done
gated_on: nothing
opened: 2026-08-07
---

# awaiting-review returns to the selection rule

`--next` answers with the lowest *open* step, so an item goes invisible the
moment a worker claims it, and nothing in the repo emits the review that
would move it on — the review is typed by hand
(`findings/loop/2026.08.07-awaiting-review-leaves-the-selection-rule-and-never-returns.md`).
An item that is finished-but-unreviewed and an item that does not exist look
identical to the queue.

`--next` should answer with the work that is actually next, which is a review
when one is pending and the lowest open step otherwise, and say which it is.
The reason it does not is worth keeping: a worker must not be able to review
its own item (`agent-must-not-author-its-own-completion`), and a selection
rule that hands the same session both is exactly that failure. So the answer
is the shape of the output, not a new status — `--next` names the item and
the role, and the queue starts the session that role belongs to.

What this cannot fix from inside the repo is a review that never gets run.
That is the harness's half, and this item's job is to make the omission
visible in `--next` rather than only in a stalled index.

## Closed on code that landed under other work (2026-08-07)

`next_action` in `scripts/doc_index.py` is this item built: it returns a role
beside the path, answers `review` ahead of the queue head when one is pending,
and its docstring cites the same finding this item does. The item never moved
because it carries no criterion, so nothing re-read it once the code existed —
which is the shape the merge-first rule in CLAUDE.md exists to reduce and the
argument for a criterion being what closes an item rather than a reader.

The harness half above is unchanged and is not owed here: a review that is
never queued is invisible to `--next` by construction, and it is the
orchestrator that would notice.
