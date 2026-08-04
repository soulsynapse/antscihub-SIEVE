---
title: filter_base.py exceeds even the contract-module prose budget
status: open
priority: unassessed
gated_on: >
  nothing structurally — a Kendrick decision on whether CONTRACT_FILE_PROSE_WORDS
  is the wrong number, or whether some of this file's rationale has another owner
reads: [src/sieve/core/filter_base.py, tools/docstring_audit.py]
---

# filter_base.py exceeds even the contract-module prose budget

`core/filter_base.py` was picked by `tools/docstring_audit.py --next` for the
docstring-convention sweep. It is flagged rather than brought to the
convention.

**The secret is genuinely one, and the module docstring already states it.**
The filter contract as data — `FilterSpec`, `ParamsBase`, `ArraySpec`, `Mode`
— kept pure so a saved pipeline's structure validates on a machine with no
codec, no CUDA, and none of the filters installed. `filter_base.py` is
already one of the three `CONTRACT_MODULES`, exempt from the per-symbol
docstring ban on the grounds that a caller arrives by hovering a symbol
rather than reading start to end. This item is not clause (a) of the flag
path — it is not proposing two secrets or a split.

**What does not fit is the budget, and this time it's the contract budget
itself.** The tool's own measurement: 340-word module docstring (under the
600 cap), 25 symbol docstrings, 1,625 words of comments, 4,649 words of
prose total against the 900-word contract cap — over by 3,749, the largest
excess of any file in the queue. Reading through the docstrings that make up
the bulk of that (`node_element`, `ParamsBase.output_rate`/`warmup_frames`/
`frame_bytes_ratio`, `FilterSpec.stateful`/`cacheable`, `node_warmup_frames`,
`input_warmup_frames`, `source_warmup_frames`), each one is a non-obvious
reason for a specific asymmetry: why `warmup_frames` is a bound refined
downward by `ParamsBase.warmup_frames()` rather than a single number; why
`output_rate` overrides are cross-checked against `rate_changing` and
`frame_bytes_ratio` is cross-checked against nothing; why `stateful` exists
as a separate disqualification from `deterministic` and cannot be verified
from a decorator; why the warmup fold walks sink to root instead of summing.
These pass the "could a competent reader derive this from the code" test in
the wrong direction — they fail it, which is what keeps them. Two are
already pointed at their real owner (a `docs/findings/` entry for
`stateful`, ARCHITECTURE's own quoted claim for `source_warmup_frames`); the
rest have no other natural home; they are the specific reason this module's
methods are shaped the way they are, not a measurement or a filter's
science.

**No split is proposed.** This is one coherent contract, and splitting the
warmup arithmetic (`node_warmup_frames`, `input_warmup_frames`,
`source_warmup_frames`) out would separate three functions from the exact
field declarations (`FilterSpec.warmup_frames`, `ParamsBase.warmup_frames`)
whose relationship is the entire content of their docstrings — the seam
would be worse than the file. The co-change check was not run because no
split is being proposed to check.

**What this item is asking Kendrick to decide**, one of:
1. Raise `CONTRACT_FILE_PROSE_WORDS` (or add a fourth, higher tier) for
   modules where the per-symbol rationale is this dense — `filter_base.py`
   is already getting the contract-module treatment and it is not enough.
2. Accept the loss and force the file to 900 words anyway, deleting the
   asymmetry rationale in `output_rate`/`warmup_frames`/`frame_bytes_ratio`
   and the three warmup functions, on the grounds that a reader who needs it
   can reconstruct it from `docs/completed-todo/` history instead.
3. Leave it flagged permanently, the same as `filter_tab.py`,
   `document.py`, `pipeline_model.py`, and `preview_runner.py` — at which
   point it is worth asking whether the sweep should stop treating
   contract-module status as the intended resting place for this file
   rather than a stepping stone toward it.

No code or docstring in `filter_base.py` was changed by this pass.
