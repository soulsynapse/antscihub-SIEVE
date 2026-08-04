---
title: prefetch.py docstring budget
status: open
priority: unassessed
gated_on: >
  nothing structurally — a Kendrick decision on whether the docstring
  convention's per-symbol ban and 400-word prose cap should exempt this file,
  or fold it into CONTRACT_MODULES alongside cache_key.py
reads: [src/sieve/decode/prefetch.py, tools/docstring_audit.py]
---

# prefetch.py docstring budget

`decode/prefetch.py` was picked by `tools/docstring_audit.py --next` for the
docstring-convention sweep (module docstring stating the file's one secret;
no class/function docstrings elsewhere; 250/400-word caps). It is flagged
rather than brought to the convention.

**The secret is genuinely one.** `PrefetchFrameSource` runs N `VideoReader`s
on a sliding window of `lookahead` indices just ahead of one consumer, so
decode-ahead parallelism is bought without a second decode path: every frame
it returns is byte-identical to what one `VideoReader` would have returned at
the same index, which is the constraint `cache_key.source_key` depends on
through `decoder_identity()`. `resolve_workers`, `INFERRED_WORKER_CAP`, and
`LUMA_WORKER_CAP` are the same secret's tuning — how many readers, derived
from measurement rather than core count — not a second responsibility.

**What does not fit is the budget.** The tool's own measurement: 952-word
module docstring alone (over the 250 cap by itself), 15 symbol docstrings, 342
words of comments, 2,392 words of prose total against the 400-word cap — over
by roughly 6x. The excess is not restated signature or control flow; it is
one-off, underivable reasoning specific to one method or constant: why
`INFERRED_WORKER_CAP` is 4 and `LUMA_WORKER_CAP` is 2 and why one is not a
scaled function of the other (the curves are shaped by different bottlenecks —
allocator pressure from a 47.6 MB buffer versus too little parallel work left
once the convert is gone); why the window is interleaved rather than chunked
(so peak memory is `lookahead` frames rather than a whole span); why the
epoch bump on `_restart` is hygiene and not correctness, and why that is
worth distinguishing from `gui/coalescer.py`'s superficially identical
`generation` field, which the docstring explicitly warns invites the wrong
reading; why `resolve_workers` deliberately does not read
`SLURM_CPUS_PER_TASK` or any environment variable, tying that decision back
to VISION step 6 (machine capability reaches a run as a command-line option,
never project state); the thread-safety and exception contracts on `read`,
`close`, and `_open_readers` (out-of-range message parity with `VideoReader`,
what "safe for one consumer thread" excludes, why a half-opened source closes
what it already opened before re-raising). Each is local to its one symbol,
underivable from the code, and has no other natural owner: two paragraphs
already point at `docs/findings/2026.07.26-threading-the-reads-buys-1.6x-and-
stops.md` and `docs/findings/2026.07.28-the-luma-path-has-almost-nothing-
left-to-thread.md` for the raw numbers, but the *design reasoning* built on
those numbers — why interleaved, why a second cap instead of a formula, why
epoch is hygiene not correctness — is specific to this module and not a
measurement itself. Folding 15 of these into one 250-word module docstring
would not compress them, it would delete them — clause (c) of the flag path:
"the prose is load-bearing in a way the budget would destroy... it records
why the code is the shape it is in a way the code cannot."

**No split is proposed.** Every symbol in the file — the two worker caps,
`resolve_workers`, and every method of `PrefetchFrameSource` — serves the one
window-claim-publish mechanism; there is no seam where a subset could become
a second file without both halves still needing the same `_state` condition
and the same window invariants. The co-change check CLAUDE.md prescribes was
not run because there is no candidate second file to check it against.

**What this item is asking Kendrick to decide**, one of:
1. Add `decode/prefetch.py` to `CONTRACT_MODULES` in `tools/docstring_audit.py`
   (600/900-word caps, per-symbol docstrings allowed). It is the one place a
   caller (`pipeline/executor.py`, a scrubbing GUI) learns the thread-safety
   contract, the jump-abandons-window semantics, and why the byte-identical
   guarantee holds — the same load-bearing-prose argument that put
   `cache_key.py` on the contract list.
2. Accept the loss and force the file to the convention anyway, moving what
   survives triage into the module docstring and the two `docs/findings/`
   entries the numbers already cite, and accepting the rest (the per-method
   thread-safety and design-rejection reasoning) is deleted rather than
   relocated, since nothing else in the doc tree owns per-method
   implementation rationale at this grain.
3. Leave it flagged permanently, the same as `filter_tab.py`.

No code or docstring in `prefetch.py` was changed by this pass.
