---
title: A document names footage only through a tool
adr: 34
position: "02.04"
status: settled
decided: 2026-08-09
---

`Project.source` and `SourceRef` leave schema v1: a document names footage only
in a source tool's path param, stored relative to the project file, and every
reader reaches it through the graph.

Why: [a-users-file-wires-in-like-any-other-input](a-users-file-wires-in-like-any-other-input.md)
already refused a file naming itself anywhere but a node — "the document [has]
two ways to say where input comes from, an edge when it is a node, a param when
it is a file" — and then left the project's own video standing as exactly that
second way. The revert of `4f336a8` is what made the cost concrete rather than
theoretical: `run_cmd.footage_of` reaches `Project.source_path` before
`Dag.build` has looked at the graph, so a project whose only footage was a
source node refused with "names no footage" while the canvas beside it showed
frames, and `preview_cmd` and `materialize_cmd` hold the same line. That is not
an ordering defect to be patched at three call sites. Three readers agreeing to
consult the field first is what having a field means, and any patch leaves the
next reader free to consult it again.

The relative path survives the field that carried it. `SourceRef` exists for one
property — a path meaningless without the directory holding the project file, so
that the folder can move and the project still opens — and that property is now
the source tool's param's. Resolution happens before the key, so
[a-users-file-wires-in-like-any-other-input](a-users-file-wires-in-like-any-other-input.md)'s
rule that resolution policy stays out of the key is untouched: what is hashed is
still the resolved file's own identity, and a project agreeing with itself after
its folder moves is the reason the rule was written that way rather than an
exception to it. `relocated` keeps rebasing outputs and crops and rebases the
source as a param rewrite on the node that holds it.

This supersedes [a-document-may-name-no-footage](superseded/a-document-may-name-no-footage.md),
whose subject dissolves rather than reverses. A document under construction was a
`Project.source` of `None` needing the schema's permission to be absent; it is now
a graph with no source root, which needs no affordance at all. The refusal it
bought does not go — a run still owes the user a sentence naming the file rather
than an `AttributeError` — it moves to where the graph can be seen, and the state
it refuses is the one `Dag.build` can already describe.

The cost is charged once, at the version. This is schema v1's first bump that
removes rather than adds, which is precisely the rule
`todo/a-load-restamps-the-version-it-read.md` observes nothing states; that item
is where the rule lands, and this ADR is the case that forces it rather than the
place it is decided.
