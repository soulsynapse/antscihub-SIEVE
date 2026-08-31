---
title: Deciding what belongs in the substrate is solved by TBD
group: Substrate
position: 9
status: unsettled
decided: 2026-08-28
---

SIEVE is substrate: it gets frames in a named form, schedules work over them,
shows what was produced, and routes an interaction to whatever asked for one —
without naming any tool. That list can be completed; the set of things an
ethologist might want to measure cannot, and the boundary is what keeps the
two from being one codebase with no finished state. What decides whether a
capability a tool presses for goes *into* the substrate has candidates and no
measurement.

The boundary is two prohibitions, and they fail differently. **SIEVE never
names a tool.** The moment it does, that tool is a feature, the next one is
too, and the cap is gone. **A tool never reaches past the contract.** The
moment one does, whatever internal it touched is an API whether or not anyone
meant it to be, and the substrate can no longer change there. Both are settled
and neither is what is open here: what is open is the rule for the third case,
where a tool cannot do its job through what SIEVE provides and the pressure has
to land somewhere.

## Candidates

L4's minimality principle (Liedtke, *On µ-Kernel Construction*, SOSP 1995) — a
concept is tolerated inside the kernel only if moving it outside would prevent
the implementation of the system's required functionality. Checkable per
candidate capability, which is what this ADR currently lacks, and it converts
"the pressure lands as a generalized capability" from a stance into a decision
procedure. Would have to be measured by the audit below: implement every tool
this tree has against the contract alone, count what presses and where, and
apply the criterion to each press.

Hydra's policy/mechanism separation (Levin, Cohen, Corwin, Pollack & Wulf, SOSP
1975) — the substrate supplies mechanism and the client supplies policy, and
the substrate is finished when it cannot name what the policy is about. The
ancestor, and the reason the first paragraph above can claim its list is
completable. Weaker as a candidate than L4's because it states the split
without a test for where a given thing falls.

The dogfooding constraint, as Nuke's NDK and VapourSynth enforce it — the tools
the substrate ships go through the same contract a third party gets, so a
private door is discovered from this tree's own code rather than from a
stranger's. Not a rival to the two above but the thing that makes either of
them enforceable, and the reason it is listed separately is that it is the half
that can be a check in `checks/` rather than a judgement.

The experiment all three wait on is the same and is cheap: an audit that
implements this tree's tools against the contract alone and reports every place
one presses past it. That produces a count and a list, which supersede rather
than argue.

## Rejected

Mach's kernel growth cautionary tale: the kernel that was meant to be minimal
accreted until its IPC path was the performance story, and L4 exists as the
reaction. Accretion is not a slope argument here — it is a decade of
consequences with a named successor.

ImageJ1's plugin API cautionary tale: internals leaked so thoroughly that
rebuilding the boundary required a parallel implementation (ImageJ2/SciJava)
plus a compatibility layer, and the migration is still not finished. This is
the freezing prohibition with a bill attached.

napari's npe1 cautionary tale: the same shape, recent enough to be well
documented as a post-mortem — the first plugin system let plugins reach into
the viewer, the second is a manifest-based contract, and the breaking migration
is what it cost. Both of these sit on `docs/related-software.md` under
cautionary tales, and this is what they are cautionary about.

Hyrum's Law is the general statement of why both happened — with enough users,
all observable behaviours of a system will be depended on by somebody — and it
is stronger than this ADR's second prohibition, which speaks only of reaching
past the contract. Behaviour visible *through* the contract is depended on too.

CellProfiler cautionary tale, with the caveat that it is a different bet rather
than a defect: around a hundred named modules that are the product. Viable, and
what SIEVE refuses — named here so the refusal reads as a choice rather than as
the only option.

## What this does not decide

**How tools compose.** Whether a tool is a node, what an edge means, and how a
chain is scheduled reopen on evidence. This ADR fixes only which side of the
boundary the answer lives on: composition is something SIEVE provides.

**Whether there is a published API.** The contract exists the moment two
prohibitions hold; whether it is formalized for an author outside this tree is
a separate decision.
