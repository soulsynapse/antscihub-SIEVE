---
title: One field is one populated value
adr: 21
position: "01.06"
status: settled
decided: 2026-08-08
---

A composite stereotype sits on the field that holds the whole value, never on
one bound of a pair, and registration proves it against `params_model`.

So a tool selecting an interval carries one pair-shaped parameter rather than
two bounds wearing one kind, and the map is read against the annotations it
stands over rather than trusted (`adr/declared-means-verified.md`).

Why: the alternative — a generator that groups a tool's fields by shared
stereotype — is correct only while no kind that is one-field-per-value appears
twice on the same tool, and `tools/detect.py` already declares several bands
that are each a whole value. The rule would hold by arithmetic about the
current shelf and fail silently on the first tool with two intervals or two
regions, which is a class this design expects: a lead-in and a lead-out, an A/B
of two windows, a source rectangle and a destination.

The sharper reason is that arity is undo granularity, not only widget
generation. Phase 7's undo is two stacks of whole pipeline values keyed by
intent kind, with one command layer as the document's only writer. A drag on a
timeline is one gesture; if the value it edits is two fields, that gesture is
either two commands — two undo entries, and an intermediate state the params
model's own validator refuses — or a bespoke multi-field intent, which is the
per-tool special case `adr/gui-knows-kinds-not-tools.md` exists to prevent.
`crop`'s region has never had the problem because it was always one field.

The invariant is checkable at registration today, with no generator: the
declared kind is compared against the annotation that carries it. That is what
makes this a decision the tree holds rather than a convention each tool
restates in a comment.

What it costs is one tool's parameters and the ported test that constructs
them; the goldens are unaffected, since the values do not move. Editing a
ported test is a decision under `PLAN.md`'s porting discipline, and this ADR is
that decision rather than a run's judgement call.

What this does not decide: which axis or series a band's handles are dragged
against. That declaration is owed to the plotting surface and arrives with it,
not here.
