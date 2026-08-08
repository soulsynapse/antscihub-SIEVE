---
title: The gate is one line, stated once
adr: 19
position: "03.04"
status: settled
decided: 2026-08-07
---

The checks a commit must pass are one `&&`-joined command, written once, in
`ci.yml`'s gate step. Nothing else enumerates them — not a noxfile, not a
README, not a `paths:` entry.

So a contributor runs those characters before pushing and CI runs the same
ones. Why: a second copy drifts, and it drifts in the direction that hurts,
the copy a person runs falling behind the copy that gates the push. That is
not a hypothetical about a noxfile nobody wrote; it happened on the copy
nobody counted as one. `docs/todo/ci-runs-what-a-commit-must-pass.md`'s
`done_when` holds the line character-for-character as its stated content, and
it fell a command behind twice, each time for exactly one commit, each time
repaired by a reviewer noticing rather than by a check. So the rule is about
live copies: a dated record of a gate run is not one — nobody reads a worker
note to decide whether to push — and it becomes one exactly when something
requires it to stay identical to the line.

What this rule costs is that every commit pays for every check, including
checks it cannot fail. That price is weighed at
[ADR 20](a-check-joins-the-gate-line.md). Narrowing by path is refused here
rather than there: "run this one only when these files change" is this same
enumeration in a `paths:` entry's clothing.
