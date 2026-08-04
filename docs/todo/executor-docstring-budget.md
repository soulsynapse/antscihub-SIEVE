---
title: executor.py docstring budget
status: open
priority: unassessed
gated_on: >
  nothing structurally — a Kendrick decision on whether the docstring
  convention's per-symbol ban and 400-word prose cap should exempt this file,
  or fold it into CONTRACT_MODULES alongside cache_key.py
reads: [src/sieve/pipeline/executor.py, tools/docstring_audit.py]
---

# executor.py docstring budget

`pipeline/executor.py` was picked by `tools/docstring_audit.py --next` for the
docstring-convention sweep (module docstring stating the file's one secret; no
class/function docstrings elsewhere; 250/400-word caps). It is flagged rather
than brought to the convention.

**The secret is genuinely one.** `execute` is the one place a plan, a reader,
and a store become a stream of per-frame results — rule 1's single execution
path. Every other symbol in the file exists to keep that one loop honest:
`FormatMismatchError`/`_check_format` guard the keys it writes, `_bind`
resolves and refuses nodes before any frame is read, `_crop` applies the
plan's ROI, `_run_node` enforces the index invariant the cache depends on, and
`FrameSource`/`FrameResult` are the loop's input and output shapes. None of
these is a second responsibility; they are one loop's invariants, stated where
each is enforced.

**What does not fit is the budget.** The tool's own measurement: 556-word
module docstring alone (over the 250 cap by itself), 12 docstrings total, and
1,690 words of prose against the 400-word cap — over by roughly 4x. The excess
is not restated signature or control flow; it is one-off, underivable
reasoning specific to one symbol: why the registry gets `plan.backend_for`
alone rather than a preference order (a fallback would silently write
GPU-keyed cache entries containing CPU output); why format is checked every
frame rather than once (a reader that drifts mid-run is exactly as wrong as
one that started wrong); why `_bind` runs synchronously before any frame is
read rather than lazily per node (failing after the lead-in already decoded is
a minute of wasted work for a message that was available immediately); why a
stateful node's state lives in `_bind`'s closure rather than a registry keyed
by node id (two concurrent `execute` calls must not share it, and cancellation
must drop it with the generator); why `FrameResult` carries every node's
output rather than only the leaves (the GUI shows intermediates and a
checkpoint materializes one); why `source`/`source_cropped` exist as a pair
rather than one field (a crop-served run has no whole frame to promise, and a
consumer that painted a crop where it expected one would violate rule 6's
mirror direction); why the merging-node branch trusts `outputs` without
alignment machinery (every node computes the same source index in lockstep,
so upstreams for `index` are already populated by topological order). Two
sections already point at `docs/findings/2026.07.26-stateful-output-is-not-
keyed-by-what-it-is.md`, `docs/findings/2026.07.25-the-crop-belongs-in-the-
graph.md`, and `docs/todo/the-decode-format-has-six-derivations.md` for the
adjacent measurements and the open gap, but the design reasoning built on top
— why no fallback, why per-frame not per-run, why the closure and not a
registry, why the field pair — is specific to this module's symbols and not a
measurement itself. Folding 12 of these into one 250-word module docstring
would not compress them, it would delete them — clause (c) of the flag path:
"the prose is load-bearing in a way the budget would destroy... it records
why the code is the shape it is in a way the code cannot."

**No split is proposed.** This is the module rule 1 names as the one place a
frame is computed; every helper here (`_bind`, `_crop`, `_check_format`,
`_run_node`) exists only to keep `execute`'s loop correct and is private to
it. There is no seam where a subset could become a second file without both
halves still needing the same per-frame loop state (`decoded`, `source`,
`outputs`, `hits`) — splitting it would either duplicate the loop or produce
two files that must change in lockstep on every edit, which CLAUDE.md's
co-change test treats as not a seam. The co-change check was not run because
there is no candidate second file to check it against.

**What this item is asking Kendrick to decide**, one of:
1. Add `pipeline/executor.py` to `CONTRACT_MODULES` in
   `tools/docstring_audit.py` (600/900-word caps, per-symbol docstrings
   allowed). It is the module CLI, GUI, and HPC all call identically, and a
   caller arrives at it the way a caller arrives at `cache_key.py` — by
   hovering a symbol to learn a contract — which is the same argument that put
   `cache_key.py` and `filter_base.py` on the contract list.
2. Accept the loss and force the file to the convention anyway, moving what
   survives triage into the module docstring and the two `docs/findings/`
   entries the numbers already cite, and accepting the rest (the per-symbol
   design-rejection reasoning) is deleted rather than relocated, since nothing
   else in the doc tree owns per-method implementation rationale at this
   grain.
3. Leave it flagged permanently, the same as `filter_tab.py`.

No code or docstring in `executor.py` was changed by this pass.
