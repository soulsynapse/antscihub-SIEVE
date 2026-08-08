---
title: A run commits what it wrote
priority: high
status: done
gated_on: nothing
opened: 2026-08-07
---

# A run commits what it wrote

02.1's work run wrote nothing outside `docs/todo/`, ran one `git add -A`, and
shipped a hand edit to `CLAUDE.md` that was already sitting uncommitted in
the worktree — under its own authorship, under a message about something else
(`findings/loop/2026.08.07-git-add--a-commits-the-tree-the-run-inherited-not-the-work-it-did.md`).
The commit log is the only durable record of who decided what, and a run that
sweeps the tree it inherited makes that record wrong in the direction nobody
checks: it attributes a human's decision to an agent.

Two halves. The instruction half is that a run stages the paths it wrote, by
name, and never `-A`. The checkable half is that a run that finds unexpected
uncommitted changes at its start says so before it starts working — which is
also the only way a human's in-progress edit survives a queued session.

The worktree is shared with v2 through one `.git`, so "unexpected" has to be
defined against this branch's tree and not against the repository.

## Adjudicated against the prose, with no criterion to re-run (2026-08-07)

Both halves landed in `71508df`, and this review re-verified them rather than
reading the transcript that claimed them. Instruction half: `CLAUDE.md` says to
stage by explicit path and never `-A`. Checkable half: `scripts/inherited_changes.py`
reports the porcelain lines a run inherited, and all three loop prompts open with
it. Scope is the worktree — `test_a_sibling_worktrees_dirt_is_not_this_ones`
dirties a second worktree of the same `.git` and asserts each side sees only its
own, which is the paragraph above as a case.

`tests/scripts/test_inherited_changes.py` is 7 passed, and an independent
mutation sweep killed the git-failed raise, `--untracked-files=no`,
`--ignored`, an unset `cwd`, and the dirty exit code flipped to `0`. A sixth
survived: dropping the `if line.strip()` clause in `inherited()` changes no
test, because `git status --porcelain` emits no blank line for it to drop. It
is dead rather than wrong, and left alone here.

Closed without a `done_when`, which is not the protocol's preference. This item
is in `UNSPECIFIED_DEBT`, and that set is shrink-only against a ratchet in
`tests/docs/test_doc_index.py`: writing a criterion here means deleting the name
from `scripts/doc_index.py`, and a review does not edit code. The adjudication
is therefore against the two-halves paragraph above, which is what the item
actually asked for.
