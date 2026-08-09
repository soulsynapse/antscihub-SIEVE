---
title: A run names the external files it needs before it starts, deriving the list from the graph
status: open
gated_on: nothing
priority: normal
phase: "03"
done_when: 'uv run pytest tests/unit/test_external_inputs.py -k "every_named_external_input_is_reported_missing_before_execution or a_project_with_no_source_tool_owes_nothing or the_list_follows_a_rewired_graph_with_nothing_to_migrate or a_source_root_reaches_the_plan_as_a_picked_identity or a_recorded_input_that_changed_refuses_before_any_key_is_built" -q'
opened: 2026-08-07
---

# A run names the external files it needs before it starts, deriving the list from the graph

[VISION.md](../VISION.md)'s reviewer now loads the video, the project, and the
external files the project names, and is told by name what is missing before a
run starts. This is the mechanism under that sentence. It was
`whether-a-project-declares-the-inputs-it-depends-on` — a question deferred on
Kendrick, answered on 2026-08-07: the promise grows to cover external inputs
rather than narrowing to projects that have none.

**The list is derived, not stored.** A source tool
([ADR-18](../adr/a-users-file-wires-in-like-any-other-input.md)) is a root
whose file is a param, so the graph already holds every external file a run
reads; a field on `Project` repeating them would be a second copy that can
disagree with the nodes it describes, and it would need a migration the derived
form does not. Walking the roots for their path params and resolving each one
answers "what am I owed" and "what is absent" from the document as it stands,
so a rewired graph is right the moment it is rewired.

What that buys is naming and absence, not identity. A reviewer whose own file
sits at the matching name resolves it, the run completes, and the numbers differ
with no symptom — exactly the gap that exists today for the source video, whose
`source_identity` is `abspath|size|mtime_ns`, a cache key rather than a portable
identity and recorded nowhere in the document. Closing that is a content hash, a
home for it, and a staleness surface for the colleague who legitimately
regenerates the background; none of it is bought here, and the promise VISION
now states does not claim it. Say so wherever this reports, so "nothing
missing" is not read as "the same files".

Two statements move together. The check itself is `sieve run`'s, before
execution, beside the existing "source video is not where the project says"
refusal and reporting every missing input rather than the first. And
`core/pipeline_model.py`'s opening sentence — "Given this document and the
source video it names" — is the same promise stated for the code and is now
narrower than VISION's; it grows to the same shape in the same change.

Absence and ambiguity already refuse under ADR-18 — a pattern resolving to
nothing is a run that cannot happen, one resolving to several is refused — so
what is added is when and how the reviewer hears it, not whether the run is
stopped. This follows
[the first source tool](the-first-source-tool-moves-the-three-single-root-assumptions.md):
until a project can have a second root there is no external input to report,
and that item is where the roots stop being one. It is also where the walk
above gets the thing it walks by. "The roots' path params" names no field
today — `ParamStereotype`'s vocabulary is closed and none of its members is a
path (five when this was written, six once
[a-band-has-no-stereotype-of-its-own.md](a-band-has-no-stereotype-of-its-own.md)
lands, neither of them a path) — so a walk written before the path member
exists could only find a file param by branching on `tool_id`, which is what
[gui-knows-kinds-not-tools](../adr/gui-knows-kinds-not-tools.md) and
[a-tool-is-one-file](../adr/a-tool-is-one-file.md) each refuse. The source-tool
item spends that decision; this one reads the result.

## 2026-08-09: the gate lifted, and the walk it waited for exists

`44b6456` landed the first source tool. `ParamStereotype.PATH` is the member
this item's walk was owed, `ToolSpec.path_params` derives the names off it, and
`Dag.source_roots` is the roots split by the declaration — so "the roots' path
params" names something today and the deferral's stated subject is here.
`status` and `gated_on` moved on that; nothing about the work below changed.

**And the same walk owes `picked` to the plan.** `resolve_source.picked_identities`
resolves each source root's file and returns what `ExecutionPlan.build` wants as
`picked`, but nothing under `src/` calls it — `run_cmd.py`, `preview.py` and
`materialize_cmd.py` all build plans without it. A source root handed no
identity is left unkeyed by `dag.node_keys`, and an unkeyed node takes its whole
subtree with it, so today a picker and everything below it recompute on every
run and on every preview — the tuning loop `CLAUDE.md` names as the product
constraint. It is not a wrong answer, only an uncached one, which is why it goes
here rather than into a defect item: this is the item whose walk already visits
every source root at run start, and the identity it resolves for the missing-file
report is the identity the keys want. `done_when` above was written for the
absence check alone and does not reach this; widen it or add a case when this is
worked.

**And the same walk is where the recorded hash is checked.**
[The portable identity](whether-an-external-input-carries-a-portable-identity.md)
landed its model half: `Project.input_hashes` records a `content_hash` per node,
`with_input_hash` re-records the file a colleague regenerated on purpose, and
`Project.check_input_hashes` refuses — naming every node whose file differs — when
a recorded input is not the file that was recorded. Nothing calls it. The call
belongs here rather than in a third place, for the reason the two paragraphs
above already give: this is the item whose walk resolves every source root's file
at run start, so the mapping `check_input_hashes` wants is a by-product of a walk
that had to happen, and a second walk would be a second answer to which file a run
reads. The order at the call site is the one the reports read in — absent first,
since a missing file has no hash to compare, then changed — and both are refusals
before any key is built. The same amendment applies: `done_when` was written for
the absence check alone and does not reach this.

`core/pipeline_model.py`'s opening sentence is still narrower than VISION's and
is still this item's second statement to move; the portable-identity work
deliberately left it, growing only the identity line where its new field sits.

## 2026-08-09 review: the criterion is widened, and the pointer it inherits is wrong

Three amendments in a row asked for it, so `done_when` above now names five
cases rather than three: the two added are the `picked` identity reaching the
plan, and a recorded input that changed refusing before any key is built. The
names are the shape the cases should take and not a spelling to be obeyed — what
the criterion has to reach is that all three statements this item now carries are
run, not that a test is called what a review guessed.

One correction to fold in with them. `Project.check_input_hashes`' `Args:` says
the run start "already walks its source roots to resolve exactly this
(`pipeline/resolve_source.picked_identities`)". The walk is a by-product; the
return value is not. `picked_identities` returns `dict[str, str]` — node id to
`cache_key.source_identity` — and discards the `Path` that `ToolSource.file`
handed it, while `check_input_hashes` wants `Mapping[str, Path]`. Whoever writes
the call site here will follow that pointer to a function whose return type
cannot be passed to the parameter it is named for, and the choice waiting there
is one of this item's: either `picked_identities` returns the paths alongside the
identities, or the walk is written once here and both functions read from it.
Nothing is wrong in the tree today — `check_input_hashes` has no caller — so this
is a doc pointer to correct in the same change, not a defect.
