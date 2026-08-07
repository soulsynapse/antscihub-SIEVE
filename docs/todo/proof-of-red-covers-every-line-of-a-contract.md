---
title: Proof of red covers every line of a contract
priority: low
phase: 0
status: open
gated_on: nothing
opened: 2026-08-07
---

# Proof of red covers every line of a contract

00.2's gate added one violating edge per contract and watched each go red,
which proves the contract is wired up and leaves every other line in it
untested. The one line that went untested was also the only one that could
not have fired — a forbidden module that does not exist is inert
(`findings/2026.08.06-a-forbidden-module-that-does-not-exist-is-inert.md`,
`findings/loop/2026.08.06-one-red-per-contract-certifies-the-contract-not-its-lines.md`).

Per-line proof is the honest version: each forbidden module, each layer edge,
each exception, violated in turn. That is a lot of red for a contract file
that grows slowly, so the version worth building is the one that generates
the violations from the contract file rather than listing them by hand — a
test that reads `.importlinter` and asserts every line in it can fail cannot
go stale when a line is added.

The trigger to build it is a contract gaining a line, which 02.0.1 does when
`sieve.mutual` joins the layers. Doing it then means the new line is proven
by the mechanism rather than by another hand-written edge.
