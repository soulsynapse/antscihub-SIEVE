---
title: Qt-free logic is stranded under gui/
status: open
priority: unassessed
after: [headless-detection]
opened: 2026-07-28

gated_on: >
  nothing structurally — but do headless-detection.md first, which moves the
  largest of these on its own terms

reads:
  - docs/SCAFFOLD.md
  - .importlinter
  - src/sieve/gui/chain_model.py
  - src/sieve/gui/timeline_model.py
---

# Qt-free logic is stranded under gui/

Ten modules under `src/sieve/gui/` import no PySide6 at all — 2,685 lines of
domain logic sitting in the topmost layer, where nothing below can reach it:

| module | lines |
|---|---|
| `wizard_model.py` | 526 |
| `chain_model.py` | 497 |
| `concurrency.py` | 306 |
| `timeline_model.py` | 292 |
| `coalescer.py` | 240 |
| `history.py` | 225 |
| `crop_binding.py` | 218 |
| `series_collector.py` | 170 |
| `scrub_policy.py` | 145 |
| `editing_sources.py` | 66 |

`docs/SCAFFOLD.md` already annotates `chain_model.py` as "its Qt-free half", so
the split was deliberate at the file level. What was not decided is the
*layer*: a Qt-free module under `gui/` is still unreachable from `cli`,
`pipeline`, and `bench`, because the layers contract makes `gui` and `cli`
siblings.

**This item is placement, not design.** Nothing is split and nothing is
rewritten; files move down and imports follow. The gate proves it: pyright
strict catches a missed import, and `.importlinter` catches a module that moved
below a layer it still depends on — which is exactly the signal that a given
module has *not* in fact shed its GUI coupling.

**Not all ten should move, and the test is one question:** does anything below
`gui` have a use for it, actually or plausibly? Provisional read, to be checked
per module rather than assumed:

- **Move.** `chain_model` (goes to `sieve.detect` — see
  docs/todo/headless-detection.md, which supersedes this row), `concurrency`
  (see docs/todo/machine-share-policy-is-above-its-consumers.md),
  `timeline_model` and `crop_binding` — window arithmetic and boundary-state
  derivation that a CLI reporting on a project would want.
- **Probably stay.** `coalescer`, `scrub_policy`, `history`, `editing_sources`
  — these are interaction policy. Qt-free is a testability property here, not
  evidence of misplacement, and moving them would put GUI concerns in a lower
  layer, which is the opposite defect.
- **Undecided.** `wizard_model`, `series_collector`.

Do the per-module call in the item, and record the ones that stayed with the
reason, so the next reader does not re-run the same analysis and reach a
different answer.

**Order matters.** headless-detection.md moves `chain_model`'s substance on its
own terms and with a designed boundary. Doing this item first would move the
file and leave the boundary undesigned, which is the more expensive mistake.
