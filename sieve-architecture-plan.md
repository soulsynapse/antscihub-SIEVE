# SIEVE v4 Architecture Plan — Index ADR

> Status: living index. Renumber into the ADR sequence on commit.
> This document is the tracking system. It must not grow tooling, dashboards, or status taxonomies.

## Purpose and economics

SIEVE is a scientific video analysis pipeline: a DAG of filter operations over behavioral video, with pipeline YAML as the canonical project format, CLI as the canonical run path, a Qt GUI over the same API, HPC (Slurm) batch handoff, and a live-tuning mode on short representative clips. Outputs: processed video, per-frame tabular data, detection events.

Governing constraint: most code is agent-authored, so **the binding cost is human verification bandwidth, not code volume**. A small number of reviewed files (the contracts) must enforce correctness across many unreviewed files. Every task below is therefore classified by whether a strong oracle exists: if yes, agents build it and the oracle verifies it; if no, the human designs it and agents may only draft/red-team.

The reviewed set = edge types, node contract, time model, fingerprint scheme, schema versions, the metamorphic relations, and this document. Everything else is disposable behind those contracts.

## Methodology rules (non-negotiable)

1. **No consumer, no start.** An item without a real consumer (a real pipeline, node, file, or failure) is not "in progress" — it is not started.
2. **One construction site.** One architecture item open at a time. All others are frozen at their done-state. Agent loops may touch closed items only when carrying a ticket.
3. **Growth by regression only.** check_node, the property suite, and golden masters grow only when an escaped bug buys exactly one new check. Nothing enters on "might catch something."
4. **Reopening = ADR amendment with ticket attached.** A ticket is an artifact in hand — a failing test, a real file, a real incident. Never an anticipated need. Reopening is deliberately heavier than closing.
5. **Done is boring and stays boring.** No polish passes, no consistency sweeps, no "while I'm in here." Aesthetic dissatisfaction is not a ticket.

Agent-specific corollary: never let an agent both write a node and invent its correctness criteria. Humans author metamorphic relations and properties; agents implement generators, shrinkers, harnesses, and nodes.

## Critical path

contracts (human) → check_node + oracles (human reviews, agents build) → everything else (agent loops against oracles).

Contracts are finalized **against the first ~10 real nodes**, not before them. Stub dataclasses in week one; ingest + real nodes immediately after; amend by ADR as reality objects.

---

## The fundamentals

Format per item: principle → concrete requirement → **Done when** → **Reopens only on** → delegation note.

### 1. Edge type algebra
What flows between nodes is the decision that forces rewrites when wrong. Three edge types: dense video stream, per-frame table (aligned to a video time base), sparse event stream. Strictly typed edges with explicit converter nodes — no format negotiation. Close the node-signature algebra (video→video, video→table, table→events, events→overlay, …).
**Done when:** one contracts file defines the 3 types; 10 real nodes type-check against it.
**Reopens on:** a concrete node that cannot be expressed, attached to the ADR.
*Human-designed. Agents may red-team ("generate ten node types that break this algebra").*

### 2. Time model
Timestamps, not frame indices, are the ground-truth coordinate carried by tables and events. Every node contract declares its time transform: rate change, offset, halo/warmup consumption. Generalize halo to a declared temporal support region.
**Done when:** written time spec exists; decimation metamorphic test (timestamps change exactly per declared transform, nothing else) is green.
**Reopens on:** a failing timestamp test from real footage.
*Human-designed. Hard thinking, little code.*

### 3. Fingerprint completeness
Node identity = (op version, params, parent content hash) and this must capture **everything** affecting output — no ambient config, no library drift, no undeclared reads. The measurand/estimator/cosmetic parameter taxonomy is machine-readable in the contract; cosmetic changes provably do not invalidate cache.
**Done when:** perturbation suite green — mutating any contract-declared input moves the hash.
**Reopens on:** a cache-hit-with-different-output incident.
*Discipline, not a build. Agents implement the perturbation suite.*

### 4. Chunked execution in the kernel contract
Every kernel is a pure function over chunk+halo with a declared spatial/temporal support region. Execution strategy (lazy, streaming, tiled, Slurm) is a scheduler concern, never a kernel concern.
**Done when:** support-region fields exist in the contract; chunked ≡ whole-clip differential test green on 3 pipelines. (Run whole-clip-as-one-chunk until HPC is real.)
**Reopens on:** an OOM on real data, or an actual Slurm submission.
*Strong oracle (differential test) — chunked executor is safely agent-built.*

### 5. Schema versioning
Pipeline YAML, run manifests, and the store key scheme each carry a schema version field from day one, with a migration path. Changing the hash scheme without versioning silently orphans every cache and manifest.
**Done when:** version fields exist in YAML/manifest/store-key; one round-trip migration test passes.
**Reopens on:** shipping an actual breaking change.

### 6. Normalized graph IR, distinct from authoring syntax
YAML is surface syntax. The canonical object is the normalized in-memory IR: converters inserted, defaults resolved, nodes fingerprinted. GUI, CLI, and any future API are frontends to one IR — never independent interpreters of text. Optimization (prefix dedup, dead-subtree elimination) operates on IR.
**Done when:** YAML → IR → YAML round-trips; CLI and GUI both consume IR only.
**Reopens on:** a new frontend existing.

### 7. Hermetic, content-addressed re-execution
Cache validity is derived from content hashes, never asserted by dirty flags. Any chunk job may die, be preempted, or run twice with no correctness effect; resume = re-walk graph, skip cache hits; no job-state database. Determinism discipline: seeded RNG in the fingerprint, pinned dep versions in op version, honest `nondeterministic` flag (see 15) exempting an op from replay-equality.
**Done when:** delete-cache-and-replay test green (bit-identical or within declared tolerance, per 16).
**Reopens on:** a nondeterminism incident.

### 8. Node registry + check_node conformance suite
Core defines the node contract and never imports a node (dependency inversion, enforced by import-linter). Builtin, agent-authored, and future third-party nodes all register identically and pass `check_node`: halo honesty, time-transform correctness (metamorphic), fingerprint completeness (perturbation), effects honesty where checkable.
**This is the load-bearing item**: check_node is the machine-readable oracle that lets all other agent loops run unsupervised. Invest review hours here disproportionately.
**Done when:** every contract clause has ≥1 check; suite green on all builtin nodes.
**Reopens on:** an escaped node bug — each buys exactly one new check.

### 9. Coordinate provenance
Crop/resize/pyramid/undistort change the pixel frame. Edges carry the accumulated transform back to raw-sensor coordinates; tables and events carry (timestamp, raw-frame coords, units) intrinsically. **Affine-only for now**; nonlinear (lens undistortion) is explicitly deferred.
**Done when:** affine carried on edges; crop∘detect ≙ detect∘crop metamorphic test green.
**Reopens on:** a node needing nonlinear transforms, in hand.
*Per-node boilerplate tax transfers to agents; the metamorphic relation is the oracle.*

### 10. Narrow waist, semantics-free executor
The waist = edge types + node contract + fingerprint scheme, and it is embarrassingly small. The executor walks graphs, hashes, and schedules chunks; it never knows what a Morlet band or halo means. Any executor feature requiring node semantics is a layering violation.
**Done when:** import-linter rules merged.
**Reopens:** never — violations are bugs.

### 11. Property and metamorphic testing
No oracle exists for most outputs, so correctness = properties + metamorphic relations derived from the contracts: crop∘detect commutes (9), decimation respects declared time transform (2), cosmetic perturbation leaves measurands within declared tolerance (3, 16), fingerprint perturbation moves hashes (3). Golden masters are few, curated, and human-blessed — they catch *unintended* change only.
**Humans author the relations (they are restatements of the contracts, roughly one page). Agents implement generators, shrinking, harness (Hypothesis).**
**Done when:** the one-page relation list exists, human-authored; harness in CI.
**Reopens on:** a new contract clause.

### 12. Ingest boundary — parse, don't validate
One reviewed subsystem converts hostile container/codec reality into canonical SIEVE frames in SIEVE time. It (a) assigns every frame a canonical timestamp from container PTS, (b) verifies claimed timing by full scan on first contact, building a content-addressed frame index (frame → PTS → byte offset), (c) implements exact-frame seek as index lookup, never a codec seek. Decoder identity+version is in the ingest fingerprint (decoder builds are not bit-stable).
**Scope: the Pi-fleet's actual formats (H.264/MP4) only.** Written non-goals list: VFR, exotic codecs.
**Oracle: synthetic ground-truth videos** (ffmpeg-generated, frame index + PTS burned in visually and steganographically). Agents build the oracle harness (human reviews it — it is small), then build ingest against it unreviewed-but-verified.
**Done when:** ground-truth harness green for Pi-fleet codecs; non-goals list written.
**Reopens on:** a real file in the project's own data that fails.

### 13. Store — immutable objects, mutable refs
git/Nix model: content-addressed immutable objects (chunk outputs, frame indexes, manifests) keyed by fingerprint; runs and pinned results are named refs into the object graph; liveness = reachability from refs; eviction is pure policy. Two decisions baked into every stored byte, made now: key scheme (= 5's versioned fingerprint) and object granularity (chunk-level, composing with 4). GC deferred; human-meaningful metadata lives above this layer.
**Done when:** object/ref layout documented; fsck-style integrity check exists.
**Reopens on:** disk pressure or corruption, actually experienced.

### 14. Experiment layer stays above the waist
Sweeps, replicates, and aggregation are **graph generation, not graph execution** — an external layer takes (pipeline template × parameter grid × clip manifest), emits many SIEVE runs, consumes their outputs as a dataset (Snakemake-style, files as the boundary). SIEVE's side of the contract, exactly two things: (a) machine-readable run manifests (fingerprints, tagged params, input identities, output refs); (b) template + bindings → concrete fingerprinted graph as a first-class IR operation, so sweeps share cached common prefixes.
**Done when:** manifest schema + template/binding IR op exist; one 2-parameter sweep executed by an *external* script.
**Reopens on:** a separate, deliberate project decision.

### 15. Effects declaration (no enforcement)
One contract field: `effects: pure | reads_external(paths) | network | gpu | nondeterministic`, default `pure`; declared external reads enter the fingerprint. Declaration precedes enforcement (the Chrome-manifest lesson) so a permission model can tighten later without breaking the ecosystem. **Skip sandbox enforcement entirely for now.**
**Done when:** enum field exists, defaulted, in fingerprint.
**Reopens on:** first third-party node actually distributed.

### 16. Numerical policy
(a) Small dtype/colorspace lattice for edges with promotion rules decided once — this completes 1's algebra. (b) Each measurand declares comparison semantics: bit-exact | abs ε | rel ε | distributional; check_node, golden masters, and replay tests read tolerance from the contract, never invent it locally. (c) `nondeterministic` ops are the only replay-equality exemption.
**Done when:** dtype lattice in contracts; tolerance field exists (values filled just-in-time as each golden master is written — choosing tolerances is human measurand judgment).
**Reopens on:** per-measurand, as golden masters are authored.

### 17. Compatibility promise
Inverted for now: one ADR stating **"0.x — everything may break."** At 1.0, the real promise: promised surfaces = the waist (YAML schema, node contract, store format, manifest schema); a break requires schema version bump + shipped migration (5) + deprecation window (Rust-editions model).
**Done when:** the 0.x ADR exists.
**Reopens on:** 1.0.

---

## Delegation summary

| Safely agent-built (strong oracle) | Human-designed (agents draft/red-team only) |
|---|---|
| Ingest subsystem (vs. synthetic ground truth, 12) | Edge algebra (1), time model (2) |
| Chunked executor (differential test, 4) | Metamorphic relations & properties (11) |
| Coordinate plumbing (metamorphic, 9) | Tolerance choices (16) |
| Perturbation/replay suites (3, 7) | All ADRs, this document |
| check_node harness plumbing (8) | Contract clauses themselves (8) |
| Store integrity check (13), GC later | Experiment-layer boundary (14) |

Standing warning: agent labor makes speculative generality nearly free to build and expensive to be wrong about. The old brake (construction cost) is gone; these methodology rules are its replacement. Nothing gets built without a consumer, regardless of how cheap building has become.
