# DEFERRED — not-yet-due intentions (hand-authored)

Type-2 debt: things intended to exist, recorded with the trigger that makes
them due. Nothing here is presently owed; building from this file goes
poorly, which is why it is kept apart from DEBT.md. When a trigger fires,
the item moves: a decision gets made, or a placeholder enters the tree and
the automatic ledger.

- **The how-to runner** — scoped agent sessions spawned from a
  how-to's structured fields (plain-line convention): the commands, how
  to run them, the check, tightly scoped to the guide's content with no
  hand-crafted context (PAR-0003 "The runner"). Stakes, stated so this
  entry is not mistaken for a convenience: it is the how-to layer's
  verification story — a guide is a program whose interpreter is an
  agent, drift reds as a failed run, and run logs disambiguate
  quiet-under-use from quiet-from-neglect (PAR-0003's standing
  challenge). Due when: following an existing how-to by hand is a
  session's bottleneck — the utility bar the script heuristic already
  uses, applied at layer scale.
- **Marker rule v3 — the multi-marker text surface** — text files admit
  multiple `Owed:` markers, keyed `(path, stamp)`; stamps are already
  each entry's identity, globally unique, and survive rewording and
  relocation, so the stable-anchor argument that produced the
  one-per-file grain is satisfied without it (PAR-0003 Consequences;
  primary Exchange 5 for the grain's provenance). Ruled in
  conditionally — "fine as long as it all works." Scope when due:
  PAR-0002 rewritten whole and reviewed as a diff, `debt.py` and its
  tests, the ledger's pinned rule version, the "states one debt"
  wording in `README.md`/`AGENTS.md`, and `DEBT.md`'s second-entry
  tripwire restated. Due when: the first PAR outcome is judged mostly
  settled — the extension lands before the second simultaneous marker
  in `ARCHITECTURE.md` would red the suite.
- **How-to position hierarchy** — a stated logical nesting for the
  generated index, distinct from the alphabetical folder walk
  (PAR-0003 "The index"). Due when: the folder walk stops making sense
  as the read surface — a judgment, explicitly "if ever wanted."
- **The debt read layer** — `sieve.debt` read modes over the v2 ledger
  (PAR-0002 "The line, and the history" / "The planning surface"):
  list/show/log with derived columns — age and last-touched from ledger
  history by stamp (`stamp_landings` exists), restatement count,
  reference extraction — emitting the derived default order a planning
  session reorders. Nothing history-derived is ever written into the
  ledger. Due when: the first planning session over the ledger convenes
  (the dissolution in DEBT.md landing is its natural occasion), or a
  mismatch investigation first needs per-stamp history.
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
  says "build in the safeguard or it won't happen." Refined 2026-08-03
  (PAR-0005's primary, Exchange 9, and the session's closing exchange):
  the swap test relocates most of the corpus question, since for the
  decision actually being made the user's own footage is the corpus —
  what stays open is whether a result transfers to the next project,
  which needs footage characterized. Hand annotation as the selection
  target fixes the post-hoc-criterion half and converts the rest into
  ordinary model selection, so the safeguard's mechanized form is four
  things the affordance does rather than advises: score against a
  held-out split that played no part in selection, count and display
  the configurations tried in the session, resample at the bout level
  rather than the frame level (frames within a bout are autocorrelated,
  so frame-count intervals are far too narrow), and surface the
  annotation's own inter-annotator agreement as the ceiling. The
  distance metric is fixed before the search for the same reason the
  target is.
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
  docs/archive/PLAN.md "After this plan" so it is not later invented as novel. Due
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
  the unary-looking signatures of the retired five-form table do not say
  how the second input enters. Due when: the first stateful op is written
  — under PAR-0005's admission rule its form is admitted then, with the
  rewrite it licenses, and its signature is settled by the op that needs
  it (the `(state, frame)` arity was already known wrong on this case,
  PAR-0005's first primary, Exchange 2).
- **Further forms enter the kernel** — the kernel implements the affine
  coordinate map and `Opaque`; the retired five-form table's `PixelMap`,
  `Window`, and `Fold` survive here as the intended factoring for a
  contributor to aim at, and each is admitted under PAR-0005's rule —
  when a rewrite it would license is both wanted and provable — with
  its signature settled by the op that needs it, never in advance.
  Rider: a standalone spatial-neighborhood op (erosion on a mask, a
  spatial blur or gradient) fits none of the reasoned-about factorings
  and is an `Opaque` until measurement says it is worth a form of its
  own. Due when: an op of that kind is written, or instrumentation
  shows an `Opaque` on a hot path.
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
  every future tool uses it), and the docs/archive/PLAN.md Phase 3 layout
  settlement gave the view vocabulary its own module as the tool↔GUI
  boundary language. Field types are the identical argument on the right
  pane — a tool's `Params` names them, the GUI walks them — but their only
  current home is inside `gui.py`'s marker scope, and a tool importing its
  field type from the GUI module would couple in the forbidden direction.
  Due when: the first `Params` field type the generic renderer cannot
  derive from Pydantic primitives — the ROI Rect, i.e. crop's cycle
  (docs/PLAN-TOOL-CONTRACT.md "After this plan" already assigns those
  fields' design there; this entry adds the placement question).
