# ADJUDICATION

The record of the session that settled the corpus's open contradictions: ten
scope questions about what SIEVE is for, and twelve adjudications between
documents that disagreed. The author's answers are verbatim and are the source
for STRATEGY §1's disclosure rules and §8's settled table.

Archive, in STRATEGY §6.4's sense. Its citations point at the frozen tree and at
document sections as they stood when the questions were asked, which is why they
cannot go stale — several of the positions quoted here as live have since been
amended precisely because of what was decided in this session. Nothing below is
updated to match the current corpus.

**On the text.** The original was captured from a terminal and several long lines
were overwritten by later renders, destroying spans of text rather than
scrambling them. Every gap is marked `[…lost…]` at the point it occurs. Nothing
is inferred or smoothed. Two spans are recovered from `principles_inputs_distilled.md`,
which quoted the answers before the capture was damaged, and each is marked at
the site. Terminal artifacts and interface chrome are removed; no other editing
was done to the author's words.

---

# Part I — The ten questions

The framing that produced them: the science appears in three places in roughly
1,400 lines of corpus — CHARTER's two user limitations, neither checkable;
CHARTER's feasibility claim, which is about whether a project can run rather than
what it produces; and FINDINGS 21, filed under extension costs. Each question is
phrased so the answer `[…lost…]`.

## 1. When SIEVE says an event happened and it did not, what does that cost you — and is it the same cost as SIEVE missing one?

Yields whether asymmetric error is a system property or a detector setting. If
asymmetric, "a derived view reports its settled boundary" stops being a display
nicety and becomes a rule about what SIEVE is permitted to assert — and Q3a
decides itself.

> SIEVE gives feedback that is validated against the user's metrics for what an
> event is, and the measures that the user tunes. SIEVE doesn't know what these
> are and doesn't need to know what these are.

## 2. Is SIEVE's output ever the final answer, or is it always a proposal a human accepts or rejects?

Yields whether the durable unit is the artifact or the artifact-plus-a-human-decision.
Decides FINDINGS 21 outright: if a human always adjudicates, intervals are input
as well as output, the timeline must hold tracks regardless of origin, and
"events are terminal" is a defect rather than an extension cost.

> SIEVE's output is never the final answer. SIEVE makes a product that fits
> specifications. In a sense, it is almost a purely mathematical instrument;
> SIEVE will produce the answer given what it was told to do.

## 3. When you hand a tuned pipeline to someone else, what do they need before they trust its numbers — and what makes them re-tune instead of reusing?

Yields the actual content of "redeployable." The corpus reads CHARTER 7.1(b) as
serialization fidelity. If the honest answer is "they always re-tune, their
lighting differs," round-trip fidelity is not the property that matters and
transferable calibration is — which nothing addresses.

> They run SIEVE on a sample of their footage and likely tune it from SIEVE
> itself to work with their controlled environment.

## 4. Do the detector's parameters go in a methods section?

Yields whether provenance is an external obligation or an internal debugging
aid. If external, the log's serialization is a published format and §8.1's
versioned-schema rule extends to the spec, which the corpus claims only for
outputs. It also converts FINDINGS 19's migration story from "don't break saved
files" to "reproduce published work" — a much stronger reason for the same rule.

> Yes, and it is SIEVE agnostic. SIEVE is a way to do things other programs can
> do but faster; it can be built faster, it can be validated faster, it can be
> computed faster.

## 5. Over what span does one scientific question run — one video, one recording session, one season?

Yields the unit that must be addressable and keyed. §1.6 makes the artifact a
frame range `[…lost…]` a question spans forty videos, there is a per-study unit
above it with no name anywhere, cross-source aggregation is a first-class
operator kind rather than a downstream script, `[…lost…]` bearer.

> SIEVE has no interest in the scientific question frankly and doesn't exert
> opinion on it. The immediate use cases are footage that spans 3 weeks, footage
> that spans 1 week, footage that spans 8 weeks, footage that spans 30 hours, and
> footage that spans 10 minutes. All of these have different volume counts; the 8
> weeks footage is over 100 replicates and 100,000 video files, for example.

## 6. How much of a recording is worth looking at — rare events in mostly empty footage, or something continuous?

The most likely way the whole performance section is aimed wrong. §7's
megapixels-per-second assumes uniform work across the source. If the job is "find
forty seconds in six hours," "how long to process the whole thing" is not the
feasibility question, §7.1's throughput estimate answers something `[…lost…]`
the sensible claim is cost per candidate found. §2.3's content-dependent cost
terms gesture at this and stop short.

> `[…lost…]` on this and can obviously do both. Finding the 40 second window is
> just the output parameter that the user uses to scope the output. It's one step
> of SIEVE that leads into a second SIEVE session.

## 7. When the answer looks wrong, what do you do — re-tune, re-record, or distrust the tool?

Yields whether SIEVE owes explanation or only numbers. CHARTER's loop is
load→measure→tune→load with no diagnosis step. If the real loop has a "why did it
say that" step, intermediate artifacts are a user-facing surface and §1.3's "the
only consequence is recomputation cost" acquires a caveat — recomputing something
you were mid-way through looking at costs more than time.

> When the answer looks wrong, it can either be retune, or rerecord, but the tool
> itself will do what it says. Not all behavior has a signal that can be filtered
> out.

## 8. What has to be true before you believe a detection threshold is right?

Yields whether "verification" in §9 means artifact integrity or scientific
validity. The corpus uses one word for both; §9 is entirely about bytes surviving
a write. If the answer is "I compared it against hand-scored footage,"
ground-truth comparison is in scope, and detector evaluation is a pipeline kind
rather than a spreadsheet.

> The user can validate it. SIEVE makes no judgement on the validation, it just
> outputs the result.

## 9. Which of CHARTER's two user limitations actually loses you a user — the fragile workflow, or not knowing where to begin?

Yields which of two incompatible top-level claims leads. Recoverability — every
action undoable, nothing gets slower by doing it — is what CHARTER 34 describes
and is stated nowhere as a principle. Sequencing is CHARTER 35, and PLAN Phase 8
concedes it has no architectural answer. Both cannot lead, and right now neither
is stated as a claim at all.

> Both lose the user. This is a false dichotomy. SIEVE has to do both, but the
> actual design of the UI is not something an agent needs to concern itself with.
> The ability to build the UI from everything that SIEVE provides is what matters,
> and ultimately goes back to the GUI being a glorified parameter interface for
> `[…lost…]`

## 10. Name one thing you would refuse to add to SIEVE even though a user asked for it.

Yields the scope rule with teeth. "Something that doesn't enable something for the
pipeline is outside the scope of SIEVE" is the only claim in the corpus that can
reject work, and it has never been run against a real candidate. One worked
example makes it usable; without one, an agent will find that everything adjacent
enables something for the pipeline eventually.

> `[…lost…]` solid foundation step, it should deliberately exclude analysis of
> the results (stats on the detections - this is user decisions which SIEVE
> doesn't own), recommendations on how to provide good footage (it works with
> what it's given, a pipeline works with what it receives). I don't know if this
> gives you enough for teeth though

---

# Part II — The adjudication queue

Twelve contradictions between documents, each stated as a binary with what each
branch costs, and a preference named without the decision being made. The author's
ruling follows each.

## Q1 — Warmup shortfall: error, or legal and keyed?

ARCH §3.1 says error; FINDINGS 3 says legal at a source boundary and keyed there
and explicitly corrects §3.1; PLAN Phase 6 still verifies it raises. The tree does
neither — `cli/run_cmd.py:134` warns and proceeds, and the shortfall is not in
`node_key`, which is exactly the defect finding 3 diagnoses.

*Error:* every windowed operator is unusable in the first *w* frames of every
source; a user who crops the start gets a refusal. *Legal and keyed:*
`lead_in_supplied` becomes a key term, cold frame N and warm frame N stop
colliding, and §3.1's forbidden case becomes impossible by construction rather
than by prohibition.

**Preference:** legal and keyed. It is FINDINGS principle 3 applied to its own
case. Adopting it edits three places, not one.

> Warmup shortfall is legal and keyed; SIEVE lets the user do the wrong thing but
> ann`[…lost…]`os are failing.

*The lost span reads, in the distilled's record of it: "and announces loudly
where assumptions are failing."*

## Q2a — Does determinism class propagate?

*Stops at the boundary:* cheap, matches how §1.5 already handles tolerant
artifacts, but collides with §1.3 — delete the tolerant intermediate and the
"bitwise" downstream artifact changes, so not everything derived is freely
deletable. *Infectious:* preserves §1.3 exactly, costs byte-for-byte comparison
downstream, which Phase 5's wipe-and-recompute and Phase 7's divergence test both
rely on.

**Preference:** infectious with tolerant artifacts pinned — deletable, but the
delete is recorded as invalidating the byte-identity claim. That is a third
option, so it needs deciding rather than defaulting.

> Determinism follows what you stated as preference, infectious with tolerant
> artifacts pinned.

## Q2b — What makes a declared tolerance falsifiable?

*Author declares a number:* fast, reproduces §1.5's own named failure. *Bound
derived from a stated numerical argument,* tested against the argument's
prediction rather than the author's number.

**Preference:** the second, narrowed to require naming the source of
non-determinism (threaded reduction, float atomics, library build), because a
source is checkable by inspection and a number is not. Same complaint FINDINGS 3
makes about `backend_identity`: a version string is not a determinism guarantee.

> Bound derived from a stated numerical argument, and yes needs a source.

## Q3a — §4 and provisional-versus-settled

§4's Forbids refuses event-time machinery outright; FINDINGS 6 restores the
settled-prefix boundary v2 already computes at `detector.py:69`.

*Keep §4:* completeness is unmodeled, and the detector's settled logic goes back
to living in a widget — which is how `_settled` ended up in `filter_tab.py` in
the `[…lost…]` -ness becomes part of what an artifact carries, distinct from
freshness; §4 keeps its refusal of watermarks and out-of-order arrival, which
remain referentless.

**Preference:** amend. The boundary is computable from the declared window, and
putting it in the artifact is what stops it living in a tab.

> Amend.

## Q3b — §5.4, freshness or freshness plus identity?

v2's player silently swaps between pipeline output and raw proxy decode, and
`core/types.py:120` `Frame` has no identity field to make that visible. *Freshness
only:* the swap stays invisible. *Plus identity:* every view can say what it is
showing, at the cost of a key on the most-copied object in the system.

**Preference:** amend, but this one is genuinely not free and should be decided
rather than inherited.

> Unsure. I think this needs a more clever solution, I suspect the bloat answer
> might prevent the tool from existing.

## Q4 — Visibility: the GUI, or the user surface?

Under the GUI-scoped reading, Phases 0 through 7 are unconstitutional. *GUI:* the
invariant is unsatisfiable for the entire duration of the plan implementing it,
which is how rules become decorative. *User surface:* satisfiable from Phase 3,
makes CLI completeness a real obligation, and weakens the original claim — a
capability reachable only from a CLI flag is not what CHARTER's naive user needed.

**Preference:** user surface, with the naive-user problem separated out rather
than smuggled in. CHARTER 65 fuses two claims: no capability is silently
unreachable (durable, checkable, surface-independent) and a new user can find the
entry point (durable, uncheckable, and PLAN Phase 8 concedes it has no
architectural answer). The fusion is what makes it read as GUI-scoped.

> GUI is a debt that is marked to be paid when it is available to come due.
> Otherwise features early on are earmarked and ignored forever. These due
> features need to be grouped and accessible to anyone working on the repo, but
> the build order must be respec`[…lost…]`ce will be marked to be paid earlier
> than they can be and will result in v3 having the same problem as v2.

## Q5 — Free folder proposal, or a new-type gate?

*Free:* depends entirely on §3.2's dissolve remedy being applied, and §3.3
concedes the problem while routing its signals to CI as warnings nobody has to act
on. *Gated:* one sentence per new folder — cheap for a human, genuinely expensive
for an agent with no context, which is the population §6 explicitly optimizes for.

**Preference:** free, with the gate moved to the dissolve side — a folder carrying
a bin warning for N commits must be defended or dissolved. Creation stays free and
§3.2 gains the trigger it currently lacks. Third option; needs deciding as one.

> I suspect stating it as a free option will make it into a target. There
> probably needs to be some kind of specific criteria for it, or a check of some
> kind.

## Q6 — Is v2 frozen or deleted?

*Frozen:* the tree stays readable, which matters more than PLAN allows —
FINDINGS' 41 citations point into it, and five modules are explicitly marked for
carrying forward (`core/machine.py`, `bench/sweep.py`, `bench/retention_trace.py`,
`bench/budgets.py`, `tests/conftest.py`). Porting from a deleted t`[…lost…]`
*Deleted:* the phases are the only path, at the cost of the corpus's only evidence
base.

**Preference:** frozen, made mechanical rather than intentional — moved to a path
CI refuses to run and packaging refuses to ship, so "patch it quickly" stops being
available without anyone having to decline. PLAN's warning applies to freezing
that leaves it patchable, which is a property of the mechanism.

> There are things that v1 does better than v2, and v1 is frozen currently, but
> the things it does better somehow didn't make it into v2. I'm not sure how to
> fix that. However I don't want to inherit the problems of v2 and every time you
> look directly at v2 you praise it and then try to follow it's problems,
> sometimes in ways that aren't clear to me.

## Q7 — Is the authoring surface graph-shaped from the start?

FINDINGS 14 says yes. ARCH §2.6 allows multi-input in the engine. PLAN Phase 8
says nothing about graph authoring, and Phase 3's reference operator is a single
transform. *Graph from the start:* affordance rules, placement, the
reason-it-cannot-go-here message, and engine/interface divergence are all defined
over a graph once — costing Phase 8 design work PLAN has not scoped. *Path first:*
exactly what v2 did, and finding 14 is the record of the cost.

**Preference:** graph from the start. Note it makes ORG §7.2's multi-input
reference member load-bearing on the interface side too. Phase 8 is under-scoped
either way.

> Graph from the start.

## Q8 — Is an invalid graph a legal state?

FINDINGS 16 says the invalidating edit is a legal log entry and belongs in ARCH §1
and §5; it is in neither, and it contradicts `charter-invariants.md`'s Closure.

*Admission rejects:* cleanest contract, but interactive authoring then requires
the interface to hide invalid intermediates from the `[…lost…]` lives, which is
§5.5's forbidden case through a side door. *Log accepts:* interactive authoring is
normal; the log holds entries that do not resolve to a runnable graph and
"unreached" becomes a reported state.

**Preference:** log accepts. Consequence: §1.2's "membership in the DAG is
deterministic keyability" becomes a claim about what executes, not what can be
authored, and those need different words. Nothing currently makes that distinction.

> Invalid graphs need to state the failure mode clearly to the user; this follows
> the debt system I outlined above. User can select any end state or output they
> want by design, the different ways to get there are debts to be paid and are
> made clear to the user. How this is resolved is going to be determined at the
> GUI stage and will be tooled by me directly; the capability just needs to be
> there so that the entire thing doesn't have to be retooled for that eventuality.

## Q9 — Frame-exactness: gate before the key algebra, or assumption?

FINDINGS 5 says verified by test before any key schema is committed. PLAN Phase 1
commits the key algebra and its check list omits it. *Assumption:* if the decoder
does not seek exactly, every key ever computed is wrong invisibly, because two
runs that seek the same way agree. *Gate:* one t`[…lost…]` already exists —
`tests/conftest.py` makes frame *n* a solid field of intensity *n* × 5
specifically so a test can assert which frame a seek landed on.

**Preference:** gate. Possibly a straightforward PLAN oversight rather than a real
disagreement, but PLAN's own "a phase is done when that check runs in CI" gives it
teeth.

> This is the hyper-accuracy focus from before; it is not a concern. A more
> performant tool is prioritized, because the results are user-verifiable where
> SIEVE will very frequently lack any capacity to pass judgement.

## Q10 — Is the determinism taxonomy closed at two?

*Closed:* simplest key algebra; the first operator fitting neither gets forced
into tolerant with a meaningless numeric bound, which is §1.5's own named failure.
*Open registry, two members today:* the class is a declared name with a declared
equivalence predicate.

**Preference:** open registry, clos`[…lost…]` refuse a third without an explicit
decision. Cheap under PLAN's Phase 1 rule and requires no guess about what the
third is.

> Open registry, closed by policy. The user can pick. Frankly, the ability to
> select between different modes being announced to the user and giving them full
> knowledge of what they're selecting bypasses most of the judgements that you
> seem to think SIEVE needs to make. The main outcome of this is that however it
> is implemented eventually, the structural organization of the repo and how the
> code is organized makes any choice possible.

*The span from "needs to make" through "the repo and how the code" is recovered
from `principles_inputs_distilled.md` B1, which block-quotes this answer from
before the capture was damaged. The damaged capture reads "SIEVE needf this is
that … the structural organization of therepo".*

## Q11 — Where does detection live, and are windows two-sided?

The sharpest one. ARCH §3.1 declares history only. FINDINGS 1's solution class
requires two-sided windows, and `core/detection.py:23` is the live case — with
`centered`, `window_bounds` reads `t + (window - window // 2)`, future frames,
which no one-sided declaration can express. That is why the detector was built
o`[…lost…]` `ChainKind.EVENTS` has no engine counterpart, and why the product's
centerpiece is not a pipeline component. PLAN Phase 3 and ORG §7.2 both name three
hard shapes — stateful, multi-input, rate-changing — not this one.

*One-sided:* the v2 arrangement with the v2 consequences — unkeyed, uncacheable,
unschedulable, its own worker, thread, and CLI command. *Two-sided:* lookahead is
a declared field, the reference set grows a fourth shape, and Q3a's settled
boundary becomes computable from the declaration.

**Preference:** two-sided, in Phase 1. It is the clearest case in the corpus of a
contract field nearly free now and a full rewrite later, and it is the one
FINDINGS nominates as the repeat-failure risk.

> Your preference is the answer here; all of my answer to q10 is what guides most
> of these answers and the previous answers, I think.

## Q12 — Are measurements keyed artifacts?

Unstated and cheap. §1 says everything not source-or-spec is derived and keyed;
§9.3 `[…lost…]` attribution to a machine profile, which functions as a key term
without being called one. *Outside §1:* two derived-data disciplines, and every
argument about invalidating a fitted cost shape happens twice. *Inside:* refitting
is invalidation, and FINDINGS 9's insight — the ceiling is an allocation, not the
hardware — becomes a key term, so a measurement taken under a SLURM allocation
cannot silently answer a question about a laptop.

**Preference:** inside §1.

> Inside 1, as you said.

---

# Errata reported to the author in the same session

FINDINGS carries three factual errors: four stateful filters, not five; "691
`self._` references" is the line count, and the reference count is 817 across 154
distinct names; four interface threads is five, and the decode thread is created
in `player.py:77`, not `decode_worker.py`. Separately, finding 15 cites
`test_chain_model.py:173-174` for the wrong proposition — the test's own rationale
comment went stale when element meaning became a registration requirement, which
is a sharper lesson than the one recorded.

These corrections belong in FINDINGS and had not been applied there as of this
session.
