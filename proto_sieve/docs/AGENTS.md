# proto_sieve — a disposable spike

This is not SIEVE v3. It is an experiment **on the decomposition**, with a
disposal plan and a falsification criterion. The deliverable is not working
code; it is the answer to three questions, recorded in `FINDINGS.md`:

1. Which chunks forced an edit to an earlier chunk's proof.
2. Which chunks could not be specified without a decision that did not exist.
3. Which anticipated changes turned out to be absorbed by two modules.

Keep or throw the code afterwards, genuinely either.

**`STATUS.md` says how far this has got and what the next action is.** Read it
before doing anything. Update it before you stop — it is the only thing here
that survives a cleared context.

## This directory is exempt from the repo's apparatus

The root `AGENTS.md` does not apply here. Specifically, while working in
`proto_sieve/`:

- **No PAR is written.** If a decision comes up, make it, put one line in
  `DECISIONS.md`, keep moving. This rule exists because the design loop it
  suspends is what this spike is diagnosing.
- **No `Owed:` markers, no stamps, no `sieve.debt`, no ledger regen.** A
  column-0 `Owed:` line here would be scanned by the real machinery — do not
  write one, in any file, including comments.
- **No session primaries, no `docs/`, no `ARCHITECTURE.md` amendment, no
  orientation order.** Nothing here is cited from anything there.
- **No placeholders raising `sieve.debt.Owed`.** A thing that does not exist
  yet simply does not exist.
- Do not import from `src/sieve/`. This tree stands alone.

What still applies: one chunk at a time, and a proposal is the deliverable
until it is confirmed.

## The proof vocabulary

Two proofs, and no others. If a chunk needs a third kind, that is a finding —
write it down before inventing one.

- **Hash equality.** `recipe_hash(a) == recipe_hash(b)`, or `!=`.
- **Golden image.** Run it, compare the frame against a committed reference.

Rules on proofs:

- The proof is written **before** the implementation and **observed red**.
  Record the red in the test's docstring. A proof green the moment it was
  written proved nothing.
- **An agent may never edit or delete a test.** A test that looks wrong is a
  halt-and-report, not a judgement call.
- A chunk's proof lives at the boundary, never inside the module. If a proof
  needs revisiting when an implementation changes, it was testing a secret and
  it is in the wrong place.
- At least one test must exercise the whole thing a user does, and it may
  never skip.

## The fence

Each chunk names the files it may touch. Anything outside that set is a
violation, visible in the diff before a line is read.

If a chunk needs something a neighbour does not expose — **halt and report**.
Do not work around it. Every halt is either a missing interface item or a
leaked secret, and the halt list is the point of the exercise.

## The chunks

Each names one secret, one fence, one proof. Order matters: 1 and 2 are the
only decisions here that are unrecoverable if wrong.

| # | Secret | Fence | Proof |
| --- | --- | --- | --- |
| 1 | how an op is represented | `kernel.py` | build the same graph in two processes; hashes equal |
| 2 | what identity means | `kernel.py`, `test_identity.py` | the adversarial pairs — see below |
| 3 | how a graph is evaluated | `executor.py` | golden frame from a hand-built one-node graph |
| 4 | whether a result was computed or retrieved | `executor.py` | chunk 3's golden test **unchanged**, plus two calls byte-identical, plus a counter showing no recompute |
| 5 | how a named user operation becomes a graph | `tools/base.py`, `tools/crop.py` | `hash(lower(p))` equals the hash of chunk 1's hand-built graph |
| 6 | how a pipeline is represented on disk | `pipeline.py` | write, read, lower, same hash |
| 7 | how a result is described for display | `views.py`, `Tool.view` | the view is a value and compares structurally; nothing renders |

Chunk 4 is the load-bearing one: if chunk 3's test has to change to
accommodate the cache, materialization is not a secret and that is the most
valuable thing this spike can tell us.

The GUI is not a chunk. It has no cheap proof, so it is done in a sitting
with Kendrick watching, after everything under it is green.

### Chunk 2, the adversarial pairs

The whole architectural risk on one screen. Each line is one assertion: two
situations that must hash the same, or must hash differently.

- same params, different op
- same op, different implementation (must these collide? — the open one)
- **same requirement, the resolver picked a different op** — the live one; if
  these collide, the store serves whichever landed first
- same everything, different seed
- same everything, different OpenCV / CPU / thread count (bit-reproducibility)
- a hash scheme version field exists at all

**Nothing may be persisted until this file is green.** Everything outside it
can be wrong and fixed with a refactor. Everything inside it, once data
exists, costs a migration.

## Deliberately absent

Named so their absence reads as a decision rather than an oversight:

- **The store.** Content-addressing is proven by the hash; an on-disk store
  with size-budget aging proves nothing about the decomposition.
- **Format migration and the registry.** One version, no registry.
- **Fusion and peephole rules.** One op composes with nothing.
- **Dispatch, eligibility, field types, port binding.** If a chunk reaches for
  any of these, that is a halt and a finding — four deferred decisions all
  converge on `tools/base.py` and this spike is how we learn whether they
  belong there.

## Rebuild passes

When a chunk is rebuilt "properly, by domain":

- The rebuild runs against the tests **with the prototype's source withheld**.
  If it can see the old code it will port it, and porting preserves the
  decomposition we are trying to discard.
- One domain at a time, neighbours available **only as fakes**, and the fakes
  are written by Kendrick or in a separate step — never by the rebuilding
  agent.
- A fake that has to reimplement its neighbour to be useful is a leaking
  boundary. That is a finding, recorded before anything else happens.
- A domain that cannot be tested with its neighbours faked is not a domain.
