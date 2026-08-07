---
title: A per-replicate setting is asserted against the whole README rather than its section
priority: normal
phase: 5
status: open
gated_on: nothing
opened: 2026-08-07
---

# A per-replicate setting is asserted against the whole README rather than its section

`test_both_documents_configured_the_same_run` in
`tests/integration/test_v2_oracle.py` is the one test in the oracle whose
subject is the correspondence between v2's own account of its settings and v3's
document. It loops over both replicates and asserts each one's detection window
is a substring of the entire README, so swapping the two replicates' windows
leaves it green — each assertion is satisfied by the other replicate's section.
It discriminates a dropped mechanism and not a misattributed value
(`docs/findings/loop/2026.08.07-a-per-entity-loop-asserted-against-the-whole-document-checks-only-the-union.md`).

The heading it already computes is the fix's anchor: `f"### {name}"` is asserted
present and then discarded, when it marks exactly the slice of the document the
window fragment has to be found inside. The per-replicate fragments belong in
that slice; the four project-wide fragments below the loop — the signal node, the
bands, the count threshold — are correctly scoped to the whole file, since v2
writes them once per replicate from one `DetectorSettings` and either section
proves them.

Not blocking the oracle: the two gate-parity tests kill the permutation, so the
file as a whole is not vacuous. What is lost is that the failure names a frame of
footage instead of naming the configuration that moved, which is the harder
diagnosis of the two and the reason this test exists.

Done when the permutation of the two replicates' windows in `REPLICATES` fails
`test_both_documents_configured_the_same_run`.
