---
title: The output is a step, and its ticks are edges
step: "09.7"
status: open
gated_on: nothing
done_when: "uv run pytest tests -q -k ticks_are_edges"
opened: 2026-08-09
---

# The output is a step, and its ticks are edges

What leaves the chain is a card at the foot of it, not a screen beside it:
the write list is the output step's param, ticking a product makes the step
that emits it an input of the output node — derived, so the picture cannot
disagree with the writes — the edges into the card are labeled by product,
and Run sits on the output's form. The save screen dissolves into it; its
pane was one step's form, so it is that step's form. MOCKUP-MAP.md row
"Output is a step" — `WRITES`, `refresh_output_inputs`, `_write_list`,
`_port_name`'s output branch and `_run_row` in the referent; VISION's
`output-1` guidance paragraph carries the argument. The map's review also
bounds it: the `into` folder and format combo on the referent's form are
*not* settled — the settled part is the shape. This spans layers by design —
an output tool on the shelf, the tick-to-edge derivation beside the graph,
the GUI rendering both — and the ticked list is what 07.9's checkoff becomes,
entering as the output node's param through the ordinary command path.

`done_when` at minting, red because nothing matches:

    $ uv run pytest tests -q -k ticks_are_edges
    1000 deselected in 0.93s
    exit: 5
