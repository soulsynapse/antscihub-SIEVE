---
title: A presentation edit moves no cache key
status: open
opened: 2026-08-05T19:22:24-07:00
priority: high
gated_on: nothing structurally
reads: [src/sieve/core/filter_base.py, src/sieve/pipeline/cache_key.py]
after: [the-spec-has-three-channels]
---

# A presentation edit moves no cache key

ARCHITECTURE.md rule 7's own named gap — "no test toggles a checkpoint and
asserts every key survives" — in its generalized form. Nothing today asserts
that the non-identity side of the spec stays out of the digest.

Once `SPEC_CHANNELS` exists, the test writes itself: for each field whose
channel is `Channel.PRESENTATION`, build a one-node plan, `dataclasses.replace`
the spec with a different value for that field, and assert `node_key` returns
the same string. One test in `tests/unit/`, driven off `SPEC_CHANNELS` rather
than a typed list of three names, so a fourth presentation field is covered by
the row that declares it.

**Be honest about what this is.** It passes on day one for a structural reason
and not a lucky one: `node_key` digests `filter_id`, `version`,
`params.canonical_json()`, the sorted upstream pairs, and `backend_identity`
unless `backend_agnostic` — and never reaches `cost`, `primary_params`, or
`summary`. So this is a tripwire on a whole `FilterSpec` that is handed to a
key function, against the day somebody keys on cost. That is worth having and
it is not a discovery; do not dress it up as one, and do not go looking for a
second assertion to make it feel bigger.

**Scope to presentation, not to "everything unhashed."** Two execution fields
do change what `node_key` does: `deterministic` and `stateful` both feed
`spec.cacheable`, and flipping either makes the call raise `NotCacheableError`
rather than return an unchanged key. A test that swept all non-identity fields
would fail on those two, and the repair somebody would reach for is weakening
the assertion. Execution fields legitimately steer the one path; that is the
channel's definition.

Values to substitute must stay legal — `primary_params` names are checked
against `params_model` in `__post_init__`, so vary it between `()` and a real
field name, not a made-up one.
