---
title: A composite parameter prints no shape and no bounds
priority: low
phase: 7
status: open
gated_on: nothing
opened: 2026-08-07
---

# A composite parameter prints no shape and no bounds

`sieve inspect` reads each parameter's constraints out of the params model's
JSON Schema, which works for a scalar and degrades to nothing for a field whose
annotation is a model or an optional. `crop`'s `region` prints type `any` with
its whole default dict beside it, and `detect`'s `count_frac` prints type `any`
because an optional is an `anyOf` and the keywords sit one level down. So the
three parameters whose legal range a user is least able to guess — a rectangle,
a band, an optional band — are exactly the ones the bounds are missing from,
while `window_frames` gets its `minimum` and `maximum` printed.

The fix is to walk one level into `anyOf` and `$ref` before reading
`_CONSTRAINT_KEYS`, not to give the CLI a second description of the parameter
space: the schema is what Phase 7's generator will build widgets from, and a
hand-written table here would be the drift `core/tool_base.py` keeps
`params_model` as the single source of truth to avoid.

Filed under Phase 7 because that generator meets the same schema and the same
gap, and whoever writes it will have to resolve a `$ref` anyway. Nothing gates
this; the terminal is simply less useful than the declaration allows until then.
