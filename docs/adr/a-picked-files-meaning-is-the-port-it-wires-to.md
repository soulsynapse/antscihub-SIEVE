---
title: A picked file's meaning is the port it wires to
adr: 31
position: "04.04.01"
status: settled
decided: 2026-08-09
---

What a user's file *means* — a background rather than a plate — is the port it
wires to, and the user states it. No spec field declares it, no `ElementKind`
encodes it, nothing derives it.

Why: [a-users-file-wires-in-like-any-other-input.md](a-users-file-wires-in-like-any-other-input.md)
made choosing among sources a move of an edge; this says who makes the move and
where the answer lives. A mask is the third case and behaves like the other two:
the port is the whole of the answer, so the list never needs extending. The two alternatives are both closed on their own
reasoning rather than by this ADR.
[an-outputs-kind-is-the-picture-it-makes.md](an-outputs-kind-is-the-picture-it-makes.md)
refuses a member added for a tool, because `ElementKind` answers what an output
*is* and a scene description is not an answer to that. Derivation is refused
because it cannot work here, not because it is unwelcome: the offering ruling
(`todo/the-offering-predicate-is-not-the-edge-legality-check.md`) computes an
offer from what a position's input resolved to, and a file from outside the
project resolves identically whatever it depicts — one `PIXEL` picture of the
same extension class. Derivation is how candidates are *offered*, and an offer
is a suggestion the user overrides; a file the user brought is exactly the case
where there is nothing to suggest from, so the answer is asked for.

What that costs is a question with one answer until a node has two inputs, which
is why the gesture is deferred rather than built
(`todo/which-axis-carries-a-meaning-like-generated-background.md`, gated on the
port-keyed window). What it buys is that the meaning is a fact about the graph:
it is on the edge, it is in the saved file, and it reaches the cache key through
the ordered `(port, key)` pairs the merge introduces rather than as a second
identity beside them — so a reviewer rerunning the project a year later gets the
author's reading of their own file, not a guess made from its pixels.
