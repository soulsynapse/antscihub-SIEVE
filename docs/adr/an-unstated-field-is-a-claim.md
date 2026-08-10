---
title: "An unstated field means any, and the side it sits on says what kind of claim that is"
adr: 32
position: "01.04.01"
status: settled
decided: 2026-08-09
---

An unstated `dtypes`, `channels` or `columns` means *any*: on an `accepts` a
declared universal, on an `emits` a preservation claim that is ignorance only
at a root.

Every predicate over specs reads it that way. A tool declaring an empty
`accepts` field takes anything, so a predicate that refuses it refuses that tool
at every position rather than at one; a tool declaring an empty `emits` field
emits whatever arrived, which is a claim while it has an upstream and nothing at
all without one.

Why: this was already the rule in four places and had no home, so a fifth reader
could contradict it without going red. `ArraySpec` documents the empty tuple as
"any" and gives the reason — a tool that indexes with a stride does not care, and
made to enumerate it would be lying the first time a dtype was added.
`dag._requires_chroma` answers "no demand" for an empty `accepts.channels`,
`cli.inspect` renders it "any dtype", and
[the first source tool](../todo/the-first-source-tool-moves-the-three-single-root-assumptions.md)
rules `crop` and `span`'s empty pair a statement of preservation while refusing
the same pair on a picker, which is where the root exception comes from and is
cited rather than restated here. `ArraySpec.matches` was minted reading a
wildcard as unproven *on either side*, and the measurement is the third
amendment on
[the shelf declares too little](../findings/2026.08.09-the-shelf-declares-too-little-for-eight-of-ten-positions-to-offer-anything.md):
twelve of fourteen tools leave an `accepts` field unstated, so twelve matched
nothing for every produced spec that exists and every one a resolution could
hand them — a predicate no argument can move, which is a constant and not a
shortlist.

The consequence, and the only code the ADR moves: `ArraySpec._unused` stops
giving `not required` and `not produced` one return, and slack becomes
lexicographic — wildcard fields ahead of unused members — so a tool naming the
dtype it takes sorts before one that takes anything, which is the specificity
ordering the offer was already ruled to display by
([todo/the-offering-predicate-is-not-the-edge-legality-check.md](../todo/the-offering-predicate-is-not-the-edge-legality-check.md)).
`matches` stays strictly stronger than `admits`: a partial overlap still admits
and does not match, and an unresolved *produced* side still never matches.

Not enforceable at registration, which is where [ADR 11](declared-means-verified.md)
would otherwise put it: `crop` means the empty tuple, and nothing distinguishes
meaning it from forgetting it, so there is no refusal to make by name. What is
checkable is agreement — the readers above give one unstated field one answer —
and that is the shape the gate takes.
