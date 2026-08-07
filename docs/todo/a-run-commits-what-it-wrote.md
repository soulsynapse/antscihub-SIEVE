---
title: A run commits what it wrote
priority: high
status: open
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
