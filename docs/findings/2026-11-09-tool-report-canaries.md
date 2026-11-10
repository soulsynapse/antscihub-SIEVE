# Two reports over what tools declare, and what each found in the catalogue in a minute

2026-11-09, on v5 at e17fe0fc, from docs/findings/experiments/2026-11-09-tool-naming-table.py and
docs/findings/experiments/2026-11-09-tool-pair-report.py, both run over `tools/` through
`sieve_player.registry.discover`. Neither reads a tool's body; each reads the facets a tool declares
(`EXPECTS`, `PRODUCES`, `INPUTS`, `PATHS`) and, for the second, the module's top-level names. The
session was a naming conversation (docs/spec/tool-naming.md); the reports were written to test a
naming grammar and found tool defects instead.

## The class strain report

The first script was to derive a contract-carrying name per tool. To name a tool that takes several
types it needed a word above the types, so it declared two classes, `plane` over bgr, gray, hsv,
mask and flow, and `table` over blobs and tracks, and wrote a strain column wherever a tool's
declared union is a proper subset of a class. Ten of forty tools strained, and bake spanned both
classes. Read against each tool's docstring the ten sort in two:

| tool | declared | class less | principled |
|---|---|---|---|
| motion | gray, mask | bgr, hsv, flow | yes: a single-channel absolute difference |
| changeenergy | gray, mask | bgr, hsv, flow | yes: single-channel |
| reduce | gray, mask | bgr, hsv, flow | yes: a per-pixel statistic wants one channel |
| flow | gray, mask | bgr, hsv, flow | yes: optical flow is single-channel |
| blobs | gray, mask | bgr, hsv, flow | yes: components of one channel |
| bg-subtract | bgr, gray | mask, hsv, flow | mask arguable; hsv and flow principled |
| rescale | bgr, gray, mask | hsv, flow | hsv arbitrary; flow principled, vectors scale |
| background | bgr, gray, mask | hsv, flow | hsv arbitrary; flow arguable |
| coarsegrain | gray, mask, flow | bgr, hsv | arbitrary: a block mean of three channels is a block mean |
| inrange | bgr, hsv | gray, mask, flow | gray arguable, see threshold below |

Four refusals the tools' own docstrings cannot defend: rescale and background without hsv,
coarsegrain without bgr and hsv, bg-subtract without mask. None was known before the column was
printed. The class table is the one thing declared by hand; everything else is read.

## The pair report

The second script asked which pairs of tools look like one tool declared twice. Three signals were
tried. A shared operation word once kind words are stripped from `NAME` named exactly two pairs,
csv with tracks-csv and filter with tracks-filter, and no other. The fraction of top-level names
the two modules share, facets excluded, then separated them: csv and tracks-csv share five of eight
(the sink's `count`, `default_name`, `write`, `settings`, `lines`), filter and tracks-filter one of
six. Reading the bodies agrees: the csv pair differs only in whether a row writes one value or one
line per record, which is the wire's shape and not the file's, while the filter pair are two
operations, a per-record field range and a per-id property over the window. A difflib ratio over
the source with facet lines removed was the third signal and was dropped: it rated fifty pairs
above 0.45 because forty short modules share their `settings` and `__main__` boilerplate, and it
rated the two real pairs lowest of all, 0.21 each.

## What a report of this shape can and cannot see

Both reports are derived from declarations, print, and gate nothing; a line they print is a
question for a reader, not a failure. That is the shape `python -m sieve_player.registry --check`
already has in one instance, its orphan-type check, which also catches a typo in `EXPECTS` since a
misspelt type is expected by one tool and produced by none. The pattern is cheap because the facets
exist for the player's own reading and the report borrows them; it adds no vocabulary a tool
author must learn, and its reasoning cannot go stale because none is stored.

Its limits, met in the same session. It cannot see whether a body is generic over a class: that
count's fold is a table's length and size's method reads any numeric column, so both serve tracks
unchanged, was a reading of the bodies, and no declaration says it. The verb stripping is lexical
over the kind words of the day and would miss a pair whose names differ by a synonym. The
names-shared threshold was tuned on one pair and may need retuning when the catalogue holds a
second sink family. And a class table drawn by hand can be wrong in the same way a name can: `any`
in the first script meant every type including path, which no tool but a selector takes, so bake
read as spanning classes when it takes every wire type and no path.
