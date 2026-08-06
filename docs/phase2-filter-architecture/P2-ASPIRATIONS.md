# SIEVE Aspirations

**Status:** Draft for review. Not yet authoritative. **Purpose:** Define the end state that all SIEVE development rules derive from. Where any other document conflicts with this one, this one wins or the conflict gets resolved explicitly (see §9). **Audience:** Anyone adding a filter, changing the shell, or planning work.

---

## 1. The invariant

> **Adding a filter is a self-contained act.** A new filter lives in one place, declares what it consumes and produces, and the rest of SIEVE absorbs it without being edited.

Everything below is either a restatement of this, a boundary on it, or a mechanism that enforces it.

The three-year test: SIEVE has ~30 filters. Someone adding the 31st inspects what existing filters offer as handoffs, writes their filter against those declared types, and ships it without opening a file outside their own filter's directory.

---

## 2. The boundary: free filters, deliberate views

This is the honest limit of the invariant, and it is accepted rather than worked around.

- **Free:** a filter with scalar, band, region, or otherwise already-typed parameters costs zero edits outside itself. Its settings surface, its graph validation, its cache behavior, and its catalog presence are all generated from its declaration.
- **Deliberate:** a filter that needs a _genuinely new kind of view_ — a new interactive editing modality, a new plot type, a new spatial interaction — requires a shell-level change. This is expected, is reviewed, and is rare.

The asymmetry is intentional. The first act happens a hundred times. The second happens a handful of times. Optimize accordingly.

---

## 3. Layers and their dependency direction

Dependencies point downward only. A violation is a bug, not a tradeoff.

|Layer|Owns|Must not know|
|---|---|---|
|**Contract**|Stream/element types, port declarations, semantic parameter types, temporal & cost class, compatibility relation|That filters or a GUI exist|
|**Filters**|Behavior, params model, spec, declared presentation intent, own param migrations|Other filters; any GUI module|
|**Graph**|Nodes, typed edges, validation, compatibility queries, cache keys, serialization, migration dispatch|Which filters exist|
|**Shell**|Presentation slots, focus, playback clock, arbitration, layout, failure containment|Filter identities|
|**Editors**|Widgets keyed on semantic param type|Which filter requested them|

**Corollary that matters most:** the question _"what can attach here?"_ is answered by the **graph** layer, from declared specs alone. The shell asks; it never computes. Any private type vocabulary inside the GUI is a symptom that the contract layer failed to answer a question the shell needed — fix the contract, don't relocate the vocabulary.

---

## 4. Rules, in testable form

Each rule states the mechanism that catches its violation. A rule without enforcement is an aspiration that will decay.

**R1 — One filter, one directory.** A filter's behavior, params model, spec, presentation declaration, and params migrations live together. _Enforced by:_ the canary test (§7).

**R2 — No filter identity outside `filters/`.** No module outside `filters/` may branch on, enumerate, or string-match a filter ID. _Enforced by:_ a static check for filter-ID literals outside `filters/`; allow-list entries require a written justification satisfying R7.

**R3 — Nothing enumerates filters.** Catalogs, menus, wizards, and validators derive their contents from the registry. Hand-written lists of offerable operations are prohibited. _Enforced by:_ canary test — a filter registered at test time appears everywhere a filter should appear.

**R4 — Compatibility is declared, never inferred by the UI.** `compatible_targets(graph, node, port)` is graph-layer, computed from specs. The shell renders its result. _Enforced by:_ the shell has no import path to type-comparison logic; canary test asserts a synthetic filter's ports are offered on the correct nodes.

**R5 — Adapters are filters.** Type mismatches between filters are resolved by explicit conversion nodes in the graph, not by private conversion logic inside a consuming filter. Adapters are typed, cacheable, testable, and reusable. _Rationale:_ private adapters reproduce the blast-radius problem one level down and make semantic drift invisible to validation and cache keys. _Enforced by:_ review, plus the absence of untyped ingestion paths in filter code.

**R6 — Presentation is declared into a closed vocabulary of slots.** A filter declares which slot(s) it contributes to. It does not reach into another filter's representation, ever. _Arbitration rule:_ **any node may contribute a passive rendering to a slot; interactive editing within a slot is exclusive to the focused node.** Conflict is shell policy — z-order, focus, exclusivity — not a negotiation between filters. _Enforced by:_ filters cannot import shell view modules; canary test asserts a synthetic filter's declared slot receives its contribution.

**R7 — Acceptable coupling costs performance, never correctness.** Where a site genuinely cannot be made unaware of filter identity, it must be unable to _break_ on an unknown filter — only to be slower or less optimal. Fast paths are opt-in; the general path is always correct. _Precedent:_ decoder folding for spatial ops. A spatial filter the optimizer doesn't recognize still runs correctly, just slower. That is the shape every remaining coupling must be forced into. _Enforced by:_ canary test runs correctly with all optimizations bypassed and produces identical output.

**R8 — Params surfaces are generated.** A filter's settings UI is derived from its params model and the semantic types of its fields. Hand-built per-filter forms are legacy, not a pattern. _Enforced by:_ canary test asserts a usable form exists for a filter with no GUI code.

**R9 — Failure is contained to a subtree.** A node raising at runtime degrades its downstream subtree and reports; it does not take down playback or the app. _Rationale:_ if a new filter can destabilize the app, people stop adding filters, and the invariant dies socially rather than technically. _Enforced by:_ a canary filter that raises on demand; assert the app remains interactive and other branches still render.

**R10 — Saved graphs load forever.** Graph schema is versioned. Params are versioned per filter, with migrations owned inside the filter's own directory. _Rationale:_ migration logic is the classic place where filter enumeration re-centralizes and blast radius quietly returns. _Enforced by:_ a corpus of saved graphs from prior versions in CI.

---

## 5. Open contract decisions

**These must be settled before graph-model work begins.** Each one, if deferred, forces the graph model to be rewritten. Restrictive answers are acceptable; ambiguous answers are not.

|#|Decision|Why it gates|Recommended default|
|---|---|---|---|
|D1|Is `emits` static, or resolved after params are bound?|If dynamic: validation, `compatible_targets`, cache keys, and edge invalidation all become params-dependent.|**Static.** Config variants that change output type are separate filter IDs. Revisit only with a concrete case that can't be split.|
|D2|What is the compatibility relation — exact type equality, subtyping, or declared coercion?|Determines whether R5 adapters are frequent or rare, and whether `compatible_targets` is a lookup or a search.|**Equality plus explicit adapter nodes.** Simplest to explain, validate, and cache.|
|D3|What is the semantic parameter type vocabulary?|Editor dispatch (R8) and interactive editors (R6) both key on it. Getting this wrong means rebuilding both.|Start with scalar, bounded scalar, enum, band-in-a-named-domain, spatial region, reference-to-artifact. Extend by review.|
|D4|What is the temporal/cost class vocabulary?|The shell cannot support live playback while assembling a graph unless it knows which nodes stall it. Also drives invalidation scope on param change.|`streaming`, `windowed(n)`, `full_pass`, `cached_artifact`, plus a coarse cost hint.|
|D5|Do the current tab-side pseudo-steps become real filters, or move out of catalog ownership?|Two non-filters are currently the stated reason the catalog is hand-enumerated, blocking R3.|Promote to real filters if they have behavior; otherwise move them under shell ownership, out of the catalog.|

D4 deserves emphasis: **real-time playback during graph assembly is the hardest stated requirement in this document,** and real-time coupling is where clean layering gets violated first. Attaching a `full_pass` node behaves nothing like attaching a `streaming` one. The shell can only respond correctly — progress state, deferred edges, incremental scrub — if the difference is declared.

---

## 6. What SIEVE promises, unchanged

The invariant is a constraint on _how_ SIEVE is built, not a reduction of what it does. A filter added under these rules must still:

- appear as an offerable operation wherever its input types are available
- expose tunable parameters with live feedback
- render into the appropriate presentation slot
- participate in caching and invalidation
- survive save/load
- run during playback without special-casing

If any of these requires per-filter integration work, the mechanism is incomplete — that's a defect in the layer, not a cost the filter author absorbs.

---

## 7. The canary: how this is kept true

A test fixture registers a **synthetic filter at test time** and asserts the whole system absorbs it with **zero edits outside its own module**:

- appears in catalog / offerable operations (R3)
- receives a generated params form (R8)
- validates in the graph; its ports are offered on compatible nodes (R4)
- caches and invalidates correctly (R1)
- serializes and round-trips (R10)
- its declared slot receives its contribution (R6)
- produces identical output with optimizations bypassed (R7)
- a variant that raises degrades only its subtree (R9)

Variants: one scalar-param streaming filter, one two-input merging filter, one `full_pass` artifact producer, one deliberately failing filter.

**The metric.** Each assessment cycle reports one number: **files touched outside `filters/<name>/` to add a working, GUI-visible filter.**

- Target: **0** for filters using existing param types and slots.
- Target: **1** (a slot registration) for filters needing a new view.

Report the number every cycle. This is what turns an aspiration into a ratchet and prevents the looped assessment from becoming indefinite refactoring.

---

## 8. Sequencing

Ordered by dependency, not by visibility of results.

1. **This document, ratified.** Plus §9 reconciliation.
2. **Contract decisions D1–D5.** Cheap, no UI churn, unblocks everything downstream.
3. **Canary harness + R2 static check.** Do this early. It is the highest-leverage item here: it makes the invariant survive contributors who never read this document. Initially it fails loudly; that's the point.
4. **Eliminate catalog enumeration** (R3), resolving D5.
5. **Graph model replaces the linear chain model.** The GUI is currently a linear list while the core is a DAG with ports; a two-input filter cannot be drawn or edited at all. This is a rewrite, and it must come _after_ step 2 so it translates a settled contract rather than guessing at one.
6. **Retire the duplicate GUI type vocabulary** — only once the contract answers the question it was invented to answer (R4).
7. **Semantic param editor dispatch**, one level above the scalar form generator (R8, D3).
8. **Presentation slots + focus/exclusivity policy** (R6).
9. **Delete the legacy hand-built filter UI island last,** gated by parity tests against the generic path.

Leave decoder-folding optimizations alone. They already satisfy R7 and are the model for the rest.

---

## 9. Reconciliation of existing directives

Existing documentation contains requirements that push against this document. Silently leaving them in place guarantees they get resurrected and relitigated.

**Process:** every conflicting directive is either (a) **retired**, with a one-line rationale referencing the rule that supersedes it, or (b) **preserved**, with a one-line rationale for why the invariant yields here. No third option; nothing stays ambiguous.

|Existing directive|Conflicts with|Disposition|Rationale|
|---|---|---|---|
|_(to fill during reconciliation pass)_||||

Output of this pass is a table with no blank cells.

---

## 10. Claims requiring verification

The reading that motivated this document was produced from a partial view of the repo and includes specific coordinates — file paths, line numbers, file sizes, counts of grep hits, claims that certain modules contain zero filter references. **Treat all of these as claims to re-verify, not as findings.** Re-verification is step zero of planning; a plan built on stale coordinates will be confidently wrong.

Specifically re-confirm before sequencing: which files actually reference filter identity; whether the merging-filter port mechanism validates and caches as described; whether the generated params form is genuinely the path new filters take; and where the linear chain assumption is load-bearing.