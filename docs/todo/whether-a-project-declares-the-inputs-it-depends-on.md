---
title: Whether a project declares the external inputs it depends on, or the reproducibility promise is scoped to projects with none
status: deferred
deferred_for: decision
gated_on: Kendrick deciding whether the reproducibility promise narrows to projects whose only input is the source video, or the document grows a declaration of what else it reads — settled before the first source tool lands, because retrofitting a declaration onto saved projects is dearer than deciding it now
priority: high
phase: "03"
opened: 2026-08-07
---

# Whether a project declares the external inputs it depends on, or the reproducibility promise is scoped to projects with none

The promise is stated twice and both statements assume one file. [VISION.md](../VISION.md)'s
reviewer "load[s] the video file and the project file, and ha[s] SIEVE run. It
outputs the same results." `core/pipeline_model.py` opens with the same
sentence for the code: "Given this document and the source video it names, any
executor — CLI, GUI, or a batch job on a cluster — performs the same run and
writes the same files." The document backs that with exactly one file
reference, `Project.source`, and `sieve run` resolves it and refuses with
"source video is not where the project says" when it is absent.

[ADR-18](../adr/a-users-file-wires-in-like-any-other-input.md) settles that a
picked file enters as a source tool, so its path is a param inside
`Node.params` — resolved per replicate through the ordinary overrides path, and
possibly a pattern rather than a path. That is a file the run reads which the
hand-over does not cover. The reviewer was handed the video because there is
one and the interaction demands it; nothing hands them `*_bg.png`, and nothing
in the project tells them it is owed.

Absence and ambiguity already fail loudly under either reading — a pattern
resolving to nothing is a run that cannot happen and one resolving to several
is refused, which ADR-18 settles. Substitution does not fail: the reviewer's
own file at the matching name resolves, the run completes, and the numbers
differ with no symptom. That gap exists today for the source video too —
`source_identity` is `abspath|size|mtime_ns`, a cache key and not a portable
identity, recorded nowhere in the document — and is tolerable there only
because the hand-over is explicit and singular.

**Scope the promise.** The claim narrows to projects whose only input is the
source video, and nothing is built: no schema field, no identity to record, no
verification pass, no migration. What it costs is that VISION spends two
scenarios (the picker, the folder of pre-cropped videos) encouraging exactly
the projects the promise would then exclude, and the reviewer of one of those
gets whatever resolves on their machine with the tool holding no position on
it. The scope line is checkable rather than prose — a project has an external
input iff its graph has a root that is not the source video — so the narrowing
can be enforced instead of asserted, which is a small cost and not a free one.

**Declare the dependency.** The reviewer is told what is missing, by name,
before a run starts rather than after. The costs are three. It needs a
portable identity, which `source_identity` is not, so a content hash — a read
of every external file at save time and again at check time, and for a video
that is not free; the size of that cost is a measurement and not an
assumption. It needs a home, and the identity line in `pipeline_model.py`
constrains it: everything on `Node` feeds the cache key and nothing else does,
so a recorded identity sits on `Project` keyed by node id, the shape
`checkpoints`, `outputs` and `crops` already use, and it must not move a key —
what is hashed for the cache stays the resolved file's own identity, which is
ADR-18's "resolution policy stays out of the key" holding unchanged. And a
declaration goes stale legitimately: the colleague regenerates the background,
the file changes on purpose, and every run refuses until something can say
"yes, this one" — a mutation and a surface nobody has scoped. Whether a
mismatch refuses or reports is part of this, not a later detail: reporting
keeps a stale project runnable and makes the promise advisory; refusing makes
it binding and makes the staleness path required.

Either way VISION's reviewer paragraph gains a clause — a condition under the
first, a sentence about what the reviewer is told under the second. This run
did not edit it. Nothing else moves: ADR-18 stands as written, and
[the first source tool](the-first-source-tool-moves-the-three-single-root-assumptions.md)
is unaffected mechanically, since a source tool keys from its own file under
both.
