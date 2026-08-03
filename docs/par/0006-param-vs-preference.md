# PAR-0006 — Param vs. preference: what belongs to the recipe

Status: Proposed
Date: 2026-08-03

Owed: 20260803T072355Z: two amendments from the tool-contract scoping session (primary `SESSION-2026-08-03-tool-contract-scope.md`) — the Consequences' "hash over effective params" rule exists only because every field lives in one model, and becomes unnecessary rather than obeyed once a method's params live on the method, since no inert field survives to be excluded; and the record classifies by effect while measurement-versus-method is a question of ownership it cannot express, which is why `dis_preset` is correctly a param under its rule and still does not belong beside the fields that survive a method swap

## Outcomes

What this system looks like working as intended: a pipeline file
carried to another machine reproduces the number it produced here, and
where it cannot, the run record names the one choice that differed and
what the measured difference was. Nobody debugging a discrepancy has to
ask what was configured on the other machine, because every input that
could move the answer is in one of three places — the file, the run
record, or nowhere, because it provably could not have mattered. A tool
author never thinks about the boundary at all: there is no channel
through which they could get it wrong.

## Context

The named system: the classification of everything a run depends on
into what belongs to the authored recipe and what does not. Decided
2026-07-31 in `docs/archive/DESIGN-SESSION.md` Exchange 2, "One
boundary to fix on day one," with Exchange 4's settlement that the base
layer a result is drawn over "is a view setting, never a param, never
in the task hash" and that preview is not a separate system but the
same recipe with two ops prepended. The domain qualifier below is
Exchange 1's intent/progress split and Exchange 8's measured selection,
both of which the same session already holds; the session's own
settlement list restates the rule as "anything that can change an
output value is a param."

The seams. This record owns the *user's* inputs and nothing else. What
the executor may substitute without telling anyone is PAR-0005's, and
it is a proof question rather than a classification one; what licenses
an implementation choice to move an answer at all is PAR-0012's
measured equivalence; where the param set is hashed and where the run
record lives are PAR-0009's; the absence of a preference argument from
the tool signature is stated here and lands in PAR-0007's contract; the
GUI's consumption of preferences without ever writing one into a param
field is PAR-0013's.

The occasion is the failure mode Exchange 2 named and the cost of
discovering it: "the same pipeline file produces different results on
two machines and finding out why takes a very long time." Both clauses
are load-bearing. The first is what the rule prevents; the second is
what makes a violation expensive out of proportion to its size, because
a misclassified knob produces a small, plausible difference in a number
nobody can attribute, and the search space is the whole machine. That
the difference can be large is also on record: by PAR-0005's verified
citation, v1 measures 0.364 RMS grey-levels for scale before
`format=gray16le` against 3.80 reversed — a 10× accuracy difference
from ordering *inside* an implementation, which under a two-class
scheme is neither a param nor a preference and therefore had no home.
It lived in a comment.

The classification is not a hypothetical, and v1
(`antscihub-optical-flow-detector`, `core/config.py`) is where its
difficulty is legible. Three of its fields carry the argument in their
own comments. `downsample` defaults to off with the reason stated —
"a pipeline that silently downsamples has already decided which
behaviours are detectable" — which is a param argued as one even though
what it buys is compute. `block_size` tracks the scale rather than
moving with it, so that "turning the compute knob would also coarsen
localization" is not something a user has to disentangle: separability
between a speed lever and an answer lever is engineered there, not
given. And the aliasing limit is enforced by capping the frequency bank
at `0.45*fps` in `core.wavelet.default_freqs` rather than by the
`validate_bands` warning, which the docstring records as *uncalled* —
the same structural-over-declarative move this record makes below,
arrived at independently under production pressure.

Primary: none filed, and the reason is not that a distillation reads its
source. It is that the argument has not been had. The doubts below are
agent-raised and unratified, and the reasoning this draft supplies beyond
Exchange 2 — the pricing of the tiebreak, the ratification of the
contract's silence as the enforcement — has not been argued against
anyone. A primary is owed at the sitting where it is.

## Decision

**The criterion, and the domain it runs over.** If a user-supplied
input can change an output value it is a **param**: it lives in the
pipeline file and in the task hash. If it can only change presentation
or speed it is a **preference**: it lives in neither, and travels with
the machine rather than the recipe. Anything ambiguous is a param.

The domain qualifier is what makes the binary complete. It partitions
inputs *the user supplies*; a choice the system makes for itself is
neither, and Exchange 1 already built its home — the progress side of
the intent/progress split, the run record. Three things fall there and
none is a param: which member of a verified-equivalent implementation
class was selected on this machine for this input shape (Exchange 8),
the seed a stochastic method drew, and what was baked. Each can move a
number and none is authored intent. Pinning a seed in the pipeline file
would make two runs of one file the same run and destroy the ability to
measure run-to-run variability; pinning an implementation would put the
machine into the recipe, which is the failure the harness exists to
avoid. They are not inputs to the recipe. They are outputs of the run.

*Verified-equivalent* is doing the work in that sentence, and v1 shows
why. `FlowConfig.backend` chooses between Farneback, DIS and RAFT.
Those are not members of one equivalence class — they are different
methods that answer differently — so the choice is a param, authored
and hashed. A backend that had earned membership by measurement would
be provenance. The same-looking knob lands in different homes according
to whether equivalence was earned, and nothing about the knob's surface
says which.

**The property the three invariants jointly hold** is that there is no
*unaccounted* difference: every input that can move an output is in the
file, or is provably unable to matter, or is recorded in the run with
the measured claim that licensed it. Invariant 5 owns only the first
and second. Invariant 3 (PAR-0005) makes silence conditional on proof;
invariant 4 (PAR-0012) makes an unproved system choice conditional on
measurement and on being recorded. Read alone, invariant 5 looks
violated by the harness, which lets machine-local selection move a
number. It is not: that difference is bounded by a measurement,
version-pinned, and carried in the provenance, so the second clause of
the failure mode — finding out why — becomes a query rather than a
search.

**The tiebreak is asymmetric, and the asymmetry is its argument.**
Exchange 2 states "anything ambiguous is a param" without the pricing,
and the pricing is what makes it obeyable rather than arbitrary.
Misfiling a preference as a param costs recomputation and store space:
the knob enters the hash, so changing it names an address not yet in
the store and the work reruns. Nothing is invalidated, no result is
wrong (Exchange 5's store), and the user watches it happen — v1 paid
exactly this, hashing `compression_level` into the feature cache's
identity key alongside the fields that set precision. Misfiling a param
as a preference costs a wrong number that reproduces reliably on the
machine that produced it. One cost is bounded, visible, and paid in
seconds; the other is unbounded, silent, and paid by whoever cites the
result. No threshold makes the second the better bet, which is why the
rule takes no judgment.

Ambiguity is also the common case rather than the edge, and the rule
must be read knowing that. In v1's flow config, `dis_preset`
(ultrafast/fast/medium) and `raft_iters` are speed knobs whose speed is
bought with accuracy; `dtype: float16` sits beside `compression: zstd`
in one dataclass where the first changes the stored value and the
second cannot. Real speed settings in measurement code are usually
accuracy trades wearing a performance name, so "can only change speed"
is a strong claim about an op, not a description of a field's title.

**Classification is by effect, never by surface.** The pane a value
arrives through says nothing. A crop box drawn with the mouse on the
left canvas is a param, because overlays are editors bound to param
fields and drawing the box is the same mutation as typing the
coordinates (Exchange 2). The base layer it is drawn over is a
preference, because swapping tracks-over-mask for tracks-over-source
changes what is displayed and no value that is computed (Exchange 4).
Same pane, same mouse, opposite classes. And the tempting third case is
already closed: preview quality is not a preference, because "run this
on frames 2000–2500 at quarter resolution" is a subrange op and a
geometric op prepended to the same recipe, so preview cannot diverge
from production — a correctness property rather than a convenience
(Exchange 4).

**The guard is structural, not declarative.** Three times this design
rejected a property a contributor asserts — the random-access flag, a
lowering's declared output type, the catalog entry's claim — and each
time the repair was to make the structure carry the property rather
than bolt on a conformance test. Param-vs-preference as a rule a tool
author is asked to obey is that same rejected pattern: nothing detects
a misclassification, and anything a contributor can assert, a
contributor can assert wrongly.

The repair is already in the tree and costs nothing to keep. The tool
contract as rebuilt in Exchange 5 is `lower(self, p)` and
`view(self, p, out)`: the sole channel from a tool to the answer takes
the params and nothing else. Prompt 2 asked for a step that "also takes
SIEVE preferences"; the rebuilt contract has no argument for them, and
this record ratifies that removal as the enforcement rather than as an
omission. A preference cannot enter the op graph, because the wire does
not exist to be grabbed — the same move that keeps the executor out of
tools. The only remaining route is ambient state read inside `lower` —
a module global, an environment variable, a settings file — which the
purity rule already forbids and which is now *testable*: evaluate
`lower(p)` under two scrambled preference sets and require the emitted
op value to be equal. That test is why preferences need exactly one
home, a settings object the scrambler can vary; a preference read from
anywhere else is precisely the ambient state being forbidden, and its
unreachability by the test is the tell.

The two components that do consume preferences are the two that cannot
launder them into an answer. The GUI renders and never computes
(invariant 2), and where it writes, it writes params through bound
editors. The executor's answer-affecting choices are governed by
invariants 3 and 4 — proof, or measurement plus a record — so a
preference reaching the executor selects among outcomes those
invariants have already made equivalent, and nothing else.

## Consequences

- Acceptance amends `ARCHITECTURE.md` in the same commit: invariant 5
  gains its domain qualifier and names the structural guard rather than
  reading as a rule to be obeyed, and its citation moves from Exchange
  2 to PAR-0006.
- PAR-0007 carries the contract's silence on preferences as a
  load-bearing absence, so a later signature change does not restore
  the argument as a convenience.
- PAR-0009 receives three consequences. The hash consumes the param set
  and the op values, so an implementation chosen per machine is not in
  the address — otherwise two machines running measured-equivalent
  implementations never share a store entry, a cost the harness exists
  to remove; `Opaque` stays the stated exception, its logical identity
  collapsing into a hand-bumped implementation version. The hash is
  over *effective* params, or a field inert under the current
  configuration (v1's `fb_*` under a non-Farneback backend) fragments
  the store while changing nothing. And the run record's format, which
  must hold selection, seed, and bake, is PAR-0009's to design.
- PAR-0013 owns the rule's GUI face: every control binds either to a
  param field or to the settings object, and the pane it sits in is not
  the discriminator.
- The conformance suite gains the preference-scramble test — `lower`
  emits an equal op value under varied preferences — which is what
  gives this record teeth beyond exhortation. Enforcement's home is
  PAR-0017's.
- Preferences get a single home as a precondition of that test, not as
  a convenience. Where it lives is the layout question, not this
  record's.
- Reclassifying an existing field is deliberately expensive: a schema
  migration plus a changed hash for every affected result. It is an
  architecture act, not routine work, and the how-to layer's silence on
  it is the signal.

## Challenges

*Agent-raised, none human-confirmed yet (PAR-0001: friction is stated,
never inferred).*

- **2026-08-03 — half the guarantee rests on a stub.** The three-home
  claim is only as good as the third home, and the run record exists
  today as a citation to PAR-0009, which is undrafted. The file half is
  enforceable now; the provenance half is an intention.
- **2026-08-03 — the scramble test detects reachability, not
  intent.** It catches a preference that reaches the op graph. It
  cannot catch the opposite error — a genuine param the author never
  put in `Params` at all, hard-coding it as a constant. Nothing
  structural forbids that and nothing proposed here would, because the
  constant is not a knob to classify.
- **2026-08-03 — a property of the input is neither param, preference,
  nor system choice.** v1's config docstring records that a cache key
  "MUST fold in `meta['clip_provenance']`: below `lossless`, a
  clip-derived and a source-derived result are different
  measurements." The codec a clip was transcoded with moves the number
  and is authored by nobody. It presumably belongs to the source
  identity inside the recipe hash, which is PAR-0009's, but this
  record's three homes do not name it and the classification says
  nothing about it.
- **2026-08-03 — "provably unable to matter" is asserted per
  preference, not proved.** The no-unaccounted-difference property
  reads as though the preference class were verified answer-neutral. It
  is verified only at the tool boundary. That a cache size or prefetch
  depth cannot perturb an executor result is a property of the
  executor's construction, claimed rather than tested.
