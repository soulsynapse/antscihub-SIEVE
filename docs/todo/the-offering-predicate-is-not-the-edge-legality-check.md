---
title: The offering predicate is a plausibility question, and admits cannot answer it
status: deferred
deferred_for: decision
gated_on: what a plausibility offer is keyed on — an Emission name, a new ElementKind member, or the path stereotype ADR-18 spends — and whether the answer is an ordering or a yes or no, and whether a tool declares its own plausibility or has it derived
priority: normal
phase: "07"
opened: 2026-08-07
---

# The offering predicate is a plausibility question, and admits cannot answer it

[VISION.md](../VISION.md)'s last scenario has a user select a folder of videos
and be offered both the concatenate-videos tool and a folder of pre-cropped
videos, "with the tool picker display: the user decides how the input is
interpreted". Whatever computes that shortlist, it is not `StreamSpec.admits`,
and that negative is what this item exists to hold. Nothing here invents the
replacement.

`ArraySpec.admits` says of itself that it is "deliberately permissive: it is
false only when the two sets are provably disjoint. A wildcard on either side
admits" (`core/tool_base.py`), and its one caller is `Dag._edge_faults`, which
runs it over every edge of a drawn graph to reject the graphs that *cannot*
work. That is a legality question, and permissiveness is the right answer to it
— the docstring's own reason is that rejecting a graph which merely cannot be
proven to work "would make declaring `dtypes` at all a liability". Reused as an
offering predicate the same permissiveness inverts: an empty `dtypes` or
`channels` on either side admits, so the shortlist for a folder of videos would
be nearly every registered tool whose `accepts` is an `ArraySpec`. An offer that
admits everything is a tool list, and the user already has one. The two
questions also want opposite failure modes — legality must never refuse a graph
that would have run, while an offer must refuse most of the shelf to be worth
displaying — so a predicate tuned for one is wrong for the other by
construction, not by an oversight fixable with a threshold.

What a plausibility ranking is keyed on is open, and is this item's own second
half. Nothing in the tree answers it: what is available at offer time is a set
of picked files and their extensions, the specs on the shelf, and — once
[the first source tool](the-first-source-tool-moves-the-three-single-root-assumptions.md)
lands — the path stereotype ADR-18 spends, which is what makes a tool
recognisably one that reads a file at all. Whether that is enough, whether the
answer is an ordering rather than a yes or no, and whether a tool declares its
own plausibility or has it derived, are the questions to settle before anything
is built. Two constraints do bind whatever it turns out to be:
[gui-knows-kinds-not-tools](../adr/gui-knows-kinds-not-tools.md) and the empty
`gui-computes-nothing` exception list put the computation below `gui`, so the
picker display renders a shortlist it is handed; and a wrong offer is a
suggestion the user overrides, where a wrong `admits` is a graph that will not
run — which is the second reason they are not one function.

Filed in Phase 7 because that is where the surface consuming this lives, not
because the predicate is GUI code.
