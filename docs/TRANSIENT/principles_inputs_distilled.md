# Distilled inputs — and the fold-in queue

## Status against the normative set

`principles.md` no longer exists; its unique content is in ARCHITECTURE and the
rest was already here. This file was the work queue for the fold-in, and the
section below is the map of where each claim went.

**Parts A through E are closed.** What remains is Part F: F2, which gates
ARCHITECTURE §10 and is a design decision rather than a transcription; F3, the
unnamed tune-on-a-sample operation; and F1's residue, which has no source and
cannot be reconstructed. Everything below this section is the derivation and the
evidence, and two entries are now superseded by what landed rather than by
anything they say — C8 by ARCHITECTURE §1.11 and Part D's table by its own third
column.

The map was built by reading the current text of the three normative documents
rather than from memory, but phrase-matching across wrapped lines has false
negatives, and the fold-in found two: C48's argument was already half-stated in
ARCHITECTURE §2.3, and C8's framing had been overruled by ADJUDICATION Q9. Both
are recorded where they landed.

**Part A.** All landed except A4, which is superseded by STRATEGY §6's four
document kinds and §3's in-code ledger. A1 is STRATEGY §6.5, with clause 3
stated over the accumulated class and pointing at §2.3 for why. A2 is §2.3,
with *generated* restored as level 1 after the move dropped it; *default path*
was deliberately not restored — it is not a place where anything is refused, and
the mechanism it named lives in ORGANIZATION §7. A3 is §4's closing paragraph:
the coupling relation is a graph over contracts, its edges are not the import
edges, and the edge is recorded as a citation in the rule that depends on it.
Half of that reaches rung 3 and half is read, which is stated rather than
smoothed. A3 had been dropped twice — it was also the deleted `_TEMPLATE.md`'s
`Depends on` field.

**Part B.** All three landed. B1 is STRATEGY §1.4, B2 is §1.2 with both worked
refusals, B3 is §1.6 with two guards the distilled did not state: the precursor
relation is derived from declared I/O and never authored beside it, and the
enumeration is unordered or ordered only by a declared cost.

**Part C, by group.** Sections are ARCHITECTURE unless marked.

- *Derived data.* C1–C8 landed (§1.1, §1.1, §1.2, §1.3, §1.1, §1.5, §1.10,
  §1.11). C8 landed in its adjudicated form and not the one stated below:
  ADJUDICATION Q9 refused the gate, and STRATEGY §8's table already carried the
  ruling — measured and keyed as a source-layer property rather than verified
  before the key schema is committed. The entry below is pre-adjudication and is
  superseded by §1.11.
- *The operator contract.* C9–C24 landed (§2.7, §2.7, §3.5, §3.5, §3.1, §2.1,
  §2.1, §2.2, §2.3, §2.3, §2.3, §2.5, §2.6, §8.5, §2.9, §8.4).
- *Ownership.* C25–C27 landed. C26 is §2.8 and C27 is §9.4; C25's general form
  is now §2.8's closing paragraph, with §9.4 and §2.2 named as its other two
  instances.
- *The log.* C28–C34 landed (§5, §5.1, §5.2, §5.3, §5.5, §5.6, STRATEGY §1.6).
- *Legibility.* C35–C43 landed (§6.1, §6.2, §6 with STRATEGY §6, §6.6, §6.5,
  §6's Forbids, §6 with STRATEGY §0, STRATEGY §3 and §1.6, §4.4 and §5.4 with
  identity held open at STRATEGY §9).
- *Measurement.* C44–C53 landed (§7.1, §7.2, §7.4, §7.4, §7.6, §7.3, §7.5, §7's
  preamble, §1.9, STRATEGY §0). C47 and C48 were the two the normative set was
  missing while PLAN Phase 4 already stated both in full — PLAN carrying a
  requirement it had nothing to derive from, which inverts STRATEGY §6.3.
- *Verification.* C54–C60 landed (§9.1, §9.2, §9.2, §9.3, §9.3, §8.1, §8.2).
- *Structure.* C61–C68 and C71 landed in ORGANIZATION (§1, §2, §2.1, §5, §4,
  §7.2, §7.4, §8, §3.2). C69 landed as the second paragraph of STRATEGY §2.3 —
  a rule whose violations are individually cheap and unbounded in count is
  enforced automatically or not at all, the aggregate being the unit, which is
  the justification for the ladder and was missing from it. C70 landed as
  ARCHITECTURE §2.9's closing paragraph — an optimization is a new operator
  version with identical declared semantics and a different cost shape.
- *Scope.* C72–C74 landed (STRATEGY §1.2 and §0, ARCHITECTURE §10, §1.4).

**Part D** is landed. All twelve carry an expiry; the third column of its table
says where. The treatment was decided once for the batch rather than per claim,
because the twelve differ only in their bearer:

- The expiry is written **inline, in the rule's own text**, in the form of an
  observable event. The rule that requires this is STRATEGY §6.5's bearer clause,
  which is why A1 had to land first — without it the twelve annotations are a
  tidiness pass that the next amendment undoes.
- A **Decision debt under §3.5 is the stronger half and cannot be declared yet**:
  the ledger is in code, collected by import, and there is no code. §6.5 states
  the sequence — the expiry lives in the text now and acquires a declaration in
  the register once a module owes it — so this is deferred by a stated mechanism
  rather than dropped.
- Two rows were already handled (determinism §1.5, event time §4's Forbids), and
  two had **no contingent claim in the normative set to annotate**: nothing
  asserts cgroup or SLURM as the mechanism of a ceiling, and nothing asserts a
  fixed set of named interactions. Both were closed by stating the durable core
  where it belongs and leaving the today-nouns unnamed, which is the outcome the
  row wanted rather than a row that could not be done.

**Part E** is fully discharged. Ten items landed in the normative set or the
archive headers during this session's amendment pass; the two FINDINGS errata
were applied to FINDINGS directly.

**Part F.** F2 is decided: the unit above a source is a declared **collection**
whose members are a source plus that source's parameter overlay. Two members can
name one asset and differ in a threshold, so the member is the overlay and not
the file. It landed as ARCHITECTURE §1.12, with the reduction axis at §2.10, cost
as a sum over members at §7.7, the member axis on the addressing descriptor at
§8.5, a fifth hard shape at ORGANIZATION §7.2, and a row in STRATEGY §8.
Membership is a key term by inheritance from §1.1 rather than by a new rule.

F3 is answered by F2 and needed nothing else. The sample is a subset of the
members, the full run is all of them, and the spec does not change between them —
what the operation was missing was never machinery but a unit to be a subset of.

ARCHITECTURE §10's boundary is **withdrawn**, on the author's account of what it
was for: planning for eventualities was not meant to dictate the design, and it
was never meant as a constraint. Written as a boundary it read as one and could
not survive being one, since a hundred-member collection is the ordinary case and
is what one machine per run forbids. §10 keeps the permanent exclusions and the
durable half — nothing in §§1–9 may assume the executing machine holds the
interface.

**F1 is open and its premise was wrong.** This file says the v1 list cannot be
reconstructed from the repository; v1 exists on disk at `optical-flow-detector`
in the parent folder. The one thing recorded so far is the author's: v1 is more
performant and does things v2 is slow to do, cause unknown. Per F1's own
argument, the transferable form is a check that fails until the behaviour exists,
not a module and not a note.

F4 is answered: the superseded documents survive as ARCHIVE.

**Part G** is closed. Both defects are fixed.

---

# Distilled inputs for `principles.md`

Every entry is stated as settled unless it says otherwise. Nothing here is posed as a
question that has been answered, and nothing carries a framing that a later decision
replaced. `principles-inputs.md` is the derivation and the evidence; this file is what
survives it.

Indices (`A1`, `C7`) are local to this file and are **not** constitutional IDs. IDs are
permanent once minted and none are minted here.

**References prefer the tree over the documents.** CHARTER, ARCHITECTURE, ORGANIZATION,
PLAN and FINDINGS are being superseded, so a `§3.1`-style pointer dies with them; a
`src/sieve/...:NNN` pointer survives. Every in-tree line number below was checked against
the working tree at commit `9ed3b40`. Where a document reference is the only one available
it is marked *(dying source)*.

---

# Part A — How the document must be built

## A1. The durability test

A claim belongs in `principles.md` only if it passes all three clauses.

1. **Discrimination.** Describe, in one sentence, the system in which the claim is false, as
   something a competent person would build on purpose. If you cannot, the claim is the
   product rather than a principle.
2. **Bearer.** Name the noun the claim constrains and why that noun exists under any
   implementation. If the bearer is a today-noun — *frame*, *video*, *widget*, *GUI*, *tab*,
   *thread*, *filter*, *pixel*, *rectangle*, `__init__.py` — the claim is contingent on that
   noun and must be marked with the condition that expires it. Permanent bearers in this
   corpus: *derived value*, *the call*, *contended resource*, *declaration*, *artifact*,
   *consumer*, *edit*, *unit of work*, *version*, *module*, *contract*, *hazard*.
3. **Cost asymmetry, measured over the accumulated class rather than one instance.** State
   what adopting the claim costs now versus after the system is built. A claim that is cheap
   to fix once, with no bound on how many times it will need fixing, has a large aggregate
   ratio and is a principle. Measured per instance this clause demotes every repo-side claim
   and keeps every contract-side one, which is a defect in the test rather than a fact about
   the material.

The framing this test rests on: "won't go stale no matter what" is a decision, not a
prediction. The operative question is not *which of these will remain true* but *which am I
willing to reject a change for*.

**References:** `principles-inputs.md` §1 for the argument and for why the five-substitution
candidate test fails; §8.1 for the clause-3 correction and the evidence that produced it.
Prior art named for rejection: Parnas & Clements 1986 (*A Rational Design Process: How and
Why to Fake It*), Parnas 1972, Lampson 1983 (*Hints for Computer System Design*, the
counterargument), Lakatos on hard core versus protective belt.

## A2. The adherence ladder

Adherence is ranked by when the cost is paid. A rung-4 check is a placeholder for a
rung-1/2/3 mechanism nobody built, and should read that way.

| Rung | Mechanism | Cost paid |
|---|---|---|
| 1 | **Unrepresentable** — the wrong thing cannot be written | Never |
| 2 | **Generated** — the thing is not authored; it derives from a declaration | Never |
| 3 | **Default path** — the easy way is the correct way | Negative, at authoring |
| 4 | **Checked after** — CI fails, the work is redone | After the work |
| 5 | **Reviewer judgment** — capped, closed list | Every time, by whoever reads |

The operative form: **a principle whose adherence requires knowing the principle has already
failed.** The population is agents; an agent that has lost context will not recall a rule, it
will do whatever the tooling makes easy. Rungs 1 and 2 do not require the rule to be known.
Rung 3 mostly does not, because copying the nearest working example is what a context-free
agent does anyway. Rung 4 requires the rule known *after* the work, which is the
write-fail-rewrite loop.

Two riders. **Judgment is a budget, not a fallback** — if every rule may fall back to
judgment, every rule will; the irreducibly-a-reading rules are enumerated once and that list
is closed. **A rung-1 refusal states the alternative** — refusing and handing over the fix
costs an agent nothing, refusing alone costs it a search, and the search is where it invents
something.

**References:** the in-tree model for a teaching refusal is
`src/sieve/core/filter_base.py:199-211`, which refuses registration of an array-emitting
filter that declares no element meaning and names both legal answers in the error.
Implemented in `docs/CONSTITUTION/_TEMPLATE.md`. Prior art: Shingo (poka-yoke), Bloch (easy
to use correctly, hard to use incorrectly), Lampson, correct-by-construction.

## A3. The document is a graph, not a list

ARCHITECTURE's sections are nodes; the edges — which properties are only valid in the
presence of which others — are what the principles document supplies and what no existing
document states. Two contracts can import nothing of each other and still be unable to change
independently, and that pair is what produces a rewrite nobody predicted. An unwritten edge is
a rewrite waiting to be discovered.

Edges already identifiable: staleness-as-display-state is required by shedding and optional
without it; materialize-tolerant-artifacts-once is required by engine-owned placement and
meaningless without it; start-offset-in-key is required by checkpointing; frame identity's
mechanism is determined by whether delivery is ordered.

Import levelization (Lakos, and ORGANIZATION §5) is a different relation and does not catch
these.

**References:** `principles-inputs.md` §8.6. Author's framing: "if streaming is part of the
criteria and you want to change how the streaming coupling works, now you have to change at
least two things. This is why principles feeds architecture."

## A4. Template fields

Each invariant carries **Holds / Bearer / Breaks if violated / Depends on / Scope**. Each rule
carries **Rule / Bearer (if narrower) / Rationale / Depends on / Example / Adherence /
Latitude**. `Adherence` states the rung and the mechanism and replaces the former `Check` and
`Guarded by`, because a field named *Check* asks to be filled with a check rather than with
the truth about how the rule is held.

**References:** `docs/CONSTITUTION/_TEMPLATE.md`, already written.

---

# Part B — The top-level claims

## B1. SIEVE makes every choice available and legible; it does not make the choice

The corpus's missing top-level claim. Stated by the author, and absent from CHARTER,
ARCHITECTURE, ORGANIZATION, PLAN, FINDINGS and both invariant derivations:

> "The ability to select between different modes being announced to the user and giving them
> full knowledge of what they're selecting bypasses most of the judgements that you seem to
> think SIEVE needs to make. The main outcome of this is that however it is implemented
> eventually, the structural organization of the repo and how the code is organized makes any
> choice possible."

Two halves. The second is organizational: structure must not foreclose a choice, because the
choice belongs to someone else. This subsumes visibility (announce), the open registry (the
choice is available), the debt register (announce what is not available yet and why), and the
scope exclusion (do not judge).

It is strictly stronger than ORGANIZATION §1's Parnas criterion for the case that matters
here. Parnas says hide a decision that might change; this says do not *make* a decision that
is the user's, and a well-hidden decision is still made.

Consequence not yet drawn anywhere: every enumeration presented as exhaustive is a foreclosed
choice. That is a larger commitment than the open-registry decision alone made — see D.

## B2. SIEVE may not own a decision whose correctness depends on the user's scientific question

The only rule in the corpus that can reject work, now with a general form and two worked
examples. Rejects: detection statistics; footage quality recommendations; any parameter
default presented as *recommended* rather than merely *preset*; quality scores; a
did-this-work verdict; automatic threshold selection; ranking of results.

Does not touch cost estimation, determinism class, pressure policy, scheduling, or numeric
tolerance — those are decisions about **computation**, not **interpretation**. Checkable by
inspection: name the decision, then name what would make it wrong. If the answer involves the
user's animals, it is out of scope.

**References:** author's exclusions — "it should deliberately exclude analysis of the results
(stats on the detections — this is user decisions which SIEVE doesn't own), recommendations on
how to provide good footage (it works with what it's given, a pipeline works with what it
receives)." Charter's original, worth carrying close to verbatim: "Something that doesn't
enable something for the pipeline, it is outside the scope of SIEVE" *(dying source: CHARTER
line 55)*.

## B3. The mirror, in operational form

**Given a desired target, the set of things that can satisfy its precursors is enumerable, and
each candidate is announced with what it in turn requires.** Backward chaining over a declared
precursor relation, serving both halves.

Product side: the user wants output artifact T; the engine enumerates operators whose declared
`emits` admits T and recurses on their declared inputs, terminating at sources. Repo side: an
agent needs capability C; the enumerable candidates are the reference members demonstrating a
contract that admits C.

An invalid graph is a target with unsatisfied precursors. A debt is a capability with
unsatisfied precursors. One query, two lifetimes, two materializations.

**Where it is weaker than it reads, and this must not be smoothed:** the two sides are not
equally checkable. The product-side relation is a type relation and is mechanical. If the
repo-side relation runs over `__init__.py` purpose lines it is prose, and prose has no
`admits` — which is why ORGANIZATION §8 can only promise a generated guide and then concede it
is a diagnostic. The repo side becomes mechanical only if the precursor index is the
**reference members**, because those execute. Holding the mirror therefore costs ORGANIZATION
§7 being load-bearing rather than advisory, and its hard-shape set must be complete rather
than illustrative.

**References:** author, on Q8 — "how to get from having a desired target and filling in all the
requirements to get to that target should be obvious and self-announcing... how we work in
SIEVE's repo is almost move for move the same as SIEVE itself." The product-side parts exist
in the tree and were never run backwards: `src/sieve/pipeline/dag.py:201` (`admits`) and
`:215` (`ElementKind` propagation), while `src/sieve/gui/wizard_model.py:84` hand-wrote the
catalog instead. Prior art: type-directed program synthesis; Hoogle for the repo side.

**Correction of record:** both scratch derivations and `principles-inputs.md` §6 independently
rejected the mirror thesis as uncheckable and recommended it as an epigraph. All three were
wrong. Carry CHARTER line 69 verbatim *and* mint an ID for it.

---

# Part C — Durable claims

Grouped by bearer. Each survives all three clauses of A1. Stated self-containedly so the entry
does not depend on a document that is being deleted.

## Derived data — bearer: *derived value*

**C1.** A key is the transitive closure of everything the output depends on: operator identity
and version, resolved parameters, requested geometry, and the keys of its inputs.
**C2.** And nothing else. A key names *what an artifact is*, never *how it was obtained*; the
route of derivation is provenance. A cheaper route to identical bytes must not invalidate
everything it was meant to help.
**C3.** Membership in the executable graph *is* deterministic keyability, checked at
registration rather than by review.
**C4.** Nothing derived is authoritative. Any cache, proxy, or materialized intermediate can be
deleted with recomputation cost as the only consequence.
**C5.** Key the hazard rather than forbid the capability it endangers.
**C6.** Determinism is declared, and the declaration is a key term. Never inferred from a
version string.
**C7.** Source identity is content-derived, or at minimum path-independent.
**C8.** Frame-exactness of a source is an obligation verified by test before the key schema is
committed, not an assumption about a third-party decoder.

**References.** C2's failure is live: `src/sieve/pipeline/resolve_source.py:47` returns
`source_identity(path)` at `:70` when a crop artifact backs a replicate, while
`src/sieve/pipeline/dag.py:286` drops the ROI for pre-cropped sources — so the same frames key
differently depending on whether an optimization has run. C5's counter-example is
`src/sieve/core/filter_base.py:250` (`cacheable = deterministic and not stateful`) with
`src/sieve/pipeline/cache_key.py:61` raising and `src/sieve/pipeline/dag.py:311` and `:293`
skipping any node whose parent was skipped, so one stateful node leaves the whole downstream
graph unkeyed. C1/C2's omission is verifiable: the digest terms at
`src/sieve/pipeline/cache_key.py:68-75` are upstream keys, filter id, version, canonical
params and backend identity — no start offset, no span, no supplied history. C6:
`src/sieve/backend/identity.py:17-20` names the numpy version and a policy integer and nothing
about BLAS build, thread count, or SIMD path. C8: `src/sieve/decode/reader.py:86`
`_position_at` grabs forward to `GRAB_FORWARD_LIMIT = 40` (`:13`) and otherwise seeks, and
`src/sieve/decode/identity.py:12` captures only the OpenCV version — **the hazard is
confirmed, the defect is not; no seek-versus-sequential comparison was run.**

## The operator contract — bearer: *the call*

**C9.** One invocation signature covers every capability axis. A new axis is a field of that
signature, never a new signature.
**C10.** Admission rejects any operator the engine cannot actually run, so declaration and
capability cannot drift.
**C11.** State is a first-class protocol participant with a declared lifecycle: created at a
named offset, snapshot to bytes, restored from bytes. Snapshot *frequency* is an engine
decision; *being* snapshottable is a contract obligation.
**C12.** And it must be in the first operator or it can never be added. Retrofitting is
impossible, not merely expensive.
**C13.** Windows are declared two-sided — history and lookahead.
**C14.** An operator declares its I/O shape: arity, dtype, geometry transform, temporal extent.
**C15.** Parameters carry a semantic type, not a primitive shape.
**C16.** An operator never chooses its own thread, process, buffer size, or cache location, and
never reads a machine-capability probe.
**C17.** Cost is declared as a shape; constants are fitted by measurement, never hand-written.
**C18.** A cost shape may take measured data properties as terms, which makes estimation
two-pass — sample, then estimate.
**C19.** Cost is computed per *task* from that task's resolved parameters, never one estimate
scaled by task count.
**C20.** Parameters are separated from execution context supplied by the engine.
**C21.** Operators may take more than one input; the engine reconciles differing rates and
geometries, and both inputs are key terms.
**C22.** Elements and regions carry a declared addressing descriptor: how to map an element
index to a source region and back, and how to test a point against it. Rectangles and uniform
grids are the common case of that facility, not the assumption underneath it.
**C23.** A version declares whether it supersedes an earlier one and how parameters convert, so
saved work can be upgraded in place and retired code can actually be removed.
**C24.** A schema says what one value *is*, not only how wide it is. There is no safe default.

**References.** C9/C10: `src/sieve/backend/dispatch.py` defines three protocols at `:30`,
`:34`, `:40`, policed by three decorators whose port-arity enforcement is at `:146`, `:169`,
`:193`; the missing fourth cell says so at `:195-196` — "no stateful merging protocol exists
yet — the filter that needs one should bring its signature". Declaration/capability drift is
at `src/sieve/pipeline/executor.py:107-117`, which refuses every non-streaming and every
rate-changing node while the spec declares both. C11/C12:
`src/sieve/backend/dispatch.py:61` `start()` captures state in a closure at bind time, so
nothing can ask what offset it corresponds to. C13: `src/sieve/core/detection.py:23` reads
`t + (window - window // 2)` — future frames — which no one-sided declaration can express, and
is why detection was built outside the graph at `src/sieve/detect/detector.py:35`. C16:
`src/sieve/decode/prefetch.py:21` reads `src/sieve/core/machine.py:27` from outside any engine.
C19: `src/sieve/core/replicates.py:30` carries per-node `overrides` and `detector_overrides`
merged at `src/sieve/core/pipeline_model.py:165`, so cost varies per task by construction.
C23: `src/sieve/core/filter_registry.py:118` binds the spec to the params class, so keeping an
old version resolvable means keeping its class and kernels forever.
C24 **is already implemented at rung 1 in the tree** — `src/sieve/core/filter_base.py:199-211`
refuses registration without an element declaration, and
`src/sieve/filters/block_signal.py:65`, `normalize.py:43`, `rescale.py:27` comply.

## Ownership — bearer: *contended resource*

**C25.** One owner per contended resource, one entry point per capability.
**C26.** One engine entry point taking requests that carry priority, deadline, and a
shed-or-wait disposition. Surfaces pass requests; they never assemble stages.
**C27.** One facility owns artifact writing: temp staging, read-back verification, digest
comparison, cancellation, atomic commit.

**References.** C25: five `QThread()` sites, not the four FINDINGS records —
`src/sieve/gui/preview_runner.py:304`, `detector_worker.py:140`, `materialize_worker.py:72`,
`player.py:77`, `resource_probe.py:98`; `decode_worker.py` creates none, it is moved onto the
thread `player.py:77` names `"sieve-decode"`. Allocation is static at
`src/sieve/core/shares.py:8/11/14`. Three incompatible caches:
`src/sieve/pipeline/cache.py:15` (unbounded dict, engine-side),
`src/sieve/gui/proxy_cache.py:11` (byte-capped LRU keyed by index alone, holding `QImage`),
`src/sieve/gui/render_ring.py:22`. C26: `src/sieve/gui/coalescer.py:34` is correct work in
the wrong place, and `src/sieve/cli/run_cmd.py`, `PreviewSession`, and `detect` each assemble
the orchestration independently. C27: arrived at twice by necessity, at
`src/sieve/detect/tables.py:338` (full row compare) and
`src/sieve/pipeline/materialize.py:120` with `:91` and `:148` (digest compare) — differing in
strength and error quality because no bag owned it.

## The log — bearer: *edit*

**C28.** Parameter edits form an ordered, replayable log; the preview, the caches, the
provenance record and every view are materialized views over it.
**C29.** Undo, cache invalidation, provenance and view refresh are one question — what changed
between two states — answered once. Undo is truncation, invalidation is a key diff, provenance
is the log.
**C30.** The log is the pipeline spec; saving and loading is serializing it.
**C31.** Every edit is representable as data and replay is deterministic.
**C32.** No state that determines a result lives outside the log, with exactly two named
legitimate exceptions: view-local state (zoom, scroll, hover), which changes nothing computed,
and machine-local preferences, which change what is *requested* but never what an artifact
*is*.
**C33.** Every derived quantity — completeness boundaries, histograms, aggregates — is an
engine-owned keyed artifact that views read. A quantity derived inside a view cannot be keyed,
cached, or reused.
**C34.** An edit that invalidates the graph is a legal log entry; the engine executes the valid
subgraph and reports what is unreached.

**References.** C29: four mechanisms for one question — `src/sieve/gui/history.py:13`
(`SNAPSHOT_LIMIT = 50`, whole-project snapshots), `src/sieve/gui/commands.py` (**ten**
hand-written `QUndoCommand` subclasses, not the nine FINDINGS lists; `RestoreSnapshot` at
`:285` is omitted there), `src/sieve/gui/document.py:65` and `:424` (gesture coalescing) with
`:343`, and **twelve** distinct change signals on `ReplicateDocument` at `:71`. C32/C33:
`src/sieve/gui/filter_tab.py` is 1,629 lines with **817** `self._` references across **154**
distinct attribute names — FINDINGS' figure of 691 is the count of *lines containing*
`self._`, and 154 is the number the lesson wants. `_filled`, `_settled`, `_series_final`,
`_partial_published` at `:134-138`; `parity_chain(30.0)` bakes a source frame rate into
interface defaults at `:119`. Views computing: `src/sieve/gui/density_plot.py:31` and `:54`
with its own bin count at `:28` — **these are module-level functions in the widget's module,
not methods on the widget, so the coupling is weaker than FINDINGS states and rests on the
widget being the sole caller.** C34: `src/sieve/gui/chain_model.py:87` `runnable_prefix`
truncating at the first non-OK step was correct behaviour.

## Legibility — bearer: *capability*

**C35.** Parameter controls are generated from declarations, never hand-written per operator.
**C36.** A hand-written panel means exactly one of two things: the declaration is incomplete,
or the semantic type has no registered widget. The second is fixed by registering a widget.
**C37.** One declaration, many generated presentations. Anything a human maintains in parallel
with a declaration will drift, and a test that pins the copy against itself makes the drift
pass.
**C38.** Generation covers more than widgets: connectivity kind, placement, guidance, and the
reason-it-cannot-go-here message all derive from declared I/O and declared metadata.
**C39.** The authoring surface must express everything the engine can and nothing it cannot.
Both directions are failures.
**C40.** Authoring is graph-shaped from the start, with affordance rules defined over a graph
rather than a sequence.
**C41.** The gap between what the pipeline can do and what the user can reach is enumerable and
loud. Visibility is disclosure, not parity.
**C42.** The debt register is generated, not written. A debt is the difference between declared
capability and reachable capability — the B3 query returning empty — so an unbounded list
cannot grow and drifting files cannot drift because there are none. Only the prose reason is
authored.
**C43.** A derived view reports the key of the artifact it is showing and its settled boundary,
not only its freshness.

**References.** C37's exact failure: `src/sieve/gui/wizard_model.py:84` `catalog()` calls
`discover()` and then returns a hand-written tuple, with hand-written `Guidance` at `:46` and
`:53`; `tests/unit/test_chain_model.py:173-174` then asserts the hand-written kinds against
the interface's own catalog. **The test's rationale comment at `:167-170` claims the kinds are
not derivable from `FilterSpec`; that comment went stale at commit `48635fc` and is now false**
— see C24. The transferable lesson is that a stale rationale comment kept a duplicate alive
after the thing justifying it was built, which no import or type check catches. C38's working
precedent is in the same tree: `src/sieve/cli/inspect_cmd.py:111` generates its whole parameter
presentation from `model_json_schema()`, with `:135` reading the sidecar via
`src/sieve/filters/__init__.py:23`. C39: `src/sieve/gui/chain_model.py:87` builds edges with
`itertools.pairwise` — a path, never a branch — while the engine supports branching,
multi-input ports, merges and fan-out; and `ChainKind.EVENTS` at `:33` has no engine
counterpart because detection is outside the graph. C42's model for the authored half is
`src/sieve/bench/budgets.py:133` `IN_DEBT`, which records accepted performance misses with a
prose reason. C43: `src/sieve/gui/player.py` displays from either the render ring or the proxy
decode path and `src/sieve/core/types.py:120` `Frame` carries no identity, so the user cannot
tell which; the settled-prefix half is already computed at
`src/sieve/detect/detector.py:69-79`.

**C43's mechanism, since the naive form is too expensive.** Identity belongs on the
subscription, not the frame — a viewport shows one source at a time and what changes invisibly
is which feed fills it. Out-of-order delivery is handled by a small integer token the frame
carries, resolved to a key through a side table the engine owns; v2 already pays for this at
`src/sieve/gui/coalescer.py` with generation counters and sequence numbers. What matters more
than the mechanism is that the component doing it has a named contract and is swappable — and
that its coupling to the delivery discipline is written down, per A3.

## Measurement — bearer: *unit of work*

**C44.** Two questions get two statistics, never one number: percentile latency for
responsiveness, throughput with an uncertainty interval for feasibility. Latency is never
reported as a mean.
**C45.** Performance is stated against a named load parameter, per path.
**C46.** Every measurement is attributed to a machine profile. A number without the machine it
was taken on is not a number.
**C47.** The profile is a portable descriptor, not a label on local results. The estimator must
accept a profile it did not measure and return an estimate for it.
**C48.** An interval must be narrow enough to discriminate, not merely correct. Without that,
"somewhere between 2 and 200 seconds" counts as a correct prediction.
**C49.** Fan-out waits take the maximum, not the mean. Straggler skew is the normal case.
**C50.** Memory is a declared and measured dimension, not a footnote to time. A time-only model
reports health while a run dies.
**C51.** Attribution is satisfied by a slow operator with an honest cost model and violated by a
fast one with none. *(Worth carrying verbatim; it is what stops the measurement invariant
reading as a performance mandate.)*
**C52.** Measurements are keyed artifacts governed by the same regime as everything else
derived. Refitting is invalidation.
**C53.** The differentiator is three speeds, not one: **built** faster, **validated** faster,
**computed** faster. Only the third is what a benchmark harness measures, and the measurement
invariant must be stated over all three or the other two lose their justification.

**References.** C44: `src/sieve/bench/metrics.py:88` `median_ms` and `:94` `worst`, with no
percentile function anywhere in the module. C46/C50: `src/sieve/core/machine.py` already reads
CPU affinity, per-CPU efficiency classes, cgroup v1/v2 limits and SLURM allocations — so on a
scheduler-managed machine the ceiling is an allocation, not the hardware, and a
physical-memory model fails exactly where the laptop-versus-HPC comparison lives.
`src/sieve/gui/resource_probe.py:45` `over_ledger` is a real closed loop between declared
budget and measured use. C53 is the author's: "SIEVE is a way to do things other programs can
do but faster; it can be built faster, it can be validated faster, it can be computed faster."
The existential argument, worth carrying verbatim: "A version of SIEVE that only runs on some
machines is a SIEVE that is ignored by any user that cannot run it" *(dying source: CHARTER
line 63)*.

## Verification — bearer: *artifact and consumer*

**C54.** An artifact is verified by reading it back through the same path a consumer would use.
An encoder's success code is not evidence.
**C55.** Tests assert on keyed artifacts and observable outputs, never on internals.
**C56.** Test durability is a *consequence* of keying, not a separate discipline. Tests survive
refactoring because the thing they check is the thing keying already guarantees is stable.
**C57.** Golden fixtures are keyed like anything else and regenerable from their key.
**C58.** Fixtures are synthetic, never downloaded or committed media — "a fixture that has to be
downloaded is a fixture that gets skipped, and a decoder test that skips is indistinguishable
from one that passes."
**C59.** An output carries a declared, versioned schema written with the data. Readers validate;
they do not infer.
**C60.** An output whose consumer is unspecified is not designed. The shape of outputs sets the
ceiling on extensibility, because downstream sections ingest them.

**References.** C58 is quoted from `tests/conftest.py`, which also pins
`QT_QPA_PLATFORM=offscreen` at `:26` so a local run is the same run as CI, and whose synthetic
video makes frame *n* a solid field of intensity `n * 5` so a test can assert *which* frame a
seek landed on — the instrument C8 requires, already built.

## Structure — bearer: *module*

**C61.** A module is a home for a decision that might change, not a step in the processing
sequence. Name the change that would be confined to this folder.
**C62.** Legitimacy is not enough. A module nobody can locate gets reimplemented, and a bespoke
reimplementation in the wrong place is the most expensive outcome.
**C63.** Names state a capability, not a position or a shrug. `core`, `backend`, `common`,
`utils`, `helpers` are standing invitations to accumulate.
**C64.** Dependencies point one way and do not cycle. Authoring surfaces are depended upon by
nothing.
**C65.** A package announces its secret and its exports at its surface. Reaching past it means
either the surface is wrong or you are depending on an internal.
**C66.** Each bag holding a kind of thing carries a minimal reference member, in tree and
exercised by CI, and the set covers the hard shapes — one carrying state across frames, one
taking more than one input, one changing rate, one with a two-sided window. Prose instructions
drift silently; a reference member breaks the build.
**C67.** The target is the *hidden* helper, not harmless duplication. Two similar helpers in the
folder where both belong get noticed and merged.
**C68.** The module guide is generated by walking packages, never hand-maintained. An incoherent
guide is a diagnostic of the codebase.
**C69.** A rule whose violations are individually cheap and unbounded in count is enforced
automatically or not at all. **The aggregate is the unit.**
**C70.** An optimization is a new operator version with identical declared semantics and a
different cost shape. Keying makes the swap safe, the cost shape makes the improvement
measurable, the determinism class makes "same answer" precise, and declared migration is what
lets the slow version actually be deleted.
**C71.** Creating a folder stays free; the check sits on the folder's subsequent behaviour. A
folder that has not acquired a second importer within *N* commits is defended or dissolved.
Dissolving is the normal end of life for a folder, not a reproach.

**References.** C63 is live: `src/sieve/core/` currently holds `detection`, `filter_base`,
`filter_registry`, `machine`, `pipeline_model`, `pool_meter`, `replicates`, `shares`, `types`
and `wavelet` — a Morlet transform and a CPU-topology reader in one folder, under the exact
name the rule warns about. C65 is unmet across the tree:
`src/sieve/pipeline/__init__.py`, `storage/__init__.py`, `backend/__init__.py` and
`gui/__init__.py` each contain the single word `pass`. C66's reference member is doing three
jobs — anti-reinvention, the repo-side precursor index of B3, and rung 3 of A2 — which is the
strongest structural argument in the corpus that its completeness requirement is not optional.
C69 is why v2 failed: no single one of 154 owned attributes, five thread owners, three caches,
two validators or one hand-written catalog was expensive to add. C71's signals are already
computable from the import graph.

**Not carried:** *a change's cost should be knowable before it is made*, the repo mirror of
feasibility estimation. It is predicted by B3's symmetry and has no mechanism, and it may be
much weaker than its product-side twin. Recorded as speculative, not as a claim.

## Scope — bearer: *SIEVE's boundary*

**C72.** B2, as a rule with an ID.
**C73.** Replication, consensus and distributed transactions are permanently out of scope. A
design discussion reaching for them has gone wrong.
**C74.** The source assets being video is a property of the operators that exist, not of the
system of record. Nothing outside an operator's own input declaration may assume a decodable
video exists.

---

# Part D — Contingent claims that must carry their expiry

These are true and belong in the document. An unmarked contingent claim in a document meant to
be permanent is the failure mode, so each is listed with the condition that expires it.

Sections are ARCHITECTURE unless marked.

| Claim | Expires when | Carried at |
|---|---|---|
| Determinism has exactly two classes, bitwise and tolerant | a third exists. **Decided as an open registry closed by policy** — register two, refuse a third without an explicit decision. | §1.5, before this pass |
| An artifact is a frame *range* plus its entry state, with the start offset in the key | the addressing axis stops being a totally ordered index. Durable core: *the artifact is the span plus its entry state*; "frame" is the today-noun. | §1.6 |
| Interactive paths shed; export paths backpressure | a third path class exists — a long-running background derivation the user watches but does not interact with has no assignment. | §3.4 |
| Preview and run are the two trigger policies | a third completeness policy appears. Durable core: trigger policy is engine configuration, never a branch inside an operator, and any divergence is a bug of the highest class. | §4's preamble |
| No event-time machinery: no watermarks, no late arrivals, no accumulation modes | a source arrives out of order. Provisional-versus-settled is **restored** (decided) and does not require event time. | §4's Forbids, before this pass |
| Parameters are what the user tunes; source properties are execution context | the tuner stops being a human choosing by hand. | §2.5 |
| The load parameter is megapixels per second through *n* stages | an element stops being a pixel in a frame. | §7's preamble, which notes the condition is already visible in §8.4 |
| Per-core-class capacity and cgroup/SLURM memory budgets | those stop being how ceilings are imposed. Durable core: *the ceiling is an allocation, not the hardware*. | §7.4 and §7.5 carry the durable core; no rule names cgroup or SLURM, so there was no contingent claim to annotate |
| Responsiveness as a table of named interactions with deadlines | the interaction set changes, which it does with every surface. The debt register is durable; the twelve names are an inventory. | STRATEGY §5; no rule ever asserted a fixed set of names |
| A package's surface is `__init__.py` | Python. Bearer *package surface* is durable; the filename is not. | ORGANIZATION §4's preamble |
| The reference set's hard shapes are stateful, multi-input, rate-changing, two-sided | by addition, not replacement. The list grows combinatorially — that is C9's argument. | ORGANIZATION §7.2, which also states what stops the growth being the product of the axes: §2.7 |
| Column orientation is an implementation detail | already conditioned on narrow fact tables. A note, not a principle. | §8.3 |

---

# Part E — What the source documents get wrong

Do not carry these forward. Each is a statement in a document being superseded that a decision
or a check has overruled.

1. **"A warmup shortfall is an error."** *(ARCHITECTURE §3.1; PLAN Phase 6 verifies it
   raises.)* **Decided the other way:** shortfall is legal at a source boundary and keyed
   there. SIEVE lets the user do the wrong thing and announces loudly where assumptions are
   failing. The tree already does neither — `src/sieve/cli/run_cmd.py:134` warns and proceeds
   without keying it, which is the defect.
2. **History is declared one-sided.** *(ARCHITECTURE §3.1.)* **Decided two-sided.** See C13.
3. **"Functionality not reachable from the GUI does not exist."** *(ARCHITECTURE §6; CHARTER
   line 65.)* Under this reading the entire build plan is unconstitutional. **Decided:**
   visibility is a debt keyed to the capability it depends on, generated rather than written,
   and the surface is any generated authoring surface.
4. **"The boundary is one machine per run."** *(ARCHITECTURE §10.)* At 100 replicates and
   100,000 files this is already stale, not contingent. The reserved off-box branch is the
   normal case.
5. **The two open questions on determinism.** *(ARCHITECTURE §1.5.)* **Both decided:** class
   is infectious with tolerant artifacts pinned — deletable, but the delete is recorded as
   invalidating the byte-identity claim rather than only the cost; and a declared tolerance
   must derive from a stated numerical argument and name the *source* of non-determinism, not
   merely a number.
6. **CHARTER's invariant 1(a)–(e) decomposition.** Structurally broken — (d) contains
   invariants 2 and 3 entire, and (a) does not discriminate against anything.
7. **"The bear minimum... the things that are not are relatively trivial."** *(CHARTER line
   10.)* FINDINGS is a twenty-one item argument that they are not.
8. **FINDINGS' three number errors.** Four of seven filters are stateful, not five
   (`background_ema.py:58`, `block_signal.py:72`, `motion_history.py:105`,
   `temporal_baseline.py:76`). "691 `self._` references" is a line count; the reference count
   is 817 across 154 names. "Four independent interface threads" is five, and
   `decode_worker.py` creates none of them.
9. **FINDINGS 15 cites `test_chain_model.py:173-174` for the wrong proposition.** See C37.
10. **`charter-invariants.md`'s Closure, in its strongest reading** — "cannot be built wrong"
    — as applied to *user states*. An invalid intermediate graph is a legal user state. It
    remains the right rule for repo states, and `charter-invariant-misses.md`'s rejection
    should not be carried across the mirror.
11. **`charter-invariants2.md`'s INV-2**, "measured cost on the machine it is actually running
    on." The differentiator is estimating for a machine SIEVE is *not* running on.
12. **`charter-invariants.md`'s invariant V**, the new-type gate. Superseded by the decision at
    C71 — creation stays free, the check moves to subsequent behaviour.

---

# Part F — Open

Four items. Nothing else in this file is undecided.

**F1. What v1 did better, and why it did not reach v2.** Freezing has been tried once and the
good properties did not transfer, so "keep the old tree readable" is a mechanism with one
failure against it and none for it. What crosses a rewrite boundary is a **check**, not code —
`tests/conftest.py`'s synthetic video moves because any implementation that fails it fails
visibly; a module in a frozen tree does not. This makes FINDINGS' *mechanisms worth carrying
forward* the wrong shape: it lists five modules, four of which are in the form that already
failed once. The transferable version of each is a behaviour with a test that fails until the
behaviour exists. **The v1 list has never been written and cannot be reconstructed from the
repository.** It is the only input in this file with no source.

**F2. There is no unit above a single source.** At 100 replicates and 100,000 video files
spanning eight weeks, C-part claims are all stated per-source and nothing names the collection.
Cross-source aggregation is therefore a first-class operator kind rather than a downstream
script, the addressing descriptor of C22 needs a source axis as well as a spatial one, and a
fitted cost shape must extrapolate across source count as well as across machines. **This is
the largest gap the corpus has and no decision has been made about it.**

**F3. Tuning on a sample and running on the whole set is an unnamed operation.** It is not
save/load, not preview-versus-run, and not redeployment to another user. The author's workflow
depends on it — "they run SIEVE on a sample of their footage and likely tune it from SIEVE
itself to work with their controlled environment."

**F4. Whether the superseded documents survive as an archive.** Part C references the tree
wherever possible for this reason, but Part E and the *(dying source)* marks still point at
documents. If they are deleted, those pointers must be inlined first.

---

# Part G — Two housekeeping defects

Not principles inputs; recorded because they were found while checking and will otherwise be
lost.

**G1.** `tests/docs/test_scaffold.py` is staged and reads `docs/SCAFFOLD.md`, which the gutting
deleted — 4 errors, 2 vacuous passes. It is the only docs check in the tree. Either regenerate
the file or delete the test; the second is defensible, since ORGANIZATION §9 rejects a
hand-maintained folder inventory as "stale and authoritative-looking at the same time," which is
what SCAFFOLD.md is.

**G2.** `docs/.state.md` is a placeholder carrying a do-not-delete. If it is the pointer for
someone picking up cold, it should name this file and F1–F4.
