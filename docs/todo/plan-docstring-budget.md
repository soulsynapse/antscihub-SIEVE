---
title: pipeline/plan.py docstring budget
status: open
priority: unassessed
gated_on: >
  nothing structurally — a Kendrick decision on whether the docstring
  convention's per-symbol ban and 400-word prose cap should exempt this file
reads: [src/sieve/pipeline/plan.py, tools/docstring_audit.py]
---

# pipeline/plan.py docstring budget

`pipeline/plan.py` was picked by `tools/docstring_audit.py --next` for the
docstring-convention sweep (module docstring stating the file's one secret;
no class/function docstrings elsewhere; 250/400-word caps). It is flagged
rather than brought to the convention.

**The secret is genuinely one.** `ExecutionPlan` is everything about one run
of a graph that is knowable before a frame is decoded — resolved parameters,
cache keys, lead-in, and backend assignment, derived once from an already-
validated `Dag` so nothing downstream re-derives it. This is a single
responsibility properly split from `executor.py` for `filter_base.py`'s own
reason (buildable with nothing installed). It does not fit the flag path's
clause (a).

**What does not fit is the budget.** The module docstring alone is 407 words
against the 250 cap. The file carries 12 docstrings totalling 1,455 words
against a 400-word file-wide cap — over by roughly 3.6x. The excess is not
restatement: it is why the file exists apart from `executor.py`, the
max-over-paths lead-in argument (`_lead_in`) that a property test checks
against brute-force enumeration precisely because the equivalence is not
visible in the code, why the cache is deliberately not consulted here
(`cache_key.py`'s asymmetry rule), why `roi` folds two different ways of
having "no crop" into one answer, why `decode_start` clamps rather than
refuses near frame 0 and again at a crop artifact's boundary, why `luma` is
answered on the plan rather than at each call site, and why `key` returns
`None` rather than raising for an ordinary "not cacheable" answer. Each is
underivable from the code and has no other owner: not a measurement
(`docs/findings/`), not a filter's science, not an architecture rule already
stated in general form elsewhere — `docs/ARCHITECTURE.md` does not carry
this module's specific reasoning about lead-in propagation or the crop/
pre-cropped distinction. Compressing 12 docstrings into 250 words would
delete this reasoning, not compress it — clause (c) of the flag path.

**No split is proposed.** `ExecutionPlan`, `_lead_in`, and `root_paths` are
one plan and the arithmetic it depends on (`root_paths` exists specifically
so the property test and a future diagnostic can check `_lead_in` against
its own definition) — there is no candidate second file in this module to
run the co-change check against.

**What this item is asking Kendrick to decide**, one of:
1. Add `pipeline/plan.py` to `CONTRACT_MODULES` in `tools/docstring_audit.py`
   (600/900-word caps, per-symbol docstrings allowed) — the same treatment
   already requested for `pipeline/executor.py`, `pipeline/dag.py`, and
   `pipeline/preview.py`, and already granted to `core/filter_base.py`,
   `core/pipeline_model.py`, and `pipeline/cache_key.py`.
2. Accept the loss and force the file to the convention anyway, moving what
   survives triage into the module docstring and accepting that the rest is
   deleted rather than relocated.
3. Leave it flagged permanently, the same as `filter_tab.py`.

No code or docstring in `plan.py` was changed by this pass.
