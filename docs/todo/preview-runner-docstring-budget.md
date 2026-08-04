---
title: preview_runner.py docstring budget
status: open
priority: unassessed
gated_on: >
  nothing structurally — a Kendrick decision on whether the docstring
  convention's per-symbol ban and 400-word prose cap should exempt this file
reads: [src/sieve/gui/preview_runner.py, tools/docstring_audit.py]
---

# preview_runner.py docstring budget

`gui/preview_runner.py` was picked by `tools/docstring_audit.py --next` for
the docstring-convention sweep (module docstring stating the file's one
secret; no class/function docstrings elsewhere; 250/400-word caps). It is
flagged rather than brought to the convention.

**The secret is genuinely one.** The module docstring already states it: this
is `pipeline/preview.py`'s caller — it runs a `PreviewSession` on a thread of
its own, keeps one revision current, drops frames from any render that is no
longer wanted, and keeps the session warm across renders so a second render
after an edit stays cheap. That is one coherent responsibility, not a file
hiding two or more unrelated decisions in `docstring_audit.py --next`'s
sense — it does not fit the flag path's clause (a).

**What does not fit is the budget.** `tools/docstring_audit.py`'s own
measurement: module docstring alone is 776 words against the 250 cap; 39
symbol docstrings totaling 2,439 words; 1,068 words of comments; 4,283 words
of prose total against a 400-word cap — over by roughly 10x. Reading through
them, they are not restatements of signatures or control flow; they are
one-off, non-obvious reasons for one method's shape: why `filter_to_first_tick`
is timed from the GUI thread and not the worker (the budget is what the user
actually waited through, including the thread hop); why cancellation is an
exception raised out of `on_frame` rather than a flag (`execute` is a
generator with no cancel hook, and a flag has no safe moment for either
thread to lower it); why `_reader_for` compares `identity` rather than `path`
(footage replaced under the same name must still rebuild); why a paused
render bumps the revision with nothing issued at it instead of registering as
a fourth `gui/concurrency.py` consumer (rule 5's borrow-not-own distinction
for the materialization writer); why `release_files` is a blocking queued
connection rather than a normal one (the caller's next statement deletes the
file the worker still has open). Each is local to its one method or field,
underivable from the code, and has no other natural owner — not a measurement
(`docs/findings/`), not filter science, not an architecture rule
(`docs/ARCHITECTURE.md` or a PAR-style rationale) so much as the specific
reason one method or field on this class is shaped the way it is. Folding 39
of these into one 250-word module docstring would not compress them, it would
delete them — clause (c) of the flag path: "the prose is load-bearing in a
way the budget would destroy... it records why the code is the shape it is in
a way the code cannot."

**No split is proposed.** The classes here (`_Wanted`, `RenderRequest`,
`_Crops`, `_RenderWorker`, `PreviewRunner`) are the two-thread halves of one
mechanism — a request built on the GUI thread, carried whole across a queued
signal, rendered on the worker thread, and reported back — not independently
useful pieces. The co-change check CLAUDE.md prescribes was not run because
there is no candidate second file to check it against: everything in scope
here already lives in this one module, and the question this item raises is
about the docstring cap, not about where a module boundary should move.

**What this item is asking Kendrick to decide**, one of:
1. Add `gui/preview_runner.py` to `CONTRACT_MODULES` in
   `tools/docstring_audit.py` (600/900-word caps, per-symbol docstrings
   allowed) — the same treatment `core/filter_base.py`,
   `core/pipeline_model.py`, and `pipeline/cache_key.py` already get, and the
   same request `gui/document.py` (`docs/todo/document-docstring-budget.md`)
   already made for the same reason: a reader arrives at one method by
   hovering it, not by reading the file start to end.
2. Accept the loss and force the file to the convention anyway, moving what
   survives triage into the module docstring and accepting that the rest
   (the threading/cancellation rationale, the reader-rebuild conditions, the
   rule 5 pause discipline) is deleted rather than relocated, since nothing
   else in the doc tree owns per-method implementation rationale at this
   grain.
3. Leave it flagged permanently, the same as `filter_tab.py`.

No code or docstring in `preview_runner.py` was changed by this pass.
