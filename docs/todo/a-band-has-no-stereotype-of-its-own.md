---
title: A band has no stereotype of its own, and three of detect's params are one
priority: normal
phase: 1
status: open
gated_on: nothing
opened: 2026-08-07
---

# A band has no stereotype of its own

`ParamStereotype` closes at five kinds and `SPAN` is written as "a half-open
interval of frames or time". `tools/detect.py` has three parameters that are a
pair of handles dragged along an axis — `freq_band` in Hz, `value_band` in the
incoming signal's units, `count_frac` as a fraction of the frame's elements —
and none of the three is frames or time. They are declared `SPAN` today because
the map is total over `params_model` and the tool had to register; the
declaration says the right thing about *how the value is populated* and the
wrong thing about what axis it is populated on.

Two answers are worth weighing. `SPAN` widens to "an interval on a declared
axis", which costs one sentence in `core/tool_base.py` and leaves the generator
needing to learn the axis from somewhere else. Or a sixth kind arrives, which is
what the vocabulary's own docstring says a tool that cannot be expressed in five
should force — and this is the first tool that cannot.

Nothing generates a widget yet, so the wrong-axis reading costs nothing until
Phase 7 reads it. What it costs *now* is that `adr/declared-means-verified.md`'s
registration check is the only consumer, and it is passing a declaration its
author does not believe.
