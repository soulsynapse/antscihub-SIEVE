# Where things live in v2

`../antscihub-SIEVE-v2` is a sibling worktree of this repo, on `main`. It is
the evidence base, not a parts bin: read it to check a claim; porting a file
from it is a decision, not a shortcut. Paths below are relative to that
worktree.

| If I ask for | Look at |
|---|---|
| The layer contract, or how a boundary was enforced | `.importlinter` — six contracts, each with its rationale in the comments above it |
| v2's filter contract / what a step declares | `src/sieve/core/filter_base.py` |
| The saved artifact, schema, migration | `src/sieve/core/pipeline_model.py`, `src/sieve/pipeline/upgrade.py` |
| Cache keys, what gets hashed | `src/sieve/pipeline/cache_key.py` |
| The one execution loop | `src/sieve/pipeline/executor.py` |
| Edge legality, ordering, the plan | `src/sieve/pipeline/dag.py`, `plan.py` |
| Dimensioned quantities, the frame | `src/sieve/core/types.py` |
| Reading the machine, the share ledger | `src/sieve/mutual/` |
| Decode, prefetch, lowering into ffmpeg | `src/sieve/decode/` |
| Budgets, the metric bus, retention replay | `src/sieve/bench/` |
| Array math with no spec attached | `src/sieve/core/ops/` |
| A v2 filter as a worked example | any `src/sieve/filters/<name>.py` with its `.md` |
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

Reading notes:

- Interface contracts live in module docstrings, not a spec file; the
  docstring is the primary source and the matching `docs/completed-todo/`
  entry is the reasoning behind it.
- An item's text is deleted when it completes. A slug you can't find is in
  git: `git log --diff-filter=D -- docs/todo/<slug>.md`.
- The worktree can hold uncommitted work. Read committed state with
  `git -C ../antscihub-SIEVE-v2 show main:<path>`.
- v2's eight-rule table was not adopted as a set. Rules bind in v3 only as
  individual ADRs — see `docs/ARCHITECTURE.md` for which.
