# The nodegraph spec

SIEVE's pipeline becomes a wire-node graph in the manner of Houdini's network editor: nodes on a
canvas, wires between typed connectors, a display flag on the node the frame shows, a parameter
pane for the selected node. This directory is the whole specification of that overhaul. It is
written as behavior, not instructions: every line that matters is an assertion that is either
true of the running program or not yet. Nothing here says how.

The work spans sessions. A session that opens this directory cold should be able to tell what is
built, what is next, and what it must not decide.

The final deliverable is the wire-node system working as these files describe, with the
document, the runtime, the canvas, the pane and the window as separate modules whose imports run
one way (see Seams in `window.md`). It was developed against dummy tools until Kendrick retired
them on 2026-10-26; the tools under `tools/` are the referents now, and a `Check:` that names a
dummy is done with one of them. `mock-up/` is reference only.

## How to read a spec file

Each file covers one seam. Under it, each `##` heading is a **deliverable**. A deliverable opens
with an `Assumes:` line naming the deliverables it builds on (by heading, across files), then a
list of **done-when** assertions, each a checkbox:

    - [ ] A document saved and loaded again is equal to the one saved.
      Check: a test in `tests/`.

The `Check:` line says how the assertion is verified: a test, or something Kendrick does with the
running program. An assertion without a `Check:` line is a defect in the spec, not a license.

A deliverable is **done** when every box under it is ticked. A session ticks a box whose `Check:`
is a test, once that test passes in the tree. A box whose `Check:` is something Kendrick does with
the running program is ticked by Kendrick alone; the session says in its handoff that it believes
the assertion holds and what to try. A session never unticks or rewrites an assertion. A box can
therefore lag the code: before building toward an unticked assertion, check whether the tree
already meets it, and if it does, report that instead of rebuilding.

## What to build next

Any deliverable that is not done and whose `Assumes:` are all done is available. Among those,
prefer the one earlier in this order of files: `document.md`, `graph.md`, `window.md`,
`canvas.md`. A session takes one deliverable at a time and stops when it holds, or when it hits a
decision that is not its to make.

## Non-goals and open decisions

Each file ends with **Non-goals**, things deliberately outside this overhaul, each with the reason.
A non-goal is not a prohibition on thinking: if building a deliverable turns out to require one,
the session stops and asks whether the spec may change to admit it, with the evidence. It does not
quietly build it and it does not edit the spec. Non-goals are listed only where there is a reason
to; absence from the list means nothing.

Each file may also end with **Open**, decisions that are Kendrick's and not yet made. A session
that reaches one stops and names it. It does not pick the convenient reading.

## What this spec is not

It carries no measurements, no line counts, no claims about the current shape of the code; those
rot. Where a deliverable depends on something the code has, it names the module to read, and the
reader verifies. It is not a plan and has no phases; order falls out of `Assumes:`.
