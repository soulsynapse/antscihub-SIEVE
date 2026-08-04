---
title: document.py docstring budget
status: open
priority: unassessed
gated_on: >
  nothing structurally — a Kendrick decision on whether the docstring
  convention's per-symbol ban and 400-word prose cap should exempt this file
reads: [src/sieve/gui/document.py, tools/docstring_audit.py]
---

# document.py docstring budget

`gui/document.py` was picked by `tools/docstring_audit.py --next` for
the docstring-convention sweep (module docstring stating the file's one
secret; no class/function docstrings elsewhere; 250/400-word caps). It is
flagged rather than brought to the convention.

**The secret is genuinely one.** The module docstring already states it: the
document is a `ReplicateSet` plus its undo history, GUI-side because undo is
GUI state, and every mutation goes through a `QUndoCommand` without
exception. This is not a file hiding two or more unrelated decisions in
`docstring_audit.py --next`'s sense — it does not fit the flag path's clause
(a).

**What does not fit is the budget.** `tools/docstring_audit.py`'s own
measurement: 67 symbol docstrings totaling 4,545 words, 1,098 words of
comments, 5,793 words of prose against a 400-word cap — the cap by roughly
14x. Reading through them, they are not restatements of signatures or control
flow (the "could a competent reader derive this from the code" test that
CLAUDE.md and the sweep prompt both use); they are one-off, non-obvious
reasons for a specific method's shape: why `window` derives its fallback on
every read instead of writing it into `_clip` (so a project saved before the
user chooses a window comes back with no window chosen, not "the whole
video"); why `finish_roi_gesture` fires its confirmation on release rather
than per mouse-move; why `_reset` drops crops with the source rather than
the home; why signal emission order in `load_project` and `apply_state`
matters (selection before pipeline, clip last). Each is local to its one
method, underivable from the code, and has no other natural owner — it is
not a measurement (`docs/findings/`), not filter science (a filter's `.md`),
and not an architecture rule (`docs/ARCHITECTURE.md` or a PAR-style
rationale) so much as the specific reason one method on one class is shaped
the way it is. Folding 67 of these into one 250-word module docstring would
not compress them, it would delete them — which is exactly clause (c) of the
flag path: "the prose is load-bearing in a way the budget would destroy...
it records why the code is the shape it is in a way the code cannot."

**No split is proposed.** CLAUDE.md's own co-change example already measured
this file's seam with `replicate_tab.py` and found it holding (8 together
against 9 and 10 alone) — a seam that should stay one file. The per-method
docstring volume is not evidence of multiple secrets; it is evidence that one
coherent secret was documented at a finer grain than the sweep's budget
assumes. The co-change check was not re-run here because nothing about that
finding is in question — this item is about the docstring cap, not about
where the module boundary sits.

**What this item is asking Kendrick to decide**, one of:
1. Add `gui/document.py` to `CONTRACT_MODULES` in
   `tools/docstring_audit.py` (600/900-word caps, per-symbol docstrings
   allowed) — the same treatment `core/filter_base.py`,
   `core/pipeline_model.py`, and `pipeline/cache_key.py` already get, on the
   grounds that this file's method-level rationale is read the same way a
   contract module's is: a caller arrives by hovering a symbol, not by
   reading start to end.
2. Accept the loss and force the file to the convention anyway, moving what
   survives triage into the module docstring and accepting that the rest
   (drag-gesture timing, signal-ordering reasons, the crop/window/detector
   None-vs-derived distinctions) is deleted rather than relocated, since
   nothing else in the doc tree owns per-method implementation rationale at
   this grain.
3. Leave it flagged permanently, the same as `filter_tab.py`.

No code or docstring in `document.py` was changed by this pass.
