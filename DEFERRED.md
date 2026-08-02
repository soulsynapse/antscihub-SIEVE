# DEFERRED — not-yet-due intentions (hand-authored)

Type-2 debt: things intended to exist, recorded with the trigger that makes
them due. Nothing here is presently owed; building from this file goes
poorly, which is why it is kept apart from DEBT.md. When a trigger fires,
the item moves: a decision gets made, or a placeholder enters the tree and
the automatic ledger.

- **The measured-equivalence harness** (ARCHITECTURE.md invariant 4; the §8
  EDIT in DESIGN-BRIEF.md stays recorded as the steelman alternative). Due
  when: the first second implementation of any op — also the moment the
  EDIT's lopsided-usage bet becomes testable against evidence. Rider
  (DESIGN-SESSION.md Exchange 8, objection 4): seed recording for stochastic
  methods lands with the harness — reproducibility of a published result is
  a separate requirement from equivalence testing and must not be dropped
  because the discriminator is statistical.
- **Reference corpus composition and per-signature tolerance policy**
  (DESIGN-SESSION.md, Open). Due when: the first second implementation of
  any op, which is what first needs equivalence measured. Rider (Exchange 8,
  resolution 2): the multiple-comparisons safeguard — discover a reduction
  on a pilot subset, confirm on held-out footage, report how many
  configurations were tested and both results — is built into the
  user-facing equivalence tooling, not offered as advice; the session record
  says "build in the safeguard or it won't happen."
- **GUI in-process with the executor, or separate** — if separate, the step
  declaration is also a wire format, pushing toward JSON Schema as canonical
  with Pydantic as one consumer. Due when: the Tool base's first real code
  (`src/sieve/tools/base.py`), where the canonical form of the `Params`
  declaration first becomes executable.
- **Eligible-step picker: a mode, or its own keys** — left/right already
  means siblings (DESIGN-SESSION.md, Open). Due when: the GUI's
  step-insertion flow is built.
- **Per-branch parameter override UI** — the exception is confirmed; marking
  and display are undesigned (DESIGN-SESSION.md, Open). Due when: the
  pipeline-tree view first displays overridable params.
- **Port-binding UI for multi-input tools** — type matching narrows
  candidates but won't reach one (DESIGN-SESSION.md, Open). Due when: after
  crop lands; named there as the next real UI question.
- **Trigger conditions as tests** — several triggers above are mechanically
  queryable against the tree; the prose-to-test move is named in
  docs/PLAN.md "After this plan" so it is not later invented as novel. Due
  when: a trigger is missed in practice, or queryable triggers accumulate
  enough that prose checking is error-prone.
- **`sweep(node, range)`** — the executor's sequential entry point
  (ARCHITECTURE.md "The executor"; DESIGN-SESSION.md Exchange 4). Crop is
  `Resample`-shaped end to end, so the milestone reaches only `render`. Due
  when: the first `Fold`-shaped op — adaptive background or tracking.
- **Fusion and the peephole rules** — crop alone is one op; nothing
  composes (DESIGN-SESSION.md Exchanges 3 and 6). Due when: the first
  two-op chain — downsampling landing, named in the session record as the
  first real test of whether steps compose.
- **Executor instrumentation and the cost surface** — log which pipelines
  get built and wall-clock per node from the executor's first real code
  (Exchange 6, condition 1: the evidence can't be reconstructed later). The
  queryable performance model — "how long will this take," including bake
  advice at bottleneck nodes — hangs off this; whether SIEVE volunteers the
  advice or answers when asked is undesigned and is decided when this comes
  due. Due when: the executor's first real code.
- **How a tool participates in dispatch-derived eligibility** — Exchange 7
  settles the rule: a tool is eligible when an applicable method exists for
  the argument value types, so the dispatch table is the eligibility check.
  What it does not settle is the bridge from a Tool to that table: Exchange
  5's rebuilt `lower(self, p)` exposes neither the consumed input types nor
  the requested generic function, while Exchange 1's earlier example had
  explicit `consumes`/`produces` declarations. Due when: the Tool base's
  first real code (`src/sieve/tools/base.py`), where that bridge must become
  executable.
- **How multiple inputs enter the shape signatures** — background
  subtraction consumes frame + plate, while Exchange 4 treats it as `Fold`;
  the settled unary-looking shape signatures do not say how the second input
  enters. Due when: the five-shape vocabulary's first real code
  (`src/sieve/kernel.py`), when those signatures become executable.
- **The dispatch table's home** — DESIGN-SESSION.md Exchange 7 settles the
  mechanism (multiple dispatch over the reified op description, with the
  table doubling as the eligibility check) and Exchange 8 amends selection
  to measured cost, but no record places the generic-function table itself
  as executable machinery or names what first makes it real. Due when:
  the first second implementation of any op (selection first has a choice
  to make — the harness's trigger), or the GUI's step-insertion flow
  (eligibility is a query against the dispatch table, ARCHITECTURE.md
  "Building a pipeline") — whichever fires first.
- **A field-type vocabulary home, mirroring `views.py`** — Exchange 1 makes
  field types a first-class reusable asset (the renderer learns one once;
  every future tool uses it), and the docs/PLAN.md Phase 3 layout
  settlement gave the view vocabulary its own module as the tool↔GUI
  boundary language. Field types are the identical argument on the right
  pane — a tool's `Params` names them, the GUI walks them — but their only
  current home is inside `gui.py`'s marker scope, and a tool importing its
  field type from the GUI module would couple in the forbidden direction.
  Due when: the first `Params` field type the generic renderer cannot
  derive from Pydantic primitives — the ROI Rect, i.e. crop's cycle
  (docs/PLAN-TOOL-CONTRACT.md "After this plan" already assigns those
  fields' design there; this entry adds the placement question).
- **Within-record authority for `DESIGN-SESSION.md`** — the authority line
  makes the session record govern other documents, but nothing states what
  governs within it when exchanges disagree (Exchange 1's `consumes`
  example vs. Exchange 5's rebuilt `lower()` — an ambiguity that already
  cost the eligibility-bridge entry above). De facto rule to be recorded:
  later exchanges supersede earlier ones, and "Where things stand" is the
  session's own settlement. Due when: `DESIGN-SESSION.md` is next amended
  for any other reason — the rule lands as one preamble sentence in that
  same change, rather than amending the authoritative record solely for
  this.
- **How frozen planning documents remain discoverable** — plans currently
  freeze under stable names, preserving their load-bearing pointers. Moving
  them into `docs/frozen/` would encode lifecycle status as a manually
  maintained location and break existing pointers; adding an index naming
  the live plan would duplicate status already declared by the plans
  themselves. Keep the flat named layout until this question becomes due.
  Due when: `docs/PLAN-TOOL-CONTRACT.md` freezes as the second frozen planning
  document, when the current layout first needs reassessment.
