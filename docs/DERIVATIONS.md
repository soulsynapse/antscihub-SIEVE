# Derivations

Why the architecture is what it is, section by section against
[DESIGN-BRIEF.md](DESIGN-BRIEF.md), including the designs that were considered and
rejected. The rejected ones are recorded because they are the designs an agent will
re-derive if left to itself, and knowing they were already tried is worth more than any
amount of prose about the one that won.

A note on scope: the brief asked for a session transcript alongside this. That transcript
does not exist — the brief was preserved as questions only, with the intervening answers
deliberately removed, and no faithful record of them can be reconstructed. This document is
the substitute and serves the purpose the transcript was meant to serve: it carries the
reasoning, the dead ends, and the open risks rather than only the conclusions.

## §1 — Contracts that change without breaking

Contracts must change, so the design target is not stability but *cheap change*. Four moves
give that, and they are stated normatively in [CONTRACTS.md](CONTRACTS.md): version the
records and allow only additive change within a major; confine all version tolerance to a
migration chain at the load boundary so no other code branches on version; delete retired
features from the tree entirely, leaving one line in `RETIRED.md`; and enforce every
contract with a conformance suite parameterized over all implementers, so a contract change
breaks everything it affects at once, in one place, loudly.

That last point is the one that makes the rest work. A contract enforced by review degrades
silently. A contract enforced by a suite that every implementer is registered against
cannot: adding a required field turns the build red across every implementer, which is the
correct and desirable outcome.

The brief's concern about "old features anchoring agents as plausible paths" is a real and
underrated cost, and it is why deletion is a hard rule rather than a preference. Dead code
is worse than absent code in an agent-maintained repo, because it reads as live and consumes
the context budget that should have gone to the path that matters.

For partial work: a `# DEBT(id, due=<contract@major | milestone>)` marker at the site, plus
a conformance test that fails or is explicitly skipped against that id. The marker says what
the code cannot; it does not re-explain the code. Ratchets in `ratchets.toml` keep the
aggregate honest, and loosening one shows up in the diff with its reason.

## §2 — Naming the steps, and step ownership

The brief asks what to call the steps, noting that "what any given step does varies pretty
wildly." That variance was a symptom, not a fact about the domain. It exists only while
steps contain compute. Once a step is a pure declaration — parameter schema, config panel,
view request, offers — every step does the same three things, and the variation lives
entirely in *what it requests*. The naming problem dissolved rather than being solved, so
the name stayed **step**, which is what users already call it.

The GUI rule from the brief holds exactly as stated: left is the result of configuration,
right is the configuration. Implemented as a step declaring a *view request* (an intent, not
pixels) and *overlay layers* with a mapping from overlay edits back to parameters. The video
surface knows how to draw a rectangle; it does not know the rectangle means crop.

The one thing the brief left implicit and that had to be pinned down: the difference between
the **program** the user edits and its **expansion** into instances. The user sets crop
parameters once, producing six replicate offers; downsample then has six instances. Up and
down navigate the program, left and right navigate the expansion, and per-instance parameter
overrides let one replicate differ without forking the program. Without that distinction the
navigation described in the brief is not well defined.

Binding is by *offer*, never by upstream step identity. This is what makes "subsequent steps
don't know anything other than what they're given" true mechanically rather than by
convention.

## §3 — The name for the inefficiency

It is the **logical/physical split**, and specifically the fusion problem: the user's
decomposition is not the machine's decomposition, and the saving lives in the *join*, not
in either part. Crop and downsample fused into an ROI-aware decode that decimates during
decode is cheaper than either step is separately, and that saving is attributable to
neither.

Why it "resists basic DP construction," precisely: **cost is not additive over the user's
decomposition.** A per-step cost table has no cell in which to store a saving that belongs
to a pair. The fix is not a better per-step table but a change of unit — plan over *spans*
of the intent DAG rather than over steps, which is a min-cost cover problem and is what
query planners and compiler fusion passes have always done. The same family of ideas
appears as deforestation, loop fusion, and pipeline-breaking in databases.

The design consequence answers the brief's actual question directly: downsample is its own
step, always. Never merge steps for performance. The logical vocabulary is chosen for the
user, the physical grouping is chosen by the planner, and pressure to merge them means the
planner is missing a fusion rule. That is where the fix goes, and putting it there is what
stops the compounding the brief predicts at ten steps.

## §4–§6 — Ownership, and the explosion that never materializes

**Rejected:** the executor owning a table of hand-written combination handlers, and steps
knowing which downstream operations they can feed. Both are N² glue where every new feature
touches every old one, and the brief's rejection of it in §5 is correct: an agent writes
spaghetti here every time, and so does an experienced engineer under deadline. The failure
mode is not incompetence — it is that the design makes the local, reasonable move (add one
more handler) the one that degrades the whole.

**Settled**, matching §6: steps are derivative of the executor and the executor is coupled to
the kernel, so the dependency runs `kernel ← executor ← step`. Steps request by typed
intent, never by naming an implementation. A new kernel capability becomes an executor
offering, which becomes available to every existing step that already asks for a compatible
type, with no step edited.

On §6's question — why the explosion never materializes — there are two separate answers and
they should not be conflated:

*Reachability* is free because composition is total over a closed vocabulary of typed
intermediates. Any type-correct chain is expressible without anyone having written it. You
enumerate types and providers; combinations are found, not authored.

*Tractability* is free because planning is demand-driven. Only the path a user actually
built is ever planned. The space is combinatorial; the work is linear in what was asked for.

And most combinations go unused because the useful region is small and clustered — a handful
of intermediate representations recur across nearly every real pipeline. Fast paths are
written for the head of that distribution, discovered from real plans rather than predicted.
The brief's read is right that trying to optimize the whole space automatically is the road
to rebuilding a computer algebra system, and the reason that road is unnecessary is that
nobody ever asks for most of the space.

## §7–§8 — The unifying mechanism

The brief asks for the approach that bridges every boundary and captures the fast path
automatically without crippling the slow path. Two candidates were live:

1. **Equality saturation over a typed IR** — e-graphs plus cost extraction. Fast paths are
   rewrite rules, the slow path is the base term, and the extractor picks the cheapest
   member of an equivalence class. Powerful and exactly aimed at this problem, but it is a
   substantial machine to build and maintain, and it needs a source of equivalence
   relations, which it does not supply.
2. **Declared capability plus resolution** — everything declares requires/provides with a
   cost, and one resolver does all the wiring at every boundary. This is the build-system
   and trait-dispatch shape, and it is the one that generalizes across boundaries the way
   the brief wants.

The settled design is (2) collapsed to its minimum: **a fast path is simply a provider that
declares it implements a span of the plan.** No rewrite-rule system, no optimizer plugin
interface, no registry of combinations — a span provider is an ordinary provider with a
larger `implements`. Planning is a min-cost cover. Single-intent providers always exist, so
a cover always exists, so the slow path is structurally impossible to cripple. That gets
most of what (1) offers for a fraction of the machinery, and it keeps the extension story to
"add one file."

§8's verified statistical equivalence is not a third alternative — it is the missing piece
either mechanism needs. A cover is only sound if substituting one provider for another is
permitted, and in a signal-processing kernel almost no substitution is bit-identical.
Formal rewriting would demand proofs that do not exist. Measured equivalence against
reference inputs under a declared probe supplies exactly the relation that cover selection
needs, and it supplies it in the only form the domain admits. The brief's own framing —
declare what you compute and your eligible types, test against references, let the executor
rank by speed and work backwards — is the design, and it is right.

The brief's second candidate in §8, the interpreter/handshake approach where the fast path
self-validates because it exists, is the same shape as span-provider cover but without the
equivalence check, and the brief's own worry about it is correct: existence is not licence.
Cover selection needs a *verified* relation, not merely a declared one, or the first
approximate fast path silently changes results.

Two corrections to §8 as stated, both incorporated in [EQUIVALENCE.md](EQUIVALENCE.md).
First, equivalence must be tested with an equivalence test — TOST or a bootstrap CI within
±τ — not by failing to reject a difference; a p-value above 0.05 is evidence of a small
reference set at least as often as it is evidence of sameness, and this is the mistake an
agent will make by default. Second, equivalence must be recorded *per probe*, not per
provider pair, because these relations are relative to a downstream use and become false
when transplanted.

## §9 — The concerns, and where the risk actually sits

The brief's response to non-composing tolerance is right and is now a contract field. Errors
amplify only under sensitivity plus folding; blurs, decimations, and integrations are
contractive and shrink error; the providers that are not are known when written. So every
provider declares `contractive | stable | sensitive`, tolerance composes automatically along
the first two, and a `sensitive` provider is a barrier requiring end-to-end verification
through it. The honest caveat is that this is a *declared* classification and a mislabel
licenses unsound substitution, so the conformance suite should include a numerical
perturbation probe that checks measured Lipschitz behaviour against the declared class.

The dual-use observation in §9.2 is the most valuable idea in the brief and is now
first-class rather than incidental: the probe is a user-supplied object, so a user can ask
which cheap path is equivalent *for their discriminator*. The frame-decimation case — one
frame per three minutes matching 30 fps once the channel discriminator has run — is the
difference between a six-month study being run and not being run. One mechanism serves the
planner's defaults, the user's study design, and the kernel's regression tests.

Where the remaining risk actually sits, stated plainly: reference-set curation. Every claim
is exactly as trustworthy as the coverage of the set it was verified on, a set that omits a
regime will certify a fast path that fails in that regime, and no amount of statistical
machinery fixes that. This is manual scientific work and it does not get automated away.
Budget for it.

## §10 — Signatures as baselines

Correct, and free: a provider's signature on the reference set, committed and
content-addressed, is a regression baseline against the provider's own past self. Rewriting
an implementation is automatically compared against git history with no separate golden-file
scaffolding. Two uses of one artifact — equivalence between providers, and regression
against history.

## What the brief left undecided

The repo shape (proposed in [REPO-LAYOUT.md](REPO-LAYOUT.md)), the GUI toolkit, the
decode/IO backend and whether ROI-aware decode is actually available — which determines
whether the first fast path is real or hypothetical — the initial contents of the
intermediate type vocabulary, and the reference set. These are tracked in the open-decisions
section of [ARCHITECTURE.md](ARCHITECTURE.md) and should be moved out of it as they settle.

