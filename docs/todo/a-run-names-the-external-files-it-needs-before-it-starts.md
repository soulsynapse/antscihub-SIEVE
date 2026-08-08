---
title: A run names the external files it needs before it starts, deriving the list from the graph
status: deferred
deferred_for: subject
gated_on: the first source tool, which is what gives a project a second root to walk and the path stereotype to recognise it by — two of the three cases below have no subject until it lands
priority: normal
phase: "03"
done_when: 'uv run pytest tests/unit/test_external_inputs.py -k "every_named_external_input_is_reported_missing_before_execution or a_project_with_no_source_tool_owes_nothing or the_list_follows_a_rewired_graph_with_nothing_to_migrate" -q'
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
