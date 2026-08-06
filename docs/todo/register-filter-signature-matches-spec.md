---
title: register_filter's signature is FilterSpec's field list
status: open
opened: 2026-08-05T19:22:24-07:00
priority: normal
gated_on: nothing structurally
reads: [src/sieve/core/filter_registry.py, src/sieve/core/filter_base.py]
---

# register_filter's signature is FilterSpec's field list

`register_filter`'s keyword parameters are a hand-maintained second copy of
`FilterSpec`'s fields, and its `decorate` body is a third — fifteen names
written out twice more, which ARCHITECTURE.md §3 already calls "one field
addition away from drifting silently". The symptom of the drift is not a crash:
a field added to the spec with a default is simply unreachable from the
decorator, so every filter gets the default and nothing says so.

One test in `tests/unit/`: `inspect.signature(register_filter)`'s keyword-only
parameters, minus the two that are the decorator's own (`registry`, and
`params_model` which is supplied by the decoration rather than passed), equal
`{f.name for f in dataclasses.fields(FilterSpec)}`. Assert set equality, not
containment — the direction that catches drift is the spec growing a field the
decorator never learned about, and the other direction catches a parameter left
behind after a field is removed.

Independent of `the-spec-has-three-channels`; it reads no channel and was only
ever bundled with it because both are tests over `FilterSpec`'s field list.
Split out so neither has to be started to finish the other.

Fixing the drift rather than testing for it — building the spec from
`**kwargs`, or generating the signature — is deliberately *not* this item. It
would erase the static types on every keyword at the one place a filter author
gets them checked, which is the same argument `ParamsT` exists for. The test is
the whole deliverable.
