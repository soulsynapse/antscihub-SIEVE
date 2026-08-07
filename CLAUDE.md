# CLAUDE.md — how to work in this repo

SIEVE is a video signal-processing tool for isolating ethological events. Its
value is the speed of the interactive tuning loop: drag a slider, watch the
graphs refill faster than the video plays. Architecture serves that or it does
not belong.

v3 is an orphan branch. There is no code yet and the absence is the point — a
component exists once it has been scoped, not before.

## Where things are

`docs/VISION.md` binds the target: the loop, the primary components with what
each owns and must never own — the never-lists are the forbidden edge set —
and the claims that define built-correctly. Settled decisions bind too, as
ADRs under `docs/adr/` indexed in `docs/ARCHITECTURE.md`; sequence lives in
`docs/PLAN.md`.

`../antscihub-SIEVE-v2` is a sibling worktree of this same repo, on `main`. It
is the evidence base, not a parts bin: v2 ran long enough to show which of its
boundaries held and which needed a bespoke contract written to prop them up,
and VISION.md cites it throughout. Read it to check a claim. Porting a file
from it is a decision, not a shortcut.

`../antscihub-SIEVE` is v2.5, on branch `rewrite`. It is planning that went in
circles. Treat it as a warning.

## What deliberately isn't here

v2 has nox sessions, an import-linter contract, and a completion tool. None
of those exists in v3 yet — the import contracts are a Phase-0 item, not an
installed file. What v3 did adopt is its own item/findings/ADR system with
`scripts/doc_index.py` generating the indexes. Don't recreate the rest by
reflex — port a mechanism when something here needs it, and say in the commit
what needed it.

v3 has also not decided which of v2's eight rules it carries as a set. Some
have since been adopted individually as ADRs (one execution path, the
identity values, declared-means-verified — see `docs/ARCHITECTURE.md`), but
there is no rules table and "non-negotiable #N" cites nothing here.

## "Bring X over from v2"

This means: go read v2's version, work out what it actually decided, and bring
that. It does not mean copy the file. Check `docs/VISION.md` first — it
already has
a verdict on several of these, in both directions (the spec/kernel split and
the decode boundary are marked copy-verbatim; the backend type system and a
separate detection package are marked don't).

Everything below is relative to `../antscihub-SIEVE-v2`.

| If I ask for | Look at |
|---|---|
| The layer contract, or how a boundary was enforced | `.importlinter` — six contracts, each with its rationale in the comments above it |
| The filter contract / what a step declares | `src/sieve/core/filter_base.py` |
| The saved artifact, schema, migration | `src/sieve/core/pipeline_model.py`, `src/sieve/pipeline/upgrade.py` |
| Cache keys, what gets hashed | `src/sieve/pipeline/cache_key.py` |
| The one execution loop | `src/sieve/pipeline/executor.py` |
| Edge legality, ordering, the plan | `src/sieve/pipeline/dag.py`, `plan.py` |
| Dimensioned quantities, the frame | `src/sieve/core/types.py` |
| Reading the machine, the share ledger | `src/sieve/mutual/` |
| Decode, prefetch, lowering into ffmpeg | `src/sieve/decode/` |
| Budgets, the metric bus, retention replay | `src/sieve/bench/` |
| Array math with no spec attached | `src/sieve/core/ops/` |
| A filter as a worked example | any `src/sieve/filters/<name>.py` with its `.md` |
| The import-graph extractor and viewer | `graph-system/` |
| Gates, sessions, what CI runs | `noxfile.py`, `.github/workflows/ci.yml` |
| Test layout, the synthetic video fixture | `tests/conftest.py` |
| The rules, the objectives, the budget table | `docs/ARCHITECTURE.md` |
| What overrode the rules late in v2 | `docs/REWORK.md` — six rules that beat older docs where they disagree |
| Why something is the way it is | `docs/completed-todo/.index.md`, then the entry |
| What is measurably true | `docs/findings/.index.md` |
| What was known-broken or parked, and on what trigger | `docs/todo/` — `status: open` and `deferred`, trigger in `gated_on` |
| What v2 decided not to re-decide | `docs/SETTLED.md` |
| What the product is for | the VISION and REFINED-VISION records under `docs/` |

Two things about reading it. Interface contracts live in module docstrings
rather than in a spec file, so the docstring is the primary source and the
matching `docs/completed-todo/` entry is the reasoning behind it. And an item's
own text is deleted when the item completes, so when an entry references a slug
you can't find, it's in git: `git log --diff-filter=D -- docs/todo/<slug>.md`.

That worktree can have uncommitted work in it. To read what's actually on the
branch, `git -C ../antscihub-SIEVE-v2 show main:<path>`.

## Comments

A comment earns its place by recording something the code cannot show: why this
and not the obvious alternative, a constraint from outside the file, a failure
mode that leaves no trace. The test is whether a competent reader could derive
the sentence from the code. If they could, delete it; if they couldn't, that is
the whole value and shortening it is the wrong cut.

Don't narrate what the next line does, don't address the reader, and don't
write to the reviewer — "changed this because…" is a commit message. A comment
describing a shape the code has moved past isn't stale, it's wrong, and git
holds the old shape anyway.

Match the comment density of the file you're in. Fix what you find in a file
you're already editing; a sweep for its own sake is churn.

## Docs

Say why, not what happened — a doc that only lists changes is a changelog and
git already is one. One fact, one home: if you're about to restate something
another file holds, link to it instead.

Prefer a claim a test can check over a paragraph a reader must trust. In v2 the
machine-checked tables stayed true while the prose around them drifted, and
that difference is the whole argument.

## Commits

`type(scope): the sentence, not the changelog line`. `type` is one of `feat`,
`fix`, `refactor`, `perf`, `docs`, `test`, `build`, `ci`, `chore`; scope is
omitted when nothing owns the change. `docs: order the docs by when things
happened, not by the alphabet` is the shape — `docs: update docs` is not.

You may push when given permission, but not otherwise.

## Platform

Windows. PowerShell by default, with a Bash tool also available. This directory
is a git worktree, so `.git` is a file rather than a directory — anything that
assumes otherwise fails in a confusing way.
