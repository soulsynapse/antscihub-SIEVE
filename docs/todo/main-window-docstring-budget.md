---
title: main_window.py docstring budget
status: open
priority: unassessed
gated_on: >
  nothing structurally — a Kendrick decision on whether the docstring
  convention's per-symbol ban and 400-word prose cap should exempt this file
reads: [src/sieve/gui/main_window.py, tools/docstring_audit.py]
---

# main_window.py docstring budget

`gui/main_window.py` was picked by `tools/docstring_audit.py --next` for the
docstring-convention sweep (module docstring stating the file's one secret;
no class/function docstrings elsewhere; 250/400-word caps). It is flagged
rather than brought to the convention.

**The secret is genuinely one.** The module docstring already states it: the
window is where a project becomes a file — it holds the session-only state
the document deliberately does not (which file it was read from, and the
`source`/`checkpoints`/`outputs` fields the GUI cannot edit) — and it is the
one object that wires the player, document, preview runner, resource probe,
and tabs together, because it is the one place all of them are reachable at
once. Every method on the class serves that composition-root role; nothing
here is an unrelated second responsibility smuggled in. It does not fit the
flag path's clause (a).

**What does not fit is the budget.** `tools/docstring_audit.py`'s own
measurement: 188-word module docstring (under the 250 cap on its own); 33
symbol docstrings totaling 1,538 words; 1,844 words of comments; 3,570 words
of prose total against the 400-word cap — over by roughly 9x. They are not
restatements of signature or control flow; they are one-off orderings and
race conditions specific to one method: why `_declare_source_home` is called
before `_preview.set_crops` in `_write_project` (a Save As rebases the
document's records before anything resolves a path against the new home);
why `_pending_project` is read and cleared before either branch of
`_on_opened` runs (a neighbour-project open can populate a project of its
own, and a stale pending entry would apply to the wrong video); why
`closeEvent` shuts the probe down before the player and the metrics adapter
before the preview runner (each is a specific use-after-free or delivery-to-a-
dead-thread hazard in Qt's shutdown order); why history is retargeted after
both branches of `_on_opened` rather than inside either (a neighbour project
can move where history belongs, and retargeting is idempotent so doing it
twice costs nothing but doing it once in the wrong place would miss the
move). Each is local to its one method, underivable from the code, and has no
other natural owner — not a measurement (`docs/findings/`), not an
architecture rule (`docs/ARCHITECTURE.md` or a PAR-style rationale) so much
as the specific reason one method's statements are ordered the way they are.
Folding 33 of these into one 250-word module docstring would not compress
them, it would delete them — clause (c) of the flag path: "the prose is
load-bearing in a way the budget would destroy... it records why the code is
the shape it is in a way the code cannot."

**No split is proposed.** Every method reads or writes the same handful of
fields (`_project`, `_project_path`, `_pending_project`, `_history`,
`_document`, `_preview`, `_player`) in orderings that depend on each other
across methods (open depends on close's cleanup, save depends on the same
home-declaration adopt uses, history retargeting depends on both the open and
the project-adopt paths). The co-change check CLAUDE.md prescribes was not
run because there is no candidate second file to check it against — nothing
here is a plausible second module, only a single class with more methods than
the per-symbol ban's budget was sized for.

**What this item is asking Kendrick to decide**, one of:
1. Add `gui/main_window.py` to `CONTRACT_MODULES` in
   `tools/docstring_audit.py` (600/900-word caps, per-symbol docstrings
   allowed) — the same treatment already requested for `gui/document.py`
   (`docs/todo/document-docstring-budget.md`) and `gui/preview_runner.py`
   (`docs/todo/preview-runner-docstring-budget.md`) for the same reason: a
   reader arrives at one method by hovering it, not by reading the file start
   to end, and the window's shutdown- and load-ordering hazards are exactly
   the kind of thing a hover should surface before a caller trips over them.
2. Accept the loss and force the file to the convention anyway, moving what
   survives triage into the module docstring and accepting that the rest (the
   ordering rationale for save/load/close/shutdown) is deleted rather than
   relocated, since nothing else in the doc tree owns per-method
   implementation rationale at this grain.
3. Leave it flagged permanently, the same as `filter_tab.py`.

No code or docstring in `main_window.py` was changed by this pass.
