# How-to: get a PAR from Proposed to Accepted

Task: you hold a `Status: Proposed` rationale and want it to govern.
The rules this guide executes are PAR-0001's (status, the acceptance
judgment, the roll-up discipline, primaries); what a stage means when
in doubt is that rationale's to say, never this file's. Worked examples:
PAR-0005's attack arc, primary
`docs/archive/SESSION-2026-08-03-par-0005-judgment.md` — bare exchange
citations below are to that file — and PAR-0006's plain-rewrite arc,
primary `docs/archive/SESSION-2026-08-03-par-0006-plain-rewrite.md`,
cited below by name.

## 0. Let it sit

A Proposed rationale governs nothing: whatever governed before keeps
governing, and the tier-1 citation stays put. Nothing in the repo is
inconsistent while it sits, so there is no deadline pressure — the
pressure to accept comes only from wanting the rationale to govern.

Check: `grep -l "^Status: Proposed" docs/par/*.md` lists it;
`grep -rl "PAR-NNNN"` shows tier 1 still citing the prior regime.

## 1. Choose the route to judgment

Acceptance is a judgment that the rationale is ready to govern. For a
distillation that judgment is the fidelity review against its source.
For a rationale argued fresh it is the author's call — and the call
can be made directly when the rationale is small, its claims are cheap
to check, and doubt has had time to arrive organically.

Convene a deliberate attack instead when any of these hold: the
rationale must govern before organic challenge could accumulate; it was
authored and judged by the same eyes in one sitting; its necessity
argument rests on empirical claims nobody has verified; or its value is
not clear — it feels load-bearing but cannot yet say why. An attack is
never owed (PAR-0001); it is convened.

Check: you can say which route and why in one sentence.

## 2. Convene the attack

Fresh eyes — an agent or person who did not author the draft — with
the charge stated at convening. The charge has a working formula:

- Verify the empirical claims yourself rather than accepting them,
  and say what the rationale loses if a claim fails ("the Context
  loses its footing and the Decision is left standing on much narrower
  ground").
- "Do not soften the verdict to be agreeable, and do not manufacture
  objections to look rigorous."

The attack files a session primary from its first exchange, numbered
so the verdict can cite passages, appended live, frozen at the ruling.
An error the attack finds in an already-frozen primary is corrected in
the PAR; the frozen primary keeps its error (Exchange 1).

Check: the primary exists, `Status: Open`, before the verdict lands.

## 3. What every PAR must survive

The floor — checks any rationale faces at judgment, attack or not:

- Every citation resolves, and measures what the rationale says it
  measures. A number that is real but misread (an accuracy figure
  presented as speed, Exchange 1) is a defect even when the sentence
  survives, because it is evidence of a different kind than claimed.
- The central sentence supports the central examples. Read the
  Decision's strongest rule against the rationale's own evidence; a
  standard that forbids what the rationale exists to enable, or
  licenses it only through an unstated convention, is a hole
  (Exchange 3).
- One named system, near-decomposable: dense inside, sparse across,
  seams to neighbouring rationales stated as citations. Simulate the
  decision reversing — if a sibling rationale needs substantial
  rewriting rather than re-citing, the boundary leaked (PAR-0001).
- Nothing in it belongs to a sibling, and what it owes siblings is
  routed by name in Consequences so it is not rediscovered
  (Exchange 7).
- Concessions are typed correctly: each Challenges entry narrowed to
  what actually stands, neither carrying a concession the rationale
  does not owe (Exchange 6) nor holding a doubt that in fact breaks.

Check: each bullet answered against the tree, not from memory.

## 4. What a good PAR could have

The instruments for a rationale whose value is not clear. Not every
rationale needs these — but they are what moved PAR-0005 from
"coherent draft nobody could weigh" to good enough for acceptance, and
each was passed back as a question at its judgment:

- **The value named, and the no-other-route argument** (Exchange 8):
  what does this buy that nothing else buys? Price every route that
  avoids the decision — including welding, metadata, detection-only
  alarms, and deferring the boundary to retrofit later — and state
  which costs a rewrite. A value that survives this pricing is the
  rationale's keep; claims that do not survive it ("speed") are struck
  from the Context so the rationale never leans on them.
- **Earning its keep**: what the decision costs contributors and the
  repo, and where it must never claim keep. Cheap-by-construction
  arguments (conformance free at n=0, enforcement by machinery
  already needed) belong here.
- **The touch occasions** (Exchange 9): where the system indispensably
  lives versus when it is picked up as a tool, with an
  operationalizable heuristic — enumerated occasions, each with its
  trigger. An occasion that is deliberately *not* routine work is
  named as such, so the silence is signal.
- **The skeleton test** (Exchange 9): draft the how-tos the rationale
  claims to admit, each with its check step. A check step that cannot
  be stated is the cheapest detector of a hole in the rationale above
  it — at PAR-0005's judgment, exactly the two unwritable check steps
  pointed at the two heaviest acceptance conditions.
- **The real-pipeline sweep**: classify the actual pipelines and repos
  the architecture must serve against the Decision, case by case. A
  case the vocabulary cannot classify is a finding — a concession, a
  Challenges entry, or a break.
- **The user story** (the plain-rewrite primary, Exchange 3): state
  what the rationale governs as the user experiences it — for
  PAR-0006, "which knobs recompute and which are free; the file is the
  complete measurement." A rationale that cannot be told from the
  user's chair is mis-scoped or not architecture at all. At PAR-0006's
  judgment this was the instrument that unstuck the most.
- **The plain-restatement gate** (plain-rewrite primary, Exchange 5):
  explain the rationale until the human can restate the coherent
  version in their own plain words; acceptance waits until they can,
  and their restatement becomes the Decision's opening, with the
  edge-case defense demoted to the primary. The bar, verbatim: "good
  architecture results in things being easy to implement, not hard" —
  a rationale still hard to restate is one still facing its edge
  cases. Easy first, complete second. The restatement is also where
  mis-syntheses surface and get corrected on the spot (Exchange 5's
  pass-through correction).
- **Both-worlds runs** (plain-rewrite primary, Exchange 2): the same
  concrete events run through the decided and the undecided world,
  with knobs from the real pipelines, never invented ones. The
  signature of a rule worth accepting: decided, every error is
  unrepresentable, caught at PR time, or cheap and visible.
- **The scope sieve** (plain-rewrite primary, Exchanges 4 and 7, and
  the Close): concerns argued at judgment that are not architecture —
  execution behavior, tuning, anything measurable when built — yield
  at most a one-sentence scope fence in the rationale; the argument
  goes to the primary, and nothing else is written anywhere. Arguing
  them is exercise, not drift — it is how the fences get found.

Check: for each instrument used, its result is in the rationale or its
primary, citable by exchange.

## 5. Verdict, ruling, rewrite

The verdict is not pass/fail: it is the list of acceptance conditions,
ordered by weight, filed in the attack primary (Exchange 11). Each
condition is answered as its own exchange *before* any rewrite begins,
so the answers are on record independent of the prose that lands
(Exchange 10).

The ruling clears the rewrite, not acceptance — two gates, and
conflating them is what a rough session looks like. The rewrite is
whole-rationale (PAR-0001's coherence rule), reviewed as a diff, and
the primary freezes at the ruling. The rationale stays Proposed; tier 1
keeps citing the old regime (Exchange 12's close).

Check: the primary is Frozen; the rationale still greps as Proposed.

## 6. The acceptance commit

Its own sitting. All of it lands in one commit, or in adjacent commits
chunked rationales-then-placements (AGENTS.md):

- Flip the status line; the tier-1 surface that cites the rationale is
  amended in the same commit — `docs/ARCHITECTURE.md` for the
  architecture, `README.md`/`AGENTS.md` for repo mechanisms
  (PAR-0001's roll-up discipline).
- `grep -rln "PAR-NNNN"` over the tree: every citation checked
  against the rationale's *new* body. A citation pointing at text the
  rationale no longer contains is a mismatch fixed at or before
  acceptance; if the dropped text carried a benefit still wanted, its
  new home is named (Exchange 5).
- Markers and placeholders quoting the rationale narrow to its
  accepted wording; `python -m sieve.debt write`; the regenerated
  ledger travels in the same commit.
- Anything the rationale routes to siblings is stated in their text or
  their markers now, not remembered.

Check: suite green, regen a no-op, `grep -rln "PAR-NNNN"` returns
only citations consistent with the accepted body.
