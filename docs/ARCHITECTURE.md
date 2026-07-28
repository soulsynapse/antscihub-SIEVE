---
reviewed: d6e7a46
subjects: [src/sieve/, .importlinter, noxfile.py]
---

# SIEVE — Minimal Architecture Reference

SIEVE is a video signal-processing tool built around one question: how much economy can the user buy back without losing signal? The architecture serves the ability to answer that question interactively for a representative clip, then execute the answer over the full dataset locally or on HPC.

This tool's value is first measured in speed. Speed has two distinct regimes, and both are load-bearing:

Pre-pipeline speed — from opening a video to having replicates cut and a clip selected. The intended feel is a video editor rather than a distributed system.

In-pipeline speed — from dragging a slider to seeing the graph update. The intended feel is direct manipulation rather than job submission.

Its output is a scientific claim, which is the constraint that separates SIEVE from a fast video toy: a number it renders will be read as a measurement, so a wrong answer that looks like a right one is the most expensive thing this system can produce. Rule 6 is that constraint written down.

## The objectives, and how a rule relates to them

Every binding rule below is a *proxy* — a crisp, checkable stand-in for one of
four objectives. Proxies are what make enforcement possible, and Goodhart's law
is what makes them eventually wrong: a proxy will someday fire in a case where
the objective it serves is not actually threatened. So each rule carries three
parts: the **directive** (checkable, enforced), the **objective** it was
derived from, and its **falsifier** — the pre-stated condition under which the
directive stops serving the objective and the correct response is to *revise
the rule, not obey it*. Revision through the falsifier is the legitimate,
pre-authorized path; obeying a rule into absurdity is a defect, and so is
violating one without touching its falsifier.

- **O1 — The loop feels direct.** Tuning is the product; a slider drag answers
  like direct manipulation, not job submission. The budgets are this
  objective's proxies, anchored to the perceptual response bands (~0.1 s reads
  as instantaneous, ~1 s holds the flow of thought, ~10 s holds attention;
  Card, Moran & Newell) and *scoped to the reference workload* — see the
  budget table's scope note.
- **O2 — The output is a scientific claim.** A wrong answer that looks right
  is the most expensive thing the system can produce. **O2 outranks O1
  unconditionally: speed is never bought with a lie.** Under overload, O1's
  demand becomes honesty about slowness, not speed.
- **O3 — One artifact, every front end.** A saved project runs identically
  under GUI, CLI, and HPC because there is nothing else it could do.
- **O4 — The repo stays drivable.** Small binding surface, docs as evidence
  rather than law, completion as a move. The doc rules in `CLAUDE.md` serve
  this one.

O1 is the objective being *optimized*; O2 through O4 are satisficing
constraints — met, not maximized (this is the standard resolution for multiple
objectives: constrain all but one). When two rules collide, the objectives
adjudicate, and the ranking above is the whole precedence order.

## Layer Diagram

```
┌───────────────────────────────────────┐
│  gui/          cli/                   │  UI (Qt / terminal)
├───────────────────────────────────────┤
│  bench/                               │  Budgets and the metric bus
├───────────────────────────────────────┤
│  pipeline/    (workers/)              │  Orchestration (DAG, executor, cache)
├───────────────────────────────────────┤
│  filters/                             │  Filter specs + their kernels
├───────────────────────────────────────┤
│  decode/   (storage/)   backend/      │  Decode / file I/O / device policy
├───────────────────────────────────────┤
│  core/      (types, filter contract)  │  Pure logic — no imports from above
└───────────────────────────────────────┘
```

Parenthesised packages do not exist yet. They are named here and declared in
`.importlinter` before their first commit, so the contract governs them on
arrival rather than being widened afterwards to accommodate them. `docs/SCAFFOLD.md`
lists them under **Projected**, and a test fails if one quietly lands without
the line moving.

The enforced consequences: `core/` imports nothing above it and no
Qt, Zarr, or subprocess. `pipeline/`, `bench/`, and `cli/` do not import Qt, so
headless and CLI runs can observe without a GUI toolkit — the QObject adapter
over the metric bus lives in `gui/`. This is the mechanism that makes CLI and
HPC parity real rather than aspirational; a violation is a product regression
rather than a style problem.

**`bench/` is drawn above `pipeline/` but does not depend on it, and the tier is
a prohibition rather than a dependency.** `sieve.bench` imports nothing from this
tree — only stdlib and its own two modules — so nothing observes from up there;
things below push into it. What the placement actually forbids is
`pipeline → bench`, which is why `pipeline/preview.py` receives an injected
`Measure` callable instead of importing the bus, and names its two budget keys as
string constants (`FIRST_FRAME_BUDGET`, `WHOLE_WINDOW_BUDGET`) rather than
referencing `BUDGETS`. That is the price of the tier, and it is a real one: it
reintroduces one layer down exactly the unchecked-key typo that `metrics.py`'s key
registry exists to prevent. It is paid rather than removed because instrumentation
that the instrumented layer must import is instrumentation that cannot be absent,
and `tests/bench/test_budget_producers.py` closes the hole from the other end by
failing on a budget with no producer *and* on a published key that is not a budget.

One thing this diagram implies that the linter does *not* yet check: that `gui/`
reaches `workers/` only through `pipeline/`. Because `pipeline/` and `(workers/)`
are siblings on one tier, the layers contract makes them mutually independent —
which forbids `pipeline → workers`, the very path the intent requires, and says
nothing about `gui → workers`, the one it forbids. Neither matters while
`workers/` does not exist, and both have to be settled in the commit that
creates it. Recorded in `docs/AUTO-GUARDRAILS.md` §1 as the open half of that
guardrail.

A filter is two things, and that split is what puts them on different tiers.
Its **spec** is data — id, semver, params model, declared I/O, warmup,
determinism, cost — and lives in `core/`, so a saved DAG loads and validates
structurally with no filters installed and no codec present. Its **kernels**
are code, one per backend, and live with the filter in `filters/`, free to
import `cv2` or `cupy`. `backend/` therefore holds device policy and
array-namespace helpers, never a filter's implementation: a new filter is one
module plus one markdown file, and if adding one required editing a shared
`cpu.py`, rule 3 would already be broken.

The rule is encoded as a machine-checked contract rather than
enforced by review.

---

## The Rules

Module docstrings and completed entries cite these as **"non-negotiable #N"**,
which is what they were called, and the numbers still point where they did — so
a grep for `non-negotiable #3` lands on rule 3 below. Only rule 1 changed
meaning; rules 6, 7, and 8 are new, and rule 6 has since widened — see its
section. Rule 8 is the old #1 returned to the table on 2026.07.28 under its own
number, with the writer that finally gives it instances.

These were written as five non-negotiables before the rewrite had run into
what it was describing. Revised 2026.07.27 against the code that exists. Two
things changed and the reasoning is worth keeping, because it is the test any
future rule has to pass:

- **A rule that governs no code path is not a rule.** The old #1, "filesystem is
  truth at rest", has never been true or false of anything: no sink writes, no
  materializer exists, `MemoryFrameStore` is a dict. It was stated as an enforced
  invariant and read as one. It is still a commitment, and it moved to
  *Commitments not yet in force* below, where its trigger lived — and the
  trigger fired on 2026.07.28, so it is back in the table as rule 8. The episode
  is kept because the demotion is what made the return meaningful: what came
  back is a rule with a code path and a test, not the sentence that sat here
  governing nothing for two weeks.
- **A rule with a standing documented exception is not a rule either.** The old
  #4, "no latency budget misses", is contradicted two sections down by the scrub
  budget, which is met *by degrading* and stands unmet whenever a user turns
  coarse mode off. The invariant that actually holds — and the one worth
  defending — is that a miss is always visible.

The slot numbers of 2, 3, and 5 are unchanged in meaning, because roughly
twenty-five module docstrings and completed entries cite them by number and
renumbering would silently repoint every one of those. Rule 1 is repurposed; it
had one dependent. Rule 6 is new. Rule 7 (added 2026.07.27, later the same day)
is the opposite motion from rule 1's demotion: rule 1's old meaning was stated
before anything enforced it, while rule 7 was enforced before anything named it —
the identity line was already load-bearing prose in `core/pipeline_model.py` and
already what `pipeline/cache_key.py` implements. Naming it is what lets future
work cite it instead of re-deriving it per feature.

|#|Rule|Meaning|
|---|---|---|
|1|One execution path|`pipeline/executor.execute` is the only thing that computes a frame. The GUI is a view over it, never a second implementation.|
|2|Pipeline is a data structure|Serializable DAG. No GUI-only state in the pipeline artifact. It is the *complete* input to rule 1's one path.|
|3|Filter = one module + one markdown|Discovery is automatic. No registration elsewhere.|
|4|Every budget has a producer, and a miss is visible|A budget nothing publishes is a number, not a ceiling. A miss is a defect unless the degradation that causes it is a user's explicit choice.|
|5|No consumer starves another|No consumer improves its latency at another's expense. Every path that can take more than one core, or a bounded slab of memory, declares its share. See *Dividing the machine*.|
|6|A result must never look better-founded than it is|Refuse rather than approximate. Absent must not render as zero, and an unexamined stretch must not render as a quiet one. The mirror direction: a control must never look more live than it is — an edit the system would discard or silently invalidate must be visibly inert.|
|7|Everything sits on one side of the identity line|A field either changes *what a result is* — then it is hashed — or only *where it lives and how fast it arrives* — then it is never hashed. Nothing straddles. `checkpoints` and `outputs` live on `Project`, off `Node`, for this reason.|
|8|Filesystem is truth at rest|What SIEVE writes reads back without SIEVE running, and a writer proves that by reading its own output back before it registers it. An artifact that cannot be verified is deleted, never recorded.|

### 1. One execution path

`pipeline/executor.execute` is the single loop. `cli/run_cmd.py`,
`cli/preview_cmd.py`, and the GUI's `PreviewRunner` all call it, the last through
`pipeline/preview.py`, which is a caching front end over the same function rather
than a second one. This is what makes HPC parity a property of the design instead
of a thing somebody has to keep re-establishing: there is no cluster executor to
diverge, because a cluster run is this function under a different front end.

**Enforced by:** partially. The layer contract keeps `gui/` above `pipeline/` and
`decode/` the only route to a frame, so a second execution path cannot be
assembled quietly out of the parts. What is *not* checked is output equality — no
test runs one project through the CLI and through the GUI and diffs the result.
That is `docs/AUTO-GUARDRAILS.md` §2's open half and the most valuable unwritten
check in this repo.

**Serves:** O3, and O2 through it — one implementation cannot disagree with
itself. **Wrong when:** keeping every front end on the one path forces the
executor to grow front-end concepts — a Qt type, a widget's notion of
progress — in its signature. That is the letter satisfied and the spirit
inverted: the fix is a front-end adapter over the unchanged loop, and if no
adapter can express the need, this rule is what gets redesigned, not quietly
bypassed.

### 2. Pipeline is a data structure

Schema v2, `core/pipeline_model.py`. Serializable, no GUI-only state, and the
complete input to rule 1 — which is the sense in which rules 1 and 2 are one idea
seen from two ends. Preferences are the counter-example that defines the boundary:
`proxy_width` is an assertion about *this machine's* decode budget and lives in
`QSettings`, because a project carrying it would be carrying a claim about
hardware it has never seen.

**Enforced by:** `tests/unit/test_pipeline_model.py`, for purity. See rule 1 for
the parity half.

**Serves:** O3. **Wrong when:** the same field keeps being proposed for the
artifact and rejected as GUI-only. Recurrence is the signal: either the field
is actually identity in disguise (rule 7 decides), or the artifact's boundary
is drawn through the middle of a real user concept and needs redrawing once,
deliberately — not widening one exception at a time.

### 3. Filter = one module + one markdown

`src/sieve/filters/<name>.py` plus `<name>.md`. Nothing enumerates filters;
`filters/__init__.py` is a `pkgutil` scan and a test AST-parses it to fail if it
ever names a filter module. Inside the module, `@register_filter` decorates the
params class — the one class a spec cannot be written without — and
`@kernel` / `@stateful_kernel` / `@merging_kernel` decorate the kernel functions.
The `FilterSpec` itself is constructed in `core/filter_registry.py`, never in
`filters/`.

**Enforced by:** `tests/unit/test_filter_discovery.py`. The strongest guardrail
here, and the only one that cannot be defeated by adding an import.

**The seam worth knowing:** `register_filter`'s signature is a hand-maintained
second copy of `FilterSpec`'s field list. It is correct today and one field
addition away from drifting silently.

**Serves:** O4 — adding capability must not require touching shared surface.
**Wrong when:** one-module-per-filter starts forcing copy-paste: a family of
filters sharing real logic that the module boundary makes them duplicate. The
fix is a shared helper *below* the filters (in `backend/` or `core/`) or a
package-per-filter form of the same discovery contract — the discovery stays,
the granularity moves.

### 4. Every budget has a producer, and a miss is visible

The table below is the ceilings. `bench/metrics.py` is where a span is published
and `Sample.over_ms` is computed against `BUDGETS[key]` on the way past, so a miss
is detectable by the bus rather than by a call site remembering to ask.

The rule is *not* "no misses", because the architecture already documents a
standing exception: the scrub budget is met by degrading to a coarse frame grid,
and a user may turn that off in Preferences, at which point the budget stands
unmet on that machine by explicit choice. That is a preference, not a silent
tradeoff, and a rule phrased to forbid it would be a rule everybody learns to
ignore. What must never happen is a ceiling nothing measures.

A miss can also be **in declared debt**: currently over budget, with the
`docs/todo/` item that repays it named in `budgets.py`'s `IN_DEBT`. The
benchmark gate then reports the miss (xfail, visibly) instead of failing on
it, which is what makes "temporarily slower while building toward faster"
expressible without teaching anyone to ignore the gate. A debt whose item file
no longer exists fails the suite — debt is borrowed against a repayment plan,
not against goodwill — and the runtime HUD never honors debt at all: a slow
session looks slow regardless of what the gate has agreed to tolerate.

**Enforced by:** `tests/bench/test_budget_table.py` pins the table below against
`bench/budgets.py` bidirectionally and character-exact.
`tests/bench/test_budget_producers.py` fails on a budget with no publisher unless
it is named in `budgets.py`'s `WITHOUT_PRODUCER`, which is the honest form of the
gap and is a list that only shrinks. Four of eleven are in it today. Only two
budgets are additionally *timed* in CI, by `tests/bench/test_perf_regression.py`.
`tests/bench/test_budget_debt.py` holds every debt to a real budget and a live
item.

**Serves:** O1 — the budgets are its proxies, and the anchor comments in
`budgets.py` record which perceptual band each number came from so the number
outlives the hardware that first met it. **Wrong when:** a miss arrives from
outside the promised scope (the reference workload — see the note under the
table), or from work already declared in debt. Both are the proxy diverging
from the objective, and the response is scoping or debt, never a silent
higher limit — and never a silent miss.

### 5. No consumer starves another

See *Dividing the machine*, which is the whole of it.

**Enforced by:** `gui/concurrency.py` declares the split — threads and bytes
both, since 2026.07.27 — and `tests/unit/test_concurrency.py` asserts the
thread sum leaves a core for the GUI thread and the byte floors plus the
reserve fit a 16 GB machine.
`chain_model.recompute` takes `workers` as a required argument so that a caller
cannot silently inherit every core — pyright is what checks that, which makes it
the one part of this rule enforced at the point a violation would be written
rather than by a test somebody has to think to run.

**Serves:** O1, in both regimes at once — the rule exists so neither speed is
bought with the other. **Wrong when:** the declared split leaves cores idle
while a user waits: a session with one consumer active still capped at its
share is the split failing the objective it serves. The revision is a split
that adapts to which consumers are live, not a consumer quietly taking more.

### 6. A result must never look better-founded than it is

This is the newest rule and the one with the least machinery, but it is not
aspirational: it names a discipline the code already keeps, which is why it is
worth stating rather than inventing. In every case so far the system has chosen to
refuse rather than to produce a plausible number.

- `pipeline/executor.py` raises `UnrunnableNodeError` on a node shape it cannot
  run — `Mode.WINDOWED`, `rate_changing`, more than one emitted stream — before
  any frame decodes, rather than running something adjacent.
- `cli/run_cmd.py` refuses a project that declares a `Sink` rather than running it
  and writing nothing.
- `cache_key.py` refuses to key a node it cannot key, and the whole subtree below
  drops out of the map rather than being served optimistically. "Slow and correct
  beats fast and occasionally wrong" is that module's asymmetry rule.
- `filters/temporal_baseline.py` exists so a threshold is denominated in a block's
  own null distribution rather than in the illumination of one lighting rig.
- `filters/downsample.py` offers no un-anti-aliased mode.

The rule reads in both directions (widened 2026.07.27). A *result* must not
claim more foundation than it has; a *control* must not claim more consequence
than it will be given. An editable parameter on a stage upstream of a
materialized artifact claims a tunability the system does not intend to honor —
the edit either silently invalidates the child or is silently ignored, and both
are this rule's failure arriving through an input instead of an output. So a
frozen stage must render frozen, and the rendering must bind behaviour: faded
means read-only, and unlocking is an explicit discard of what lies below.

And the standing obligations it creates, each recorded where the work is:

- A temporal decimator must carry its own anti-alias lowpass, because decimating
  without one folds high-frequency behaviour into the measured band and it arrives
  disguised as something slower. `docs/todo/kernel-protocol-beyond-one-frame.md`.
- Unexamined and examined-and-quiet must never render alike. That collapse — a
  false negative wearing the costume of a result — is named in
  `docs/todo/coverage-and-detection-lanes.md` as V1's standing failure, and it is inherited by three separate widgets that do not
  exist yet.
- A detection count that grows with clip length for no biological reason is a
  reproducibility bug that looks like a finding.
  `docs/todo/surrogate-calibration.md`.
- Faded must mean frozen. A dimmed stage whose parameters still accept edits is
  decoration wearing the costume of a state.
  `docs/todo/click-through-navigation.md`.

**Enforced by:** nothing mechanical, and it probably cannot be. It is a rule for
review and for design, and its value is that it gives the recurring objection one
name instead of being re-derived per widget.

**Serves:** O2, directly — this rule *is* O2 at the widget scale. **Wrong
when:** refusal makes the honest path so unusable that users route around
SIEVE to a tool with no honesty at all — rigor that drives the analysis to a
spreadsheet serves nothing. The revision is never silent approximation; it is
the approximate mode built openly, labeled as what it is, with the label
load-bearing (this rule's own mirror direction applied to the escape hatch).

### 7. Everything sits on one side of the identity line

`core/pipeline_model.py` states it: materializing an intermediate changes where
a result lives, never what it is. As a rule: every field in the artifact either
participates in what a result *is*, in which case it is hashed, or in where it
lives and how fast it arrives, in which case it must never be. `checkpoints` and
`outputs` live on `Project` keyed by node id rather than as flags on `Node`
precisely so a materialize bit never sits one refactor away from being hashed
with `params`. The HPC handoff depends on this — the wizard empties
`checkpoints` for a cluster and must not move a single cache key — and so does
the crop: "a materialized crop is a faster source for the same pixels" is
checkable rather than hopeful only because of this rule
(`docs/findings/2026.07.25-the-crop-belongs-in-the-graph.md`).

The consequence it will be cited for: anything the system *proposes* divides
along the same line. A suggestion to checkpoint a stage is result-preserving and
can be accepted casually mid-tuning — nothing invalidates. A suggestion to
insert a `rescale` changes what every downstream result is, partially discards
tuning already done, and is a decision about the analysis. A UI that presents
the two classes in one visual register violates rule 6 through rule 7.

**Enforced by:** structure more than test. The cache key derives from `Node`
plus the source and root replicate geometry (`pipeline/cache_key.py`);
`Project.checkpoints` is not an input to it, so hashing a checkpoint would
require moving a field across the schema, not forgetting a clause. What is *not*
checked: no test toggles a checkpoint and asserts every key survives. That test
is one function, and it would pin this rule the way `test_budget_table.py` pins
rule 4.

**Serves:** O2 and O3 — the cache can only be trusted, and the wizard can only
strip placement for a cluster, because the line is absolute. **Wrong when:** a
field appears that genuinely straddles — changes results *and* placement. None
is known, and the recorded near-misses (`checkpoints`, `backend_identity`)
both resolved by splitting. If a true straddler ever arrives, the field gets
split into its two halves; the line itself does not move.

### 8. Filesystem is truth at rest

Restored to the table 2026.07.28, by the commit that landed
`pipeline/materialize.py` and `storage/crop_writer.py` — the first writer this
repo has ever had. Until then this was a commitment with no instances, and it is
in the table now for exactly the reason it left: there is finally a code path it
governs, and one that can be violated.

What it means concretely, in the form the first writer establishes:

- **A written artifact is a source in its own right.** The replicate crop is
  FFV1 in Matroska, playable in anything, and SIEVE reopens it through the
  unchanged `VideoReader` with an identity derived from the file itself
  (`CropArtifact`). It is not a private cache format and it is not keyed under
  the thing it was cut from.
- **A writer verifies before it registers.** The read-back pass is not belt and
  braces: `docs/findings/2026.07.28-the-crop-artifact-is-ffv1.md` measured a
  *lossless* encoding whose pixels came back wrong on every frame through the
  reader that reads everything else, with the right shape and the right count.
  Nothing in a decode path catches that. So the writer holds a digest per fed
  frame, reads its own file, compares, and on a mismatch deletes the file and
  raises — which is rule 6 applied to the filesystem: a plausible artifact that
  lies is worse than no artifact.
- **What is at rest is location, never identity.** The record says where a file
  lives and what it was cut from; the identity that enters a key is computed
  from the file when it is opened. That keeps rule 7 clean and makes a replaced
  or truncated file change its own identity by construction.

**Enforced by:** `tests/integration/test_materialize.py`, which is the
verification pass turned against itself — it encodes deliberately wrong pixels
through the same path and asserts nothing is registered and nothing survives on
disk. What is *not* enforced is generality: one writer exists, and the rule will
be tested again by the general store, where "reads without SIEVE running" is a
harder claim for a chunked array than for a video file.

**Serves:** O3 and O1 — a cluster run and a next session both start from files
rather than from a live process, and the crop is what makes the second render of
a tuned arena cost 0.09 ms/frame instead of 9.93. **Wrong when:** the verify
pass becomes the dominant cost of writing, or a format arrives whose correct
read-back cannot be checked without a second full decode. The revision then is a
sampled verification declared as sampled, never a silent drop — this rule's own
second clause applied to itself.

---

## Commitments not yet in force

Real intentions that govern no code path today. They are here rather than in the
table above because a rule that cannot currently be violated cannot be relied on,
and stating one as an invariant is how three unbuilt checks read as done for two
weeks. Each has its trigger and reasoning in a `docs/todo/` item.

- **The general result store.** *Filesystem is truth at rest* left this list on
  2026.07.28 and is rule 8 above; what stayed behind is the half the first
  writer does not cover. No sink writes, `storage/zarr_store.py` does not exist,
  `zarr` is a declared dependency imported nowhere, and `MemoryFrameStore` is
  still an unbounded dict — so a *node's* output has no home on disk, only a
  replicate's crop does. During interactive tuning truth is supposed to live in
  memory, so this is not a violation; it is the second instance the rule is
  waiting for, and the thing it will be tested by is chunking, which needs a
  workload that can say what it is for. Reasoning and trigger:
  `docs/todo/materialization.md` and `docs/todo/click-through-navigation.md` —
  the latter holds the descent gesture through a *node's* output boundary, which
  has no writer until this exists.
- **GPU execution.** `backend/dispatch.py` carries a complete `Backend` type
  system, per-node backend selection, and `DEFAULT_PREFERENCE = (GPU, CPU)`. There
  are zero GPU kernels; every filter registers CPU. `runtime_available` is a
  `find_spec("cupy")` module-presence check, not a device probe. The machinery has
  a real cost today — `backend_identity` enters the cache key of every filter,
  since none claims `backend_agnostic` — for no current benefit.
- **Process isolation and HPC handoff.** Neither exists. There is no
  `multiprocessing`, no `subprocess`, no `workers/`, no `hpc/`; the whole HPC story
  today is a `--workers` flag. The architectural claim that survives is narrower
  than it sounds and is genuinely load-bearing: HPC is not a special path, because
  rules 1 and 2 mean a cluster run is the same executor over the same artifact.
  `hpc/handoff.py` is job-script generation, not a second engine.

---

## Two Speed Regimes

```
PRE-PIPELINE (feels like a video editor)
  Open file → first frame:        < 500 ms
  Scrub/seek → frame repaint:     < 100 ms
  Scrub release → exact frame:    < 250 ms
  Cut confirmed → ready:          < 200 ms

IN-PIPELINE (feels like direct manipulation)
  First filter → first graph tick: < 2 s
  Slider drag → preview repaint:   < 100 ms
  Slider drag → graph update:      < 200 ms
  Full preview render (5–10s clip): < 3 s
  Band drag → graphs repaint:      < 50 ms
  Knob settle → graphs rebuilt:    < 3 s
  Knob settle → graphs start filling: < 500 ms
```

**Scope: these ceilings are promised for the reference workload** — the
representative clip through a representative chain, which today means the
filter stack the wizard builds, not any graph a user can construct. This is
how service-level objectives are stated everywhere they work: a promise
conditioned on a workload, not a wish about all workloads. Outside the scope —
five stacked filters, a pathological source — the promise that survives is
O2's, not O1's: input never blocks, progress is visible, and a stale frame is
labeled stale. A miss *inside* the scope is a defect or a declared debt
(rule 4); a miss outside it is the scope clause doing its job, and widening
the scope is a decision about the product, made in this document, not
conceded one alarm at a time.

The two scrub budgets are a pair, and they are what makes rule 4's exception
principled rather than convenient. A random seek into 5.3K H.264 costs
~68 ms of which ~47 ms is the container seek itself — irreducible through
OpenCV, and slower still on a slower machine. So *during* a drag the player is
held to 100 ms by degrading rather than by decoding faster: when sustained
scrub latency exceeds the budget it snaps targets to a coarse time grid and
serves them from a frame cache, which is a cache hit and costs nothing. On
release the exact frame under the cursor is always decoded, and that is the
second budget. Coarse mode is user-visible and can be disabled in Preferences;
the budget then stands unmet on that machine by the user's explicit choice,
which is a preference, not a silent tradeoff.

---

## Dividing the machine

Rule 5 was written as a two-body rule — pre-pipeline against
in-pipeline — and stayed self-enforcing only while there were two things
competing for cores. There are three. The player decodes on a thread, the
preview decodes on a pool, and `gui/detector_worker.py` runs the Morlet
transform on a third to fill the graphs while a render is still in flight. The
two-body phrasing has no slot for the case that actually bites: a third
consumer starving *both* of the other two.

The old phrasing also could not catch the specific way it would have been
broken here. `scipy.fft` defaults to every core, so a derivation thread added
without thought takes the whole machine, and the symptom is not a failure but a
scrub that stutters — a pre-pipeline budget quietly bought with an in-pipeline
nicety, which is the exact trade rule 5 exists to forbid.

So the rule reads over consumers rather than over regimes, and the arithmetic
is declared in one place instead of argued in three comments.
`gui/concurrency.py` holds the split and `tests/unit/test_concurrency.py`
asserts the sum leaves the machine a core for the GUI thread. A fourth
consumer, or a raised constant, fails a test rather than degrading a budget
somebody measures three commits later.

**And a fourth consumer is exactly what the sum test could not see.** Until
2026.07.27, `gui/filter_tab.py` re-derived the detector *synchronously on the GUI
thread* on a frequency-band commit, calling `chain_model.recompute` without a
`workers` argument and so inheriting its `ALL_CORES` default — a full Morlet
transform over every core, beside the two decode pools, doing precisely what
`detector_worker.py` was built to prevent. The arithmetic in `concurrency.py` was
correct and described three consumers while four were running. The lesson is about
the shape of the guardrail rather than about the bug: a test that sums declared
constants can only ever check the declaration, so the fix was to delete the
default and make `workers` a required argument, moving enforcement from a test
that checks the sum to a type checker that checks each call. What remains open is
that this derivation still runs on the GUI thread at all; capping it at
`DETECTOR_WORKERS` restores the split but lengthens the stall it causes, and
routing it through `detector_worker.py` is the real fix.

**The byte column (2026.07.27).** The bandwidth finding showed that counting
threads misses resources that actually bind, and memory was the next one:
retention wanted a byte budget, eviction wanted a bound, render-fed playback
wanted a ring size, and each would have been a number in a different file,
wrong on most machines, and unaccountable in sum. So the rule's text is taken
at its word — a bounded slab of memory declares its share exactly as a pool
of cores does. `core/machine.py` reads the machine once (`available_memory`
reports the *allocation*: cgroup limit, then scheduler declaration, then
physical RAM — because exceeding a cgroup is an OOM kill, not a slowdown),
`gui/concurrency.py` holds the shares as fractions of the post-reserve budget
with declared floors, and the test asserts the floors fit a 16 GB machine.
The reserve is provisional until measured (`docs/todo/ledger-measurements.md`),
`MemoryFrameStore` is the named unbounded gap (`UNBOUNDED`, the same honest
form as `WITHOUT_PRODUCER`), and worker counts resolve at startup through
`resolve_worker_split`, degrading detector first on small allocations and
never scaling up on big ones — the four-worker wall is a bandwidth property,
not a core count. The ledger is a sum a test checks, never a runtime governor;
what to *keep* under a budget stays with the retention and eviction items.

`core/` deliberately holds none of this and defaults to every core.
A CLI run, a whole-clip pass, and a headless parity check on a cluster node
have nobody to leave room for, and a cap living in `core/` would throttle
precisely the runs that should saturate a node. Policy about sharing a machine
belongs to the process that is sharing one. The machine *readings* live in
`core/machine.py` so the CLI and HPC paths reach them headless — a reading is
not a policy; the shares declared against it are, and those stay here.

---

## Import Boundaries

- `core/` — no Qt, no Zarr, no subprocess, no imports from upper layers. Holds
  the filter *contract*, never a filter implementation, so it stays free of
  `cv2` and `cupy` without constraining what a kernel may call
- `pipeline/`, `bench/`, `cli/`, `decode/`, `filters/`, `backend/` — no Qt. CLI
  and HPC must run headless, and `cli/` needs saying separately because it sits
  on `gui/`'s tier, where the layers contract cannot reach it
- `core/`, `bench/`, `gui/`, `cli/` — no `cv2`
- `filters/` — one module per filter: spec plus its kernels, colocated. May
  import `cv2` and `cupy`; may not import `pipeline/` or anything above it
- `decode/` — the only package that may reach a *frame*. That is a narrower
  claim than "the only package that imports `cv2`", and the narrower one is the
  load-bearing one: a kernel calling `cv2.GaussianBlur` touches no container, no
  seek, and no decoder identity, whereas a second path to a frame is how decoder
  identity stops being one string and cache keys stop meaning anything. What
  keeps a filter's `cv2` honest instead is its declared spec version in the
  cache key plus `backend_agnostic = False`.

`.importlinter` is the machine-checked form of this list, contract by contract,
and it is the authority wherever the two disagree.

---

## Pipeline Model

- DAG (directed acyclic graph), not a linear list
- A linear chain is valid — it's just a degenerate DAG
- Schema v5. `Edge.port` names the input it feeds; one producer per port; a v1
  document still loads
- `Dag.order` is one topological order per document, not per traversal
- Materialization is user-initiated, never automatic per step. One kind exists:
  the replicate crop (`Project.crops`, rule 8). A *node's* output still has no
  home on disk — see *Commitments not yet in force*

### What a cache key is made of

Two digests, both BLAKE2b-256 and both seeded with `HASH_VERSION`.

`source_key` — the ancestor of every root — folds a source identity, the decoder
identity, and the replicate's ROI. `node_key` folds its upstream keys *bound to
their port names*, the node's `filter_id` and semver, its resolved params as
canonical JSON, and the backend identity unless the filter claims
`backend_agnostic`.

Two things about this are easy to get wrong from the outside:

**Upstream content is not hashed, and neither is the video.** A previous version
of this document claimed "cache keys include upstream content hashes". They do
not. Source identity is `path | st_size | st_mtime_ns`, because hashing the file
costs a full read of a multi-gigabyte video every time a project opens. Upstream
*keys* are folded in, so ancestry is covered transitively — but it bottoms out in
those three cheap facts, and the one way to be served stale is a file edited in
place preserving both size and mtime. `pipeline/cache_key.py` weighs both failure
directions in its docstring; that is the authority.

**Ports are in the digest, bound to their keys.** `a - b` and `b - a` are fed by
the same two upstream keys and are not the same computation. They are hashed as
sorted pairs, so edge declaration order still cannot move a key.

**Cacheable is narrower than deterministic.** `spec.cacheable` is
`deterministic and not stateful`. A stateful node's output depends on every frame
that preceded it, which a key over params and ancestry does not describe, so it is
not keyed at all — and its whole downstream subtree drops out of the key map with
it. All three stateful filters shipped today are therefore uncached. See
`docs/findings/2026.07.26-stateful-output-is-not-keyed-by-what-it-is.md` before
assuming a key could carry it.

### What the executor refuses

`_bind` walks the whole graph before any frame decodes and raises
`UnrunnableNodeError` for a node whose `mode` is not `Mode.STREAMING`, or that is
`rate_changing`, or that emits more than one stream. Multi-upstream is *not*
refused — it landed with `Edge.port` and `MergingKernel`, though no shipped filter
is one yet. The refusals are rule 6 in its cheapest form: the shapes are valid
graphs, and running them approximately would be worse than not running them.

### Warmup accumulates along the path, and does not sum

`warmup_frames` is denominated in a filter's own *input* frames, so a rate-changing
node between two others leaves them speaking different index spaces: five frames of
warmup behind a 10:1 decimator is fifty source frames, not five. The conversion at
one node is `core.input_warmup_frames`: `ceil(need / output_rate)` plus the node's
own warmup. There is exactly one implementation of it and two walks over it, which
is deliberate:

- `core.source_warmup_frames` folds it sink to root over a **single path**. This is
  the definition, and `tests/property/test_warmup.py` checks the other walk against
  it. Nothing in `src/` calls it at run time.
- `pipeline/plan.py`'s `_lead_in` is what actually runs: one backward pass over
  `Dag.order`, where a node's output requirement is the **maximum over its
  downstreams**. A DAG has more than one root-to-node path, and a diamond has
  exponentially many, so the path walk is the definition and the max walk is the
  implementation. They agree because `input_warmup_frames` is monotone
  non-decreasing in its argument — `ceil` and `+` both are — which is what makes
  the maximum over paths equal the maximum taken node by node.

The executor then requests `plan.decode_range` and discards everything before
`plan.span.start`. A plain sum compiles, runs, and under-warms every temporal
filter behind a decimator by the decimation factor, rendering a plausible frame
while doing it — which is rule 6's failure mode arriving through arithmetic.

---

## Extension Pattern

```
src/sieve/filters/
  my_filter.py      ← params class + @register_filter, one @kernel per backend
  my_filter.md      ← guidance doc (discovered automatically)
```

That's it. GUI, CLI, cache, and HPC discover it without changes elsewhere. A
filter with no GPU kernel is complete; the dispatcher falls back rather than
the filter branching.

Two declarations on the spec are easy to get wrong and expensive to fix later:

- **`deterministic`** means *same backend, same input, same output*. With
  `stateful` it governs whether the node may be cached at all — see *Cacheable is
  narrower than deterministic* above.
- **`backend_agnostic`** means the CPU and GPU kernels agree bit for bit. It
  governs whether backend identity leaves the cache key. It is false for
  essentially every float kernel — cuFFT and NumPy's FFT do not agree, and
  neither do two OpenCV SIMD paths — so it defaults to false, and claiming it
  requires an equivalence test. No filter claims it, and no such test or harness
  exists to support one.

An IIR filter's warmup is nominally infinite, so the number a filter declares
is a settled-to-within-epsilon choice, and its docstring says which epsilon.
