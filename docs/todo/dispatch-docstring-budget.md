---
title: backend/dispatch.py docstring budget
status: open
priority: unassessed
gated_on: >
  nothing structurally — a Kendrick decision on whether the docstring
  convention's per-symbol ban and 400-word prose cap should exempt this file
reads: [src/sieve/backend/dispatch.py, tools/docstring_audit.py]
---

# backend/dispatch.py docstring budget

`backend/dispatch.py` was picked by `tools/docstring_audit.py --next` for the
docstring-convention sweep (module docstring stating the file's one secret;
no class/function docstrings elsewhere; 250/400-word caps). It is flagged
rather than brought to the convention.

**The secret is genuinely one.** The file is the shelf keyed by
`(filter_id, version, backend)` that answers, uniformly, which callable
implements a spec on a given machine — including how that callable is found
when no backend is preferred (`select`'s preference walk), how it declares
its calling shape (`Kernel`, `MergingKernel`, `StatefulKernel`), and how a
stateful kernel's per-run state is minted so two concurrent previews of the
same node cannot share one closure's memory (`KernelBinding.start`). These
are not independent decisions bundled together; they are what "which kernel
runs" has to specify to be a complete answer — the calling-convention
protocols exist only because dispatch needs to know how to invoke what it
selects, and the state-lifecycle rule exists only because dispatch is what
creates the callable a run actually calls. This does not fit the flag path's
clause (a).

**What does not fit is the budget.** The module docstring alone is 270 words
against the 250 cap before touching anything else; the file carries 18
docstrings (module plus 3 protocols, `KernelBinding` and its `start`,
`DuplicateKernelError`, `NoKernelError`, `KernelRegistry` and four of its
methods, and the three registration decorators) totalling 1,705 words against
a 400-word file-wide cap — over by roughly 4x. As with the other
`*-docstring-budget` entries, the excess is not restatement of signatures: it
is the reasoning for why each protocol has the argument order it has
(positional-only so a filter author's parameter *names* never become part of
the contract; `state` last on `StatefulKernel` so a first stateful kernel is
a diff on a signature already known), why three separate registration
decorators exist instead of one typed as a union (a two-argument kernel
registered with a state factory should fail at import, not at the first
frame), why `KernelBinding.start` returns a stateless kernel unwrapped rather
than always wrapping (so a benchmark or equivalence test that names
`downsample_cpu` still gets that function's identity), and why
`state_factory`'s presence and `spec.stateful` must agree (the two say the
same thing to different readers — the registry and `dag.py`'s caching
decision — and disagreeing would let a stateful kernel's span-dependent
output be served from a cache key that does not carry the span). Each is
underivable from the code and has no other owner: not a measurement
(`docs/findings/`), not a filter's science (the `.md` beside a filter file),
not an architecture rule already stated in general form elsewhere
(`docs/ARCHITECTURE.md` states rule 3 and rule 5 in the abstract, not this
module's specific reasoning about *why* the enforcement lives at import time
for each of three decorators). Compressing 18 docstrings into 250 words would
delete this reasoning, not compress it — clause (c) of the flag path.

**No split is proposed.** `Kernel`, `MergingKernel`, `StatefulKernel`,
`KernelBinding`, `KernelRegistry`, and the three decorators are one shelf and
its calling conventions, not independently useful pieces answering unrelated
questions — there is no candidate second file in this module to run the
co-change check against.

**What this item is asking Kendrick to decide**, one of:
1. Add `backend/dispatch.py` to `CONTRACT_MODULES` in
   `tools/docstring_audit.py` (600/900-word caps, per-symbol docstrings
   allowed) — the same treatment already requested for `pipeline/preview.py`,
   `gui/preview_runner.py`, and `gui/document.py`, and already granted to
   `core/filter_base.py`, `core/pipeline_model.py`, and
   `pipeline/cache_key.py`: a reader arrives at one protocol or method by
   hovering it, not by reading the file start to end.
2. Accept the loss and force the file to the convention anyway, moving what
   survives triage into the module docstring and accepting that the rest is
   deleted rather than relocated.
3. Leave it flagged permanently, the same as `filter_tab.py`.

No code or docstring in `dispatch.py` was changed by this pass.
