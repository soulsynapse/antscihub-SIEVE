---
title: One cut written twice replaces, and nothing asserts it
priority: normal
phase: 8
status: open
gated_on: nothing
done_when: "uv run pytest tests/integration/test_materialize.py -q -k replaces_rather_than_accumulates && uv run pytest tests/integration/test_materialize.py -q"
opened: 2026-08-09
---

# One cut written twice replaces, and nothing asserts it

`CropRecord.identity`'s docstring states the rule — "writing the same cut twice
to two names is one cut recorded twice, and the second write should replace the
first rather than accumulate beside it" — and 08.3 is the commit that made the
rule load-bearing. It is the invariant that ruled out 08.3's rejected shape: a
uniquifying suffix counted off the folder would have kept two distinct cuts off
one file while making the *same* cut land twice, and the region-in-the-stem shape
was chosen precisely because it closes both directions. Nothing in
`tests/integration/test_materialize.py` asserts the second direction, so the
argument that decided the design is prose in a docstring and the suffix shape
could be reintroduced with the whole module green.

The case is one cut materialized twice under one project directory — same
`cut_from`, region, format and span — asserting one `.mkv` under the crops
folder and both records resolving to it, which is what a suffix loop breaks and
what 08.3's own collision case cannot see.

Filed as an aside rather than a decimal because 08.4 does not wait on it: the
behaviour is correct today and this pins it. The reason it is missing is in
`findings/loop/2026.08.09-an-invariant-that-only-the-rejected-alternative-breaks-has-no-red-to-show.md`.
