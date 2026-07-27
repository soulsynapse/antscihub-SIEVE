---
title: Migrate LATER.md into item files
status: open
opened: 2026-07-27
gated_on: nothing structurally — mechanical migration, exemplar established
reads:
  - docs/LATER.md
  - docs/todo/_TEMPLATE.md
  - docs/todo/sink-writers.md
---

# Migrate LATER.md into item files

**Intended for a mid-tier model (Opus); the shape is frozen, only the moves
remain.** The one judgment-bearing step is compressing each section's trigger
into `gated_on:` — when in doubt, quote the first sentence of the section's
"What would make it the right time" paragraph rather than paraphrasing. A
mis-stated trigger is worse than a verbose one.

## The recipe, per section

`docs/todo/sink-writers.md` is the migrated exemplar — match it exactly.

1. Create `docs/todo/<slug>.md` with frontmatter: `title` (the section
   heading, verbatim), `status: deferred`, `gated_on` (compressed as above),
   `reads` (the section's trailing `Read:` line, as a list; keep prose
   annotations out of the list, paths only).
2. **Body: the section text verbatim.** Do not summarize, trim, or improve it.
   The bodies carry constraints that cost a day to re-derive; fidelity is the
   whole job. Keep the trailing `Read:` prose line in the body too — it
   carries annotations the frontmatter list drops.
3. Omit `opened:` unless the section text dates itself (most do not).
4. Delete the section from `LATER.md`.

## The slugs, so cross-references resolve

gpu-execution, kernel-protocol-beyond-one-frame, coverage-and-detection-lanes,
replicate-status-columns, click-through-navigation, tuning-files,
annotation-spans, surrogate-calibration, accuracy-feedback, cache-eviction,
materialization, process-isolation, hpc-handoff-and-review-mode,
pipeline-editor-list-or-graph, slider-to-graph, application-config,
profiling-as-a-module.

`docs/todo/seeker-upgrades.md` already links `coverage-and-detection-lanes.md`
by this name — that reference must resolve when you are done.

## Special cases

- **Click-through navigation** and **Materialization** describe themselves as
  one item approached from both ends. Migrate them as *two* files that link
  each other (`[[...]]`-free, plain relative links); do not merge them — that
  is a judgment call this migration must not make.
- Sections cross-reference each other as "the entry above/below". Rewrite
  those phrases to name the target file (`the deferred **Sink writers** item,
  docs/todo/sink-writers.md`) — this is the only permitted edit to body text.
- References *from* records (`docs/completed-todo/`, `docs/findings/`,
  VISION/REFINED-VISION/SIEVE-HANDOFF) to LATER.md stay untouched: records
  are not maintained.

## Finishing

1. When the last section moves, delete `LATER.md` outright — `docs/.state.md`
   stops mentioning it automatically.
2. Grep living docs (`CLAUDE.md`, `docs/TODO.md`, `docs/todo/*.md`) for
   `LATER.md` and update any stragglers to point at `docs/todo/`.
3. `uv run nox -s checks` and `uv run nox -s docs` must both pass.
4. Complete this item the new way:
   `uv run python tools/complete_item.py migrate-later-into-item-files`,
   fill the entry, commit, push.
