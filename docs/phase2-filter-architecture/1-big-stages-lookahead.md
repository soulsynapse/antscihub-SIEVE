## Big stages lookahead.

This list of assessments is a *naive* agent assessment, who was only given a high level overview of what SIEVE is, what it essentially does, and what the deliverable is.


**This document goes more stale as development proceeds, and it may be inaccurate from the start!**

You can leave links to findings that either invalidate or support the assessment. If you do the assessment and it was done, you can point to the completed todo list item as well.

Order should not be assumed to be correct. This list is meant for inspiration only; validity must be checked.

## INITIAL ASSESSMENT

SIEVE — Structural Requirements
Each header states what must be true. Each line states what fails if it isn't. No solutions specified.

Tier I — Declaration
1. The contract is the only place a question about a stream is answered
IF a layer needs a fact about a stream that the contract cannot express, THEN that layer answers the question locally in its own vocabulary, RESULTING IN parallel type systems that each must be updated per filter and that drift out of agreement with one another.
IF an inexpressible case has no sanctioned provisional form, THEN it is expressed as an opaque payload under deadline pressure, RESULTING IN a handoff that validation, cache identity, and lineage cannot see through.
2. Declarations are extensible in shape
IF a declaration is fixed as a scalar or a closed set, THEN every later axis or member requires editing every filter that declares it and every layer that reads it, RESULTING IN a coordinated migration for what should have been an additive change.
3. Declaring a filter is the only act required for it to be available
IF availability depends on an entry in a list kept separately from the declaration, THEN every author seeking reachability edits a file every other author also edits, RESULTING IN one contended edit point whose cost grows with filter count and which silently omits whatever was never added to it.
4. Temporal, causal, and reproducibility behavior is declared
IF the shell cannot learn from a declaration whether a node streams, depends on prior frames, emits irregularly, or reproduces exactly, THEN it must branch on filter identity to schedule, scrub, and cache correctly, RESULTING IN filter identity embedded in the shell and playback semantics that break on any filter it does not recognize.
5. The set of available handoffs is queryable
IF the outputs a filter offers and what they mean can only be learned by reading its source, THEN authors copy assumptions rather than consume declarations, RESULTING IN coupling that no validation, cache key, or static check can detect.

Tier II — Authoring
6. The authored graph expresses everything the execution graph expresses
IF the authoring surface cannot represent a topology the executor supports — multiple inputs, multiple outputs, fan-out, reconvergence — THEN filters of that shape have no path to existing through the tool, RESULTING IN whole categories of filter being unreachable no matter how self-contained they are.
7. A connection carries correspondence, not only type
IF two edges of the same type are interchangeable at a node's inputs, THEN a miswiring is admissible to validation, RESULTING IN a legal graph that computes the wrong answer and reports nothing wrong.
8. Identity namespaces shared between filters are declared
IF filters agree on a naming convention — object ids, track ids, region labels — that appears in no declaration, THEN the agreement exists only in the authors' understanding, RESULTING IN a dependency that cannot be validated, versioned, or noticed when it drifts.
9. Interaction is inherited from what a parameter is
IF a parameter requiring direct manipulation must have its control hand-written, THEN the low-cost path covers only filters whose parameters are scalar, RESULTING IN every spatially or spectrally parameterized filter carrying bespoke interface code and its own state synchronization.
10. Presentation surfaces are assigned and arbitrated by the shell
IF filters render and accept input without a shell-owned assignment and a rule for who holds interaction, THEN each filter must reach toward surfaces other filters already occupy, RESULTING IN a cost per addition that scales with the number of filters already present.
11. There is one integration path
IF a second, more capable integration path exists, THEN it is what the next author copies, RESULTING IN an invariant that is optional in practice and behaviors that work in only one place and therefore cannot be reasoned about or safely replaced.

Tier III — Durability
12. The identity of a result is derived from declarations
IF cache identity is authored by hand, or omits state, ordering, or nondeterminism, THEN a stale result is indistinguishable from a correct one, RESULTING IN silent wrongness that presents as working software.
13. Failure and state are contained to the failing node's subtree
IF one node's error or corrupted state propagates beyond its own downstream subtree, THEN every author is accountable for the reliability of every filter that might share a graph with theirs, RESULTING IN additions that are guarded, half-wired, or never made.
14. Saved work survives change at both filter and contract scope
IF schema evolution has no owner at filter scope, THEN every parameter change requires editing central logic that must know every filter's history, RESULTING IN re-centralization at the most frequent kind of change.
IF schema evolution has no owner at contract scope, THEN the first change to a shared type or to topology has no migration path, RESULTING IN every previously saved graph becoming unopenable.
15. Every requirement above is checked by something that fails on violation
IF a requirement is asserted but unenforced, THEN it erodes one filter at a time under ordinary deadline pressure, RESULTING IN a property that was true when written and unverifiable at any point after.
