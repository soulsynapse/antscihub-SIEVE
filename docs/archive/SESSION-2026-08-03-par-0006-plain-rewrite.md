# Session — PAR-0006 tested and rewritten plain (2026-08-03)

Status: Frozen

One decision-cluster: whether PAR-0006's draft holds, and the form its
rewrite takes. Argued between Kendrick and the agent. Companion to
`SESSION-2026-08-03-tool-contract-scope.md`, whose two owed amendments
land in the rewrite this record accompanies. Frozen at acceptance,
2026-08-03 (the Close below).

## Exchange 1 — has the draft held?

Kendrick: "Lets look at par6 first. Has it held in it's current form?"

Assessment, accepted in the sequel: the criterion — effect-based
classification, the asymmetric tiebreak, the domain qualifier, the
structural guard — survived the tool-contract scoping session untouched;
that sitting is the only stress the draft has had. What fell was one
consequence (hash-over-effective-params, vacuous once method knobs live
on methods) and the draft's single-axis completeness (`dis_preset` is a
param under the rule and still not the tool's — hashed-or-not cannot
express ownership). Two further defects found: the draft quoted
`lower(self, p)` where the same sitting had settled
`lower(self, p, inputs)` — stale, and not covered by the marker's two
amendments — and the clip-provenance challenge left a user-supplied
input unhomed under a record whose claim is "no unaccounted difference."

## Exchange 2 — the concrete worlds

The same events run decided versus undecided, all with knobs from v1 or
the design record: `dis_preset` filed in settings by an agent reading
the bare invariant, producing machine-dependent numbers from
byte-identical files; a seed pinned into the pipeline file "for
reproducibility," destroying run-to-run variability measurement; the
base layer misfiled as a param — the cheap, visible, self-announcing
error the tiebreak deliberately falls toward; `settings.gpu_batch` read
inside `lower`, caught at PR time by the scramble test in one world and
surfacing as a failed replication months later in the other; and the
Phase 3 signature landing with or without a preferences argument, where
Prompt 2 of the design session literally asked for one. Pattern:
decided, errors are unrepresentable, caught at PR, or cheap and visible;
undecided, each error is individually reasonable and announces itself as
someone else's different number.

## Exchange 3 — cost, and the user's-eye view

Kendrick: "What does it cost to maintain it? I don't necessarily
understand what this is governing from the user's point of view."

Answer that stood: the user experiences the rule as which knobs
recompute and which are free — the classification is never read, it is
felt; the pipeline file is the complete measurement. Maintenance is near
zero by construction: no registry, no checklist, no per-knob review —
the classification is wherever the field lives, one absent wire, one
scramble test running with the suite. The two real costs are deliberate:
the over-hashing premium (ambiguous → param buys occasional visible
recompute — v1 knowingly hashed `compression_level`) and expensive
reclassification (schema migration plus changed hashes — the price of
trustworthy addresses). Honest dependency: the provenance half rides on
PAR-0009, unbuilt.

## Exchange 4 — devil's advocate: is the boundary an unnecessary tradeoff?

Kendrick: "v1 wanted fast answers because it keeps the ui responsive;
something we pretty much always want. v2 wanted accuracy, because it's
important. v3 wants both, transparently to the user; a 'pipeline design
pass' will feel good when it is snappy and responsive. A validation pass
is expected to be a bit slower. ... Go look at the v1 case, where the
users can move the handles on the thresholds. Do those qualify as
parameters or preferences? What about the ability to hold shift and see
through the overlay? Is that a preference sitting on a hotkey?"

Read against v1's code, not answered abstractly. The threshold handles
are params and v1 treats them so: committed on band release to the
tuning sidecar ("committed changes (band RELEASE, not every drag
frame)", `scalogram_explorer.py`), snappy because the flow/wavelet
energy cubes are cached and live drag feedback is a cheap in-band count
— the expensive clump analysis waits for release. Shift-to-peek is
transient view state, unpersisted; it gates a param editor (peek
suppresses the box hit-test so you cannot blind-edit) but never writes
one; classification is by effect and a hotkey is just another surface.

Resolution: fast, accurate and transparent are delivered by orthogonal
mechanisms — caching and prepended preview ops for speed, the hash for
accuracy, file-plus-run-record for transparency — so speed is never
bought at the classification boundary. Hashing a threshold costs
nothing at drag time; recompute cost is graph position, not class.

Position that lost: a fast-mode quality preference outside the hash.
Killed because the design pass and the validation pass become two
different measurements at one address — silent divergence, the exact
thing "transparently" forbids — and v1 itself kept thresholds snappy by
caching, not by demoting them to view state. Rider surfaced: commit
granularity (a hundred intermediate values mid-drag) is a real design
point and belongs to PAR-0013 and PAR-0008, not this record.

## Exchange 5 — the bar, and the plain summary

Kendrick: "Good architecture results in things being easy to implement,
not hard. This PAR is hard to understand, and won't be worth accepting
until it is very easy to understand, frankly. The summary in my
understanding is that preferences are what preferences always are:
something under a file menu, changes how the user interacts with the app
itself. Params are what params are in any model, any formula, etc.
Previous sessions decided these are owned by the ops to begin with, but
are visible to the user on the step, which is owned by the tool, and are
just passed through the tool."

Accepted: the system is easy — no channel to get wrong — and the draft
buried an easy system under a hard defense, written facing its edge
cases instead of leading with the rule. The plain summary becomes the
Decision's opening, with three footnotes: the speed-knob trap, the
run-record bin, the enforcement sentence.

One correction, confirmed by Kendrick in the sequel ("This is
correct"): params are not owned by ops and passed through the tool —
there are two param surfaces, each living where it means something. The
tool owns fields that survive a method swap; a method owns its own
knobs; the step's config pane composes them (PAR-0013). The test:
would the field mean anything to a different implementation of the same
operation?

## Exchange 6 — the rewrite

Kendrick: "This is correct. Rewrite it in as plain statements. A
rationale needs to be convincing and the current writing is overly
complicated for no reason. Keep it simple but accurate."

The rewrite lands with this record: plain criterion first; the marker's
two amendments landed (the effective-params rule dissolved; classify
scoped to this record, placement to PAR-0007); `lower(self, p, inputs)`
corrected; clip provenance homed in source identity (PAR-0009's). The
clip-provenance challenge is dropped as broken-and-repaired — a doubt
that changes the record is not an entry. The remaining three challenges
are kept, still agent-raised and unconfirmed. The stamp
`20260803T072355Z` discharges with the marker's removal. Acceptance is
not yet judged.

## Exchange 7 — pressure, and what it may decide

Kendrick, on the commit-granularity rider: "is it not a pressure thing?
Pressure has come up a few times and different things can express it; a
weak machine might have pressure from having to calculate the charts and
the overlays, for example. Storage to keep things as snappy as possible
has always been the goal and there are multiple ways to do that, not all
of which are correct, but all of which can be measured as competing ops
anyway, so because the comparison is something that can be run, the
answer can be decided right?"

Confirmed, with the line drawn: pressure decides which address gets
computed, when, and what survives eviction — never what an address
means. Three faces. View-side shedding (charts, overlays) is free
*because* of the classification — the GUI renders and never computes.
Store-side, the rider mostly dissolves: the store is size-budget aged
and never invalidates, so drag chatter is harmless by design, and what
remains is only file-write debounce (v1's release-commit), not
architecture. Compute-side, measured selection decides among candidates
— but only among candidates a declared yardstick has already made
indistinguishable: the comparator is authored by the tool (PAR-0007,
yardsticks never verdicts), because no experiment bootstraps its own
success criterion. Corollary kept for PAR-0012: two "storage
strategies" the yardstick distinguishes were never storage strategies —
they are two ops, and the choice is authored. The hash stays
pressure-blind, which is what lets two machines under different
pressure share store addresses at all.

## Close — accepted

Kendrick, confirming the scope of Exchanges 4 and 7 before ruling: "a
bunch of these concerns aren't architecture questions and PAR is
project architecture rationale. We're arguing about how the code
executes as exercise, and the problems with the PAR that don't need to
be decided now are why they're scoped to load bearing one way door
decisions." The execution material decided nothing and lives only
here; the record keeps one-sentence scope fences.

Then the ruling: "anyway, I think that should close out 0006." He also
named what unstuck the judgment — the user's-eye view (Exchange 3),
and the plain restatement: "The main overall effect of explaining it
to me so that I can explain the coherent version from the uncoherent
synthesis unstuck nearly every problem" — routed to the acceptance
how-to as reusable instruments. Accepted 2026-08-03; invariant 5
amended in the same commit; the three Challenges stand agent-raised
and unconfirmed; this record freezes here.
