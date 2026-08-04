---
title: pipeline_model.py prose budget
status: open
priority: unassessed
gated_on: >
  nothing structurally — a Kendrick decision on whether pipeline_model.py's
  contract-module budget should rise further, whether the file should split,
  or whether it stays flagged
reads: [src/sieve/core/pipeline_model.py, tools/docstring_audit.py]
---

# pipeline_model.py prose budget

`core/pipeline_model.py` was picked by `tools/docstring_audit.py --next` for
the docstring-convention sweep. It is flagged rather than brought to the
convention.

**It is already a contract module and still blows the elevated cap.**
`tools/docstring_audit.py`'s own measurement: a 753-word module docstring
against the 600-word `CONTRACT_DOCSTRING_WORDS` cap, 52 symbol docstrings
totaling 3,879 words, 1,582 words of comments, 6,214 words of prose total
against the 900-word `CONTRACT_FILE_PROSE_WORDS` cap — the cap by roughly 7x,
after already receiving the treatment `document-docstring-budget.md` asked
for and this file already has. Whatever is happening here is not the ordinary
"250/400 is tight for a rich file" case the contract-module exemption exists
to solve.

**Whether it is one secret is a real question, not a formality.** The module
docstring states a single line — "the serialized form a run is reproducible
from" — but the file's actual content reads as several decisions bundled
because they all touch the artifact, not because they are one decision:

1. The graph identity model — `Node`, `Edge`, `Sink`, `Pipeline`, and the
   "identity line" rule for what enters a cache key.
2. Replicate lateral inheritance and the two-write editing mechanism —
   `DetectorSettings`, `resolved_params`/`edited_params`,
   `resolved_detector`/`edited_detector`, `equivalence_groups`,
   `Project.with_param_edit`/`with_detector_edit`.
3. Crop artifact provenance and matching — `CropArtifact`, `.identity()`,
   `.backs()`, the deliberate asymmetry between `cut_from` (matched) and
   `decoder` (not matched).
4. Document lifecycle — schema versioning and the refuse-the-future rule on
   `Project.schema_version`, `to_yaml`/`from_yaml`/`save`/`load`,
   `relocated`, and the referential-integrity validator tying replicates,
   checkpoints, sinks, crops, and `visited` together.

Each of these has its own non-obvious rationale (a rejected alternative, a
failure mode, a "this used to say X and was wrong" note) that is genuinely
underivable from the code and, unlike `document.py`'s per-method rationale,
does not obviously fold into one paragraph without losing which decision it
is arguing for. That is closer to clause (a) of the flag path — plausibly two
or more secrets — than to clause (c) alone, though (c) applies too: several
of these passages (the crop-artifact identity-line argument, the schema
version bump log, the `with_param_edit` cost-accepted-knowingly paragraph)
are exactly the kind of decision-recording prose CLAUDE.md's comment rule
says to keep.

**No split is proposed here.** The co-change check CLAUDE.md prescribes
compares two *existing* files' git history; there is only one file, so the
check does not apply to a from-scratch split and running it would not answer
anything. Proposing where the four groups above should live — one module
per group, two combined, or left as one file with a raised budget — is the
architecture call the flag path reserves for Kendrick, not something this
pass should force by picking a boundary and moving code across it.

**What this item is asking Kendrick to decide**, one of:
1. Raise `pipeline_model.py`'s own budget further (a second tier above
   `CONTRACT_*_WORDS`, or a per-file override), on the grounds that this is
   the one document two machines must agree about and its rationale is read
   by hovering a symbol, the same argument that put it in `CONTRACT_MODULES`
   at 600/900 in the first place.
2. Split along some cut of the four groups above (or a different one),
   accepting the churn of moving `Node`/`Edge`/`Pipeline` or `CropArtifact`
   into their own modules under `core/` or `pipeline/`.
3. Leave it flagged permanently, alongside `filter_tab.py` and `document.py`.

No code or docstring in `pipeline_model.py` was changed by this pass.
