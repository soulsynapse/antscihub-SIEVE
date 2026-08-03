# SIEVE architecture

SIEVE turns video into behavioral measurements using interpretable
signal-processing filters. The user builds a pipeline; SIEVE runs it. Everything
below exists so that stays true as filters are added, without the codebase
becoming something nobody wants to extend.

This document is the synthesis and the first stop for *understanding*: it
reports the settled architecture, it does not govern it. For *doing*, the
walking path has a tier 0 above this one — task-oriented guides in
`how-to/`, split by domain, read first and fallen back from when a guide
fails ([PAR-0003](par/0003-how-to-layer.md)). The reasoning lives in
`docs/par/`, the primary records in `docs/archive/`; the walking path and
the authority order are
[PAR-0001](par/0001-project-architecture-rationale.md). On conflict the deeper
record wins and this synthesis gets fixed. Each section below names the
records that govern it — exchange numbers cite
[DESIGN-SESSION.md](archive/DESIGN-SESSION.md). The founding decisions are
being distilled into retrospective rationales; until a decision's rationale
lands, its exchange citation remains the governing pointer.

## The components

**The kernel** is the set of primitive operations — resample, threshold, wavelet
transform, optical flow, background model, tracker. Every primitive is an op
*value* — a closed, serializable constructor with typed fields, never a callable —
and the form it is written in is an authorization: it states which substitutions
the executor may make *without telling anyone*, proved under the answer defined
at the logical level (the composed map from the nearest barrier, applied once).
The vocabulary is what has been proved, and no more:

| Form | What it is | What it authorizes silently |
| --- | --- | --- |
| affine coordinate map | exact map over (t, y, x) | composition with neighbours, random access, reordering with spatial work |
| the sequential bit | structural: state carried frame to frame | nothing — a sweep barrier |
| `Opaque` | no structure exposed | nothing at all — always correct, never fused |

`Opaque` is what you write when you don't want to think about any of this. It is
correct and slow, and it is the resting state, not debt. Reshaping it into a
proved form later makes it fast with no change to the tool's public surface —
same params, same view, the answer preserved under the defined semantics. A
further form is admitted when a substitution it would license is both wanted and
provable — never because an op feels like it deserves a category. Everything
proof cannot back is user-initiated, shown, and recorded — the measured world of
invariant 4. (Record: PAR-0005.)

**The harness** decides which implementations may exist and which is preferred. A
new implementation does not *declare* that it computes change energy; it earns
that membership by producing statistically equivalent output to the reference
implementation across a versioned corpus of deliberately hard footage — low SNR,
motion blur, compression artifacts, near-threshold contrast. Having verified
membership, the harness measures cost per machine and input shape, and measures
each op's sensitivity: a Lipschitz gain for smooth ops, boundary mass for
thresholds. End-to-end error is then bounded from measured numbers rather than
assertions.

The same machinery is exposed to users. "Is decimating to one frame every three
minutes equivalent, for the statistic I actually care about?" is the same question
the executor asks internally, and answering it is what makes a six-month recording
study tractable. (Record: Exchange 8; deferred with its trigger in DEFERRED.md.)

**Tools** are what the user picks up: crop, downsample, background subtraction,
tracking. A tool is a pure front-end — three things in one file:

```python
class Downsample(Tool):
    class Params(BaseModel):
        factor: int = Field(2, ge=1, le=16, title="Downsample factor")

    def lower(self, p):     return Resample(scale=(1, 1/p.factor, 1/p.factor))
    def view(self, p, out): return Image(out)
```

A tool holds no reference to the executor, performs no I/O, and keeps no state
outside `Params`. It cannot couple itself to anything, because the wires don't
exist to be grabbed. (Record: Exchange 5, the rebuilt version; naming — Tool /
Step / Task — Exchange 2.)

**The pipeline** is what the user authored: an ordered DAG of steps, each a tool
plus its filled-in params. Human-readable, diffable, version-controllable, and it
holds *intent only* — never progress. (Record: Exchange 1.)

**The store** holds every value ever computed, addressed by the hash of its recipe
(source, composed ops, implementation version). Nothing is ever invalidated.
Changing a param doesn't invalidate a result — it names a different hash that
isn't in the store yet. Old entries age out under a size budget. Undo is free, and
"which steps are complete" is a query rather than a stored flag. (Record:
Exchange 5, "Delete invalidation rather than owning it"; Exchange 1's
intent/progress split.)

**The executor** is the only component that knows about the others. It lowers
steps to ops, fuses adjacent ops, asks the harness for the fastest verified
implementation of each, and evaluates — `render(node, frame)` for a single frame,
`sweep(node, range)` for sequential ops that must run in order. Results go to the
store. It is not a planner: it has a naive evaluator that always works, plus a
handful of peephole rules added when profiling shows a path is hot. (Record:
Exchanges 4 and 6.)

**The GUI** is two panes. The right pane is configuration, generated by walking
the tool's `Params` and choosing a widget per field type. The left pane shows the
result, generated from the tool's `view` declaration using a closed vocabulary of
layers: image, mask, points, paths, vectors, regions, series strip. The GUI knows
field types and layer kinds. It never knows about any particular tool.
(Record: Exchanges 1 and 2.)

## Building a pipeline

Up and down move between steps. Left and right move between siblings — the six
replicates a crop produced. Pressing down offers the tools whose inputs are
satisfied by what exists at that point, which is a query against the dispatch
table rather than a hand-maintained list. Ineligible tools appear greyed with the
missing requirement named, so the system is never silently unable.

Configuring a step applies to all its siblings — one definition, mapped over the
branch set — with per-branch override as a deliberate, marked exception.

Drawing a box on the left and typing coordinates on the right are the same
mutation to the same param, so undo, validation, and saving work identically for
both. (Record: Exchange 2; greyed-ineligible-steps — Exchange 6, condition 3;
eligibility as a dispatch query — Exchange 7.)

## Running one

```
 pipeline ──lower──> ops ──fuse──> plan ──dispatch──> kernel impls ──> store
                                            ▲                           │
                                        harness                         │
                                   (equivalence + cost)                 │
                                                                        v
                                                              GUI (render / scrub)
```

Steps are lowered to ops and fused: crop ∘ downsample becomes a single coordinate
map — one correctly-filtered resample rather than two — and temporal decimation
hoists above spatial work, so frames that will be discarded are never decoded.
Sequential ops sweep once and persist their small results; a track table is a few
MB for a hundred thousand frames, which returns everything downstream to
random-access. Scrubbing is then one decode plus one array lookup.

Because geometric ops are invertible, an annotation computed in downsampled space
can be drawn over the full-resolution source. The user swaps the base layer freely
— tracks over the mask, over the source, over the background plate — and that
choice never touches configuration. (Record: PAR-0005 for fusion and its
semantics; Exchange 4 for reprojection and the sweep-then-index composite.)

## The invariants

Five rules. Each is load-bearing, and breaking any one is how this becomes
unmaintainable.

1. **Adding a tool writes one file.** Anything the tool needs that doesn't
   exist — a field type, a view, an executor offering — is declared, not
   reached for; building the missing capability is a separate change under its
   own contract. A tool that can't be written in one file means a declaration
   point is missing — stop and fix that, don't spread the tool. (Record: the
   settled rewording, archive/PLAN.md Phase 1 decision 2.)
2. **The GUI dispatches on types, never on tool identity.** The first
   `if tool == "crop"` is the beginning of the end. (Record: Exchange 1.)
3. **The executor substitutes silently only what an op's form proves, under the
   answer defined at the logical level.** Classification still never comes from
   a flag: the form you wrote is the authorization you granted, and anything a
   contributor can assert, a contributor can assert wrongly. Everything unproved
   is user-initiated, shown, and recorded. (Record: PAR-0005.)
4. **Equivalence is earned by measurement, never declared; rankings are measured,
   never estimated.** The harness runs verification at registration — contributors
   never write their own equivalence tests, because people write tests that pass.
   (Record: Exchange 8.)
5. **If it can change an output value it is a param**, and it lives in the
   pipeline file and the hash. **If it can only change presentation or speed it is
   a preference**, and it lives nowhere near them. Anything ambiguous is a param.
   (Record: Exchange 2.)
