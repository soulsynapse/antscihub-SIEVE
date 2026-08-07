---
title: CLAUDE.md tells a new session the tree is empty
priority: high
status: open
gated_on: nothing
done_when: "uv run python -c \"import pathlib,sys; t=pathlib.Path('CLAUDE.md').read_text(encoding='utf-8'); sys.exit(any(p in t for p in ('There is no code yet','not an installed file')))\""
opened: 2026-08-07
---

# CLAUDE.md tells a new session the tree is empty

`CLAUDE.md` opens with "v3 is an orphan branch. There is no code yet and the
absence is the point". The branch now carries 51 modules under `src/sieve/`,
ten tools, six import contracts and 608 tests, so the first paragraph a session
reads is false, and the section under it ("What deliberately isn't here")
inherits the doubt — a reader who has just been told the tree is empty cannot
tell which of its claims were true when written and which are true now.

The sentence worth keeping is the rule, not the state: a component exists once
it has been scoped, not before. What should be different is that the opening
describes the branch as it is and states that rule as a rule, and that the
neighbouring claims about what is absent are checked against the tree in the
same pass rather than trusted — `.importlinter` in particular is called a
Phase-0 item that is not an installed file, and it has been one since 0c79929.

Repo-wide, so no phase: the file is read by every run in every phase, which is
also why it is `high` — a stale onboarding paragraph is wrong for each of them
in turn.
