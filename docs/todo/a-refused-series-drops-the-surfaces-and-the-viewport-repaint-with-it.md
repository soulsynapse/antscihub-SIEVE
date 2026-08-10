---
title: A refused series drops every surface picture and the viewport repaint with it
priority: normal
phase: 10
status: open
gated_on: nothing
done_when: "uv run pytest tests/gui -q -k a_refused_trace_still_publishes"
opened: 2026-08-10
---

# A refused series drops every surface picture and the viewport repaint with it

`TuningLoop._publish` hands the trace to the graph panel first and the surface
collectors' pictures second, and 10.4 moved the whole of it inside `_render`'s
guard. So a `set_series` that raises — which is the ordinary state of a pinned
`BLOCK` step with no cell soloed, and therefore the state the user is in the
instant they pin one, before the pointer has ever crossed the field — takes the
surfaces with it and leaves `refilled` unemitted. `refilled` is what
`app._paint_viewport` hangs off for everything that is not a walk or a playhead
move, so a parameter drag in that state redraws nothing at all: the trace and
the surfaces carry their stale marks, and the canvas carries none and is simply
old. The product constraint this repo exists for is that drag.

The drop is older than 10.4 — before it the refusal propagated out of the timer
slot and the surfaces were equally unpublished — but 10.4 is where the tree
started calling the outcome "held", and what it holds is one panel's answer
rather than the refill's. `_publish`'s own docstring says the refusal leaves the
panel with its previous answer; it does not say the other three panels and the
viewport get the same treatment, and a reader of that paragraph would not guess
it.

What should be different: one document that one widget cannot render refuses for
that widget only. Everything the same refill produced still reaches the widgets
that can draw it, and `refilled` still says a refill happened, so the picture
under the pointer keeps tracking the sliders while the trace says it has no
answer. Where the refusal is then recorded — `last_error` as now, or something
the graph slot itself carries — is the work's to settle, but a state in which
the whole screen quietly stops moving is not it.
