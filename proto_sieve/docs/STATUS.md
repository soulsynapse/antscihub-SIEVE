# Status

Where the spike is. Update this at the end of every working stretch — it is
the only thing that survives a cleared context. Read `AGENTS.md` first; this
file says only *how far*, never *what the rules are*.

Last updated: 2026-08-03 (chunk 2's live pair decided).

**The proof-first regime (red-then-green tests, `tests/`) was dropped by
Kendrick this session.** `proto_sieve/tests/` was deleted. Chunks 5 and 6
below were built and hand-verified at the REPL, not pinned by a committed
test. `AGENTS.md`'s "the proof is written before the implementation" section
is stale for everything after chunk 4 — do not treat it as still governing.

Code now lives under `proto_sieve/src/sieve/` (mirrors the real repo's
`src/sieve/` path, so a future promotion is a directory move) rather than
directly under `proto_sieve/`. Docs live under `proto_sieve/docs/`.
`proto_sieve/CLAUDE.md` stays at the top level as the pointer file.

| # | Chunk | State | Verified by |
| --- | --- | --- | --- |
| 1 | op values, recipe hash | green | test, deleted this session |
| 2 | identity — the adversarial pairs | green, **incomplete** | test, deleted this session |
| 3 | `render`, no cache | green | test, deleted this session |
| 4 | the cache, invisibly | green | test, deleted this session |
| 5 | tool declares a requirement; resolver picks the op | green | REPL check only |
| 6 | pipeline on disk | green | REPL check only |
| 7 | view as a value | green | REPL check only |
| — | GUI | not a chunk; a sitting with Kendrick, last | — |

Chunk 2's live pair — *same requirement, resolver picked a different op* — is
resolved (see `DECISIONS.md`, 2026-08-03): the resolved op enters the hash,
so `Slice` and `Resample` never collide, even when bit-identical. This was
true of the code as written (`Node.op` is the concrete resolved op, and
`_canon` tags every dataclass by type name) before it was named a decision —
naming it is what this entry records. Still unexercised by a committed test,
per the caveat below.

## Next action

All seven chunks are green and chunk 2's live pair is decided. The remaining
item is the GUI sitting with Kendrick (not a chunk — no cheap proof).

## Caveat a fresh session must not skip

Nothing here is committed — `proto_sieve/` is entirely untracked. The claims
in `FINDINGS.md` (chunk 4 not forcing an edit to chunk 3, chunks 5/6/7 hashing
or comparing correctly) are demonstrated, not pinned. Without either the old
tests or committed code, none of it is re-checkable except by rerunning the
REPL snippets by hand.
