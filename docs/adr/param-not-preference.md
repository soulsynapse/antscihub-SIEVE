---
title: What can change an output is a param
adr: 9
position: "02.03"
status: settled
decided: 2026-08-06
---

A value that can change an output is a param — in the artifact, in the cache
key; one that can only change presentation or performance is a preference,
and anything ambiguous is a param.

Why: this is what makes one artifact produce one result on two machines; let
a result-shaping value hide in preferences and finding out why two runs
disagree takes a very long time. v2.5 named it the one boundary to fix on day
one (`docs/archive/DESIGN-SESSION.md`, Exchange 2). The canonical preference
is the preview base layer: flipping tracks between source, mask, and
background plate is the fastest diagnosis in the product ("did subtraction
drop the animal, or did association break?"), and it works precisely because
the choice never touches the artifact — swap mid-scrub, invalidate nothing.
