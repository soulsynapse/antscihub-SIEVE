# PAR-0007 — The tool contract: what a tool owns, and what it must never own

Status: Proposed
Date: 2026-08-03

## Outcomes

What this system looks like working as intended: someone who wants a new
filter writes one file, reads nothing first, and it lands — it appears in
the picker, it can be placed, and running it errors at the backend with a
marker naming what is still owed, because the operation it asked for
doesn't exist yet. That is the system working, not failing. What they
wrote stays right when the executor learns three new rewrites, because
nothing in it said anything about execution. Adding a second method to an
existing operation is also one file, and no tool changes. And when
someone finds themselves editing the renderer to make a tool work, they
know immediately what has gone wrong, because the edit is the symptom of
a responsibility sitting in the wrong module.

## Context

The named system: the responsibility boundary around a tool — what a tool
owns, what it is structurally denied, and how a violation announces
itself. Not what an op *is* or what its form authorizes (PAR-0005), not
what the executor does with the graph it gets (PAR-0008), not the
vocabulary `view` draws from or how the config pane is generated
(PAR-0013), not the schema versioning and identity of the `Params` model
(PAR-0016), not the dispatch table eligibility is a query against
(PAR-0011), not equivalence and its measurement (PAR-0012), not the
correspondence between two methods a user chooses between (PAR-0019), and
not where enforcement lives (PAR-0017).

The occasion is a rejection, and not for being wrong. The first design in
Exchange 5 was coherent — tools as compiler front-ends, three registries,
dispatch on op class — and Prompt 6 killed it: *"I suspect an agent would
write spaghetti code every time... Your solution makes extending the repo
a headache for all future edits."* The diagnosis names two distinct
failures. One is unverified declaration — *"it required a conformance
test to check whether an op honestly declared itself random-access"* —
and that is PAR-0005's. The other is *"it made every future contributor
pay compiler tax before shipping anything,"* and this record is its home.

The cost of getting the boundary wrong is asymmetric in time, which is
what licenses settling it before any tool exists. PAR-0005 states the
asymmetry for the return type: free at n=0, a contract rewrite at any
later moment, because a tool's return type is the one thing not
retrofittable per-tool. The same holds for every mandatory element of the
signature. What this record therefore contains is exactly the claims
whose cost of being wrong later is a rewrite or a store migration;
everything else about what a tool owns waits for tools to argue against,
because a record cannot adjudicate an empty room and should not pretend
to.

Primary: `docs/archive/SESSION-2026-08-03-tool-contract-scope.md` — the
surface having grown from three members to five, and the spine as the
boundary rather than a governance rule (Exchange 1); the adversarial pass
and what it killed (2); the v1 admission test (4); `lower` challenged and
kept (5); the Tool as the only object with a contract (6); `lower`'s
arity, non-inspectable handles, and properties-not-history (7);
configuration interchange outgrowing this rationale (8); the one-file
rule's provenance (9); the responsibility recolor, which is the sitting's
central result, and the import finding (10); where a method's params
live, and the partition proposal that lost to a cheaper one (11). Three
positions that lost are kept there with the arguments that killed them.

## Decision

**A tool owns the translation of authored params into a description of
what should be computed. It owns nothing else.** Every rule below is that
sentence applied to a particular thing a tool might otherwise reach for,
and each is stated as an absence rather than as a prohibition, because an
absent wire cannot be grabbed and a prohibition can only be obeyed.

**It does not own execution.** `lower` and `view` are pure functions: no
executor handle, no context object, no callbacks, no I/O, no state
outside `Params`. This is the design's strongest lever against
agent-written coupling and it is why registries are derived by scanning
the tools package at import rather than maintained by hand. Removing a
handle after twenty tools take one is twenty rewrites, which is why the
absence is fixed while the room is empty.

**It does not own presentation or machine configuration.** There is no
preference argument. Prompt 2 asked for a step that "also takes SIEVE
preferences" and the rebuilt contract has none; PAR-0006 ratifies that
removal as the mechanism enforcing the param boundary rather than as an
omission. A preference cannot reach an answer because no channel exists
to carry it, which also makes the boundary testable — scramble the
preference set, and `lower` must emit an equal op value.

**It does not own what it is attached to.** `lower(self, p, inputs)`
receives its upstream values, and they are typed and non-inspectable.
Typed, because eligibility must be answerable from the class before any
params are filled — Exchange 6's third condition requires ineligible
tools shown greyed *with the missing requirement named*, which is a
static read off the signature. Non-inspectable, because a tool that can
pattern-match its upstream and emit differently is doing planner work
inside a tool, which belongs to PAR-0008 alone and is exactly what an
agent writes when asked to make a tool efficient. The cut that makes both
true: **a handle exposes properties of the value — shape, fps, dtype —
and never its history.** A frequency bank capped at `0.45*fps` stays
writable, as v1 writes it; "the upstream is already a resample, so skip"
stays unrepresentable, because there is no lineage to branch on.

This is also why the alternative — a declared `consumes` list — is not
the answer, and the reason is narrower than the design's usual one. The
three declarations this design rejected were each a *second copy* of a
fact that existed elsewhere with nothing checking the copy. A declaration
is only dangerous when it can disagree with something, and against a
`lower` that receives nothing, `consumes` disagrees with nothing. It is
ruled out because the arity is the one-way door and the declaration is
not: an argument added later rewrites every tool, a declaration added
later is additive.

**It does not own the shape of what it produces.** `lower` returns a
graph with named outputs, not a single op. Exchange 2 settles that a
tracker offers centroid trajectories *and* segmentation masks as two
named ports, both always present, with the user choosing what to connect;
a tool that can produce two logical values cannot return one op. A single
op is the one-node case. `view(self, p, out)` taking one output value is
the same settlement from the other side — views are per-value, so they
compose with ports for free.

**It does not own the meaning of the operation.** Ops live outside the
tool module. The tool is the occasion for an operation — most operations
are built because a tool needed them — but the operation is a different
file because it is *different debt*, with its own marker and its own
governing record. An op co-located with its tool has its identity
entangled with that module path, and hoisting it out later changes the
recipe hashes that name it, orphaning stored results: the one mistake
here that costs data rather than code. The record states the negative
only; where non-trivial primitives do live is open, and naming a
destination at n=0 is the guess the catalog admission rule exists to
prevent.

**It does not own the method.** A tool's `Params` holds what is true of
the measurement regardless of how it is computed — spatial scale,
temporal window, sensitivity. A method's own knobs live on the method, in
the method's file, and never beside them. The test is whether the field
would mean anything to a different implementation of the same operation:
a temporal window would, `dis_preset` would not. This is not a partition
inside the tool's model — there is nothing to partition, because those
fields were never in it — and it costs nothing today, since crop and
downsample have no method choice and stay flat. It also removes a rule
rather than adding one: PAR-0006's hash over *effective* params exists
only because inert fields sit in the wrong model, and with the fields on
the methods no inert field survives to be excluded.

Two things are called *method* and they behave oppositely. Two
implementations producing statistically equivalent output are two
implementations of **one op**: the user never learns which ran, the
recipe does not change, and selection is by measured cost. Two methods
that answer differently are **two ops**: different descriptions,
different numbers, the choice authored and hashed — which is what
PAR-0006 already ruled for Farneback, DIS and RAFT. Both arrive as one
file, and in neither case is anything appended to a tool, because a
registration line would be the tool owning knowledge about the method.
Grouping is the generic function, with membership earned by measurement.

**The Tool is the only object with a contract.** A Step is a tool placed
at a level with its params filled in — data in the pipeline file, with no
methods. A Task is one realized execution, constructed by the executor
and authored by nobody. The audiences are already disjoint in practice —
users say step, authors say tool, and only the executor says task — but
`pipeline.py` will hold Steps as data and an agent reading
`ARCHITECTURE.md` sees three nouns of equal weight, so the silence needs
stating once.

**A tool declares yardsticks, never verdicts, and never a guarantee it
does not hold.** The equivalence spec PAR-0005 routes here — the
comparator, tolerance, and target statistic for the ops a tool emits —
does not reopen any of the above, because it is data travelling with the
description and it claims what the tool's output *means* rather than what
may be substituted for it. The tool is the only party that knows the
meaning; the harness is the only party that decides. The companion
convention PAR-0005 also routes here is declined: a tool declaring the
guarantees it voids is refuted by its own first instance, since
`Opaque`'s lost reprojection is derivable from the form and a declaration
would be a second unchecked copy of what the value already carries. What
is not derivable is the user-facing consequence of that loss, which is
computed at selection (PAR-0011) and displayed by PAR-0013.

**How a violation announces itself.** If adding a tool ever requires
editing something that already exists, some other module owns a piece of
the tool — the renderer knowing tool identity, a registry owning
registration that should be derived, the executor holding per-tool
knowledge. That is what the one-file property in `ARCHITECTURE.md`
detects, and this record is why it is true rather than a restatement of
it. Read as a claim that a tool works after one file, it is false; read
as a detector, it is exact, because a tool naming an operation that does
not exist yet lands anyway and errors at the backend with its debt
recorded. The diagnostic when the detector fires: name what the edited
module owns that belongs to the tool.

## Consequences

- Acceptance amends `ARCHITECTURE.md` in the same commit. The one-file
  invariant keeps its wording and its citation moves from
  `archive/PLAN.md` Phase 1 decision 2 to this record, which supplies the
  reason it holds. The "Tools" section's Exchange 5 citation moves here,
  and its example gains `lower`'s inputs argument. `README.md`'s "Where
  contracts live" moves from Exchange 1 to this record.
- PAR-0002 settles the placeholder-form split, and stamp
  `20260803T072353Z` discharged at the sitting that stated it:
  vocabulary reached for by name takes the function-body position,
  behavior only called into takes the module position, and the tell is
  whether a `from <module> import <name>` appears anywhere the milestone
  reaches. What remains is not a missing rule but an unsettled surface —
  which names `kernel.py` exposes is `docs/PLAN-TOOL-CONTRACT.md` Phase
  2's, since PAR-0005 retired the five-shape table and a placeholder may
  not invent one. Until that lands, a tool naming an unbuilt op still
  dies at import rather than at use.
- PAR-0005 amends the Consequences bullet that routes the voiding
  declaration here (its marker, `20260803T072354Z`), or the refusal
  above falls.
- PAR-0006 amends twice (its marker, `20260803T072355Z`): the effective-
  params hash rule becomes unnecessary rather than obeyed, and the
  record's classification by effect cannot express measurement-versus-
  method ownership, which is why `dis_preset` is correctly a param under
  its rule and still does not belong beside the fields that survive a
  swap.
- PAR-0009 hashes the tool's params, the chosen op's identity, and that
  op's own params.
- PAR-0011 owns grouping by generic function with membership earned, and
  the user-facing consequence of a form's lost guarantee.
- PAR-0012 owns the invisible half of substitution; PAR-0019 owns the
  correspondence between alternatives a user chooses among, and the
  visible/invisible line is the seam between them.
- PAR-0013 receives the config pane composing the tool's params with the
  selected op's own, and the rule that an op declares field types and
  never rendering.
- PAR-0017 receives two contract tests: the preference scramble, and a
  purity check that no tool module reaches the executor, the store, or
  the filesystem.
- `docs/PLAN-TOOL-CONTRACT.md` Phase 3's gate is narrowed rather than
  answered. Its first decision is settled here as `lower`'s arity with
  non-inspectable typed handles; its fourth must land in tests rather
  than in a base class that merely withholds. Canonicalization and tool
  identity are untouched — the first waits on the GUI-topology deferral,
  the second is PAR-0016's.
- The how-to layer gains three residents at acceptance: writing a tool;
  adding a second method to an existing operation; and suggesting an
  equivalence spec for an op a tool emits. Where non-trivial primitives
  live is deliberately not among them, because it is unsettled rather
  than merely unwritten.

## Challenges

*Agent-raised except where noted; none human-confirmed yet (PAR-0001:
friction is stated, never inferred).*

- **2026-08-03 — the Outcomes describe something the tree cannot do
  yet.** The whole record rests on a tool landing against operations that
  do not exist. The rule that permits it is settled — PAR-0002's position
  split, stamp `20260803T072353Z` discharged the same sitting — but
  `kernel.py` stays module-form until Phase 2 settles which names it
  exposes, so such a tool still dies at import today. Narrowed
  2026-08-03 from a missing rule to a pending surface; this record's
  central property remains an intention, and the detector it offers has
  never fired on anything.
- **2026-08-03 — non-inspectable handles are asserted, not designed.**
  "Properties, never history" is a clean line in prose. Nothing here says
  what makes it hold — whether a handle is a distinct type withholding
  lineage, whether lineage is simply absent from the value a tool
  receives, or whether it is convention. If a tool can reach lineage by
  any route, the planner-work-in-a-tool failure is available again and
  the argument for passing inputs at all weakens.
- **2026-08-03 — the method/op distinction leans on an unbuilt
  system.** "Verified-equivalent implementations of one op" versus
  "different ops answering differently" is the axis on which method
  params, grouping, and user visibility all turn. Membership is earned by
  measurement, and the harness that measures is a `DEFERRED.md` entry
  whose own record opens by asking whether it exists as a system at all.
  Until then the distinction is made by judgment, which is the thing this
  design otherwise refuses.
- **2026-08-03 — the contract is designed at n=1 in the dimension that
  matters.** Crop and downsample are both affine coordinate maps with
  scalar params and a single output. Neither exercises multiple ports, a
  second input, a method choice, or an equivalence spec. Exchange 6's own
  rule is that an abstraction is designed with two examples in hand; on
  the page there are two, and in shape there is one.
- **2026-08-03 — purity is a property of behavior and the proposed check
  is static.** Nothing stops a tool importing a video library and reading
  a file inside `lower`. An import check catches the obvious case and not
  the determined one, and this record should not be read as claiming
  more.
