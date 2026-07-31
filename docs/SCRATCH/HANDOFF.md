# Handoff — writing the constitution

**What exists.** `docs/SCRATCH/principles-inputs.md` is the derivation and the evidence.
`docs/SCRATCH/principles_inputs_distilled.md` is what survived it: 3 top-level claims (Part
B), 74 durable claims grouped by bearer (Part C), 13 contingent claims with expiries (Part
D), 12 corrections to the source documents (Part E), 4 open items (Part F), 2 housekeeping
defects (Part G). `docs/CONSTITUTION/_TEMPLATE.md` is the per-invariant form.

**What does not exist.** Any invariant file. Any minted ID. Any check on the document.

**What this file is.** The order of operations, the decisions that cannot be made later, and
the per-file recipe. It dies when `docs/CONSTITUTION/` is complete.

---

## The shape of the plan, and why

Not one `principles.md`. `_TEMPLATE.md` already commits to one file per invariant with a
permanent ID scheme, and that is the right call for the reason C61 gives: a single document
is a folder with several unrelated secrets in it.

**The unit of work is one invariant file, written vertically to completion.** Not a
horizontal pass that drafts every `Holds` line, then every `Rule`, then every `Adherence`.
The template's two hard fields — `Depends on` and `Adherence` — are only tested by finishing
a file, because an edge is discovered while writing the rule at the other end of it, and a
rung is discovered by searching the tree for enforcement that already exists. A horizontal
pass produces 76 rules at rung 5 and calls it a constitution.

**The first file finished is the reference member for the rest** — C66 applied to this work.
Whichever file goes first sets what a real `Example` and an honest `Adherence` look like, and
every later file is written by copying it. That is worth spending disproportionate effort on.

**Size, honestly.** 76 rule slots. A rule with a copy-pasteable example from the tree and a
researched rung is 25–40 lines. That is 2,200–3,000 lines across nine files, and the
expensive part is not the writing — it is the tree search behind each `Adherence` line. Plan
one file per session; `O` (16 rules), `S` (11) and `M` (10) will not fit in one each.

---

## Phase 0 — Decisions that cannot be made later

IDs are permanent once minted. Everything here must be settled before the first ID exists.

### D0.1 — The partition and the letters (irreversible; needs your confirmation)

`_TEMPLATE.md`'s CONVENTIONS block proposes `D` (DAG), `M` (Measurement), `V` (Visibility),
`X` (crosscutting) — the charter's three invariants plus a bin. **Do not use it.** Under that
partition, `X` receives ownership (C25–C27), verification (C54–C60) and structure (C61–C71):
twenty-one rules in a folder whose secret is "several unrelated ones," which is the failure
ORGANIZATION §3.2 names and which C61 is a rule against. The document would violate itself on
its first page.

Partition by **bearer** instead. Bearer is the template's own discriminator, and A1 clause 2
is the reason: the bearer is what makes a claim survive an implementation change, so it is
also what makes a *file* survive one. Part C is already grouped this way.

The charter's three invariants are not lost — they become the target of every `Breaks if
violated` line. Each file's loss must reduce to one of: *the pipeline stops being executable
or reproducible*, *the user cannot answer will-this-run-on-my-machine*, *the user cannot know
what the tool can do*. A file whose loss reduces to none of those is not an invariant.

| File | Letter | Bearer | Carries | Rules |
|---|---|---|---|---|
| `PREMISES.md` | `P` | SIEVE's boundary | B1, B2/C72, B3, C73, C74 | 5 |
| `OPERATOR.md` | `O` | the call | C9–C24 | 16 |
| `KEYING.md` | `K` | derived value | C1–C8 | 8 |
| `MEASUREMENT.md` | `M` | unit of work | C44–C53 | 10 |
| `LOG.md` | `L` | edit | C28–C34 | 7 |
| `VISIBILITY.md` | `V` | capability | C35–C43 | 9 |
| `OWNERSHIP.md` | `R` | contended resource | C25–C27 | 3 |
| `VERIFICATION.md` | `T` | artifact and consumer | C54–C60 | 7 |
| `STRUCTURE.md` | `S` | module | C61–C71 | 11 |

`R` at three rules is the one call worth re-examining. Keep it separate anyway: *contended
resource* is a distinct permanent bearer, and C69's argument — no single one of five thread
owners or three caches was expensive to add — is the reason v2 failed. Folding it into `O` or
`S` hides the thing that killed the last attempt inside a file about something else.

Part D's 13 contingent claims are **not** separate rules. Each attaches to an existing rule as
an expiry. See D0.5.

### D0.2 — F2: is there a unit above a single source? (blocks `K`, `O`, `M`)

The distilled file calls this "the largest gap the corpus has." Every C-part claim is stated
per-source, and the target workload is 100 replicates over 100,000 files spanning eight weeks.
Downstream of the answer: C22's addressing descriptor needs a source axis or it does not;
C1/C2 either key a collection or they do not; C19's per-task cost either extrapolates across
source count or it does not; C45–C47's load parameter is either per-source or not. Writing
`K`, `O` or `M` before this is decided means rewriting them.

Not a research task. Decide whether cross-source aggregation is a first-class operator kind or
a downstream script, and write the sentence.

### D0.3 — F3: name the tune-on-sample-run-on-the-set operation (blocks `L`, `K`)

It is not save/load, not preview-versus-run, not redeployment. It is the author's actual
workflow. If it is an operation, it produces a log entry and a key relation, and `L` and `K`
must both account for it. If it is deliberately unnamed, `L` says so.

### D0.4 — F4: do the superseded documents survive as an archive? (blocks Part E)

Part E's 12 corrections cite `ARCHITECTURE §3.1`, `CHARTER line 55`, `PLAN Phase 6`. If those
files are deleted, every one of those pointers has to be inlined first — the correction has to
carry the text it corrects. Cheap decision, do it early, because it changes how Part E is
consumed in Phase 1.

Note that PLAN.md is not merely superseded, it is **wrong**: Phase 6 verifies that a warmup
shortfall raises, and Part E item 1 decides the other way. It cannot be left in the tree for
an agent to read as instructions.

### D0.5 — Amend `_TEMPLATE.md` before the first file uses it

1. **Add an `Expires when:` field to the rule form.** Part D requires every contingent claim
   to carry its expiry, and the template only accommodates this when the *bearer* is the
   today-noun. It does not accommodate the case where the bearer is durable and the
   *enumeration* is contingent — "determinism has exactly two classes," "preview and run are
   the two trigger policies." Those need an explicit field or they will be written as flat
   claims.
2. **Resolve A1 clause 3.** The distilled file states the cost-asymmetry clause and then says
   it "demotes every repo-side claim and keeps every contract-side one, which is a defect in
   the test rather than a fact about the material" — while Part C asserts every entry survives
   all three clauses. Those cannot both be true. The repo-side claims are exactly C61–C71, the
   `S` file. Repair the clause (the fix is in the text: the aggregate is the unit, per C69) and
   write the repaired version into CONVENTIONS, or `S` gets written against a test known to
   reject it.
3. **Close the rung-5 list.** The template says the irreducibly-a-reading rules "are enumerated
   once in CROSSCUTTING.md and that list is closed." There is no CROSSCUTTING.md under the
   bearer partition. Move the closed list into `CONVENTIONS.md` and populate it as files are
   written — a rule may only land at rung 5 by being added to that list, and additions stop
   when the list is declared closed.

**Phase 0 output:** `docs/CONSTITUTION/CONVENTIONS.md` (ID scheme, partition and its
rationale, the closed rung-5 list, the repaired A1) and an amended `_TEMPLATE.md`.

---

## Phase 1 — Make the document check itself, before writing the bulk of it

This is the highest-leverage item in the plan and it is ~150 lines of pytest. Every rule
written after it exists is verified for free; every rule written before it has to be
re-verified by hand.

**Replace `tests/docs/test_scaffold.py`.** It is staged, it reads `docs/SCAFFOLD.md` which the
gutting deleted, and it currently produces 4 errors and 2 vacuous passes. It is the only docs
check in the tree. Delete it rather than regenerating SCAFFOLD.md — ORGANIZATION §9 already
rejects a hand-maintained folder inventory as "stale and authoritative-looking at the same
time," which is what that file was. Reuse the module docstring's framing; it is the right idea
pointed at the wrong artifact.

`tests/docs/test_constitution.py` asserts:

1. **Every `src/sieve/...` citation resolves.** The file exists and contains the named symbol.
   **Change the citation format from `path:NNN` to `path::symbol` when transcribing.** Every
   line number in the distilled file was checked at `9ed3b40` and will rot; `filter_base.py`
   moving one line silently falsifies eight citations. A symbol reference survives edits and is
   checkable. Where the citation is genuinely to a line (a constant, a magic number), cite the
   symbol that encloses it.
2. **Every ID is unique and well-formed**, matching the letter of the file it appears in.
3. **Every `Depends on` resolves** to an ID that exists, or is marked as forward-referencing an
   unwritten rule. A3 says an unwritten edge is a rewrite waiting to be discovered; a dangling
   edge should be visible, not silent.
4. **Every rule has an `Adherence` rung**, and every rule at rung 5 appears on the closed list
   in CONVENTIONS.
5. **Every rule at rung 1–3 names its mechanism**, and the named file exists.
6. **No section is vacuous** — the failure mode `test_scaffold.py`'s own docstring identified.
   If a file parses to zero rules, that is a failure, not a pass.

Item 1 is the one that makes the corpus durable. The other five are cheap.

---

## Phase 2 — Write the files

Order, and the reason for each position:

1. **`P`** — five rules, mostly verbatim carries. It is the only file that can reject work, so
   an agent needs it first. Write B3 (the mirror) with an honest rung: it is rung 5 on both
   sides today and the plan for the product side is `dag.py::admits` run backwards.
2. **`O`** — the reference file. Best rung evidence in the corpus: C24 is already rung 1 at
   `filter_base.py::_require_element_meaning`-equivalent, and C9/C10 have live port-arity
   enforcement in `dispatch.py`. Spend the disproportionate effort here.
3. **`K`** — depends on `O`'s declarations. C2's failure is live in the tree and gives the
   file a real worked example.
4. **`M`** — after D0.2. C51 is worth carrying verbatim; it is what stops the file reading as a
   performance mandate.
5. **`L`** — after D0.3.
6. **`V`** — depends on `O` (declarations are what generation reads) and `L` (C33).
7. **`R`**, **`T`** — short, independent.
8. **`S`** — last. Its claims are the ones A1 clause 3 demotes, so it needs D0.5.2 settled and
   it benefits from eight files' worth of practice at honest rungs.

### Per-file recipe

1. **Invariant header.** `Holds` is a fact about the system, not an instruction. `Breaks if
   violated` must name one of the three charter losses concretely — "the user cannot answer X,"
   never "quality degrades." If you cannot name the loss, the claim is not an invariant.
2. **One rule per claim.** If it needs an "and," split it. Part C's entries are already mostly
   one claim each; C1/C2 and C11/C12 are deliberate pairs and stay two rules with an edge.
3. **`Example` comes from the tree, not from imagination.** Part C's References section already
   names the file for most rules. Where the `# do` half does not exist in the tree, write only
   the `# don't` half and let `Adherence` say rung 4 or worse — an invented canonical form is
   how a rule claims enforcement it does not have.
4. **`Adherence`: search before you write the rung.** The default is not rung 4. C24 turned out
   to be rung 1 already; C38's generation precedent already exists in `inspect_cmd.py`; C42's
   authored half already exists in `bench/budgets.py::IN_DEBT`. For every rung-4/5 that
   survives the search, write one line naming the rung-1/2/3 mechanism that would replace it
   and what it costs. That line is the debt register entry (Phase 3).
5. **`Depends on`.** A3 names four edges to start: staleness↔shedding,
   materialize-once↔engine-owned-placement, start-offset↔checkpointing,
   frame-identity↔ordered-delivery. Find more while writing. Import direction is not the test.
6. **Run the Phase 1 test.**

### Corrections that must land while transcribing

Part E is not commentary; it is a list of statements an agent will otherwise read and act on.
Six of the twelve change what a rule says:

- **E1** — warmup shortfall is legal at a source boundary and keyed there, not an error.
  Contradicts ARCHITECTURE §3.1 *and* PLAN Phase 6's verification. Goes in `K`.
- **E2** — history is two-sided. Goes in `O` as C13.
- **E3** — visibility is disclosure, not parity. Goes in `V`. Under the old reading the entire
  build plan is unconstitutional.
- **E5** — both determinism questions are decided: class is infectious with tolerant artifacts
  pinned, and a declared tolerance names the *source* of non-determinism. Goes in `K`.
- **E10** — closure ("cannot be built wrong") is right for repo states and wrong for user
  states; an invalid intermediate graph is a legal user state. Splits across `S` and `L` (C34).
- **E12** — the new-type gate is superseded; creation stays free and the check moves to the
  folder's subsequent behaviour. Goes in `S` as C71.

E6–E9 and E11 are corrections *to the source documents* and need no rule; they matter only if
D0.4 keeps those documents readable.

---

## Phase 3 — What the document produces, which is not the document

Two outputs fall out of Phase 2 and belong in a successor to PLAN.md, not in the constitution:

**The debt register (C42).** Every rung-4/5 line from recipe step 4. C42 requires it be
*generated* — the difference between declared capability and reachable capability — so the
authored half is only the prose reason, modelled on `bench/budgets.py::IN_DEBT`.

**The reference member set (C66).** Four hard shapes — one carrying state across frames, one
taking more than one input, one changing rate, one with a two-sided window — none of which
exist. This is the single highest-leverage code item in the corpus because it is doing three
jobs at once: anti-reinvention (C66), the repo-side precursor index that makes B3 mechanical
rather than prose, and rung 3 for most of `O`. Every `Adherence: rung 3` line written in Phase
2 is a promissory note against it.

---

## Contradictions in the corpus, unresolved

Flagged rather than smoothed. Each needs a decision, and four of them are already Phase-0
items.

1. **`_TEMPLATE.md`'s ID scheme presupposes a partition the corpus outgrew.** See D0.1. The
   template also references `CROSSCUTTING.md`, which does not exist under any partition the
   distilled file supports.
2. **A1 clause 3 is stated as defective and applied anyway.** See D0.5.2.
3. **B3 makes ORGANIZATION §7 load-bearing while ORGANIZATION is scheduled for deletion.**
   "Holding the mirror therefore costs ORGANIZATION §7 being load-bearing rather than advisory,
   and its hard-shape set must be complete rather than illustrative." A load-bearing commitment
   cannot cite a dying document. §7's content must be lifted into `S` and `P` verbatim, not
   referenced.
4. **C43 puts a mechanism inside a principle.** The principle is "a derived view reports the key
   of the artifact it is showing and its settled boundary." The subscription-token design —
   identity on the subscription, a small integer resolved through an engine-owned side table —
   is architecture. Carry the principle; move the mechanism to ARCHITECTURE's successor. The
   distilled file half-anticipates this by saying what matters more is that the component has a
   named contract and is swappable.
5. **B1's consequence versus Part D's enumerations.** B1 says every enumeration presented as
   exhaustive is a foreclosed choice. Part D presents four: two determinism classes, two trigger
   policies, two path classes, four hard shapes. The resolution is that Part D's expiry
   discipline *is* the mechanism that satisfies B1 — an enumeration that carries the condition
   expiring it has not foreclosed anything. **State that explicitly in `P`**, and make the rule
   general: a new enumeration arrives with an expiry row or it does not arrive. This is also why
   D0.5.1's `Expires when` field is not cosmetic.
6. **Part D's shed-versus-backpressure row names a gap and leaves it.** "A long-running
   background derivation the user watches but does not interact with has no assignment." That is
   not an expiry condition, it is a case with no policy — and it describes the export path of the
   author's own workflow. Decide it in `R` or record it as an open item alongside F1–F4.

## Housekeeping

- `tests/docs/test_scaffold.py` is staged and broken. Phase 1 deletes it. Do not commit the
  staged version.
- `docs/.state.md` should point here and at the distilled file's F1–F4 (Part G2). Updated.
- **F1 has no source and cannot be reconstructed from the repository.** What v1 did better, and
  why it did not reach v2. It is the only input in the corpus with nothing behind it. Do not
  block on it: the distilled file already gives the transferable form — what crosses a rewrite
  boundary is a *check*, not code, so if F1 is ever recovered it arrives as tests, and tests can
  be added at any time.
