# SIEVE Architecture

This is the settled design. It is normative: if code disagrees with this document, one
of the two is wrong and the disagreement gets resolved before more code lands on top of it.

Companion documents: [CONTRACTS.md](CONTRACTS.md) for the normative record shapes and how
they change; [EQUIVALENCE.md](EQUIVALENCE.md) for signatures and the statistics;
[REPO-LAYOUT.md](REPO-LAYOUT.md) for the tree and import rules;
[DERIVATIONS.md](DERIVATIONS.md) for why it is this and not something else, including the
designs that were considered and rejected.

## The one-paragraph version

The user builds a **pipeline**: an ordered, possibly incomplete DAG of **steps**. A step is
a pure declaration — parameters, a config panel, a request for something to display, and a
set of named typed **offers** it publishes downstream. Steps contain no compute. The
**executor** compiles the pipeline into a DAG of typed **intents** and covers that DAG with
**providers** drawn from the **kernel**. A provider may implement a single intent or a
connected *span* of several; the span providers are the fast paths. Because every single
intent always has a provider, a cover always exists, so the slow path is never crippled;
because span providers are just providers, adding a fast path is adding one file and
changing nothing else. Which cover the executor picks is decided by measured cost, and
whether it is *allowed* to pick a cheaper cover is decided by the **equivalence registry**,
which records statistically verified equivalence between providers against reference inputs
under a declared probe.

## Layers and the direction of dependency

```
kernel  ←  executor  ←  step  ←  pipeline  ←  gui
```

Dependencies point left and never right. Nothing imports back up the chain. This is checked
in CI, not by review (see [REPO-LAYOUT.md](REPO-LAYOUT.md)).

**Kernel.** The closed vocabulary of typed intermediates and the providers that compute
them. Frames, intensity fields, change energy, appearance energy, motion fields, masks,
regions, tracks, scalar series — the list is short, deliberately, and grows only by
deliberate act. A provider is a declaration (`implements` an intent shape, `eligible` input
types, output type, parameter schema, sensitivity class, measured cost) plus a function.
The kernel knows nothing about pipelines, steps, files, or the GUI.

**Executor.** Two verbs, and it owns both:

- `resolve(request) -> Plan` — expand the pipeline into an intent DAG, cover it with
  providers, pick the minimum-cost admissible cover, decide what gets materialized.
- `realize(plan, scope) -> Result` — run it. `scope` is what makes preview and commit the
  same code path: the left panel asks for one frame at time *t*; the run button asks for
  the whole clip with materialization on.

**Step.** A declaration with four parts and no compute: a parameter schema, a config panel
(the right side of the GUI), a *view request* (what the left side should show, expressed as
an intent, not as pixels), and its offers. Steps ask the executor for things by typed
intent. A step never names a provider and never calls the kernel.

**Pipeline.** The persisted file. It owns the user's chosen steps, their parameters, and
the bindings between one step's offers and the next step's input ports. Incomplete is a
valid state — validity is *computed on load*, never enforced at write time, and every node
reports `ready` or `blocked(reasons)` where the reasons are what the GUI shows the user.

**GUI.** A two-panel shell that knows nothing about any specific step. Left is the result
of configuration: a project viewer or a video surface with overlay layers, driven entirely
by whatever view request the active step handed it. Right is the configuration: a host that
mounts the step's own panel. The GUI has never heard of a crop.

## The step contract

All steps do exactly the same three things — declare parameters, request a view, publish
offers — and the variation between them lives entirely in *what they request*, not in what
they are. This is why naming them was hard while compute lived in them and stopped being
hard once it didn't.

Each **offer** is a named, typed value with a delivery mode. `information` offers are cheap
and inherited freely — a crop's coordinates, a downsample ratio. `artifact` offers are
materialized media the executor writes to disk. The crop step publishes both: the boxes as
information, and optionally the cut clips as artifacts. Downstream steps declare which
delivery modes and which types they accept on each input port; if several offers qualify,
the user picks, and can swap later. Binding is by offer, never by step identity, which is
what keeps steps from knowing about each other.

Overlay interaction runs the same way in reverse. A step declares overlay layers (a
rectangle tool, a polygon tool, a point set) and a mapping from overlay edits back into its
parameter schema. The video surface knows how to draw rectangles; it does not know that
these particular rectangles mean *crop*.

## Program versus expansion, and navigation

The user edits a **program**: the ordered DAG of step kinds and their parameters. The
executor **expands** the program over fan-out into instances. Crop publishes six replicate
offers; downsample then has six instances, one per replicate, sharing the program-level
parameters. An instance may carry a parameter *override* — that is how one replicate gets a
different downsample ratio without forking the program.

Navigation falls straight out of that. Up and down move between program depths. Left and
right move between siblings at the same depth, which are exactly the instances of that
expansion. Descending to a new depth lists only the instances whose requirements are
satisfied; the rest are shown as `blocked` with their reasons. A step sees nothing but what
it is given.

## Planning: cover, not sequence

The pipeline says *what*; the plan says *how*, and they are allowed to disagree in shape.
Never fold one step into another for performance. The logical vocabulary is chosen for the
user; the physical grouping is chosen by the planner. If you ever feel pressure to merge
crop and downsample into one step, the planner is missing a fusion rule, and that is where
the fix goes.

Concretely: `resolve` lowers the expanded pipeline into a DAG of intents — typed,
parameterized requests like *"decimated intensity field at 2 Hz over region R"*. It then
covers that DAG with providers. A single-intent provider covers one node. A **span
provider** covers a connected sub-DAG: one that reads only the ROI and decimates during
decode covers the crop and downsample intents together, and captures the saving that
belongs to neither of them alone.

Cover selection is a min-cost cover over the intent DAG, using measured provider costs
(from the same benchmark that produces signatures — declared costs are measured, not
guessed). This is the operation that a naive per-step dynamic program cannot express,
because the saving is a property of the span and a per-step table has nowhere to put it.

Three properties hold by construction and they are what stop the combinatorial explosion
from ever becoming a code problem:

1. **A cover always exists.** Every intent has at least one single-intent provider. The
   slow path is the floor and can never be removed by adding fast paths.
2. **Reachability is free.** Composition is total over the closed vocabulary of
   intermediates, so any type-correct chain is expressible without anyone writing it. You
   enumerate types and providers; combinations are *found*, not authored.
3. **Tractability is free.** Planning is demand-driven. Only the path a user actually built
   is ever planned. The space is combinatorial; the work is linear in what was asked for.

The useful region of that space is small and clustered — a handful of intermediate
representations recur across nearly every real pipeline. Fast paths get written for the
head of that distribution, discovered from real plans rather than predicted in advance.

## Substitution and the equivalence registry

A cheaper cover is usually not a *bit-identical* cover. Box-filter decimation is not
Lanczos decimation. The executor is therefore only permitted to substitute a provider for
another when the registry holds a verified equivalence claim covering that substitution.

An equivalence record is `(provider_a, provider_b, probe, reference_set, statistic,
margin τ, verdict, commit)`. Equivalence is always *relative to a probe* — a downstream
use — never absolute. "One frame per three minutes is equivalent to 30 fps" is false in
general and true for a specific detector at a specific threshold, and the record says
which. Verdicts come from an equivalence test (TOST or a bootstrap CI on the difference
contained within ±τ), never from failing to reject a difference; a p-value above 0.05 is
not evidence of sameness.

Tolerance does not compose through everything, so every provider declares a **sensitivity
class**. `contractive` and `stable` providers let tolerance compose along a span
automatically. A `sensitive` provider — anything with a discrete decision or history
dependence: thresholds, argmax, trackers — is a **barrier**: substitutions upstream of it
must be verified end-to-end *through* it at the plan's terminal output, not link by link.
That one flag is the whole answer to error composition, and it is checkable.

The same machinery is a user-facing feature, and this is the part that changes what SIEVE
is for. The user can supply their own discriminator as the probe and ask the registry which
cheaper path is equivalent *for their question*. When frame decimation to one frame per
three minutes turns out to be statistically equivalent to 30 fps once the channel
discriminator has run, a six-month recording study becomes tractable. The tooling that
picks the executor's defaults and the tooling that finds that result are the same tooling.

Signatures are also baselines. A provider's recorded output statistics on the reference set
are content-addressed and committed, so rewriting a provider is automatically compared
against its own past self out of git history. Details, including reference-set curation and
multiple-comparison discipline, are in [EQUIVALENCE.md](EQUIVALENCE.md).

## Adding things

Adding a **kernel capability** is one provider file plus its signature record. Every
existing step that requests a compatible intent can use it immediately; no step is edited.

Adding a **fast path** is one span provider plus an equivalence claim. If the claim fails
verification, the provider is simply never selected, and nothing else breaks.

Adding a **step** is one package: parameter schema, panel, view request, offers. It touches
no other step, no GUI code, and no kernel code.

Adding a **contract field** is additive within a major version. Removing or changing one is
a major bump with a migration; see [CONTRACTS.md](CONTRACTS.md).

## Build order

The crop step is the milestone that proves the contract, and downsample is the milestone
that proves fusion. In order: kernel types and the provider registry; executor `resolve` and
`realize` with single-intent covers only; pipeline model, load/save, and validity; the GUI
shell with the project viewer and video surface; the crop step end to end. Then the
equivalence harness and reference set, then downsample, then the crop+downsample span
provider — which should require no edit to either step. If it does, the boundary is wrong,
and that is worth stopping for.

## Open decisions

Deliberately unsettled, and to be recorded here when they are settled:

- GUI toolkit. The shell is small and the step panels are the bulk of the UI surface, so the
  choice is load-bearing for whoever writes steps. Needs an owner.
- Decode/IO backend and whether ROI-aware decode is available, which determines whether the
  first fast path is real.
- The initial contents of the intermediate type vocabulary. Start minimal; every addition is
  a deliberate act, because this vocabulary is what makes composition total.
- Reference set composition and where the media lives.
