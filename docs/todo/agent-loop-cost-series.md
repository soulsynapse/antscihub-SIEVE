---
title: Where agent wall-clock goes, as a series rather than a reading
status: open
opened: 2026-07-28

gated_on: >
  nothing — the miner exists and is tested; what is missing is a baseline, so
  no tooling or docs change can currently be scored

reads:
  - tools/transcript_stats.py
  - tests/unit/test_transcript_stats.py
  - tools/doc_index.py
  - docs/findings/2026.07.27-session-time-is-generation-not-tools.md
  - docs/todo/slow-path-surfacing.md
---

# Where agent wall-clock goes, as a series rather than a reading

`tools/transcript_stats.py` already answers "where did this session's time
go", down to the residual-attribution heuristic its docstring documents. It
has four passing unit tests. What it does not have is a **second reading**, so
every number it produces is uncomparable and every change to the loop is
unscored.

That is structurally `docs/todo/slow-path-surfacing.md` — "sessions log how
the app was used, and changes are scored against a moving baseline" — one
layer up, applied to the agent instead of the app. Building a second tool
would be the mistake; the tool is done.

## What to build

Have `nox -s docs` append one dated row per session to a series file, and put
the current split in `docs/.state.md` as one line.

**The line placement is the constraint, not the parsing.** `.state.md` is
compared byte-for-byte by `tests/docs/test_doc_index.py`, so anything that
varies with the working tree or the clock makes the primer stale on every
commit and turns a real staleness failure into noise. That is why tree state
went to the Stop hook and `doc_drift`'s worst line stayed a report. A session
series has the same problem and needs the same kind of answer before the line
is written — most likely: the series file is generated but not compared, and
`.state.md` carries only a value that changes when the *tooling* changes, not
when a session runs.

## What this measures, and what it does not

Transcript timings measure the **harness**, not the model. Residual is
attributed to the phase of the *next* tool call, which the docstring
correctly labels a heuristic: a long think before an edit is charged to
editing. That is fine for scoring a tooling change and wrong for anything
else, and the finding this produces has to say so.

Two of the largest costs need no instrument at all and should not wait on
this: gate wall-clock (~37 s, which is cheap and is not the problem) and
context spent reading documents the session did not need, which is what
`docs/SETTLED.md`, the `status:` frontmatter, and the primer hook were for.
