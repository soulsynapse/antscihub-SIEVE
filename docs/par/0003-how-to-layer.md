# PAR-0003 — The how-to layer

Status: Accepted
Date: 2026-08-02 (accepted 2026-08-03)

## Outcomes

What this layer looks like working as intended: an agent or person
picking up a task finds the guide for it, follows it, and never opens
the PAR — and when the guide is wrong, the cost is one tier's walk
down the chain rather than being stranded, and the guide is repaired on
the spot by whoever hit it. The `how-to/` folder set stays closed under
the seams the PARs define, so a new folder means a new seam rather than
a judgment call. Guides are written at an altitude that does not churn,
and the layer goes quiet the way a rationale does — quiet because the
guidance holds, which the runner's logs are what let anyone believe.
Scripts appear inside guides only where automating a step actually
gains speed, so the scripts folder stays small enough to read.

## Context

The tiers before this record: `docs/ARCHITECTURE.md` holds the settled
what, `docs/par/` the why, `docs/archive/` the frozen record — and how
execution in the repo should respect the rationale was left to the
reader. In diataxis terms, tutorials arrive by convention from working
in the repo and PAR carries the explanation and the reference; the
how-to guides — task-oriented, "I need to do X now" — had no named
home, and the gap was already leaking: `README.md`'s mismatch how-to
and `AGENTS.md`'s Procedures are how-to fragments living where they
landed, which under PAR-0001's granularity rule is what "no named
system" looks like.

Primary: `SESSION-2026-08-02-runbook-gap.md` — the gap named
(Exchange 1); the name and the script heuristic (2); home and form,
where the scripts-only counterproposal lost (3); the debt's home, the
utility bar, the fallback chain (4); the marker-grain dispute and its
provenance (5); the conventions and the index (6).

## Decision

**Purpose and constraints.** The how-to layer closes the diataxis
loop: task-oriented guides codifying how agents and people improve,
use, and otherwise leverage the benefit each governed system exists to
provide. It is outside PAR — execution guidance folded into rationales
is the ballooning force arriving by another door. Its three
constraints: human-legible, agent-legible, trusted.

**Name.** How-to — the diataxis quadrant adopted directly, pattern-
matching deliberately; "runbook" is retired wholesale, no subgenre
survival. Frozen records keep the word; retirement bars reuse, not
history.

**Home.** A top-level `how-to/` folder, so the repo's organization is
visible from the root. Inside it: a scripts folder holding the layer's
meta-tooling, visibly not a domain; and domain folders split on the
major seams the PARs define — sieve work, repo work. Every how-to
lives in exactly one domain folder, so the folder set is closed under
the seams: new seam, new folder, proliferation arriving by derivation
rather than judgment.

**Form.** The default is the hand-written guide — not a script, and
not YAML-fronted: plain column-0 lines, the convention every record
class already uses. Guides are written defensively to resist
stagnation: broadly accurate at an altitude that does not churn,
rather than precise at one that does, with the fallback chain (below)
bounding what that costs. Found inaccurate, a how-to is cheaply
repaired on the spot — repair-on-contact, the mismatch discipline
applied to prose. Written to not need fixing. Within a guide, a step
is turned into a script when it crosses the utility bar: a repo task
standard enough that following a script gains speed. "Can be a script
→ should be a script" is defined by that bar — usefulness to
automate, a human-judged tipping point like friction confirmation and
template owing — never by bare capability (primary, Exchange 4). The
format of an individual how-to beyond these conventions is
deliberately TBD.

**The four-fold distillation, and the fallback chain.** A how-to
exists as the terminal tier of a walked chain: the session archive
made it into the PAR, the PAR into `ARCHITECTURE.md`, and
`ARCHITECTURE.md` points at the how-to. Its existence is the
confirmed validity of the implementation of one of the PAR's
outcomes — confirmed as walked once; staying valid is carried by
continuous update, and like a PAR the sign it is settled is that it
is quiet. Reading falls back by design: the how-to is good, you don't
need architecture; architecture is good, you don't need PAR; PAR is
good, you don't need session. The walking path gains a task-oriented
tier 0, read downward only until convinced, and a bad how-to degrades
to a walk down one tier, never to being stranded.

**The debt class.** A PAR outcome that explicitly enables something
is debt to be paid to `ARCHITECTURE.md` and the associated how-to
file. The debt is `ARCHITECTURE.md`'s to state — an `Owed:` marker
there, the separation of responsibility: the PAR holds why, and what
its outcomes are owed downstream is the synthesis surface's business.
It comes due when the PAR is mostly settled — a human judgment. Its
exercise beyond one simultaneous marker gates on marker rule v3
(Consequences).

**The index.** `how-to/` holds one generated file, the layer's read
surface — the automatic ledger's pattern applied again: it walks the
domain folders alphabetically, a pure function of the tree with no
hand-stated fields, never hand-edited, regenerated in the same commit
as the change it reflects, with a mismatch test so staleness reds. A
stated position hierarchy — logical nesting distinct from the folder
walk — is deferred, if ever wanted.

**The tests.** Every how-to is referenced from `ARCHITECTURE.md`, and
every such reference either resolves to an existing how-to or is
stated as an `Owed:` marker — under this record's debt class an
unresolved reference *is* the legal owed state, so the test's grammar
distinguishes debt from dangling; dangling in either direction
without a marker reds. Plus the index mismatch test.

**The runner — deferred, and load-bearing.** The end goal: structured
fields in a how-to (plain lines, when they arrive) from which a
tightly scoped agent session is spawned — the commands, how to run
them, the check — with no hand-crafted context. This is the layer's
verification story, not a convenience: a how-to is a program whose
interpreter is an agent, so drift reds as a failed run rather than
accumulating silently, and run logs are what disambiguate
quiet-under-use from quiet-from-neglect. Held in `DEFERRED.md` with
those stakes stated.

## Consequences

- The design debt (stamp `20260802T210348Z`) discharges with this
  rewrite: the design session it named has landed (primary, Exchanges
  2–6). `Proposed` alone carries the remaining acceptance-and-
  hardening debt, exactly as it does for PAR-0004 — restating that in
  a marker would double-state it.
- Acceptance amends `ARCHITECTURE.md` in the same commit (the roll-up
  discipline): the layer enters the synthesis, and the walking path's
  tier 0 is stated there.
- Marker rule v3 — the text surface admitting multiple markers per
  file, keyed `(path, stamp)` — gates the debt class's first real
  exercise and is ruled in conditionally ("fine as long as it all
  works", Exchange 6). Held in `DEFERRED.md` with its trigger; the
  one-marker grain it replaces is traced in the primary (Exchange 5)
  to an inference doctrinalized without a ruling.
- The existing fragments — `README.md`'s mismatch how-to,
  `AGENTS.md`'s Procedures — become the layer's first residents once
  this record governs; until then they stay put as inventory.
- The index generator is code work, planned from
  `PLAN-TOOL-CONTRACT.md`'s side, including whether it lands as a
  `sieve.debt` sibling or one shared regen entrypoint.
- PAR-0004's second challenge named this record's acceptance as its
  resolution point — whether the template convention folds into this
  layer. Taken at acceptance (2026-08-03): PAR-0004 stays its own
  record. Templates are a sub-system in service to this layer under
  PAR-0001's pointer criterion — exactly one place they live, exactly
  one way to cite them — and their derivation-guard rationale stands
  independent of any guide; folding later remains the cheap, lossless
  direction if the boundary ever leaks.

## Challenges

- **2026-08-02 — quiet-from-neglect is indistinguishable from
  quiet-under-use.** Raised by the agent at the design session,
  confirmed by Kendrick (primary, Exchanges 3–4): a PAR goes quiet
  when doubts stop arriving, but a how-to can go quiet because nobody
  uses it, and "settled when quiet" cannot tell the two apart from
  the file alone. Held, not breaking: the fallback chain bounds the
  cost of a stale guide to one tier's walk, repair-on-contact repairs
  on the next real use, and the runner's logs disambiguate when it
  exists. The doubt stands until the runner lands.
