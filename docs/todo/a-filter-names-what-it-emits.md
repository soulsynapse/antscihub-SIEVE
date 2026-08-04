---
title: A filter names what it emits
status: open
opened: 2026-07-29T12:18:58-07:00
priority: normal
gated_on: nothing
after: [the-spec-has-three-channels]
reads: [src/sieve/core/filter_base.py, src/sieve/detect/tables.py]
---

# A filter names what it emits

Channel labels on the spec — the settled half of the old presentation
question, and it is *interop* vocabulary, not presentation: if the CSV writer
and the plotter invented separate naming schemes they would be wrong about
each other, which is R4's test for promotion into the shared vocabulary.
`ElementKind` is this bug already half-fixed — a count has a noun that came
from the graph — while the column it lands in is still hand-authored in
`detect/tables.py`, downstream, where rule 8 makes every column name an
agreement with a reader that is not SIEVE.

A filter declares the names of what it emits; `detect/tables.py` reads them;
the plot axes read the same declaration. This is the CSV bug, the plot-axis
problem, and detection column naming as one fix. The cross-layer column-name
check in `a-filter-id-spelled-twice` stops being vacuous the day this lands.
