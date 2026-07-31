# STRATEGY

ARCHITECTURE says what the running system owes. ORGANIZATION says where code
lives. This document says what SIEVE is for and how the work gets done: what one
unit of work is, what makes it finished, where unfinished work is recorded so
that it comes due instead of being forgotten, which tools exist and why there
are so few, and what keeps these documents from quietly becoming false.

It is normative and it outlives PLAN. PLAN is an ordering derived from this
document and the two above it; it is meant to be finished and deleted, and
where PLAN and STRATEGY disagree, PLAN is wrong.

This is a rewrite. The third implementation is built by the phases and by
nothing else; the second is frozen and is consulted through FINDINGS rather than
through its source (§7). A strategy for a refactor would be a different document
and would not work, because the properties being installed — keys, declarations,
one engine entry point — are the ones that cannot be added to code written
without them.

## 0. What SIEVE is, and what would end it

SIEVE executes a pipeline DAG over a set of sources and produces outputs that are
reingested or built upon, and it lets a user tune that pipeline by hand. That is
the product, and as a claim it discriminates against nothing: only total breakage
violates it, so no change can be evaluated against it. What follows are the
properties whose loss takes away something the user could otherwise do.

That is also the test for anything proposed for this list later. Name what the
user can no longer do when the property stops holding; if the honest answer is
that the codebase gets harder to work in, it is a means and belongs in §1 through
§7 rather than here. Every section of every document in this corpus is a means by
that test, which is the point — means are how the three below are held, and
promoting one of them to this level would make the distinction useless.

**It must be faster in three ways, and only one of them is measurable.** SIEVE
does what other programs can already do; the claim is that a pipeline can be
*built* faster, *validated* faster, and *computed* faster than by the
alternatives. A benchmark measures the third and is the only instrument for any
of them. Without it there is no reason to prefer SIEVE to anything else: a
version that runs on some machines and not others is ignored by every user who
cannot run it, and one that cannot say how long a pipeline will take on the
machine someone actually has answers nothing about whether a detection project is
feasible — which is the question the tool exists to answer. §5 makes the bench
the one tool that cannot be deferred, and this is why.

**Capability the user cannot reach does not exist**, and the obligation is
disclosure rather than parity: the gap between what the engine can do and what a
user can reach is enumerable and loud (ARCHITECTURE §6). Silence is the failure,
not incompleteness.

**Anything that does not enable something for the pipeline is out of scope.**
This is the only claim in the corpus that can reject work rather than shape it.
§1.2 is its worked form, with two refusals that have referents.

Underneath the three: **the codebase and the product are the same shape.**
Working in the repository is close to how a user works with SIEVE — a good
codebase shows the tools available so it stays extensible, and SIEVE shows the
tools available so the user's own capability extends. This was carried for years
as an aesthetic and repeatedly declined as uncheckable, on the correct reasoning
that an uncheckable rule at this level teaches agents that rules at this level
are decorative. That reasoning was right about uncheckable claims and wrong about
this one: §1.6 is its operational form and a query answers it. It sits here as
the reason the three above are the three, not as a fourth.

## 1. SIEVE discloses; it does not judge

An operator declares it needs sixteen frames of history. At the start of a
source there are four. Three responses are available: refuse the run, emit a
sentinel that reads downstream as a real value, or produce the result and record
in its key that it was computed with four frames of lead-in. The third is
correct, and the reason it is correct generalizes into the rule that decides
roughly a dozen otherwise-unrelated questions.

1. A **mechanical hazard** — anything about how a result was computed that could
   make two results differ or make one untrustworthy — is legal, keyed, and
   disclosed. Warmup shortfall, a graph the user has not finished wiring, a
   viewport fed by proxy decode instead of pipeline output, an operator that
   reproduces only within a tolerance, a decoder whose seek is not frame-exact.
   None of these is refused and none is hidden. Each becomes a term in a key or
   a field on an artifact, so the difference it makes is visible to the system
   rather than absorbed by it. This is FINDINGS principle 3 — key the hazard
   rather than forbid the capability it endangers — and v2's most expensive
   single decision was taking the other branch once.
2. An **interpretive judgment** — anything requiring SIEVE to hold an opinion
   about what the user is studying — is out of scope permanently. SIEVE does not
   know what an event is, does not need to, and any feature that requires it to
   know is refused regardless of how reasonable the request. Two worked
   refusals, so the rule has a referent: statistics and analysis over the
   detections SIEVE produces, and recommendations about how to record better
   footage. Both are things users will ask for. Both require SIEVE to assert
   something about the biology, and a pipeline works with what it receives.
3. Consequently there are two obligations that the corpus has so far called by
   one word. **Integrity** is SIEVE's: an artifact is what its key says it is, a
   cost estimate falls inside its stated interval, an output matches its declared
   schema, a written file reads back as what was written. **Validity** is the
   user's: whether a threshold is right, whether the events are real, whether the
   asymmetry between a false positive and a miss matters here. SIEVE owes
   integrity absolutely and owes validity nothing except the speed to iterate on
   it. §9's verification is integrity; ground truth is validity and is the user's
   instrument to build, not SIEVE's opinion to have.
4. Where a genuine choice exists, it is announced and the user picks, with the
   consequences of each option stated. Determinism classes, pressure policies,
   preview resolution, output scoping: these are registries the user selects
   from, not heuristics SIEVE applies on their behalf. The structural
   requirement this places on the code is that every such choice must remain
   selectable — the organization has to make any of them possible, because the
   default is chosen by the user and not by us.
5. The user's loop is tune-on-a-sample, run-on-the-set, and the output of one
   run scopes the input of the next. A run that narrows six hours to forty
   seconds is not a final answer; it is the input parameter for the next
   session. Reingestion is therefore not an extensibility nicety, it is the
   normal shape of use, and the scale it runs at is real: the working cases span
   ten minutes to eight weeks, with the largest at over a hundred replicates and
   roughly a hundred thousand files.
6. Declining to decide is only a service if the options are enumerable, so the
   obligation §1.4 places is not merely to announce a choice but to make the
   candidates a query. Given a target — an artifact the user wants — the things
   that can satisfy its precursors are enumerated from declarations, and each
   candidate announces what it in turn requires: the operators whose declared
   output admits the target, recursing on their declared inputs, terminating at
   sources. This is one shape appearing in three places the corpus otherwise
   models separately. An invalid graph is a target with unsatisfied precursors,
   which is why it is a legal state and not an error. A debt (§3) is a capability
   with unsatisfied precursors, which is why the register is a query rather than
   a list. And "how do I add one of these" is a capability whose precursors are
   satisfied, answered by the reference member that demonstrates them — which is
   what makes ORGANIZATION §7's hard-shape coverage load-bearing rather than
   illustrative, since an incomplete reference set is a query with missing
   answers. Both available failures are forbidden. The precursor relation is
   derived from declared inputs and outputs and never authored beside them, or it
   becomes a second source of truth about connectivity and drifts from the first,
   which is FINDINGS 15 under a new name. And the enumeration is unordered, or
   ordered only by a declared cost the user can see, because a ranked list of
   candidates is a recommendation and §1.2 refuses those.

The repo and the product share that shape and do not share a mechanism, and the
difference is worth holding onto: the product side is a recursive search over a
type relation, and the repo side is an indexed lookup over a small set of
executable examples. Treating them as one implementation builds a synthesis
engine where a table would do.

Forbids: a refusal where a key term would have done; a sentinel standing in for
something that was not there; and any feature that encodes what counts as an
event.

## 2. The loop: one chunk, one check

A chunk is one secret (ORGANIZATION §1) or one rule's check. It is not a phase,
not a file, and not a feature. It is the smallest thing that can be landed with
a check that would have failed before it.

1. **Cite the obligation.** Every chunk names the numbered rule it discharges or
   the ledger entry it pays. Work citing neither is out of scope by §1.2's own
   test, and the citation is what lets someone with no context evaluate whether
   the chunk is finished.
2. **Write the check first, and write it as a refusal where possible.** The
   check for a contract is a test that a non-conforming operator is *rejected*,
   not a test that a conforming one is accepted. Acceptance tests pass on
   systems with no contract at all.
3. **Push the rule down the ladder.** Enforcement has six levels, ordered by how
   far a wrong thing gets before something stops it, and every rule in the corpus
   carries one: **0** — unrepresentable, the wrong thing cannot be expressed in
   the type or the signature; **1** — generated, the thing is not authored at all
   and so has no place for a divergence to live; **2** — refused at registration;
   **3** — failed in CI; **4** — warned in CI; **5** — reviewer judgment.
   Correctness by construction is not a slogan, it is the instruction to
   implement each rule at the lowest level it admits, and a rule sitting at 5
   that could sit at 2 is a defect in the rule rather than a fact about it. A
   rule that cannot reach any level is a value, not a rule; putting it in a
   normative document teaches agents that these documents are decorative.
   Levels 0 and 1 are the only two that do not require the rule to be known:
   everything from 2 down is a refusal an agent meets after writing the wrong
   thing, which is why the distance between 1 and 2 is larger than the numbering
   suggests.

   What makes pushing down the instruction rather than merely the preference is a
   fact about how these particular rules fail. **A rule whose violations are
   individually cheap and unbounded in count is enforced automatically or it is
   not enforced at all: the aggregate is the unit.** No single hand-written
   control, no single privately owned thread, no single duplicated helper is
   expensive enough to reject at review, and a reviewer pricing them one at a time
   is right every time and wrong in sum. That is how the last implementation
   reached a hundred and fifty-four owned attributes on one tab and five
   components each creating threads, with no individual decision anyone would
   name as the mistake. Level 5 prices one instance because a reader sees one
   instance; only 0 through 3 can price the class.
4. **Land on trunk with the check green.** Chunks are not batched into branches
   that integrate later. A chunk too large to land is too large to have been cut.
5. **Declare what was not done** (§3), at the site that owes it, with a trigger
   and a check. This is part of the chunk, not follow-up.
6. **Regenerate.** The module guide, the ledger, and the capability coverage
   table are outputs of a walk over the tree and are never edited by hand.

The five constructions this project depends on, because they are the ones that
cannot be installed afterwards — four of them low on the ladder and the last one
higher, which is a fact about it worth noticing rather than smoothing over:
registration is the only path
into the DAG, so an unadmitted node cannot be constructed; one invocation
signature carries every capability axis as a field, so an operator cannot declare
what the engine cannot run; the interface is generated from declarations, so it
cannot express what the engine does not know about; everything derived is keyed,
so an unreproducible artifact has no name; and each bag's reference member is
executed by CI, so the runbook cannot be stale without breaking the build.

A chunk whose check cannot be stated is misspecified and gets re-cut. This is
PLAN's rule for phases, applied at the size work actually happens at, and it is
the whole of the answer to "manageable chunks" — the check is what makes a chunk
finishable by someone who did not cut it.

One class of work is not chunkable and is not delegated: the arrangement of the
interface. What an agent owes is the substrate — every capability, parameter,
cost, and state expressible and queryable, so that any arrangement is
constructible from what SIEVE provides. Which control sits where, and in what
order a new user meets them, is authored by hand. This is why generation is
load-bearing rather than a convenience: generation is what makes the raw material
complete, and completeness of the raw material is the entire architectural
obligation. The sequencing problem — a naive user not knowing where
to begin — is answered by §1.6 only for the user who can state a target, since
enumerating what satisfies a target's precursors requires a target. The residue
is the user who cannot name one, and nothing in this corpus answers that;
pretending otherwise would put a rule at the bottom rung that belongs on no rung
at all.

Forbids: a chunk that cites no obligation; validation by running the interface
and watching for lag; and a test that asserts a hand-maintained value against
itself, which is how v2 certified the drift between its two type systems.

## 3. The ledger

Unfinished work is declared in code, next to the thing that owes it, as a
structured object rather than a comment. Four fields: what is owed, in one line;
the **trigger** that makes it due; the **check** that will pass when it is paid;
and where it was incurred. The walker collects them by import and emits the
register. Nothing about the register is hand-maintained, and a debt declared in
a module nobody imports does not exist — which is deliberate, because it means
deleting the code deletes its debt, and a markdown to-do list has never once had
that property.

1. **The trigger is a build-order event, never a date and never "soon."** The
   vocabulary is closed and every member is observable: a phase landing, a
   capability being registered, a check coming into existence, the first
   instance of a shape appearing (the first two-input operator, the first
   tolerant operator), or a count threshold crossing (a folder carrying a bin
   warning for N commits). This is the mechanism that makes the GUI a debt
   rather than an omission: the interface debt on every capability is triggered
   by the interface phase, so it is loudly visible from the day it is incurred
   and cannot come due before the phase that makes it payable. A debt marked due
   earlier than it can be paid is how a plan gets abandoned, and it is the
   specific way v2's build order came apart.
2. **A debt with no trigger and no check is refused at declaration.** That is a
   wish, and wishes are what turn a register into a graveyard nobody reads.
3. **Three states, and only one fails the build.** *Deferred* — trigger has not
   fired; visible, costs nothing. *Due* — trigger has fired; visible and it is
   the work queue. *Overdue* — trigger fired, the commit that fired it did not
   pay, CI fails. Overdue is reachable only through a debt that became payable
   and was not paid, so the build never blocks on something that cannot be done.
4. **Re-deferring is legal, explicit, and counted.** One edit, one line of
   reason, and the walker reports how many times each debt has been re-deferred.
   Serial deferral is not prevented; it is made impossible to do quietly. This is
   FINDINGS 10's accepted-miss register — a miss recorded with its reason in prose
   rather than absorbed silently — generalized from performance budgets to every
   kind of unpaid obligation, and it is the one mechanism in v2 that already did
   this job correctly.
5. **Five kinds**, because they have different triggers and different payers.
   *Capability* — something registered with no user surface, which is §0's
   disclosure obligation restated as a query rather than an aspiration. *Contract* — a
   declared field with no enforcement behind it yet. *Budget* — an accepted
   performance miss against a named interaction, with its ceiling re-expressed as
   a percentile against the load parameter per machine profile. *Structural* — a
   folder carrying bin warnings, which is the trigger ORGANIZATION §3.2's
   dissolve remedy currently lacks. *Decision* — a question deliberately left
   open, whose trigger is the first case that forces it.
6. **A debt is paid by the commit that removes its declaration.** The marker and
   the fix land together or neither does. There is no separate closing step and
   no state in which the code is fixed and the register still says otherwise.

This is not a decision log, which ORGANIZATION §9 rules out and this document
does not reintroduce. A log accumulates and is read for history; a ledger empties
and is read for work. The distinguishing property is that every entry in a ledger
has a condition under which it disappears.

Forbids: work earmarked early and ignored forever; a register that disagrees with
the tree; and a build blocked on work that cannot yet be done.

## 4. Change amplification is the design metric

The question a newcomer or an agent actually asks is not where code lives but
what a given change touches. Each row below is a change that will be made
repeatedly, and each is designed to touch exactly one place. Where a change is
found to touch more than one, that is the design defect to fix — the table is a
specification, not a description of a hoped-for tendency. This is Ousterhout's
change amplification used as the acceptance criterion for the decomposition
ORGANIZATION §1 argues for.

| Change | Touches | Must not touch |
| --- | --- | --- |
| Add an operator | its folder: declarations, kernel, fixture | interface, engine, catalog |
| Add a parameter to an operator | that operator's declaration | any control code |
| Support a new parameter shape in the interface | one widget-bag member | any operator |
| Add a determinism class, pressure policy, or trigger policy | one registry member | operators, keys |
| Add an output consumer | nothing; it reads the declared schema | the writer |
| Change the decode backend | the source folder | everything else |
| Change scheduling, fusion, or placement policy | the engine | operators, contracts |
| Add a user surface (batch, off-box submit) | that surface | the engine's internals |
| Add a semantic type | contracts, plus one widget when it needs one | operators that do not use it |

The last row is the one that is honestly two places, and it is two because a
semantic type is a contract and a presentation. That is the whole reason
ARCHITECTURE §2.1 requires parameters to declare a semantic type rather than a
primitive shape: nothing recovers "this is a crop rectangle" from four integers,
so a type declared late is a type whose control is hand-written, and a
hand-written control is where state goes to become unsavable.

Two rows encode failures already paid for. "Add an operator must not touch the
interface" is FINDINGS 15: v2 required editing a hand-written interface catalog
to add a filter, and the test that should have caught the divergence asserted the
catalog against itself. "Add a user surface must not touch the engine's
internals" is FINDINGS 17: v2 had three independent assemblies of the same
orchestration, so a fourth surface would have been a fourth variant.

The table states the blast radius for the changes anyone can predict. The
relation it approximates is a graph over contracts, and its edges are not the
import edges: two contracts can import nothing of each other and still be unable
to change independently, because one is only valid in the presence of the other.
Staleness as a display state is required by shedding and is optional without it.
Materializing tolerant artifacts once is required by engine-owned placement and
means nothing without it. A start offset in the key is required by
checkpointing. None of those pairs appears in a dependency graph, so
levelization — the one organizational property ORGANIZATION §5.3 can verify
exactly — does not catch them, and an unwritten edge is a rewrite nobody
predicted. The edge is recorded where the dependent rule states what it depends
on, which is what makes "what does amending this touch" a query over citations
rather than an act of memory. Half of that reaches level 3 and half does not:
that an amendment names the rule it replaces (§6.1) makes the citing rules
findable, while whether the edge was written down at all is read. The half that
is only read is the reason the edges are named in the rules rather than
collected in a list, since a list of couplings is a second account of the
corpus and drifts from it.

Forbids: any change kind whose blast radius nobody has stated, and a coupling
between two contracts that is real and unwritten because no import shows it.

## 5. Three tools

The tool budget is small on purpose, and each tool has to earn its place against
one of the three speeds SIEVE exists to provide — a pipeline that can be *built*
faster, *validated* faster, and *computed* faster than doing the same work by
other means. A proposed tool serving none of the three is refused.

**The walker** — one traversal of the package tree, four outputs. It checks
import direction and acyclicity, checks that every package states its secret and
declares its exports, emits the generated module guide, and emits the ledger and
the capability coverage table. These are one program because they are one walk,
and separating them produces three tools that disagree about the tree. It serves
build speed: it is the thing that stops the repository from getting slower to
work in, which is the failure mode Lehman's laws describe and the reason a third
implementation exists.

**The registry** — the single admission point. Every "is this legal" question is
answered here at registration: contract conformance, determinism class, element
meaning, cost shape, addressing descriptor, version migration, and the two-sided
window declaration. There is no second path into the DAG and no review-time
equivalent. It serves build speed by making the answer to "did I add this
correctly" immediate, and it is §2.3's level-2 rung for everything that cannot
be made unrepresentable or generated.

**The bench** — machine profiles, cost-shape fitting, the named-interaction
budget table, percentiles and intervals rather than means, and the per-unit
regression gate. It serves validation speed and compute speed at once, and §0
makes it the one tool whose absence removes SIEVE's reason to exist. The
interactions its budget table names are an inventory rather than a set — they
change with every surface — so what is durable is the table and its accepted-miss
register and not the names in it (§6.5). Its substance is largely carried forward: v2's factorial sweep over
core sets and worker counts, its named budgets with an accepted-miss register,
and its heterogeneous machine descriptor were right and are ported rather than
reinvented.

Deliberately not built, each because something above already does the job or
because the thing itself is the rot: an architecture decision log; a
hand-written folder inventory; a per-filter, per-machine stress ritual; a second
orchestration entry point for any surface; any document that restates a
declaration; and any per-operator interface panel.

New folders stay free to propose, with the one criterion that makes free
proposal safe rather than a target: the folder states on its surface, at creation,
the secret it hides and the change that would be confined to it (ORGANIZATION
§3.3). That sentence is required by the walker's surface check, so the cost is one
sentence and the benefit is that a folder which never claimed a secret cannot
later be shown to have lost one. The gate is on the other side — a folder accumulating bin
warnings incurs structural debt, and when that debt comes due it is defended or
dissolved.

Forbids: a tool that serves none of the three speeds; and a check that exists in
two programs.

## 6. Four kinds of document, and no fifth

Documents rot in one specific way: they describe a tree that then moves. Every
mechanism below is a way of removing the conditions for that.

1. **Normative** — STRATEGY, ARCHITECTURE, ORGANIZATION. These state
   rules and cite no file, no line number, and no folder inventory. They change
   only by amendment, and an amendment states which rule it replaces. A normative
   document that begins citing the tree is mechanically detectable and is the
   sharpest anti-staleness check available, because it removes the only thing in
   a normative document that *can* go stale. Section and rule numbers are
   permanent once written, because they are how one document cites another and
   how a commit cites the decision it implements: an amendment appends a new
   number or rewrites an existing rule in place, and never inserts, since
   inserting renumbers every rule below it and breaks every citation from outside
   the file without touching a line anyone will read. A withdrawn rule keeps its
   number and says it was withdrawn. Where a new rule belongs beside an existing
   one rather than at the end, it is folded into that rule rather than given a
   number between.
2. **Generated** — the module guide, the ledger, the capability coverage table,
   output schemas, and the parameter documentation for every operator. Produced
   by a walk, never edited. If the generated guide reads as incoherent, the
   codebase is incoherent and the guide is the diagnostic.
3. **Transient** — PLAN. Derived from the normative set, finished, and deleted.
   It is legitimate for PLAN to be rewritten after the fact so that it reads as
   though the work had been rationally ordered from the start; that is Parnas and
   Clements' rational design process, faked deliberately and documented as such,
   and it is why a plan that has been overtaken gets rewritten rather than
   annotated.
4. **Archive** — the lessons drawn from the second implementation, the record of
   the decisions that settled this corpus's contradictions, and the evidence
   behind both. The defining property is that everything an archive cites is
   frozen: a tree that no longer changes, or a document that has been superseded
   and will not be edited again. That is why its citations cannot go stale, and
   it is the test for whether something belongs here — not whether it is old, but
   whether what it points at can still move. An archive is corrected for fact and
   never updated for the current tree; when what it describes is deleted it
   stays, because the lesson is the artifact and the code was only the evidence.
   A superseded normative document becomes an archive entry once the claims worth
   keeping have been lifted out of it, and not before, because until then it is
   the only copy of something load-bearing.
5. **Not a fifth kind, but the test a claim passes before it earns a number in
   the first.** Three clauses, applied before it is written rather than after it
   is disputed. *Discrimination* — describe in one sentence the system in which
   the claim is false, as something a competent person would build on purpose. If
   you cannot, the claim describes the product instead of constraining it, and §0's
   admission test is this clause applied to §0's own list. *Bearer* — name the noun
   the claim constrains and say why that noun exists under any implementation. The
   durable bearers in this corpus are the derived value, the call, the contended
   resource, the declaration, the artifact, the consumer, the edit, the unit of
   work, the version, the module, the contract, and the hazard. A claim whose
   bearer is a noun of today — a frame, a video, a widget, a thread, a filter, a
   rectangle, a file name — is contingent rather than wrong, and is written with
   the condition that expires it. *Cost asymmetry* — state what adopting the claim
   costs now against what it costs after the system is built, measured over the
   accumulated class and never over one instance (§2.3). A claim that is cheap to
   fix once, with no bound on how many times it will need fixing, has a large
   ratio and is a rule. Measured per instance the clause demotes every claim about
   the repository and keeps every claim about the contract, which is a defect in
   the test rather than a fact about the material.

   An expiry condition is a trigger in §3.1's vocabulary and the claim carrying
   one is a Decision debt in §3.5's, so a contingent rule states its expiry in its
   own text now and acquires a declaration in the register once there is a module
   that owes it. The text is the weaker half — it is read when someone opens the
   document, and the register is read when the trigger fires — which is why the
   condition is written as an observable event and not as a hedge. "Expires when a
   third path class exists" is a condition. "May need revisiting" is a way of
   writing nothing down.

   What the test rests on is that durability is a decision rather than a
   prediction. The question is not which of these will still be true later; it is
   which of them a change would be rejected for.

The general form of the anti-rot mechanism, which every one of the four kinds is
an instance of: nothing is maintained in parallel with something else that can
change independently. Where two representations of one fact are genuinely
needed — a machine-readable schema and a human-readable README, an engine's
admission rule and an interface's affordance — one is generated from the other,
and the test asserts the generation rather than the copy. v2's most instructive
failure was a test that pinned a hand-written duplicate against itself, which
does not merely fail to catch drift but certifies it.

Forbids: a hand-maintained parallel to a declaration; and a normative document
with a line number in it.

## 7. The frozen tree

The second implementation is frozen mechanically rather than by intention: it
moves to a path CI refuses to run and packaging refuses to ship, so "just patch
it quickly" stops being available without anyone having to decline it. Freezing
that leaves the tree patchable removes all urgency from the rewrite and makes the
new work a permanent parallel branch, which is the stall PLAN warns about — but
that is a property of the freezing mechanism, not of freezing.

1. **Extraction precedes freezing.** A tree is not frozen until the document that
   carries its lessons forward exists, because the code is not the channel and
   memory is not either. FINDINGS is v2's extraction, and its "mechanisms worth
   carrying forward" section is the part that does the actual work.

   This rule previously recorded that the first implementation was frozen without
   an extraction and that the loss was permanent. **That is false, and correcting
   it strengthens the rule rather than weakening it.** v1 carries an extraction of
   its own, written before v2's, which states in its opening line that it holds
   the measurements that must not be re-derived and marks which of its conclusions
   had been reached wrongly at least once. What actually happened is worse than
   the loss recorded here and is the more useful lesson: the document existed,
   nothing pointed at it, and v2's extraction was written as though it did not.
   Extraction is therefore necessary and not sufficient. A document nothing cites
   is not a channel either — the same anti-rot argument §6 makes about the tree,
   turned on the corpus itself — and it is why the carry-forward list is stated as
   behaviours owing checks rather than as modules: a check fails when it is
   ignored and a document does not. Retail remains a channel and is no longer the
   only one. When someone notices a specific thing an earlier tree did better it
   becomes a ledger entry at that moment, which is where it will not evaporate.
2. **The frozen tree is consulted through FINDINGS, not through its source.**
   Reading v2's code to answer a design question is how v2's shape propagates
   into v3, and it propagates most effectively where the code is *good* — the
   coalescer, the settled-prefix computation, the read-back verification are all
   genuinely well built, and each sits inside a structure that is the thing being
   replaced. Admiring the implementation and inheriting its placement is one
   motion. Three uses of the frozen tree are permitted and no others: porting a
   named carry-forward module, adding an archive entry, and reading a pure
   numeric kernel whose entire contract is array in, array out.
3. **Porting is against the new contract, not from the old file.** The five
   modules marked for carry-forward — the machine descriptor, the factorial
   sweep, the retention trace, the budget table, and the synthetic-fixture
   discipline — carry their substance forward. None arrives as a file copy,
   because each was written against a signature that no longer exists.

Forbids: reading the frozen tree to decide how something should be shaped.

## 8. What the plan inherits

The following are settled and the plan places them; it does not reopen them.
Each was adjudicated against a specific contradiction in the corpus, and the
column that matters is the third, because a contract decision deferred is paid
for by rewriting every operator written before it.

That third column is a constraint, not a phase. Phases are PLAN's numbering and
PLAN is deleted when it is finished; an ordering this document states in PLAN's
numbers would not survive its own dependency. The constraints below are stated
over constructions this document names, so each is decidable without reading
PLAN, and PLAN's job is to map them onto an order and to add the constraints
that come from build convenience rather than from contract. Where PLAN's
numbering and these constraints disagree, PLAN is wrong.

Five constraints, ordered by how expensive the deferral is. **Before the first
operator** — anything in the invocation signature or in an operator's
declaration, because a signature change rewrites every implementer. **Before the
first key** — anything that is a key term, because a key change invalidates every
artifact ever written. **Before the first key is trusted** — anything that
decides whether keys mean what they claim, which is narrower and comes with the
first source rather than with the algebra. **Before the first engine decision** —
anything the engine's scheduling, materialization, or placement reads. **Before
the first generated surface** — anything a surface must be able to express.
*Continuous* is the sixth entry and is not an ordering at all: it attaches to
every increment and is finished by nothing.

| Decision | Settled as | Not later than |
| --- | --- | --- |
| Windows | Two-sided: history *and* lookahead are declared fields | the first operator |
| Warmup shortfall | Legal at a source boundary and a key term | the first key |
| Determinism class | Open registry, closed by policy at two; propagates infectiously, with tolerant artifacts pinned so deleting one is recorded as invalidating the byte-identity claim downstream | the first key |
| Declared tolerance | Bound derived from a stated numerical argument, naming the source of non-determinism; tested against the argument's prediction, not the author's number | the first key |
| Measurements | Keyed derived artifacts under §1, so refitting is invalidation and the machine profile is a key term | the first key |
| Authoring surface | Graph-shaped from the start; affordances defined over a graph | the first operator (contract), the first generated surface (surface) |
| Invalid graphs | A legal log entry; the engine runs the valid subgraph and reports what is unreached and why | the first engine decision |
| Settled boundary | Computed from the declared window and carried on the artifact, not in a view | the first operator (field), the first stateful operator (use) |
| Frame-exactness | Measured and keyed as a source-layer property rather than gated on | the first key is trusted |
| Interface completeness | Every registered capability carries an interface debt triggered by the interface phase | continuous |
| The unit above a source | A declared collection whose members are a source plus its parameter overlay; membership is a key term by inheritance, and reduction across members is an axis of the invocation signature | the first key (the unit), the first operator (the axis) |

Two notes on that table. **Frame-exactness** is entered as a disclosure rather
than a gate, per §1.1, and its constraint is the narrow one for a reason that is
not accuracy: if a decoder does not seek exactly, two runs that seek the same way
agree, so every key is wrong invisibly and no downstream check can find it. The
key algebra can be built without it; the first key that anyone relies on cannot.
Keying the seek path makes the hazard visible without refusing anything, and
FINDINGS 5 states the measurement — read a range sequentially, read the same
indices after seeks, compare bytes — against the synthetic fixture §7.3 already
carries forward. **Determinism propagation** being infectious is what lets a
wipe-and-recompute check and a preview-divergence check compare bytes at all;
without it both compare nothing, which is why it is a key constraint and not a
scheduling one.

One thing the plan must place that no current document places: events are
terminal in v2 — computed, exported, never held — while the loop in §1.5 requires
one run's output to scope the next run's input, so intervals are input as well as
output.

Two others stood here and are now decided, in the row above and in ARCHITECTURE
§1.12. The unit above a single source is a collection of members, each a source
with its own parameter overlay, which is what makes cross-source addressing a
first-class concern rather than a downstream script at a hundred replicates over
a hundred thousand files. And tune-on-a-sample then run-on-the-set is a member
selection over that collection rather than an operation of its own: the sample is
a subset, the full run is all of them, the spec does not change between them, and
what it was missing was never machinery but a unit to be a subset of.

## 9. Open, with triggers

Two things this document deliberately does not settle, each with the trigger
that will force it.

**Frame identity.** A view cannot currently say whether it is showing pipeline
output or raw proxy decode, and the fix — an identity field on the frame — puts a
key on the most-copied object in the system. The cost is real and may be the kind
of cost that prevents the tool from existing at all, so the obvious answer is not
adopted by default. Trigger: the first surface that displays two feeds into one
viewport. Until then, the obligation is only that the artifact carries its key,
not that every frame does.

**The structural-debt threshold.** The number of commits a folder may carry a bin
warning before its dissolve debt comes due is a guess. Trigger: the third folder
to reach it.

Both are Decision debts and live in the ledger like any other, which is the
point — an open question with a trigger is tracked work, and an open question
without one is a document that will be found to have been wrong.
