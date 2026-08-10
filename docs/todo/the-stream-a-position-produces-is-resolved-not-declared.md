---
title: The stream a position produces is resolved, not declared
priority: high
phase: 3
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests -q -k \"offering_from_a_resolved_source or an_unstated_accepts_field\""
opened: 2026-08-09
---

# The stream a position produces is resolved, not declared

`offered_tools` is handed the upstream node's `emits`, and a declaration is not
what a position produces. Two faces of that, both measured in
[findings/2026.08.09-the-shelf-declares-too-little-for-eight-of-ten-positions-to-offer-anything](../findings/2026.08.09-the-shelf-declares-too-little-for-eight-of-ten-positions-to-offer-anything.md):
mid-chain a preserving tool leaves a field unstated because it emits what it
was handed, and at the root a source states a union because which member it
yields is settled elsewhere. `ArraySpec._unused` reads both as unproven, so the
box under a `crop` is empty and crop is the first tool in every pipeline.

VISION's new-project scenario rules on which side moves:

> What is offered is derived from what the source resolved to rather than
> declared by any tool, which is why concatenate appears the moment there is a
> second file and not before.

That refuses the three alternatives together, and for one reason rather than
three: narrowing the tools' `emits`, a declared stream relation beside
`ToolSpec.element`, and relaxing `matches` to overlap are all constant across
the event the sentence uses to define the feature — a file appearing in a
folder, with every declaration and the graph untouched. What is left is a fold,
and it answers this finding's `open_questions` from VISION rather than by a
decision this item carries.

**The seed is the source as resolved, not the decode format.** `graph_needs_chroma`
(`pipeline/dag.py`) looks like the seed and is the wrong one: it derives the
format from the graph, so a second file in the folder cannot move it. What the
root resolves against is the source node's params and the files they name —
their count and extension class, which is what the finding already named as the
fact the source site lacks.

The fold's shape is `element_kinds` (`gui/pinned.py`), which walks in
topological order against one parent per node and is the same walk over the
other half of the spec. Its hardcoded `PIXEL` root is the one thing not to
copy.

One thing stays as it is, and one no longer does. `ArraySpec.matches` was to be
untouched on the grounds that the predicate was ruled correct twice and this only
changes what is handed to it; that is false on the required side, where an empty
`accepts` field is a tool declaring it takes anything and the predicate read it as
proving nothing. Twelve of fourteen tools match nothing for *every* produced spec,
so the fold alone leaves the offer empty — measured in this finding's third
amendment, ruled at
[adr/an-unstated-field-is-a-claim.md](../adr/an-unstated-field-is-a-claim.md), and
its `_unused` change belongs to this item because a resolved position with an empty
offer is not the feature. What stays: no field joins `ToolSpec`: an unstated field in `emits` already
means "any", which at an emit position is the same claim as "whatever arrived"
for every tool on the shelf, so the fold reads a declaration that exists rather
than adding one ([adr/declared-means-verified.md](../adr/declared-means-verified.md)).

**A long offer is the target.** VISION offers "crop, downsample, and the rest of
what takes a single video", so a resolved position offering most of what accepts
its stream is the feature and not a regression of the shortlist the predicate
was tuned for. `admits` and `matches` differ only where something is unstated:
against a produced spec of one dtype and one channel layout, overlap and
containment are the same test. The finding's `admits` column reads at or near
the whole shelf because every position it probed was unresolved, so resolution
converges the two and the choice between them stops being one anybody makes.

The root offer is this same call, so `_offer_over` (`gui/app.py`) stops
returning `()` at the chain's root, and the sentence in its docstring naming
that as "what makes the source unswappable" goes with it. VISION swaps a video
source for the folder holding it, and swaps a generated-background step for a
second source tool; ADR 30 gives the source card un-removability, which is a
different property from the one that docstring claims.

The finding takes a dated amendment in the same commit, its probe re-run over
resolved positions. The count of positions offering nothing is the number it
says to watch, and this is the work that moves it.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests -q -k offering_from_a_resolved_source
    1196 deselected in 0.93s
    exit: 5

The cases the criterion names are the two the fold exists for — the offer under a
source resolved to one video, and the offer under a `crop` reading that source —
and the third the ADR adds, that a tool leaving an `accepts` field unstated is
offered where the stated fields fit.
Both are empty today. `concatenate` is VISION's illustration and not a shelf
entry, so nothing here may name it.

## Folded 2026-08-09: the same scenario's other half, and it is a refusal today

The paragraph above quotes VISION's sentence about the offer; the sentences
either side of it are about the source itself, and nothing carries them. The user
"swaps the source to the folder itself — SIEVE shows the folder as the source,
and the one video in it", then drops a second video in and comes back, and SIEVE
"re-reads the folders the project's own source params name; two files now show in
the source tool, and the box has changed to match".

Two things there that the resolution above stands on and cannot assume. A source
param has to be able to *be* a folder, and several files resolving from one param
has to stop being an error: the landed source tool pins the opposite outcome —
[the-first-source-tool-moves-the-three-single-root-assumptions.md](the-first-source-tool-moves-the-three-single-root-assumptions.md)
carries `a_pattern_matching_several_files_is_refused` in its criterion, and its
body states the policy as "one resolving to several is refused rather than
ordered". That refusal was right for a pattern standing in for one file and is
the wrong answer for a folder, so what is owed is the distinction rather than a
reversal — and the ordering question the refusal was avoiding comes back with it,
since two videos concatenated in the wrong order is a silent wrong answer rather
than a failed run.

And the re-read has a trigger nobody has named. "Comes back to SIEVE" is a window
regaining focus, which is the first thing in the product whose input is neither a
user gesture nor a run — so it is view state that invalidates a resolution, and
the resolution is what this item's fold is computed from. A stale offer is the
visible failure; a stale *resolution* under a live offer is the quiet one.

This is folded rather than minted because the offer and what it is derived from
are one question and were split across two scenarios only by where VISION put the
sentence. `done_when` above is untouched and does not reach either half: it names
the offer under a source resolved to one video, and both additions here are about
a source resolving to more than one. The review that takes this item should widen
it or split the folder half back out — the second is defensible, and this note is
the record of why it was not done unilaterally.
