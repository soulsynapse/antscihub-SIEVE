---
title: background_ema.py docstring budget
status: open
priority: unassessed
gated_on: >
  nothing structurally — a Kendrick decision on whether to add
  filters/background_ema.py to CONTRACT_MODULES, or accept deleting
  per-method design reasoning that currently has no other owner
reads: [src/sieve/filters/background_ema.py, src/sieve/filters/background_ema.md, src/sieve/filters/temporal_baseline.py, tools/docstring_audit.py]
---

# background_ema.py docstring budget

`filters/background_ema.py` was picked by `tools/docstring_audit.py --next`
for the docstring-convention sweep (module docstring stating the file's one
secret; no class/function docstrings elsewhere; 250/400-word caps). It is
flagged rather than brought to the convention.

**The secret is genuinely one.** An EMA background model, updated in place
each frame and either emitted or differenced against, with a declared warmup
that a per-run method refines from the static worst case. Everything in the
file — `settle_frames`, `Emit`, `BackgroundEmaParams`, `_Buffers`,
`BackgroundState`, the kernel, `_narrow` — serves that one mechanism; there
is no seam a split would cut along.

**What does not fit is the budget.** The tool's own measurement: 548-word
module docstring alone (over the 250 cap by itself), 9 symbol docstrings,
627 words of comments, 2,137 words of prose total against the 400-word cap —
over by roughly 5.3x. Two different things are bloating it, and they need
different fixes:

1. **User-facing science already duplicated in `background_ema.md`.** The
   module docstring's alpha semantics, the EMA formula, the 90-frame warmup
   consequence (`lead_in_shortfall`), and the "why it does not cache"
   explanation are all restated — sometimes near-verbatim — in the `.md`,
   which guardrail 3 already designates as the home for a filter's science.
   This portion should shrink to a pointer, not survive in the module
   docstring.
2. **Per-symbol implementation reasoning with no other owner**, comparable
   in kind to what kept `decode/prefetch.py` flagged rather than cleaned:
   why `alpha = 1.0` is special-cased in `settle_frames` rather than raising
   (`log(0)` is undefined, but one frame is the true answer, not an
   exception); why `warmup_frames()` may only shrink the static bound, never
   grow it, and why `emit` does not enter that computation; why `_Buffers`
   is one dataclass rather than three optional fields (the shape check and
   the allocation are one atomic decision, and an independently-optional
   field is a place for a stale `None` to survive); why the seed is `None`
   until the first frame rather than a zero array (a zero seed is a *wrong*
   background, not an absent one, and warmup exists to make the seed's
   influence negligible rather than to hide a bad one); why the shape-change
   check in `for_frame` raises instead of silently reseeding (the executor
   guarantees one geometry per run, so a shape change can only mean a bug
   upstream, and reseeding would hide it behind a warmup nobody was told
   restarted); why the kernel updates the model *before* reading the
   difference, tied to `alpha = 1.0` meaning two different things depending
   on order; which buffer the in-place rewrite may alias at each step, and
   the 40.6ms-vs-20.6ms measurement that rewrite is justified by; why
   `_narrow` rounds instead of truncating (truncation biases every pixel of
   a long-lived model downward); and why `_narrow` always copies rather than
   ever taking a view (the source buffers are live state, rewritten next
   frame, and a view would hand a caller — the GUI mid-paint, a store entry
   — a frame that changes under it).

   Each of these is local to one symbol, underivable from the code alone,
   and specific to this filter's own implementation rather than to the
   contract it implements (`core/filter_base.py` already owns the
   *existence* of `warmup_frames()` as a params-derived method — this file
   only owns what its own refinement computes). The raw performance numbers
   (`9.9 ms/MP`, `40.6` vs `20.6 ms`, `17.9` vs `20.6 ms`, the `14x`
   peak-bytes accounting) are measurements and belong in `docs/findings/`
   rather than restated in a docstring; two paragraphs already gesture at
   this by citing `docs/findings/2026.07.26-stateful-output-is-not-keyed-
   by-what-it-is.md` for the caching argument, but the numbers themselves
   are inlined rather than pointed at.

**Why this matters beyond this one file.** `temporal_baseline.py`'s own
flag (`docs/todo/temporal-baseline-scope-split.md`) already treats this
file's stateful/uncacheable argument as the canonical statement other
filters should point back to rather than restate. That only holds if this
file's own copy survives in some form — which is in tension with getting it
under 250 words, and is itself a bit of the argument for adding this file to
`CONTRACT_MODULES` rather than forcing it down to the ordinary cap.

**No split is proposed.** One filter, one class, one kernel, no candidate
second file — the co-change check CLAUDE.md prescribes was not run because
there is nothing to check it against.

**What this item is asking Kendrick to decide**, one of:
1. Add `filters/background_ema.py` to `CONTRACT_MODULES` in
   `tools/docstring_audit.py` (600/900-word caps, per-symbol docstrings
   allowed) — on the same reasoning as `core/filter_base.py` and
   `pipeline/cache_key.py`: it is the file another module (`temporal_
   baseline.py`) already points to for a load-bearing argument.
2. Accept the loss: relocate what genuinely has another owner (science to
   the `.md`, measurements to `docs/findings/`), and delete the rest of the
   per-method reasoning enumerated above, since nothing else in the doc tree
   owns per-method implementation rationale at this grain.
3. Leave it flagged permanently, the same as `filter_tab.py`.

No code or docstring in `background_ema.py` was changed by this pass.
