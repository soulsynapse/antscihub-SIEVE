# Decisions

One line each, made in passing, never argued into a document. This file exists
so that a decision does not become a drafting session.

Format: `<date> — <decision> — <why, in a clause>`

- 2026-08-03 — the harness splits in two: a **measurement** harness that
  produces an interchangeability table (offline, statistical, corpus-driven)
  and a **resolver** that consumes it (hot path, deterministic, no
  measurement) — because a runtime path must not depend on a statistical
  instrument, and the table is a value that can be stale without being
  wrong-in-kind. Only the resolver is in this spike.
- 2026-08-03 — a tool **declares a requirement**; it does not construct a
  graph of named ops — because implementation choice belongs to the resolver,
  which is what lets ops be free and autopopulated by dispatch. This differs
  from `Tool.lower(p)` as written in the repo, deliberately.
- 2026-08-03 — the pipeline is a DAG, and the GUI's up/down arrows walk a
  **spanning tree** over it, not the graph — so "down" from a branch is a
  choice the GUI makes, not a fact the pipeline holds.
- 2026-08-03 — "ops are free" means free to *write* (proliferation is fine,
  dispatch finds them). It is not a claim about run cost; only the resolver
  reasons about that.
- 2026-08-03 — the recipe hash carries a scheme version from the first commit
  — one field now converts an unrecoverable decision into a recoverable one.
- 2026-08-03 — **open, and the most expensive thing here**: does the resolved
  op enter the recipe hash? If it does not, two computations share one address
  and the store serves whichever landed first. Chunk 2 states the pair; it is
  not answered by writing the hash function.
- 2026-08-03 — the proof-first regime is dropped for chunks 5 onward; `tests/`
  is deleted — Kendrick chose to move on plain implementation instead. See
  `STATUS.md` for what that costs (chunks 5/6 are REPL-verified, not pinned).
- 2026-08-03 — code moved from `proto_sieve/*.py` to `proto_sieve/src/sieve/*.py`,
  docs moved to `proto_sieve/docs/` — mirrors the real repo's `src/sieve/`
  path so a later promotion is a directory move, not a rewrite. Nothing was
  copied from the real `src/sieve/`; the two trees still do not import each
  other.
- 2026-08-03 — chunk 2's live pair resolved: the resolved op enters the hash,
  so `Slice` and `Resample` never collide even when bit-identical — collision
  would smuggle the deferred interchangeability claim into the resolver's hot
  path; no-collision-to-collision is additive later, the reverse isn't.
- 2026-08-03 — tests live in a `__tests__/` directory colocated with the
  modules they cover (`sieve/__tests__/test_kernel.py` next to `sieve/kernel.py`,
  `sieve/tools/__tests__/test_crop.py` next to `sieve/tools/crop.py` — one
  `__tests__/` per directory of modules, not a top-level `tests/` tree) — a
  module that can't test its own claim isn't the one that owns that claim.
