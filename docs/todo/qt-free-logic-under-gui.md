---
title: Qt-free logic is stranded under gui/
status: open
priority: unassessed
after: [headless-detection, the-mutual-tier]
opened: 2026-07-28T12:57:15-07:00

gated_on: >
  nothing structurally — but the rework moves the biggest rows on its own
  terms (rescoped 2026-07-29: this item is the residue, not the plan)

reads:
  - docs/SCAFFOLD.md
  - .importlinter
  - src/sieve/gui/chain_model.py
  - src/sieve/gui/timeline/geometry.py
  - src/sieve/gui/transport/pacing.py
---

# Qt-free logic is stranded under gui/

> **Rescoped 2026-07-29.** The rework claims the big rows on its own terms:
> `chain_model`'s computation dissolves through `detection-is-a-filter` and
> `detector-state-dies`, `concurrency`'s readings move with `the-mutual-tier`
> (its *policy* stays in `gui/` — ARCHITECTURE's "policy belongs to the
> process sharing a machine"), and `wizard_model`'s judging half follows
> `one-definition-of-edge-legality`. What this item still owns is the
> residue's per-module call — `timeline_model`, `crop_binding`,
> `series_collector`, and the probably-stay set below — made after those
> land, with the stays recorded so the analysis is not re-run.

Seven modules under `src/sieve/gui/` import no PySide6 at all — 2,072 lines of
domain logic sitting in the topmost layer, where nothing below can reach it.
`history.py` (225 lines), `crop_binding.py` (218), and `series_collector.py`
(170) were the tenth, ninth, and eighth and have since moved; see the
per-module call below.

| module | lines |
|---|---|
| `wizard_model.py` | 477 |
| `chain_model.py` | 497 |
| `concurrency.py` | 306 |
| `timeline_model.py` (now `src/sieve/gui/transport/pacing.py` + `src/sieve/gui/timeline/geometry.py`) | 292 |
| `coalescer.py` (now `src/sieve/gui/transport/coalescer.py`) | 240 |
| `scrub_policy.py` (now `src/sieve/gui/transport/scrub_policy.py`) | 145 |
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
  docs/todo/headless-detection.md, which supersedes this row) and `concurrency`
  (see docs/todo/machine-share-policy-is-above-its-consumers.md).
- **Probably stay.** `scrub_policy`, `editing_sources` — these are interaction
  policy. Qt-free is a testability property here, not evidence of misplacement,
  and moving them would put GUI concerns in a lower layer, which is the
  opposite defect.
- **Split, decided — partly.** `coalescer`: `RequestKind` →
  `core/request_intent.py`; the two slots, the rank arithmetic, and the
  generation stamp stay. The row above filed the whole file as interaction
  policy and that is right about the arithmetic and wrong about the
  vocabulary. Two modules below `gui` had already restated the enum rather
  than import it, and only one of the two restatements was reasoned:
  `decode/prefetch.py` argues its epoch stamp is a *different* mechanism from
  the coalescer's generation and is correct, but `bench/retention_trace.py`
  carried `SCRUB_KIND = "scrub"`, a hand-copied member value, because `bench`
  sits below `gui` in the layers contract and could not import the symbol that
  answers "was this request a drag?" — the question its whole replay scores
  on. The comment on that constant conceded the defect and could only offer a
  Qt test driving a real cursor as the thing that would notice drift. The
  enum's docstring also claimed it "governs rank, snapping, caching, and
  timing" while all four governances were spelled as separate comparisons at
  four call sites, so the four predicates moved with it and that sentence is
  now code. `SETTLED.md`'s coalescer row stays true as written: it is about
  the two slots and the rank rule, and those did not move.
- **Moved, decided.** `history` → `core/history.py`. The row above had it as
  interaction policy and that was wrong about half the file: *when* to snapshot
  is the window's, but the `.history/` directory, the `NNNNNN-kind-slug`
  filename grammar, and the retention rule are how the artifact reads back
  without SIEVE running, which is rule 8 and not a GUI concern at all. The
  giveaway is that the two halves separated cleanly — `age_text` went to
  `history_dialog.py` and nothing else in the file was reached for. Not
  `storage/`: that package declares it never knows a project.
- **Moved, decided.** `crop_binding` → `pipeline/crop_binding.py`. Not `core/`,
  which is what its imports alone would have suggested: it walks the same
  clauses over the same records as `pipeline/resolve_source.py`, so a clause
  added to `CropArtifact.backs` is owed to both and they change in one commit or
  one of them is silently wrong. The row above justified the move as something a
  CLI report would want, which understates it — `resolve_source` falls back to
  the parent and says nothing about the artifact sitting beside it, which is
  rule 6's underclaim, and the sentence that fixes it was one layer out of
  reach.
- **Moved, decided.** `series_collector` → `pipeline/series_collector.py`. The
  row above filed it as a plot feeder, which reads as presentation and is why it
  sat undecided: what it actually holds is how a run's per-frame output becomes
  the array a detector runs on. `cli/detect_cmd._collect` is the same assembly
  written a second time one layer down — this class with the revision fence
  removed, because a batch run has nothing to supersede — and two answers to
  *what the detector was run on* is precisely the drift
  `tests/gui/test_gui_cli_parity.py` was built to catch. Not `core/`: it is
  typed on `executor.FrameResult`.
- **Split, decided — and the residue split again.** `timeline_model` → the
  window rules to `core/clip_window.py`; `Geometry` and
  `playback_step`/`feed_bounds` stay under `gui/`. They no longer stay
  *together*: drawing `gui/transport/` and `gui/timeline/` as packages put the
  two halves on opposite sides — `src/sieve/gui/transport/pacing.py` and
  `src/sieve/gui/timeline/geometry.py` — because a single module consumed by
  both would have made the two packages import each other. Which is this row's
  own "not two-way but three" arriving one file later than it predicted. The
  deciding precedent is `ROI`: its `clamped_to` and `resized_in` are on
  `core/types.py` while its pixel mapping is in `video_view`/`zoom`, and
  `ClipRange` — the other saved geometry — had the same algebra one layer up
  for no reason but build order. The gap that proves it is real:
  `cli/common.span_for` returns `project.clip` verbatim, so a saved span that
  outruns the video actually bound runs partly off the end, where the GUI's
  `fitted` shows the honest `None`. Fixing that is a behaviour change and its
  own item; this move is what puts the function within reach.
- **Split, decided — partly.** `wizard_model`: the guidance grammar (`Guidance`,
  `parse_guidance`, `guidance_for`) → `src/sieve/filters/__init__.py`; the
  catalog, the seam judging, and the chain building stay. `guidance_path` was
  already there, and "where the `.md` is" and "what the `.md` is made of" are
  one fact under two names — the §3 convention moves them in one commit. The
  proof that the layer was wrong, not just the file: the §3 guardrail in
  `tests/unit/test_filter_discovery.py` could assert the file *existed* and
  nothing more, because the only code that knew the three section headers sat
  above the package it was checking. It now asserts the sections are there and
  non-empty, which is a claim §3 always meant and could not make. The move
  also surfaced a live defect — the reader caught `ValueError` where
  `guidance_path` raises `LookupError`, so a filter defined in a REPL or an
  `exec` would have taken the wizard pane down instead of degrading to its
  summary, which is what the docstring claimed it did.
- **Moved, decided.** `wizard_model._linear_order` → `pipeline/dag.linear_order`.
  The row above left it undecided because its argument in place — deliberately
  not topological — answers why it is a different function and not why it lives
  in `gui`. It is a question about the graph's shape asked of a `Pipeline`, and
  `dag.py` is where "what shape is this graph" is answered; `graph_needs_chroma`
  is the precedent, a module-level function over a raw `Pipeline` written for a
  GUI caller. The giveaway that the layer was wrong: it raised bare `ValueError`
  where every other refusal over the same structure raises a `GraphError`, so a
  caller wanting to catch "this graph cannot run as written" had to catch two
  vocabularies. It now raises `GraphError` — still a `ValueError`, so no caller
  changed. It takes no registry and builds no `Dag`, which is the property that
  keeps it separate from `Dag.order` rather than a second implementation of it:
  a chain whose filters are all missing is still a chain, and that is what lets
  the stack rebuild from a project before knowing whether the project runs.

Do the per-module call in the item, and record the ones that stayed with the
reason, so the next reader does not re-run the same analysis and reach a
different answer.

**Order matters.** headless-detection.md moves `chain_model`'s substance on its
own terms and with a designed boundary. Doing this item first would move the
file and leave the boundary undesigned, which is the more expensive mistake.
