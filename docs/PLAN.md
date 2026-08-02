# Base-form conformance plan

Scope: take the repo from docs-only to conformed with `ARCHITECTURE.md` and the
design session — the state where crop work can land. Crop itself is out of
scope; it gets its own planning cycle after this completes.

This plan is a map, not a build authorization. Per the working loop, each item
inside a phase still gets proposed and confirmed individually before it is
built. Approving this plan settles the *sequence* and the *definition of done*,
nothing else.

Each phase carries its own gate: the decisions that block it, made at that
phase and not before. A phase does not start until its gate is cleared.

## The anti-bureaucracy invariant

Every hand-maintained record in this plan is either a decision or an
intention; everything derivable from the tree is derived. Anything expressible
as a marker goes in the tree; the hand-authored present-debt file is a last
resort. The moment any step requires a human to maintain a record the tree can
derive — a status field to update, a report to refresh, an exemption to
adjudicate — that is bureaucracy arriving, and it announces itself as exactly
that shape. Checked at the Phase 4 conformance pass like everything else, by
judgment rather than mechanically — deliberately, because a mechanical
bureaucracy-detector would itself be bureaucracy. This invariant is a review
criterion and claims to be nothing more.

---

## Phase 1 — Repo mechanics

**Gate (three decisions; all settled 2026-08-01):**

1. **Is the §8 EDIT in `DESIGN-BRIEF.md` live? — settled: no.** Form 1
   (verified statistical equivalence, the measured-equivalence registry) is
   the adopted architecture, as `ARCHITECTURE.md` and invariant 4 encode. The
   EDIT stays in the brief as a recorded alternative — a steelman of the
   interpreter/handshake approach, not a reversal. The harness's not-yet-due
   entry is worded **deferred-with-trigger** (trigger: the first second
   implementation of any op — which is also the moment the EDIT's
   lopsided-usage bet becomes testable against evidence).
2. **Invariant 1 wording — settled.** "Adding a feature touches one file" was
   false as written for new field types, new view layers, and schema
   migrations. Settled wording: **"Adding a tool writes one file.** Anything
   the tool needs that doesn't exist — a field type, a view, an executor
   offering — is declared, not reached for; building the missing capability
   is a separate change under its own contract. A tool that can't be written
   in one file means a declaration point is missing — stop and fix that,
   don't spread the tool." `ARCHITECTURE.md` was committed with the old
   wording ahead of this gate, so the reword lands as an amendment commit.
3. **Package name and layout — settled.** Import name `sieve`, distribution
   name `antscihub-sieve`, `src/` layout (`src/sieve/`). The `src/` split
   also fixes the Phase 2 enumeration domain physically: `src/sieve` and
   `tests/` are the roots, with no exclusion list to maintain.

The repo becomes a real Python project with nothing SIEVE-specific in it.

- `pyproject.toml` (name and layout per decision 3), Python 3.11 per the
  existing `.python-version`.
- A real `.gitignore`.
- The package importable; a `tests/` directory with an empty suite that runs.
- Amend `ARCHITECTURE.md` invariant 1 to the settled wording (both design-doc
  commits already happened in 5428fc9; only the reword remains).

Exit: editable install succeeds, `pytest` runs green on an empty suite, `git
status` clean, all four design docs tracked.

Explicitly **not** gated anywhere in this plan: whether the GUI is in-process
with the executor. That decision first bites when the first real contract code
is written, which is after this plan's endpoint. It stays in the not-yet-due
file with that trigger.

---

## Phase 2 — Debt infrastructure

**Gate (three decisions; all settled 2026-08-01):**

4. **Placeholder marker form — settled.** As narrowed earlier the same day: a
   real module at its real import path raising a SIEVE-specific exception,
   carrying **only signatures that are quotations from the settled record** —
   `lower`, `view`, `render`/`sweep`, the five shape signatures — never
   inventing one; where only behavior is settled (the store, GUI internals,
   the pipeline loader), the docstring points at the governing doc section
   instead of presenting an API surface. The remaining calls are now made.
   The exception is **`sieve.debt.Owed`** — the plan's own vocabulary,
   grep-distinctive, and deliberately not an `-Error` name because a marker
   is not a fault and should not pattern-match visually to real exceptions.
   **Marker form rule v1**, statically decidable:
   - Canonical import: `from sieve.debt import Owed`, module top level, no
     alias.
   - Canonical statement: `raise Owed("<reason>")` where the argument is
     exactly one static string literal (adjacent-literal concatenation folds
     at parse and is fine; f-strings are not literals and are out of form).
   - Exactly two canonical positions: (a) the sole statement of a function or
     method body after its optional docstring — the signature-quoting form;
     (b) the final statement of a module whose only executable top-level
     statements are the docstring, the canonical import, and the raise — the
     behavior-only form, which raises on import. A module is never both: a
     module-level raise would make quoted signatures unreachable. Class-body
     markers are not in v1; if the Phase 3 layout proposal needs them, that
     is an additive v2, recorded by the rule-version pin.
   - Ledger key per the canonical form below: (repo-relative POSIX path,
     qualified name — dotted qualname for callables, `<module>` for
     module-level), reason text as compared content.
   - Any raise of a name bound by the canonical import that fails the form —
     non-literal reason, non-canonical position, aliased binding — is an
     **enumeration error, never a skip**. Markers the AST cannot see fall to
     the adapter's membership check.
   - The reason string's internal shape (what is owed, pointer to the
     governing doc section) is a convention, not a grammar — the compared
     content is bytes either way, and a grammar here would be the
     anti-bureaucracy invariant tripping on itself.
5. **Debt files — settled.** `DEBT.md` (present, correct debt) and
   `DEFERRED.md` (not-yet-due intentions, each with its trigger), both at
   repo root — they sort adjacent in a root listing, and an agent lists the
   root first.
6. **Automatic ledger — settled: own file**, `DEBT-AUTO.txt` at repo root,
   `-text` in `.gitattributes`. Whole-file byte compare, no delimited-region
   integrity question, no mixed hand/machine authority in one file. Its
   internal format is a build item within this phase, not part of the gate.

The machinery that makes a placeholder count as a debt entry. This must exist
*before* any placeholder is placed, otherwise Phase 3 is just stubs.

**Build sequence (settled 2026-08-01).** Phase 2 is built as reviewed steps,
not one-shot — it is large, and each step below still gets its concrete
proposal (signatures, format, test cases) confirmed before code lands:

- [x] 1. `sieve.debt` with `Owed` — the exception class alone, real code;
      adds the exception module to the closed machinery list.
- [ ] 2. The enumerator — a library function taking a root path, walking
      `.py` files, AST-matching rule v1, returning canonical entries;
      unparseable files and form violations are enumeration errors. The
      single roots-and-exclusions definition lives here. Fixture-tree tests.
- [ ] 3. Ledger format and regen command — the versioned serializer to
      canonical bytes, the one-command write mode, `.gitattributes` with
      `DEBT-AUTO.txt -text`. The published-interface review of the phase.
- [ ] 4. Mismatch test and sentinel — fresh enumeration diffed against the
      checked-in bytes with entry-level failure output; the sentinel fixture
      the enumerator must always find.
- [ ] 5. Conftest adapter — `Owed` caught in the test tree becomes a skip
      carrying the reason; membership checked against a fresh per-session
      enumeration; a caught marker absent from it fails.
- [ ] 6. Seed `DEBT.md` and `DEFERRED.md` — present debt near-empty;
      deferred items migrated from the session's durable record and
      `DESIGN-SESSION.md`'s Open list, each with its trigger.
- [ ] 7. Exit — regen against the live tree: zero entries, sentinel found,
      suite green; the commit carries `DEBT-AUTO.txt` at its zero state.

Steps 3–5 are mutually independent; that order is by blast radius (the
format is the retrofit-expensive artifact).

- The two hand-authored debt files, created and seeded: the not-yet-due file
  receives the open items from the session's durable record — which dissolves
  into the file it seeds, completing the migration it exists to hold — and the
  "Open" list of `DESIGN-SESSION.md` (each with its trigger condition); the
  present-debt file starts empty or near-empty, because at this point almost nothing is
  built and therefore almost nothing is *presently owed*.
- The SIEVE placeholder exception and marker convention (per decision 4).
- The enumerator: a test that walks the tree, finds markers, and regenerates
  the automatic ledger (location per decision 6). Both the enumerator and the
  write mode take a root path, so tests run them against fixture trees rather
  than assuming the live repo; the default roots and exclusions are one
  definition consumed by both the test and the regen command. The enumeration
  domain is `.py` files under the enumerated roots. An unreadable or
  unparseable file under an enumerated root is an **enumeration error, never a
  skip** — parseability defined by the pinned interpreter — because a skipped
  file makes debt vanish while both the mismatch test and the sentinel stay
  blind to it.
- **Canonical form, part of the versioned rule:** repo-relative POSIX paths,
  entries sorted by path then qualified name, UTF-8, LF, the ledger marked
  `-text` in a `.gitattributes` created here, so git can never rewrite the
  bytes the mismatch check compares (on Windows, `core.autocrlf` otherwise reds the check on a
  clean clone). Entries are keyed by **(module path, qualified name)** — never
  line numbers, so edits above a marker can't churn its entry — with the
  reason text as compared content: a reworded reason renders as *changed*,
  which is real signal (the debt's statement moved, the debt didn't). A
  duplicate key is an enumeration error, never a silent merge — one marker per
  scope is the grain of "this scope is owed."
- **The ledger format is a published interface consumed by git history**, and
  inherits Exchange 1's file-format discipline wholesale: additive-only
  evolution, a removed name never reused, and the enumeration rule's version
  recorded in the ledger — so rule churn is distinguishable from debt
  movement. Same pinning requirement as equivalence signatures.
- **Enforcement (settled 2026-08-01; "free" was the heuristic):** the mismatch
  check is a test in the suite — enumerate, diff against the checked-in
  ledger, fail on mismatch — and regeneration is a separate one-command write
  mode (the test never mutates the repo). The failure output is the
  entry-level diff — added, removed, changed — so "stale ledger" and
  "unintended debt change" are distinguishable at the point of failure rather
  than laundered by a reflexive regen. No hook, no CI dependency; a stale
  ledger turns the suite red until regenerated, so the wrong thing is hard
  rather than discouraged. CI, if added later, inherits enforcement by running
  pytest. Residual gap, named rather than hidden: nothing physically blocks
  committing on a red suite — which matches the design's own bar (Exchange 6
  asks for hard, not impossible).
- **Pytest semantics (settled 2026-08-01):** test-tree placeholders raise the
  same marker exception as everything else — one syntax, one enumerator key. A
  small conftest adapter converts the marker exception into a pytest *skip*
  carrying the debt as its reason: the suite stays green and the debt is
  visible in the skip summary. The adapter also checks membership: a caught
  marker present in the enumeration skips; one absent from it **fails**, named
  as a marker the enumerator can't see. The membership check consults a
  **fresh enumeration**, computed once per test session — staleness is the
  mismatch test's alarm, form-nonconformance is the adapter's; one cause, one
  alarm. The static instrument (enumerator) and the dynamic one (adapter)
  thereby cross-verify — the sentinel guards against the enumerator dying, the
  membership check guards against markers raised in forms the enumerator can't
  see.
- **The sentinel fixture:** one known marker in a test-fixture directory that
  the enumerator must always find, failing the suite if it finds zero there.
  Without it, a dead enumerator regenerates an empty ledger and passes
  vacuously — "no debt" and "monitor broken" must be distinguishable.
- **The machinery class is closed and enumerated:** the `Owed` exception
  module, the enumerator + mismatch test, the regen command, the conftest
  adapter, and the sentinel fixture are real code from this phase — the debt machinery is never itself a
  placeholder, because it is what gives every placeholder its meaning.
  Membership is this list, not anyone's judgment that their code "is
  machinery"; extending the list is a placement decision that goes through the
  normal loop.

The broader architecture conformance suite (round-trip, migration corpus,
fused-vs-unfused property tests) is *not* built here; it gets a placeholder in
Phase 3 like any other not-yet-built component.

Exit: the enumerator runs against a fixture tree and the live tree, produces a
byte-deterministic automatic ledger, correctly reports zero placeholders in
the live tree with no fixture entries, and finds the sentinel — the zero state
and the instrument's liveness proven together, before anything depends on
either.

---

## Phase 3 — Skeleton conformance pass

**Classification rule (settled 2026-08-01):** a placeholder is type-1 present
debt iff the named next milestone reaches through it. Every other component
gets a type-2 not-yet-due entry with a trigger and **no file in the tree**.
The debt-creating event is the milestone declaration, not the file placement;
placement makes already-existing debt enumerable.

The named next milestone — crop landing *as a contracted step*, working
flawlessly — reaches seven components: a Tool with Params (crop itself),
`lower()` producing a `Resample` (kernel), the executor's render path, the
store, the pipeline file, the GUI's two panes with the ROI overlay, and the
conformance suite, reached by the word "contracted" itself — a crop that
hasn't passed the contract checks isn't a contracted step, so the milestone
cannot be evaluated without the suite any more than crop can run without the
executor. Those get placeholders. The **harness** is not reached — crop has one
implementation of everything and no equivalence question — so it gets a
not-yet-due entry (trigger: the first second implementation of any op) and no
file; decision 1 settled its wording as deferred-with-trigger.

Granularity call the layout proposal must make explicitly: crop reaches
`Resample` but not `Fold`, `Window`, `PixelMap`, or `Opaque`. Either the
five-shape algebra is one design unit (one settled closed contract whose
vocabulary arrives together) or it's `Resample` now and four not-yet-due
entries. Not decided here; decided visibly there.

Process: one repo-layout proposal first — every module path, in one document,
discussed once — because placing a placeholder is itself a decision that gets
talked about, and doing that per-file would be thirty conversations about
directory names. After the layout is agreed, placement is mechanical.

Each placeholder is a real module at its real import path raising the marker
exception, carrying a signature only where the settled record supplies one to
quote (decision 4's rule). No "authorized" fields, no metadata flags —
presence in the tree is the authorization, per the settled doctrine.

Exit: every crop-reachable component resolves to a location; the enumerator
finds exactly the placed markers; the automatic ledger is regenerated as the
last step before the commit and the commit carries it; the suite is green with
placeholder-skips exactly matching the ledger's test-tree entries.

---

## Phase 4 — README as map, and the conformance check

- README grows into the map: what each location is, which of the four docs
  governs it, where the debt files are and what each is for, how to read the
  automatic ledger — including the mismatch runbook: expected change, run the
  regen command; unexpected change, investigate before regenerating.
- Final pass against the definition of done below. Anything failing it is
  either fixed or entered as present debt — a repo that accurately states what
  it owes is conformed; a repo that silently misses a criterion is not.

**Definition of done** (this is the scope reading of "conform the entire repo";
approving this plan confirms it):

- [ ] Every component the crop milestone reaches has a location holding real
      code or a placeholder; every component it doesn't reach has a
      not-yet-due entry with a trigger and no file in the tree.
- [ ] Both hand-authored debt files exist and are populated from this pass.
- [ ] The automatic ledger exists, is generated, is checked in, and matches a
      fresh enumeration.
- [ ] `pyproject.toml`, real `.gitignore`, all design docs committed.
- [ ] README is the map.
- [ ] A tests location exists holding the (real) debt machinery and the
      (placeholder) conformance suite.
- [ ] The anti-bureaucracy invariant holds: no hand-maintained record
      duplicates anything derivable from the tree.

---

## After this plan

First real code — likely the pipeline file format or the Tool base — is a
separate planning cycle, and it is where the GUI in-process decision and the
Pydantic-vs-JSON-Schema canonicalization come due. Not before.

A seam noted and deliberately not built: several type-2 trigger conditions
("first second implementation of any op") are mechanically queryable against
the tree, so triggers could someday graduate from prose to test — the same
convention→test move as everything else here. Building that now would be
ceremony ahead of need; it is named so it isn't later invented as novel.

## Known risks

- **The automatic ledger is built at zero placeholders.** Justification:
  Phase 3's exit criterion needs the generator one phase later regardless, so
  deferral buys no calendar time; building it against the zero state means the
  instrument is trusted before it measures anything; and a marker convention
  without its enumerator is the convention-not-test state Exchange 6 forbids,
  entered at the first moment it matters. The retrofit-expensive artifacts are
  the marker convention and the ledger format — they live in git-history
  semantics, which is why the rule-version pin is in the format from the first
  generated ledger.
- **"Discussed once" layout proposal could still stall.** Phase 3's single
  layout conversation is the plan's main serialization point; if it fragments
  into per-directory debate the one-at-a-time loop becomes the bottleneck. The
  proposal must arrive complete enough to be judged whole.
