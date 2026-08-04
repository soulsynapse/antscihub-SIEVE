---
title: pipeline/preview.py docstring budget
status: open
priority: unassessed
gated_on: >
  nothing structurally — a Kendrick decision on whether the docstring
  convention's per-symbol ban and 400-word prose cap should exempt this file
reads: [src/sieve/pipeline/preview.py, tools/docstring_audit.py]
---

# pipeline/preview.py docstring budget

`pipeline/preview.py` was picked by `tools/docstring_audit.py --next` for the
docstring-convention sweep (module docstring stating the file's one secret;
no class/function docstrings elsewhere; 250/400-word caps). It is flagged
rather than brought to the convention.

**The secret is genuinely one.** `PreviewSession` takes the graph fresh on
every render and relies entirely on `cache_key`'s keying — which folds in
upstream node identity but never the span or the window — to make a
re-render incremental with no invalidation logic anywhere in this module. The
docstring's several headed paragraphs (window not in the key, instrumentation
required as a callable rather than a `MetricBus` import, no coalescing at
this layer, the store's unbounded growth, a stateful node's lead-in cost) are
not independent decisions; each is a direct consequence of that one keying
choice, argued out because each one is the first thing a reader would get
wrong about it. This does not fit the flag path's clause (a) — there is one
coherent secret, not two bundled ones.

**What does not fit is the budget.** `tools/docstring_audit.py`'s own
measurement: module docstring alone is 806 words against the 250 cap; 17
symbol docstrings; 215 words of comments; 2,463 words of prose total against
a 400-word cap — over by roughly 6x. As with `gui/preview_runner.py`
(`docs/todo/preview-runner-docstring-budget.md`), the excess is not
restatement of signatures — it is non-obvious, load-bearing reasoning:
why a deliberate `invalidate(node_id)` would be a second, disagreeing answer
to what a cache key already covers, and the failure mode if someone added
one (a stale head that looks like a repaint bug); why `measure` is a plain
callable and not a `MetricBus` import (`sieve.bench` sits above
`sieve.pipeline`, so this module may not import the table it is measured
against — an `.importlinter`-enforced layering fact, not a style choice);
why `set_replicate` is invalid on a session reading a pre-cropped source and
what a caller must do instead; why the first-frame span is nested inside the
whole-window span rather than beside it. Each is underivable from the code
and has no other natural owner — not a measurement (`docs/findings/`), not an
architecture rule already stated elsewhere (`docs/ARCHITECTURE.md` covers the
budget and layering rules in general, not this module's specific reasoning
about them), but the reason this particular class and its methods are shaped
the way they are. Compressing 17 symbol docstrings and this docstring into
250 words would delete this reasoning, not compress it — clause (c) of the
flag path.

**No split is proposed.** `PreviewRender`, `PreviewSession`, and `_Tally` are
one render's request/response/scratch-state, not independently useful
pieces, and there is no candidate second file in this module to run the
co-change check against.

**What this item is asking Kendrick to decide**, one of:
1. Add `pipeline/preview.py` to `CONTRACT_MODULES` in
   `tools/docstring_audit.py` (600/900-word caps, per-symbol docstrings
   allowed) — the same treatment already requested for `gui/preview_runner.py`
   and `gui/document.py`, and already granted to `core/filter_base.py`,
   `core/pipeline_model.py`, and `pipeline/cache_key.py`: a reader arrives at
   one method by hovering it, not by reading the file start to end.
2. Accept the loss and force the file to the convention anyway, moving what
   survives triage into the module docstring and accepting that the rest is
   deleted rather than relocated.
3. Leave it flagged permanently, the same as `filter_tab.py`.

No code or docstring in `preview.py` was changed by this pass.
