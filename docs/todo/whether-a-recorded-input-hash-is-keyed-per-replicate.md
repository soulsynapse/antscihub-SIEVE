---
title: Whether a recorded input hash is keyed per replicate, since a path is a deviable parameter
status: open
gated_on: nothing
priority: normal
phase: "03"
done_when: 'uv run pytest "tests/unit/test_external_inputs.py::test_a_replicate_that_resolves_another_file_is_reported_unclaimed_and_runs" "tests/unit/test_external_inputs.py::test_a_deviated_path_that_resolves_the_recorded_file_is_still_checked" "tests/unit/test_external_inputs.py::test_an_unclaimed_input_is_named_with_its_replicate" -q'
opened: 2026-08-09
---

# Whether a recorded input hash is keyed per replicate, since a path is a deviable parameter

`Project.input_hashes` is `dict[str, str]` — node id to `content_hash` — and its
field comment argues the keying from the thing that breaks it: keyed by node
"because the path is already a parameter and resolves per replicate; what is
being claimed is what a *node* reads." Resolving per replicate is exactly the
condition under which one node reads two files in one run. `Replicate.overrides`
is sparse over arbitrary parameter names and asks nothing about stereotype, so a
path parameter is deviable like any other, and one slot cannot hold two claims.

`a50027a` made it observable by adding the only caller: `run_cmd._external_inputs`
calls `check_input_hashes` once per replicate with that replicate's resolved
files, so at most one replicate can match the recorded hash and every other is
refused. Measured in
[a node-keyed input hash refuses the replicate that deviates its path](../findings/2026.08.09-a-node-keyed-input-hash-refuses-the-replicate-that-deviates-its-path.md);
the remedy the refusal message gives — re-record deliberately — moves the
refusal to the other replicate rather than clearing it.

**No `done_when`, because the shape is a decision and not an implementation.**
Two forms are live. Key by `(node, replicate)` with the node-level entry as the
inherited default, which mirrors `Replicate.overrides`' own two-level sparsity
and makes the claim exactly as specific as the parameter it is about; or rule
that a claim is about the node's own parameters and a replicate that deviates a
path drops the claim for itself, which costs nothing in schema and leaves the
deviated file unclaimed. The first is a schema change and a migration; the
second is a sentence and a narrowing of `check_input_hashes`. Which is right
turns on whether a deviated external input is a thing the document should be
able to make a promise about, and that is Kendrick's.

**Nothing waits on it.** No caller of `Project.with_input_hash` exists under
`src/`, so no project can carry an entry, and the scenario that would exercise
the gap — an A/B of two backgrounds — was ruled out of VISION on 2026-08-08 by
[whether VISION's picker scenario states an A/B](whether-vision-states-the-background-ab.md)
and sits in PLAN.md's revival table. The gap is what will be waiting on the day
that paragraph returns, or the day a front end learns to record a hash,
whichever is first. It is filed now because the argument is cheap while the code
is one commit old and expensive once a document in the wild carries entries.

## 2026-08-09: ruled — the claim narrows, and says so

Kendrick's, and it does not go the way the fork above is drawn. The two forms
are not alternatives: form 1's node-level entry cannot be inherited *by* a
deviating replicate, because that is today's refusal exactly, so the
inheritance rule that makes form 1 coherent is form 2's rule verbatim. Form 1
is form 2 plus an optionally-writable per-replicate entry, form 2's documents
are form 1 documents meaning the same thing, and the ordering between them is
therefore free. Form 1 stays available as a widening the day the A/B returns
from PLAN.md's revival table; it is not built now, because it would be a
schema change, a migration and an extension to `_references_resolve` for a
claim no surface records.

**A deviated external input is unclaimed, and an unclaimed input is reported.**
Dropping the claim silently is the worse of the two failures available: the
document still carries a hash for that node, the run reads as though it were
checked, and the integrity check is off precisely where someone deliberately
aimed a node at a different file. VISION's reviewer paragraph is what this
answers to — what a run is owed is not something discovered from a run that
already started — and a dropped claim is owed the same up-front naming as a
missing file.

**Applicability derives from the resolved file, not from override presence.**
This is the clause neither form stated and it is what keeps the narrowing
honest. "This replicate reads a different file" is not the same fact as "this
replicate overrides the node's path parameter": an override that re-spells a
pattern to the same file would lose its check under a skip-if-overridden
narrowing. v2 ruled on this shape and refused the derivation —
`Replicate.visited` is deliberately not derived from non-empty `overrides`,
because a replicate can be visited without being pinned and the derived
version would leave exactly those unlocked. `check_input_hashes` already
receives the file each node resolved to, so it compares as it does today and
reports unclaimed only where the resolved file is not the one the node's own
params resolve to. An override that lands on the recorded file still refuses
when that file's content has changed.

The three cases in `done_when` are those three claims. None exists; the
criterion is node ids rather than `-k` so that it is red for their absence
today (exit 4) and stays red if one is later renamed away, which
`findings/loop/2026.08.09-a-k-disjunction-is-green-for-the-disjunct-that-names-nothing.md`
is the reason for.

Nothing else is owed alongside. The finding's other half — `_external_inputs`'
docstring citing VISION for an A/B VISION does not state — landed in `b354e2f`
before this was ruled, and the finding is amended to say so rather than
carrying an open call to action it no longer has.
