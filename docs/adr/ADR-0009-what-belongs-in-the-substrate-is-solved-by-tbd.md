---
title: Deciding what belongs in the substrate is solved by TBD
group: Substrate
position: 9
status: unsettled
decided: 2026-08-28
---

What decides whether a capability a tool presses for goes into the substrate
has candidates and no measurement.

Two prohibitions are settled and are not what is open: SIEVE never names a
tool, or that tool is a feature and the cap is gone; and a tool never reaches
past the contract, or whatever it touched is an API and the substrate can no
longer change there. Open is the third case, where a tool cannot do its job
through what SIEVE provides and the pressure has to land somewhere. Composition
is inside the boundary; whether the contract is ever published is separate.

## Candidates

L4's minimality principle (Liedtke, *On µ-Kernel Construction*, SOSP 1995) — a
concept is tolerated inside only if moving it outside would prevent the
required functionality. Checkable per capability, which is what this lacks;
would have to be measured by the audit below.

Hydra's policy/mechanism separation (Levin et al., SOSP 1975) — substrate
supplies mechanism, client supplies policy, and the substrate is finished when
it cannot name what the policy is about. The ancestor, and weaker: it states the
split without a test for where a given thing falls.

The dogfooding constraint as Nuke's NDK and VapourSynth enforce it — shipped
tools go through the contract a third party gets, so a private door is found in
this tree's own code. Not a rival to the two above but what makes either
enforceable, and the half that could be a check in `checks/`.

The experiment all three wait on: implement this tree's tools against the
contract alone and report every place one presses past it.

## Rejected

Mach's kernel growth cautionary tale: the minimal kernel accreted until its IPC
path was the performance story, and L4 exists as the reaction.

ImageJ1's plugin API cautionary tale: internals leaked so thoroughly that
rebuilding the boundary took a parallel implementation plus a compatibility
layer, and the migration is unfinished.

napari's npe1 cautionary tale: the same shape recently enough to be a documented
post-mortem — plugins reached into the viewer, npe2 is a manifest contract, and
the breaking migration is the bill.

Hyrum's Law is why both happened, and is stronger than the second prohibition
above: behaviour visible *through* a contract gets depended on too.

CellProfiler cautionary tale, as a different bet rather than a defect: a hundred
named modules that are the product. Named so the refusal reads as a choice.
