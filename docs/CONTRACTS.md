# Contracts and how they change

Five contracts hold SIEVE together. This document defines them and — more importantly —
defines how they are allowed to change, because the whole point of the design is that they
will change often and that changing them must not require hand-editing everything.

The contracts are: **pipeline file**, **step**, **intent**, **provider**, and
**equivalence record**.

## The rules that make change cheap

**Contracts are data, versioned, additive-only within a major.** Every record carries
`contract: <name>@<major>`. Within a major you may only add *optional* fields with
defaults. Anything else — a new required field, a removed field, a changed meaning — is a
major bump.

**Version tolerance lives at the boundary and never in the body.** There is exactly one
in-memory shape for each contract: the current one. Files are migrated on load through a
chain of `migrate_<n>_to_<n+1>` functions and rewritten on save. No code anywhere else
branches on version. If you find `if version >= 3` outside a migration module, that is the
bug.

**Deletion is real deletion.** When a step kind, provider, or field is retired, its code is
removed from the tree. A one-line entry goes in [RETIRED.md](RETIRED.md): name, date,
reason, replacement. The migration either rewrites the node to its replacement or marks it
`unsupported` with a message the user can act on. This rule exists because dead code and
dead docs are the most expensive thing in an agent-maintained repo: they read as live paths
and consume the context budget that should have gone to the real one. A retired-list entry
is one line, not a paragraph.

**Contracts are enforced by conformance tests, not by review.** Each contract has a suite in
`tests/conformance/` parameterized over every registered implementer. Adding a required
field breaks every implementer at once, loudly, in one place — which is exactly what you
want, and is what makes the additive-only rule enforceable rather than aspirational.

**Partial work announces itself.** An agent that cannot fully satisfy a contract must land
two things together: an in-place marker and a conformance test that fails or is explicitly
skipped with that marker's id. Never a silent partial. The marker is one machine-readable
line, at the site, and says what is owed and when it is due:

```python
# DEBT(sieve-14, due=provider@2): cost is hand-estimated, not measured on the reference set
```

The prose lives in the tracker; the line in the code says only what the code cannot.

**Ratchets, not vibes.** `ratchets.toml` holds thresholds that may only move in the
improving direction: count of `DEBT` markers, count of `unsupported` node kinds, fraction of
providers with a measured (not estimated) cost, fraction of providers with a committed
signature, wall clock on the reference bench. CI fails when a ratchet moves the wrong way.
Loosening one requires editing the file in the same commit, with the reason in the diff, so
that it is visible rather than absorbed.

**Ledgers are diffs.** Each contract keeps a changelog fragment of one line per change,
derived from the migration names. A changelog that re-explains the code has failed at its
job; its only job is to tell you *when the shape changed and why*.

## Pipeline file

Owns the user's chosen steps and nothing else. It is the only thing that persists user
intent, so its migration story is the one that matters most.

A node is `{id, kind, params (possibly partial), bindings: {port -> offer_ref}, overrides}`.
`overrides` are per-instance parameter overrides applied after expansion. An edge is
implicit in a binding: ports name an upstream offer, never an upstream step.

**Incomplete is valid.** Missing parameters, unbound ports, and dangling offer references
are all legal on disk. Validity is a computed property: `validate(pipeline)` returns per
node `ready` or `blocked(reasons)`, and the reasons are user-facing strings the GUI shows
verbatim. Nothing in the loader raises on incompleteness. A file that fails to load is a
migration bug, not a user error.

**Unknown kinds survive.** A node whose `kind` is not registered loads as `unsupported`,
keeps its parameters intact, blocks everything downstream with a clear reason, and round
trips through save without losing data. This is what lets a user open a file written by a
newer build without destroying it.

## Step

```
kind            stable identifier, used in files; renaming is a major bump + migration
params          schema with defaults; the only thing persisted
panel           builds the right-hand config UI; reads and writes params
view_request    params -> Intent | None; what the left panel should show
inputs          named ports, each with accepted types and delivery modes
offers          named outputs, each with a type and delivery mode (information | artifact)
overlays        overlay layer declarations + edit -> params mapping
```

A step declares. It does not compute, does not call the kernel, does not name a provider,
and does not know what other steps exist. A step that needs a new capability requests a new
*intent*; if no provider implements it, that is a kernel task, not a step task.

## Intent

A typed, parameterized request: `{op, input types, params, output type}`. Intents are the
common currency between step, executor, and kernel — the step's view request is an intent,
the plan is a DAG of intents, and a provider declares which intent shape it implements.

Intent parameters are normalized before planning (canonical units, sorted keys, resolved
defaults) so that two spellings of the same request hash identically. Cache keys and
equivalence records both depend on this, so normalization is part of the contract and not
an implementation detail.

## Provider

```
implements       an intent shape, or a connected span of intent shapes (a fast path)
eligible         input type constraints beyond the intent's own
params           schema
sensitivity      contractive | stable | sensitive
cost             measured on the reference bench; estimated costs carry a DEBT marker
signature        content-addressed record of reference-set outputs (see EQUIVALENCE.md)
```

Every intent shape must have at least one single-intent provider before any span provider
for it is admissible. Span providers are ordinary providers; there is no separate
rewrite-rule system, no optimizer plugin interface, and no registry of combinations.

## Equivalence record

`(provider_a, provider_b, probe, reference_set, statistic, margin τ, verdict, commit)`.
Defined in full in [EQUIVALENCE.md](EQUIVALENCE.md). The contract-level rule: the executor
may substitute one provider for another **only** when a record covers that substitution
under a probe compatible with the plan's terminal output. Absent a record, the executor
uses the provider the plan named. Missing records make things slow, never wrong.

