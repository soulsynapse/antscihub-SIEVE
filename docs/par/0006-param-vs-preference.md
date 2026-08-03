# PAR-0006 — Param vs. preference: what belongs to the recipe

Status: Accepted
Date: 2026-08-03

## Outcomes

What this system looks like working as intended: a pipeline file carried
to another machine reproduces the numbers it produced here, and where it
cannot, the run record names the one choice that differed and what the
measured difference was. Nobody debugging a discrepancy asks what was
configured on the other machine, because every input that could move the
answer is in the file, in the run record, or provably unable to matter.
A tool author never thinks about the boundary at all: there is no
channel through which to get it wrong.

## Context

The named system: the classification of everything a run depends on.
Decided 2026-07-31 in `docs/archive/DESIGN-SESSION.md` Exchange 2 ("One
boundary to fix on day one") and Exchange 4 (the base layer a result is
drawn over is a view setting, never in the hash; preview is the same
recipe with two ops prepended). The run-record bin below is Exchange 1's
intent/progress split and Exchange 8's measured selection.

The occasion is Exchange 2's failure mode: "the same pipeline file
produces different results on two machines and finding out why takes a
very long time." Both halves matter — the wrong number, and the search,
whose space is the whole machine. v1
(`antscihub-optical-flow-detector`) shows the stakes: a 10× accuracy
difference (0.364 vs 3.80 RMS grey-levels) came from operation ordering
*inside* an implementation — under a two-class scheme neither a param
nor a preference, so it had no home and lived in a comment.

The seams. This record owns the classification of the user's inputs and
nothing else. What the executor may silently substitute is PAR-0005's;
what licenses an implementation choice to move an answer is PAR-0012's;
the hash and the run record are PAR-0009's; the contract's missing
preference argument lands in PAR-0007, which also owns where a param
lives; the GUI's side is PAR-0013's.

Primary: `SESSION-2026-08-03-par-0006-plain-rewrite.md` — the sitting
that tested the draft against v1's GUI, rewrote it in plain statements
landing the two amendments owed from
`SESSION-2026-08-03-tool-contract-scope.md`, and judged acceptance
(2026-08-03), where it froze.

## Decision

**A param is an input to the measurement — anything in the formula. A
preference is a setting of the app — it changes how you interact with
the tool, never what it computes.** Params live in the pipeline file and
the recipe hash. Preferences live in one settings object, travel with
the machine, and no path leads from them to a number.

**A third bin: choices the system makes.** The seed a stochastic method
drew, which verified-equivalent implementation ran on this machine, what
was baked. Each can move a number and none is authored, so none is a
param — pinning a seed in the file would make two runs of one file the
same run — and none is a preference, because they move numbers. They are
outputs of the run, recorded in the run record. *Verified-equivalent* is
load-bearing: v1's `FlowConfig.backend` chooses Farneback, DIS or RAFT,
which answer differently, so that choice is authored — a param. A
backend that had earned equivalence by measurement would be provenance.

**The one trap: speed knobs in measurement code.** `dis_preset`
(ultrafast/fast/medium) and `raft_iters` look like app settings and are
accuracy trades — speed bought with answer. Real performance knobs in
measurement code usually are. Hence the tiebreak: anything ambiguous is
a param. The pricing is what makes it obeyable: misfiling a preference
as a param costs a visible recomputation, watched, in seconds; misfiling
a param as a preference costs a silent wrong number paid by whoever
cites it. No threshold makes the second the better bet.

**Classification is by effect, never by surface.** A crop box drawn with
the mouse is a param — overlays are editors bound to param fields. The
layer it is drawn over is a preference. v1's threshold handles are
params and v1 already treats them so: committed on release to the tuning
sidecar, and the drag stays snappy because the expensive upstream is
cached — not because thresholds are view state. Shift-to-peek is view
state that is not even persisted. Speed is the store's and executor's
job — caching, and preview as ops prepended to the same recipe — never a
reason to reclassify. When a dragged value commits is PAR-0013's and
PAR-0008's question, not this record's.

**Two param surfaces, one pane.** The tool owns the params that survive
a method swap — spatial scale, temporal window, threshold. A method's
own knobs live on the method — `dis_preset` means nothing to Farneback.
The step's config pane composes the two (PAR-0013). This record decides
whether a knob is hashed; where it lives is PAR-0007's.

**Enforcement is a missing wire, not a rule authors obey.**
`lower(self, p, inputs)` takes the params and the typed upstream values;
there is no preference argument, and PAR-0007 keeps that absence
load-bearing. The only remaining route is ambient state read inside
`lower` — forbidden by purity and testable: evaluate `lower` under two
scrambled preference sets and require identical op values. The test is
why preferences need exactly one home the scrambler can vary. The two
components that do consume preferences cannot launder them: the GUI
renders and never computes, and the executor's answer-affecting choices
are already governed by proof (PAR-0005) or measurement plus a record
(PAR-0012).

**A property of the input rides with the source.** v1's cache key must
fold in `clip_provenance`: below lossless, a clip-derived and a
source-derived result are different measurements. Authored by nobody, it
is part of the source's identity inside the recipe hash — PAR-0009's to
carry.

## Consequences

- Acceptance amends `ARCHITECTURE.md` in the same commit: invariant 5
  gains the run-record bin and names the structural guard; its citation
  moves from Exchange 2 to PAR-0006.
- PAR-0007 carries the missing preference argument as a load-bearing
  absence, so a later signature change cannot restore it as a
  convenience.
- PAR-0009 receives: the hash covers the tool's params, the chosen op's
  identity, and that op's params — never the machine-local selection
  (`Opaque` stays the stated exception); source identity folds in input
  provenance; and the run record holding selection, seed, and bake is
  its to design. The earlier "hash over effective params" rule is gone,
  dissolved rather than obeyed: with method knobs on methods, no inert
  field survives to be excluded.
- PAR-0013 owns the GUI face: every control binds to a param field or to
  the settings object; the pane a control sits in is never the
  discriminator.
- The conformance suite gains the preference-scramble test;
  enforcement's home is PAR-0017's. A single settings home is that
  test's precondition; where it lives is the layout's question.
- Reclassifying a field later is deliberately expensive — a schema
  migration plus a changed hash for every affected result. An
  architecture act, not routine work.

## Challenges

*Agent-raised, none human-confirmed yet (PAR-0001: friction is stated,
never inferred).*

- **2026-08-03 — half the guarantee rests on a stub.** The run record
  exists today as a citation to PAR-0009, which is undrafted. The file
  half is enforceable now; the provenance half is an intention.
- **2026-08-03 — the scramble test detects reachability, not intent.**
  It catches a preference that reaches the op graph. It cannot catch a
  genuine param the author hard-coded as a constant and never exposed;
  the constant is not a knob to classify.
- **2026-08-03 — "provably unable to matter" is verified only at the
  tool boundary.** That a cache size or prefetch depth cannot perturb an
  executor result is a property of the executor's construction, claimed
  rather than tested.
