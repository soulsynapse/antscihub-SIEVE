---
title: SIEVE is not its tools
group: Substrate
position: 9
status: settled
decided: 2026-08-28
---

SIEVE is substrate: it gets frames in a named form, schedules work over them,
shows what was produced, and routes an interaction to whatever asked for one —
without naming any tool. A tool does its work entirely through what SIEVE
provides; one that has to reach past the contract has found a defect in the
contract, not a private door. That list can be completed; the set of things
an ethologist might want to measure cannot, and the boundary is what keeps
the two from being one codebase with no finished state.

The boundary is two prohibitions, and they fail differently. **SIEVE never
names a tool.** The moment it does, that tool is a feature, the next one is
too, and the cap is gone — accretion, one reasonable request at a time. **A
tool never reaches past the contract.** The moment one does, whatever
internal it touched is an API whether or not anyone meant it to be, and the
substrate can no longer change there — freezing. When a tool cannot do its
job through what SIEVE provides, the pressure lands on SIEVE as a
generalized capability, not as per-tool accommodation — each instance of
which is small, justified, and whose sum is a substrate shaped by the
history of requests.

## What this does not decide

**How tools compose.** Whether a tool is a node, what an edge means, and how
a chain is scheduled reopen on evidence. This ADR fixes only which side of
the boundary the answer lives on: composition is something SIEVE provides.

**Whether there is a published API.** The contract exists the moment two
prohibitions hold; whether it is formalized for an author outside this tree
is a separate decision.
