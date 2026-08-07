---
title: The one VISION never-line that no contract checks gets one
priority: normal
phase: "0"
status: open
gated_on: nothing
opened: 2026-08-06
---

# The one VISION never-line that no contract checks gets one

`.importlinter`'s header calls the file "the forbidden edge set of VISION.md's
component table, made checkable". Walking the table's `Never` column against the
five contracts, every import-shaped never has a contract behind it except one:
`pipeline` must never reach into `ops/`. It is legal under every contract in the
file — `core` sits below `pipeline`, so the import points downward — which is
the same hole `gui-computes-nothing` exists to close one layer up, and the
reason it exists there applies here for the same reason: reaching a tool's array
math from the executor is the second execution path
(adr/one-execution-path.md), taken from the layer that owns the first.

Either the edge gets a contract or the header comment stops claiming the set is
complete; the first is the one worth having. Note that the entry will be inert
until `src/sieve/core/ops/` exists
(`docs/findings/2026.08.06-a-forbidden-module-that-does-not-exist-is-inert.md`),
so its proof of red is owed at ops admission, not when the line is written —
adr/ops-admission-is-two-tools.md names when that is.
