---
title: A load restamps the version it read, and no rule says a bump must be additive
step: "11.1"
status: awaiting-review
gated_on: nothing
done_when: "uv run pytest tests/unit/test_pipeline_model.py -q -k 'a_load_keeps_the_version_it_read or an_older_document_round_trips_unchanged'"
opened: 2026-08-09
---

# A load restamps the version it read

Half of the discipline is already built and worth saying so, because the shape
that is missing is easy to mistake for the shape that is there.
`Project._known_schema_version` refuses the future outright — a document
declaring a version above `SCHEMA_VERSION` raises, naming both numbers — which
is the right half and the one v2.5's Exchange 1 said was load-bearing. What it
then does is `return SCHEMA_VERSION`: a document that read as an older version
is restamped to the current one and saves as current. Inert today at
`SCHEMA_VERSION = 1`, where there is no older version to read.

11.2 is what makes it live. The node key's `upstream` slot becoming ordered
`(port, key)` pairs is a schema change, and it is the first one this repo will
make, so whatever rule holds for it is the rule by default for every bump after.
v2's record is the argument for making that rule additive-only: five schema
versions in thirteen days, four purely additive, zero transform code needed.
Against a restamp, additive-only is what keeps a round trip honest — a v1
document loaded by a v2 build and saved comes back as v2 and cannot go home, and
with `extra="forbid"` the v1 build then refuses its own project.

What lands is the rule and the case, and the rule is the smaller half: an ADR
saying a bump adds fields and never repurposes or removes one, cited from
`pipeline_model.py` rather than restated in it. The case is what stops the ADR
being decoration — a document at an older version round-trips through load and
save with its own version intact, which is exactly the assertion line 1021
currently fails and nothing runs.

The ADR is a new one, not an edit to whichever existing ADR the reader lands on
first — a changed decision takes a file beside or over the old one.

`done_when` at minting, red because nothing matched:

    $ uv run pytest tests/unit/test_pipeline_model.py -q -k 'a_load_keeps_the_version_it_read or an_older_document_round_trips_unchanged'
    61 deselected in 0.14s
    exit: 5

## 2026-08-10: the first bump queued behind this one removes a field

`adr/a-document-names-footage-only-through-a-tool.md` (34) takes
`Project.source` and `SourceRef` out of schema v1 and names this item as where
the rule for the bump lands — this is the case that forces the rule, not a
second copy of it, and the migration is
[the-field-that-names-footage-leaves-the-schema](the-field-that-names-footage-leaves-the-schema.md),
which sorts into this phase's pool and therefore after this item.

What that costs the paragraph above: "an ADR saying a bump adds fields and never
repurposes or removes one", written flat, is contradicted by the first thing
queued behind it. The v2 record it rests on is unmoved — four of five bumps
purely additive, zero transform code — and so is the argument against a restamp,
which is about what a *load* does and holds whichever way removal is ruled. What
is not settled is the removal clause: whether the rule forbids one outright and
ADR 34 is reopened, or states the terms a removing bump is paid on, of which the
ADR's own "the cost is charged once, at the version" is the direction rather
than the wording. Both readings need the round trip this item's criterion pins,
because a removal is the bump where an older document loaded by a newer build
cannot go home, so nothing below the rule changes.

This section adds no criterion; the ADR the item writes is what carries the
clause.
