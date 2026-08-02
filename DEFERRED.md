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
  with Pydantic as one consumer. Due when: the first real contract code (the
  pipeline file format or the Tool base, per docs/PLAN.md "After this plan").
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
- **How a tool declares what it consumes** — Exchange 1's example declares
  `consumes`/`produces`; Exchange 5's rebuilt one-file example drops them;
  Exchange 7 makes eligibility a dispatch-table query. Three partial
  answers, no settlement, and ARCHITECTURE.md cannot arbitrate. Also
  unpinned: how a second input enters the shape signatures (background
  subtraction consumes frame + plate; Exchange 4 treats it as `Fold`). Due
  when: the Tool base's first real code (`src/sieve/tools/base.py`), where
  both first bite.
